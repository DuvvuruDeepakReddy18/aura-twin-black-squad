"""Clock-free routine-augmented v2 development with a fresh, sealed final cohort.

Protocol and model artifact are written before final patients are generated.
The archived v1 remains an unchanged comparator, never a source of final labels.
"""
from pathlib import Path
from datetime import datetime, timezone
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('LOKY_MAX_CPU_COUNT', '4')
import hashlib
import json
import platform
import time
import numpy as np
import sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.metrics import (mean_absolute_error, mean_squared_error, roc_auc_score,
                             average_precision_score, brier_score_loss,
                             precision_score, recall_score, f1_score, confusion_matrix)
from generate import generate_patient, display_patient, SEED
from train import features as legacy_features

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = [30, 60, 90, 120]
STATIC = ['age', 'bmi', 'hba1c', 'ldl', 'diabetesYears']
DYNAMIC = ['glucose', 'lag30', 'lag60', 'lag120', 'mean120', 'std120', 'slope30', 'slope60',
           'hrMean60', 'hrvMean60', 'steps60', 'steps24h', 'sleep24h']
RICH = ['lag15', 'lag45', 'lag90', 'lag180', 'lag240', 'lag360',
        'mean30', 'std30', 'mean60', 'std60', 'mean360', 'std360', 'mean24h', 'std24h',
        'min120', 'max120', 'q25_120', 'q75_120', 'q10_24h', 'q50_24h', 'q90_24h',
        'slope15', 'slope120', 'acceleration30',
        'priorDay30', 'priorDay60', 'priorDay90', 'priorDay120', 'priorDayMean120',
        'hrSlope30', 'hrvSlope30', 'hrMean120', 'hrvMean120', 'steps120', 'sleepLast6h']
FEATURES = STATIC + DYNAMIC + RICH
ROUTINES = [
    {'id':'reference', 'title':'Regular routine', 'params':{}},
    {'id':'late_meals_2h', 'title':'Meals delayed by 2 hours', 'params':{'meal_shift_hours':2.}},
    {'id':'late_meals_4h', 'title':'Meals delayed by 4 hours', 'params':{'meal_shift_hours':4.}},
    {'id':'irregular_meals', 'title':'Irregular meal timing', 'params':{'meal_jitter_hours':1.5}},
    {'id':'day_varying_skips', 'title':'Daily timing changes and skipped meals',
     'params':{'meal_jitter_hours':.7, 'day_shift_hours_sd':1.8, 'meal_skip_probability':.18}},
    {'id':'variable_routine', 'title':'Variable sleep, activity and meals',
     'params':{'meal_jitter_hours':1.2, 'day_shift_hours_sd':2.2, 'meal_skip_probability':.22, 'variable_routine':True}},
]
SPLITS = {'train':list(range(256)), 'selection':list(range(320,368)),
          'calibration':list(range(512,560)), 'test':list(range(1000,1080))}


def robust_features(patient, cursor):
    """All slices are inclusive of cursor; quantiles use numpy's linear interpolation.

    Short CGM windows include both endpoints (e.g. 25 points for 120 min).
    Interval sums/HR means use 12, 24, 72 or 288 five-minute intervals as named.
    Prior-day targets are observed t+h-1440 minutes, never future measurements.
    """
    p = patient['series']
    history = p[cursor-287:cursor+1]
    g = np.array([row['glucose'] for row in history], dtype=float)
    f = {name:float(patient['ehr'][name]) for name in STATIC}
    lag = lambda minutes: float(p[cursor-minutes//5]['glucose'])
    f.update(glucose=float(g[-1]), lag30=lag(30), lag60=lag(60), lag120=lag(120),
             mean120=float(g[-25:].mean()), std120=float(g[-25:].std()),
             slope30=(g[-1]-lag(30))/30, slope60=(g[-1]-lag(60))/60,
             hrMean60=float(np.mean([r['hr'] for r in history[-12:]])),
             hrvMean60=float(np.mean([r['hrv'] for r in history[-12:]])),
             steps60=sum(r['steps'] for r in history[-12:]),steps24h=sum(r['steps'] for r in history),
             sleep24h=sum(r['sleep'] for r in history)/12)
    for minutes in [15,45,90,180,240,360]:
        f[f'lag{minutes}'] = lag(minutes)
    for name, count in [('30',7),('60',13),('360',73),('24h',288)]:
        f[f'mean{name}'] = float(g[-count:].mean())
        f[f'std{name}'] = float(g[-count:].std())
    f.update(min120=float(g[-25:].min()),max120=float(g[-25:].max()),
             q25_120=float(np.quantile(g[-25:],.25)),q75_120=float(np.quantile(g[-25:],.75)),
             q10_24h=float(np.quantile(g,.1)),q50_24h=float(np.quantile(g,.5)),q90_24h=float(np.quantile(g,.9)),
             slope15=(g[-1]-lag(15))/15,slope120=(g[-1]-lag(120))/120,
             acceleration30=(g[-1]-lag(30))/30-(lag(30)-lag(60))/30,
             priorDayMean120=float(g[:24].mean()),
             hrSlope30=(p[cursor]['hr']-p[cursor-6]['hr'])/30,
             hrvSlope30=(p[cursor]['hrv']-p[cursor-6]['hrv'])/30,
             hrMean120=float(np.mean([r['hr'] for r in history[-24:]])),
             hrvMean120=float(np.mean([r['hrv'] for r in history[-24:]])),
             steps120=sum(r['steps'] for r in history[-24:]),sleepLast6h=sum(r['sleep'] for r in history[-72:])/12)
    for horizon in HORIZONS:
        f[f'priorDay{horizon}'] = lag(1440-horizon)
    return f


def feature_groups():
    groups = [
        ('Historical EHR','EHR',STATIC),
        ('Prior-day glucose pattern','Wearable',[n for n in FEATURES if n.startswith('priorDay')]),
        ('Heart rate and HRV','Wearable',[n for n in FEATURES if n.startswith(('hr','hrv'))]),
        ('Activity history','Wearable',[n for n in FEATURES if n.startswith('steps')]),
        ('Sleep history','Wearable',[n for n in FEATURES if n.startswith('sleep')]),
    ]
    assigned = {n for _,_,names in groups for n in names}
    groups.append(('Recent glucose trajectory','Wearable',[n for n in FEATURES if n not in assigned]))
    return [{'name':name,'source':source,'features':names} for name,source,names in groups]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, payload, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    # LF bytes are explicit, making the fingerprint independent of host newline conversion.
    path.write_bytes(json.dumps(payload, indent=None if compact else 2, allow_nan=False).encode('utf8'))


def dataset(ids, stride=12, retain=False):
    rows, targets, groups, routines, legacy, retained = [], [], [], [], [], {}
    for routine_index, routine in enumerate(ROUTINES):
        for pi in ids:
            patient = generate_patient(pi, **routine['params'])
            if retain and pi in ids[:8]:
                retained[(pi,routine_index)] = patient
            for cursor in range(288, len(patient['series'])-24, stride):
                f = robust_features(patient, cursor)
                rows.append([f[name] for name in FEATURES])
                targets.append([patient['series'][cursor+h//5]['glucose'] for h in HORIZONS])
                groups.append(pi)
                routines.append(routine_index)
                if retain:
                    lf = legacy_features(patient,cursor)
                    legacy.append(lf)
        print(f'  {routine["id"]}: {len(ids)} identities', flush=True)
    return {'x':np.asarray(rows),'y':np.asarray(targets),'groups':np.asarray(groups),
            'routines':np.asarray(routines),'legacy':legacy,'retained':retained}


def reg_metrics(y,pred):
    return {'mae':float(np.mean(np.abs(y[:,-1]-pred[:,-1]))),
            'rmse':float(np.sqrt(np.mean((y[:,-1]-pred[:,-1])**2)))}


def score(y,pred,prob,widths=None,threshold=.5):
    labels = y[:,-1]>=180
    flagged = prob>=threshold
    result = {**reg_metrics(y,pred),'auroc':float(roc_auc_score(labels,prob)),
              'averagePrecision':float(average_precision_score(labels,prob)),
              'brier':float(brier_score_loss(labels,prob)),
              'precision':float(precision_score(labels,flagged,zero_division=0)),
              'recall':float(recall_score(labels,flagged,zero_division=0)),
              'f1':float(f1_score(labels,flagged,zero_division=0)),
              'confusionMatrix':confusion_matrix(labels,flagged).tolist(),
              'positiveRate':float(labels.mean()),
              'byHorizon':[{'minutes':h,'mae':float(np.mean(np.abs(y[:,i]-pred[:,i]))),
                            'rmse':float(np.sqrt(np.mean((y[:,i]-pred[:,i])**2)))} for i,h in enumerate(HORIZONS)]}
    if widths is not None:
        result.update(intervalCoverage=float(np.mean(np.abs(y[:,-1]-pred[:,-1])<=widths[-1])),intervalMeanWidth=float(2*widths[-1]))
        for i,row in enumerate(result['byHorizon']):
            row['intervalCoverage']=float(np.mean(np.abs(y[:,i]-pred[:,i])<=widths[i]))
            row['intervalMeanWidth']=float(2*widths[i])
    return result


def bins(labels,prob):
    result=[]
    for lower in np.arange(0,1,.1):
        # Include probability 1.0 in the final bin (persistence is binary).
        mask=(prob>=lower)&((prob<=1.) if lower>=.9 else (prob<lower+.1))
        result.append({'lower':float(lower),'upper':float(lower+.1),'count':int(mask.sum()),
                       'predicted':float(prob[mask].mean()) if mask.any() else None,
                       'observed':float(labels[mask].mean()) if mask.any() else None})
    return result


def train_family(data,names,kind):
    indices=[FEATURES.index(n) for n in names]
    x=data['x'][:,indices]
    labels=data['y'][:,-1]>=180
    if kind=='linear':
        scaler=StandardScaler().fit(x)
        z=scaler.transform(x)
        reg=Ridge(alpha=50).fit(z,data['y'])
        classifier=LogisticRegression(C=.3,max_iter=1500,random_state=SEED).fit(z,labels)
        return {'kind':kind,'names':names,'indices':indices,'scaler':scaler,'reg':reg,'classifier':classifier}
    options=dict(max_iter=160,learning_rate=.07,max_leaf_nodes=31,min_samples_leaf=60,
                 l2_regularization=10.,max_bins=63,early_stopping=False,random_state=SEED)
    regressors=[HistGradientBoostingRegressor(loss='absolute_error',**options).fit(x,data['y'][:,i]) for i in range(4)]
    classifier=HistGradientBoostingClassifier(**options).fit(x,labels)
    return {'kind':kind,'names':names,'indices':indices,'reg':regressors,'classifier':classifier}


def predict_family(family,data):
    x=data['x'][:,family['indices']]
    if family['kind']=='linear':
        z=family['scaler'].transform(x)
        return family['reg'].predict(z),family['classifier'].decision_function(z)
    return np.column_stack([reg.predict(x) for reg in family['reg']]),family['classifier'].decision_function(x)


def sigmoid(logits):
    return 1/(1+np.exp(-np.clip(logits,-700,700)))


def export_tree(estimator):
    trees=[]
    for iteration in estimator._predictors:
        nodes=[]
        for node in iteration[0].nodes:
            nodes.append([-1 if node['is_leaf'] else int(node['feature_idx']),float(node['num_threshold']),
                          int(node['left']),int(node['right']),float(node['value']),bool(node['missing_go_to_left'])])
        trees.append({'nodes':nodes})
    return {'baseline':float(estimator._baseline_prediction[0,0]),'trees':trees}


def bootstrap(values, groups, iterations=1000):
    # Every identity has equal windows and routine weight; bootstrap identity means.
    means=np.array([np.mean(values[groups==pi]) for pi in np.unique(groups)])
    rng=np.random.default_rng(SEED+2000003)
    samples=rng.choice(means,(iterations,len(means)),replace=True).mean(axis=1)
    return np.quantile(samples,[.025,.975]).tolist()


def calibration_policy(labels,prob):
    eligible=[t for t in np.arange(.01,.951,.01) if recall_score(labels,prob>=t)>=.8]
    threshold=round(float(max(eligible)),2) if eligible else .01
    return {'threshold':threshold,'selection':'Highest 0.01-grid threshold achieving >=80% recall on separate calibration identities',
            'calibrationRecall':float(recall_score(labels,prob>=threshold)),
            'calibrationPrecision':float(precision_score(labels,prob>=threshold,zero_division=0))}


def main():
    started=time.time()
    data_dir=ROOT/'data'
    archive=data_dir/'baseline-v1'
    if not all((archive/name).exists() for name in ['model.json','metrics.json','parity.json','stress.json','patients.json']):
        raise RuntimeError('Archive exact v1 artifacts before running v2 training.')
    protocol={
        'version':'2.0.0','seed':SEED,'createdAt':timestamp(),'days':4,'historyMinutes':1440,
        'splits':{name:[f'SYN-{i+1:03d}' for i in ids] for name,ids in SPLITS.items()},
        'routines':ROUTINES,'weighting':'Equal routine and patient weight; all variants of an identity stay in its split.',
        'developmentStrideMinutes':60,'calibrationAndFinalStrideMinutes':30,
        'candidateModels':['clock-free StandardScaler+Ridge(alpha=50)/LogisticRegression(C=.3)',
                           'clock-free HistGradientBoosting:160 iterations,31 leaves,.07 learning rate,60 minimum leaf,10 L2,63 bins; absolute-error regression'],
        'regressionSelection':'Lowest selection-patient +120-minute MAE, averaged equally over six routines.',
        'classificationSelection':'Lowest uncalibrated selection-patient Brier score, reported with AUROC/AP/recall/precision; independent of regression selection.',
        'calibration':'Separate calibration identities only: Platt mapping, 90th absolute residual quantiles, highest .01-grid alert threshold with >=80% calibration recall.',
        'finalLock':'No final identity is generated until chosen models, preprocessing, calibration, interval widths and threshold are exported and SHA-256 recorded.',
        'finalInterpretation':'Fresh-identity generalization within a declared six-routine mixture. Routine families appear in training; this is not unseen-routine or clinical validation.',
        'features':FEATURES,'featureCount':len(FEATURES),'absoluteClockFeatures':False,
        'limitations':['The simulator and candidate features were designed after examining v1 failures; final IDs are fresh but model development is not independent of simulator design.',
                       'Previous-day horizon-aligned readings assume some recurrence; future unannounced meals remain unpredictable.',
                       'HR includes a contemporaneous synthetic meal response. No future meal annotation or latent simulator state is a predictor.']}
    write_json(data_dir/'robustness-protocol.json',protocol)
    events=[{'event':'protocol_locked','at':timestamp(),'finalPatientsGenerated':False}]
    print('Generating training data',flush=True)
    training=dataset(SPLITS['train'])
    print('Generating model-selection data',flush=True)
    selection=dataset(SPLITS['selection'])
    candidates={}
    selection_results={}
    for kind in ['linear','hist_gradient_boosting']:
        print(f'Fitting candidate {kind}',flush=True)
        family=train_family(training,FEATURES,kind)
        pred,logit=predict_family(family,selection)
        candidates[kind]=family
        selection_results[kind]=score(selection['y'],pred,sigmoid(logit))
        print(json.dumps({'candidate':kind,'mae':selection_results[kind]['mae'],'brier':selection_results[kind]['brier'],'auroc':selection_results[kind]['auroc']}),flush=True)
    reg_choice=min(selection_results,key=lambda name:selection_results[name]['mae'])
    clf_choice=min(selection_results,key=lambda name:selection_results[name]['brier'])
    # Runtime supports tree ensembles. A linear winner requires an explicit export extension,
    # never silently choosing a losing tree model or inspecting the final cohort.
    if reg_choice!='hist_gradient_boosting' or clf_choice!='hist_gradient_boosting':
        write_json(data_dir/'selection-results.json',{'models':selection_results,'regressionChoice':reg_choice,'classificationChoice':clf_choice})
        raise RuntimeError(f'Linear candidate selected ({reg_choice}/{clf_choice}); extend runtime export before final evaluation.')
    fused=candidates[reg_choice]
    events.append({'event':'models_selected','at':timestamp(),'regressionChoice':reg_choice,'classificationChoice':clf_choice,'finalPatientsGenerated':False})
    print('Fitting sensor-only and static-only ablations',flush=True)
    families={'fused':fused,'sensorOnly':train_family(training,DYNAMIC+RICH,reg_choice),
              'staticOnly':train_family(training,STATIC,reg_choice)}
    print('Generating separate calibration data',flush=True)
    calibration=dataset(SPLITS['calibration'],stride=6)
    calibrated={}
    for name,family in families.items():
        pred,logit=predict_family(family,calibration)
        calibrator=LogisticRegression(C=100,max_iter=1000).fit(logit.reshape(-1,1),calibration['y'][:,-1]>=180)
        prob=calibrator.predict_proba(logit.reshape(-1,1))[:,1]
        widths=np.quantile(np.abs(calibration['y']-pred),.9,axis=0,method='higher')
        calibrated[name]={'family':family,'calibrator':calibrator,'widths':widths,
                          'policy':calibration_policy(calibration['y'][:,-1]>=180,prob)}
    chosen=calibrated['fused']
    model={
        'modelVersion':'aura-synthetic-2.0.0','modelKind':'hist_gradient_boosting','seed':SEED,
        'algorithm':'Clock-free, routine-augmented histogram gradient boosting with separate identity-level selection and calibration',
        'featureNames':FEATURES,'horizons':HORIZONS,'mean':training['x'].mean(axis=0).tolist(),'scale':[1.]*len(FEATURES),
        'referenceValues':{n:float(v) for n,v in zip(FEATURES,np.median(training['x'],axis=0))},'featureGroups':feature_groups(),
        'regression':{'models':[export_tree(reg) for reg in fused['reg']]},
        'classification':{**export_tree(fused['classifier']),
                          'calibrationSlope':float(chosen['calibrator'].coef_[0,0]),'calibrationIntercept':float(chosen['calibrator'].intercept_[0])},
        'interval':{'nominalCoverage':.9,'halfWidths':chosen['widths'].tolist(),
                    'method':'90th absolute residual quantile on separate calibration identities pooled with equal routine weighting; descriptive marginal coverage'},
        'event':{'horizonMinutes':120,'thresholdMgDl':180,'operator':'>=','probabilityThreshold':.5},
        'alertPolicy':chosen['policy'],
        'limits':{'minHistoryPoints':288,'maxGlucoseStalenessMinutes':15,'maxMissingFraction':.2},
        'trainingProtocol':{'trainPatients':256,'selectionPatients':48,'calibrationPatients':48,'finalPatients':80,
                            'absoluteClockFeatures':False,'routines':[r['id'] for r in ROUTINES]},
        'disclaimer':'Synthetic research prototype. Not clinically validated and not for diagnosis or treatment.'}
    write_json(data_dir/'model.json',model,compact=True)
    frozen_bytes=(data_dir/'model.json').read_bytes()
    model_hash=hashlib.sha256(frozen_bytes).hexdigest()
    events.append({'event':'model_calibration_threshold_and_intervals_frozen','at':timestamp(),'modelSHA256':model_hash,'finalPatientsGenerated':False})
    write_json(data_dir/'selection-results.json',{'models':selection_results,'regressionChoice':reg_choice,'classificationChoice':clf_choice,
               'modelSHA256':model_hash,'calibration':{n:{'policy':v['policy'],'halfWidths':v['widths'].tolist()} for n,v in calibrated.items()},'events':events})
    write_json(data_dir/'training-audit.json',{'events':events})
    print(f'MODEL FROZEN {model_hash}; generating final identities for first time',flush=True)
    events.append({'event':'final_generation_started','at':timestamp(),'modelSHA256':model_hash,'finalPatientsGenerated':False})
    final=dataset(SPLITS['test'],stride=6,retain=True)
    predictions={}
    probabilities={}
    for name,item in calibrated.items():
        predictions[name],logit=predict_family(item['family'],final)
        probabilities[name]=item['calibrator'].predict_proba(logit.reshape(-1,1))[:,1]
    predictions['persistence']=np.tile(final['x'][:,FEATURES.index('glucose')][:,None],(1,4))
    probabilities['persistence']=(predictions['persistence'][:,-1]>=180).astype(float)
    legacy_model=json.loads((archive/'model.json').read_bytes())
    lx=np.array([[row[n] for n in legacy_model['featureNames']] for row in final['legacy']])
    lz=(lx-np.array(legacy_model['mean']))/np.array(legacy_model['scale'])
    predictions['legacyV1']=lz@np.array(legacy_model['regression']['coefficients']).T+legacy_model['regression']['intercepts']
    lc=legacy_model['classification']
    probabilities['legacyV1']=sigmoid((lz@lc['coefficients']+lc['intercept'])*lc['calibrationSlope']+lc['calibrationIntercept'])
    widths={n:item['widths'] for n,item in calibrated.items()}
    widths['legacyV1']=np.array(legacy_model['interval']['halfWidths'])
    final_metrics={}
    for name,pred in predictions.items():
        result=score(final['y'],pred,probabilities[name],widths.get(name))
        threshold=calibrated[name]['policy']['threshold'] if name in calibrated else legacy_model['alertPolicy']['threshold'] if name=='legacyV1' else .5
        flagged=probabilities[name]>=threshold
        labels=final['y'][:,-1]>=180
        result['alertPolicy']={**(calibrated[name]['policy'] if name in calibrated else {'threshold':threshold}),
                               'testPrecision':float(precision_score(labels,flagged,zero_division=0)),
                               'testRecall':float(recall_score(labels,flagged)),
                               'testF1':float(f1_score(labels,flagged)),
                               'testConfusionMatrix':confusion_matrix(labels,flagged).tolist()}
        result['calibration']=bins(labels,probabilities[name])
        result['maePatientBootstrap95CI']=bootstrap(np.abs(final['y'][:,-1]-pred[:,-1]),final['groups'])
        final_metrics[name]=result
    routine_reports=[]
    for ri,routine in enumerate(ROUTINES):
        mask=final['routines']==ri
        case_models={}
        for name,pred in predictions.items():
            threshold=calibrated[name]['policy']['threshold'] if name in calibrated else legacy_model['alertPolicy']['threshold'] if name=='legacyV1' else .5
            case_models[name]=score(final['y'][mask],pred[mask],probabilities[name][mask],widths.get(name),threshold)
            case_models[name]['threshold']=threshold
            case_models[name]['maePatientBootstrap95CI']=bootstrap(np.abs(final['y'][mask,-1]-pred[mask,-1]),final['groups'][mask])
        paired={}
        for comparator in ['legacyV1','sensorOnly','persistence']:
            differences=np.abs(final['y'][mask,-1]-predictions['fused'][mask,-1])-np.abs(final['y'][mask,-1]-predictions[comparator][mask,-1])
            paired[comparator]={'meanDifference':float(differences.mean()),'patientBootstrap95CI':bootstrap(differences,final['groups'][mask]),
                                'direction':'v2 fused minus comparator MAE; negative favors v2'}
        routine_reports.append({'id':routine['id'],'title':routine['title'],'parameters':routine['params'],
                                'patients':len(SPLITS['test']),'windows':int(mask.sum()),'models':case_models,'pairedDifferences':paired})
    events.append({'event':'final_evaluation_completed','at':timestamp(),'modelSHA256':model_hash,'finalPatientsGenerated':True})
    if (data_dir/'model.json').read_bytes()!=frozen_bytes:
        raise AssertionError('Frozen model artifact changed after final outcomes were generated.')
    metrics={'schemaVersion':2,'seed':SEED,'syntheticOnly':True,'modelVersion':model['modelVersion'],'modelSHA256':model_hash,
             'modelKind':model['modelKind'],'featureSet':'clock_free_v2',
             'target':'CGM glucose >=180 mg/dL at exactly +120 minutes; not any excursion within two hours',
             'cohort':{'patients':432,'days':4,'routines':6,'cadenceMinutes':5,'windowStrideMinutes':30,
                       'trainPatients':256,'validationPatients':96,'selectionPatients':48,'calibrationPatients':48,'testPatients':80,
                       'windows':{'train':len(training['y']),'validation':len(selection['y'])+len(calibration['y']),'selection':len(selection['y']),'calibration':len(calibration['y']),'test':len(final['y'])},
                       'positiveRate':{'train':float((training['y'][:,-1]>=180).mean()),'validation':float(np.concatenate([selection['y'][:,-1],calibration['y'][:,-1]]) .__ge__(180).mean()),'test':float((final['y'][:,-1]>=180).mean())}},
             'splits':{'train':protocol['splits']['train'],'validation':protocol['splits']['selection']+protocol['splits']['calibration'],'test':protocol['splits']['test']},
             'developmentSplits':{'selection':protocol['splits']['selection'],'calibration':protocol['splits']['calibration']},
             'models':final_metrics,'probabilityThreshold':.5,'aggregateWeighting':'Equal weight across six declared routines and 80 fresh identities.',
             'environment':{'python':platform.python_version(),'numpy':np.__version__,'scikitLearn':sklearn.__version__},
             'limitations':protocol['limitations']+['All outcomes are synthetic; no external or clinical accuracy is demonstrated.',
               'Routine families are present in augmented training. Fresh identities are held out; these are not unseen routine families.',
               'Repeated windows and routine variants are correlated; uncertainty resamples identities, keeping variants paired.',
               'The calibration residual band is marginal and can be wider than v1; report width and per-routine coverage together.',
               'The event threshold trades recall for false positives. Future unpredictable meals set a ceiling on advance prediction.',
               'Counterfactual controls remain illustrative arithmetic; no treatment effects are learned.']}
    aggregate_differences={}
    for comparator in ['legacyV1','sensorOnly','persistence']:
        diff=np.abs(final['y'][:,-1]-predictions['fused'][:,-1])-np.abs(final['y'][:,-1]-predictions[comparator][:,-1])
        aggregate_differences[comparator]={'meanDifference':float(diff.mean()),'patientBootstrap95CI':bootstrap(diff,final['groups']),
                                         'direction':'v2 fused minus comparator MAE; negative favors v2'}
    robustness={'schemaVersion':2,'modelVersion':model['modelVersion'],'modelSHA256':model_hash,'syntheticOnly':True,
                'protocol':protocol,'selection':selection_results,'events':events,
                'aggregate':{'models':final_metrics,'pairedDifferences':aggregate_differences,'patients':80,'windows':len(final['y'])},
                'cases':routine_reports,'limitations':metrics['limitations']}
    stress={'schemaVersion':2,'modelVersion':model['modelVersion'],'modelSHA256':model_hash,'syntheticOnly':True,
            'protocol':'Frozen v2 model, calibration, widths and threshold; 80 fresh final identities across six declared routines also represented in training. Equal routine weighting. This is fresh-identity evaluation, not unseen-routine validation.',
            'target':metrics['target'],'alertThreshold':model['alertPolicy']['threshold'],'testPatientIds':protocol['splits']['test'],
            'cases':[{'id':c['id'],'title':c['title'],'patients':c['patients'],'windows':c['windows'],**c['models']['fused'],
                      'persistenceMae':c['models']['persistence']['mae'],'legacyMae':c['models']['legacyV1']['mae']} for c in routine_reports],
            'limitations':metrics['limitations']}
    # Representative default windows are pre-fixed, never chosen for favorable final outcomes.
    display=[]
    parity=[]
    for di,pi in enumerate(SPLITS['test'][:8]):
        ri=[0,1,2,3,4,5,4,5][di]
        patient=display_patient(final['retained'][(pi,ri)],di)
        patient['defaultCursor']=810+di*12
        patient['routine']={'id':ROUTINES[ri]['id'],'label':ROUTINES[ri]['title']}
        patient['replayNote']='Fresh final-cohort synthetic identity; routine and default cutoff fixed without selecting favorable prediction outcomes.'
        display.append(patient)
        for cursor in [patient['defaultCursor'],patient['defaultCursor']-30]:
            f=robust_features(patient,cursor)
            x=np.array([[f[n] for n in FEATURES]])
            pred=np.array([reg.predict(x)[0] for reg in fused['reg']])
            logit=fused['classifier'].decision_function(x)
            risk=chosen['calibrator'].predict_proba(logit.reshape(-1,1))[0,1]
            parity.append({'id':patient['id'],'cursor':cursor,'routine':ROUTINES[ri]['id'],'features':f,'forecast':pred.tolist(),'risk':float(risk)})
    for name,payload in [('metrics.json',metrics),('robustness.json',robustness),('stress.json',stress),('patients.json',display),('parity.json',parity),('training-audit.json',{'events':events})]:
        write_json(data_dir/name,payload,compact=name=='patients.json')
    print(json.dumps({'modelSHA256':model_hash,'selection':{'regression':reg_choice,'classification':clf_choice},
                     'aggregate':{n:{k:v[k] for k in ['mae','auroc','brier','intervalCoverage'] if k in v} for n,v in final_metrics.items()},
                     'alertPolicy':final_metrics['fused']['alertPolicy'],'elapsedSeconds':round(time.time()-started)},indent=2),flush=True)
    print('PER ROUTINE',flush=True)
    for c in routine_reports:
        print(c['id'], {n:round(v['mae'],3) for n,v in c['models'].items()},flush=True)


if __name__=='__main__':
    main()

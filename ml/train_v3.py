"""v3 development: unchanged simulator, richer observed history, frozen final gate.

The develop command never generates final IDs or the held-out combination routine.
Artifacts remain in data/candidate-v3 until the final frozen evaluation is approved.
"""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('LOKY_MAX_CPU_COUNT', '4')
import argparse
import hashlib
import json
import time
import pickle
import inspect
import platform
import sklearn
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score, brier_score_loss
from generate import generate_patient, display_patient, SEED
from train_robust import (robust_features, FEATURES as V2_FEATURES, ROUTINES, HORIZONS,
                          STATIC, score, bootstrap, bins, timestamp, write_json, export_tree)
from stress_test import predict_export

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parents[1]/'work'/'v3'
OUT = ROOT/'data'/'candidate-v3'
EXTRA_LAGS = [5,10,20,25,35,40,50,75,105,150,210,300]
EXTRA = [f'lag{n}' for n in EXTRA_LAGS] + [
    'olsSlope30','olsSlope60','olsSlope120','olsSlope240',
    'meanDelta30_60','meanDelta60_120','riseFraction30','riseFraction60','riseFraction120',
    'fallFraction60','meanAbsChange30','meanAbsChange60','meanAbsChange120',
    'maxRise30','maxFall30','range30','range60','minutesSinceMax120','minutesSinceMin120',
    'glucoseAboveQ10','glucoseAboveMedian','excessMean120','timeAbove180_120','timeAbove140_120',
    'hrMean15','hrMean30','hrvMean15','hrvMean30','hrMean24h','hrvMean24h','hrStd24h','hrvStd24h',
    'hrZ30','hrvZ30','steps15','steps30','sleepLast60','minutesSinceWake','minutesSinceActivity',
    'awakeRestingHr24h','awakeRestingHr30','hrAboveResting30','glucoseMinusPriorDay120',
]
FEATURES = V2_FEATURES + EXTRA
SPLITS = {'train':list(range(768)), 'selection':list(range(1200,1280)),
          'calibration':list(range(1400,1496)), 'test':list(range(2000,2120))}
UNSEEN = {'id':'unseen_combination','title':'Held-out combination of shifted and variable routines',
          'params':{'meal_shift_hours':3.,'meal_jitter_hours':1.,'day_shift_hours_sd':1.4,
                    'meal_skip_probability':.25,'variable_routine':True}}
CANDIDATES = [
    {'id':'rich_balanced','max_iter':300,'max_leaf_nodes':31,'min_samples_leaf':80,
     'learning_rate':.05,'l2_regularization':15.,'irregularWeight':2.},
    {'id':'rich_deep','max_iter':360,'max_leaf_nodes':63,'min_samples_leaf':100,
     'learning_rate':.05,'l2_regularization':20.,'irregularWeight':2.},
    {'id':'rich_equal','max_iter':300,'max_leaf_nodes':31,'min_samples_leaf':80,
     'learning_rate':.05,'l2_regularization':15.,'irregularWeight':1.},
]


def trajectory_features(patient,cursor):
    """Raw, prefix-only features. Definitions deliberately do not use routine labels."""
    f=robust_features(patient,cursor)
    history=patient['series'][cursor-287:cursor+1]
    g=np.array([r['glucose'] for r in history],dtype=float)
    hr=np.array([r['hr'] for r in history],dtype=float)
    hrv=np.array([r['hrv'] for r in history],dtype=float)
    steps=np.array([r['steps'] for r in history],dtype=float)
    sleep=np.array([r['sleep'] for r in history],dtype=float)
    for minutes in EXTRA_LAGS:
        f[f'lag{minutes}']=float(g[-1-minutes//5])
    for minutes in [30,60,120,240]:
        values=g[-(minutes//5+1):]
        x=np.arange(len(values))*5.
        x-=x.mean()
        f[f'olsSlope{minutes}']=float(np.sum(x*(values-values.mean()))/np.sum(x*x))
    f.update(meanDelta30_60=f['mean30']-f['mean60'],meanDelta60_120=f['mean60']-f['mean120'])
    for minutes in [30,60,120]:
        changes=np.diff(g[-(minutes//5+1):])
        f[f'riseFraction{minutes}']=float(np.mean(changes>0))
        f[f'meanAbsChange{minutes}']=float(np.mean(np.abs(changes)))
    f.update(fallFraction60=float(np.mean(np.diff(g[-13:])<0)),
             maxRise30=float(np.max(np.diff(g[-7:]))),maxFall30=float(np.min(np.diff(g[-7:]))),
             range30=float(np.ptp(g[-7:])),range60=float(np.ptp(g[-13:])),
             minutesSinceMax120=float(np.argmax(g[-25:][::-1])*5),
             minutesSinceMin120=float(np.argmin(g[-25:][::-1])*5),
             glucoseAboveQ10=f['glucose']-f['q10_24h'],glucoseAboveMedian=f['glucose']-f['q50_24h'],
             excessMean120=float(np.maximum(0,g[-25:]-f['q10_24h']).mean()),
             timeAbove180_120=float(np.mean(g[-25:]>=180)),timeAbove140_120=float(np.mean(g[-25:]>=140)))
    for name,values in [('hr',hr),('hrv',hrv)]:
        f[f'{name}Mean15']=float(values[-3:].mean())
        f[f'{name}Mean30']=float(values[-6:].mean())
        f[f'{name}Mean24h']=float(values.mean())
        f[f'{name}Std24h']=float(values.std())
        f[f'{name}Z30']=(f[f'{name}Mean30']-f[f'{name}Mean24h'])/max(1.,f[f'{name}Std24h'])
    wake_indices=np.where((sleep[:-1]>0)&(sleep[1:]==0))[0]+1
    activity_indices=np.where(steps>=50)[0]
    resting=(sleep==0)&(steps<20)
    f.update(steps15=float(steps[-3:].sum()),steps30=float(steps[-6:].sum()),
             sleepLast60=float(sleep[-12:].sum()/12),
             minutesSinceWake=float((287-wake_indices[-1])*5) if len(wake_indices) else 1440.,
             minutesSinceActivity=float((287-activity_indices[-1])*5) if len(activity_indices) else 1440.,
             awakeRestingHr24h=float(hr[resting].mean()) if resting.any() else float(hr.mean()),
             awakeRestingHr30=float(hr[-6:][resting[-6:]].mean()) if resting[-6:].any() else float(hr[-6:].mean()),
             glucoseMinusPriorDay120=f['glucose']-f['priorDay120'])
    f['hrAboveResting30']=f['awakeRestingHr30']-f['awakeRestingHr24h']
    return f


def dataset(ids,routines=ROUTINES,stride=12,retain=False):
    rows,targets,groups,regimes,retained=[],[],[],[],{}
    for ri,routine in enumerate(routines):
        for pi in ids:
            patient=generate_patient(pi,**routine['params'])
            if retain and pi in ids[:8]:
                retained[(pi,ri)]=patient
            for cursor in range(288,len(patient['series'])-24,stride):
                f=trajectory_features(patient,cursor)
                rows.append([f[n] for n in FEATURES])
                targets.append([patient['series'][cursor+h//5]['glucose'] for h in HORIZONS])
                groups.append(pi);regimes.append(ri)
        print(f"  {routine['id']}: {len(ids)} identities",flush=True)
    return {'x':np.asarray(rows),'y':np.asarray(targets),'groups':np.asarray(groups),
            'routines':np.asarray(regimes),'retained':retained}


def cached_dataset(name,ids,stride):
    WORK.mkdir(parents=True,exist_ok=True)
    file=WORK/f'{name}.npz'
    provenance={'ids':ids,'stride':stride,'routines':ROUTINES,'features':FEATURES,'extraLags':EXTRA_LAGS,
                'trajectorySource':inspect.getsource(trajectory_features),'baseSource':inspect.getsource(robust_features),
                'generatorSHA256':hashlib.sha256((ROOT/'ml'/'generate.py').read_bytes()).hexdigest()}
    signature=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode('utf8')).hexdigest()
    if file.exists():
        print(f'Loading cached {name}',flush=True)
        cached=dict(np.load(file))
        if 'signature' not in cached or str(cached.pop('signature').item())!=signature:
            raise RuntimeError(f'{name} cache provenance is missing or changed; use a fresh --work-dir.')
        expected_windows=len(range(288,4*288-24,stride))*len(ids)*len(ROUTINES)
        if cached['x'].shape!=(expected_windows,len(FEATURES)) or set(cached['groups'])!=set(ids):
            raise RuntimeError(f'{name} cache does not match the declared identities/features; use a fresh --work-dir.')
        return cached
    print(f'Generating {name}',flush=True)
    data=dataset(ids,stride=stride)
    data.pop('retained')
    np.savez(file,signature=np.array(signature),**data)
    return data


def sigmoid(raw):
    return 1/(1+np.exp(-np.clip(raw,-700,700)))


def errors(labels,probability,threshold,mask):
    tn,fp,fn,tp=confusion_matrix(labels[mask],probability[mask]>=threshold,labels=[False,True]).ravel()
    return {'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp),
            'recall':float(tp/max(1,tp+fn)),'precision':float(tp/max(1,tp+fp))}


def choose_policy(labels,probability,baseline_probability,routines):
    """One global threshold; irregular labels are grouping, never predictor inputs.

    Minimize worst FP/FN count ratio to frozen v2 across all windows, irregular
    windows, and the variable-routine case itself. A max ratio <1 means
    simultaneous reduction in all six development comparisons.
    """
    masks={'all':np.ones(len(labels),dtype=bool),'irregular':routines>=3,'variableRoutine':routines==5}
    v2=json.loads((ROOT/'data'/'baseline-v2'/'model.json').read_bytes())
    references={name:errors(labels,baseline_probability,v2['alertPolicy']['threshold'],mask) for name,mask in masks.items()}
    candidates=[]
    for threshold in np.linspace(.01,.80,317):
        outcomes={name:errors(labels,probability,float(threshold),mask) for name,mask in masks.items()}
        ratios=[outcomes[name][kind]/max(1,references[name][kind]) for name in masks for kind in ['fp','fn']]
        candidates.append((max(ratios),float(np.mean(ratios)),float(threshold),outcomes))
    worst,mean,threshold,outcomes=min(candidates,key=lambda item:(item[0],item[1]))
    return {'threshold':threshold,'selection':'One global threshold minimizing the worst FP/FN count ratio to frozen v2 across all six regimes, pooled irregular regimes, and variable-routine windows; 0.0025 grid, calibration identities only for deployment',
            'worstCountRatioToV2':worst,'meanCountRatioToV2':mean,'simultaneouslyLower':worst<1,
            'counts':outcomes,'v2Counts':references,'v2Threshold':v2['alertPolicy']['threshold']}


def protocol():
    return {'version':'3.0.0','createdAt':timestamp(),'seed':SEED,'days':4,
            'splits':{name:[f'SYN-{i+1:03d}' for i in ids] for name,ids in SPLITS.items()},
            'routines':ROUTINES,'heldOutCombination':UNSEEN,'features':FEATURES,'featureCount':len(FEATURES),
            'generatorUnchanged':True,'generatorSHA256':hashlib.sha256((ROOT/'ml'/'generate.py').read_bytes()).hexdigest(),
            'developmentStrideMinutes':60,'trainingStrideMinutes':60,'selectionStrideMinutes':30,'calibrationAndFinalStrideMinutes':30,
            'candidates':CANDIDATES,
            'classificationSelection':'Minimize worst selection FP/FN ratio to frozen v2 across overall, pooled irregular, and variable-routine windows, using one scalar threshold; tie-break average ratio then Brier score.',
            'regressionSelection':'Lowest selection +120-minute MAE across the same candidates; all four horizons use that candidate configuration.',
            'calibration':'Separate calibration identities: Platt probability map, global minimax FP/FN-ratio threshold, nominal90% residual bands. No routine label supplied to inference.',
            'finalLock':'Final2000..2119 and the held-out combination are not generated until all estimator/calibration/threshold/interval bytes are frozen and hashed.',
            'primaryAggregate':'The six familiar routine families; held-out parameter combination is reported separately.',
            'limitations':['All outcomes remain synthetic. Simultaneous FP/FN reductions are sought, not guaranteed on fresh patients.',
                           'The seven-regime aggregate includes six training families and one held-out parameter combination, not a new physiological simulator.',
                           'Unannounced future meals remain partly unpredictable from current observations.']}


def candidate_options(configuration):
    options={k:v for k,v in configuration.items() if k not in ['id','irregularWeight']}
    options.update(max_bins=127,early_stopping=False,random_state=SEED)
    return options


def feature_groups():
    groups=[('Historical EHR','EHR',STATIC),
            ('Prior-day glucose pattern','Wearable',[n for n in FEATURES if n.startswith('priorDay') or n=='glucoseMinusPriorDay120']),
            ('Heart rate and HRV','Wearable',[n for n in FEATURES if n.startswith(('hr','awakeResting'))]),
            ('Activity history','Wearable',[n for n in FEATURES if n.startswith('steps') or n=='minutesSinceActivity']),
            ('Sleep history','Wearable',[n for n in FEATURES if n.startswith('sleep') or n=='minutesSinceWake'])]
    used={n for _,_,names in groups for n in names}
    groups.append(('Observed glucose trajectory','Wearable',[n for n in FEATURES if n not in used]))
    return [{'name':name,'source':source,'features':names} for name,source,names in groups]


def freeze():
    """Fit remaining horizons/ablations and calibrate, then stop BEFORE final data."""
    if (OUT/'freeze.json').exists():
        raise RuntimeError('Candidate already frozen. Do not overwrite a frozen candidate.')
    selection=json.loads((OUT/'development-selection.json').read_text())
    development=json.loads((OUT/'development-results.json').read_text())
    p=protocol()
    write_json(OUT/'protocol.json',p)
    configuration={c['id']:c for c in CANDIDATES}
    rc=configuration[selection['regressionChoice']]
    cc=configuration[selection['classificationChoice']]
    training=cached_dataset('train',SPLITS['train'],12)
    calibration=cached_dataset('calibration',SPLITS['calibration'],6)
    with (WORK/f"{rc['id']}.pkl").open('rb') as handle: reg_selected=pickle.load(handle)
    with (WORK/f"{cc['id']}.pkl").open('rb') as handle: clf_selected=pickle.load(handle)
    for fit,configuration in [(reg_selected,rc),(clf_selected,cc)]:
        if fit.get('configuration')!=configuration or fit.get('featureNames')!=FEATURES:
            raise RuntimeError('Selected estimator cache differs from the declared configuration/features; use a fresh --work-dir.')
    reg_weights=np.where(training['routines']>=3,rc['irregularWeight'],1.)
    clf_weights=np.where(training['routines']>=3,cc['irregularWeight'],1.)
    families={}
    for name,names in [('fused',FEATURES),('sensorOnly',[n for n in FEATURES if n not in STATIC]),('staticOnly',STATIC)]:
        print(f'Fitting/calibrating {name}',flush=True)
        indices=[FEATURES.index(n) for n in names]
        train_x=training['x'][:,indices]
        regressors=[]
        for hi,horizon in enumerate(HORIZONS):
            if name=='fused' and horizon==120:
                reg=reg_selected['regressor120']
            else:
                reg=HistGradientBoostingRegressor(loss='absolute_error',**candidate_options(rc)).fit(train_x,training['y'][:,hi],sample_weight=reg_weights)
            regressors.append(reg)
        classifier=(clf_selected['classifier'] if name=='fused' else HistGradientBoostingClassifier(**candidate_options(cc)).fit(train_x,training['y'][:,-1]>=180,sample_weight=clf_weights))
        cx=calibration['x'][:,indices]
        predictions=np.column_stack([reg.predict(cx) for reg in regressors])
        raw=classifier.decision_function(cx)
        platt=LogisticRegression(C=100,max_iter=1500).fit(raw.reshape(-1,1),calibration['y'][:,-1]>=180)
        prob=platt.predict_proba(raw.reshape(-1,1))[:,1]
        baseline=json.loads((ROOT/'data'/'baseline-v2'/'model.json').read_bytes())
        _,baseline_prob=predict_export(baseline,calibration['x'][:,:len(V2_FEATURES)])
        policy=choose_policy(calibration['y'][:,-1]>=180,prob,baseline_prob,calibration['routines'])
        policy.update(calibrationRecall=policy['counts']['all']['recall'],calibrationPrecision=policy['counts']['all']['precision'])
        widths=np.quantile(np.abs(calibration['y']-predictions),.9,axis=0,method='higher')
        families[name]={'names':names,'indices':indices,'regressors':regressors,'classifier':classifier,
                        'calibrator':platt,'widths':widths,'policy':policy}
        print(json.dumps({'family':name,'calibrationPolicy':policy}),flush=True)
    chosen=families['fused']
    model={'modelVersion':'aura-synthetic-3.0.0','modelKind':'hist_gradient_boosting','featureSet':'trajectory_v3','seed':SEED,
           'algorithm':'Routine-augmented histogram gradient boosting with observed trajectory features and calibration-selected global decision policy',
           'featureNames':FEATURES,'horizons':HORIZONS,'mean':training['x'].mean(axis=0).tolist(),'scale':[1.]*len(FEATURES),
           'referenceValues':{n:float(v) for n,v in zip(FEATURES,np.median(training['x'],axis=0))},'featureGroups':feature_groups(),
           'regression':{'models':[export_tree(reg) for reg in chosen['regressors']]},
           'classification':{**export_tree(chosen['classifier']),'calibrationSlope':float(chosen['calibrator'].coef_[0,0]),'calibrationIntercept':float(chosen['calibrator'].intercept_[0])},
           'interval':{'nominalCoverage':.9,'halfWidths':chosen['widths'].tolist(),'method':'90th absolute residual quantile on separate calibration identities; descriptive marginal coverage'},
           'event':{'horizonMinutes':120,'thresholdMgDl':180,'operator':'>=','probabilityThreshold':.5},
           'alertPolicy':chosen['policy'],'limits':{'minHistoryPoints':288,'maxGlucoseStalenessMinutes':15,'maxMissingFraction':.2},
           'trainingProtocol':{'trainPatients':768,'selectionPatients':80,'calibrationPatients':96,'finalPatients':120,
                               'absoluteClockFeatures':False,'routines':[r['id'] for r in ROUTINES],
                               'regressionConfiguration':rc,'classificationConfiguration':cc},
           'disclaimer':'Synthetic research prototype. Not clinically validated and not for diagnosis or treatment.'}
    write_json(OUT/'model.json',model,compact=True)
    model_hash=hashlib.sha256((OUT/'model.json').read_bytes()).hexdigest()
    frozen={'families':families,'protocol':p,'development':development,'selection':selection,'modelSHA256':model_hash}
    with (WORK/'frozen.pkl').open('wb') as handle: pickle.dump(frozen,handle)
    record={'at':timestamp(),'modelSHA256':model_hash,'modelVersion':model['modelVersion'],'finalGenerated':False,
            'selectedConfigurations':selection,'policy':chosen['policy'],'protocolSHA256':hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest()}
    write_json(OUT/'freeze.json',record)
    # Runtime parity can be checked before touching fresh final IDs. These are old,
    # development-known v2 display prefixes, and are labeled as such in the fixture.
    development_patients=json.loads((ROOT/'data'/'baseline-v2'/'patients.json').read_bytes())
    parity=[]
    for patient in development_patients:
        for cursor in [patient['defaultCursor'],patient['defaultCursor']-30]:
            f=trajectory_features(patient,cursor);x=np.array([[f[n] for n in FEATURES]])
            pred=[float(reg.predict(x)[0]) for reg in chosen['regressors']]
            raw=chosen['classifier'].decision_function(x)
            risk=float(chosen['calibrator'].predict_proba(raw.reshape(-1,1))[0,1])
            parity.append({'id':patient['id'],'cursor':cursor,'features':f,'forecast':pred,'risk':risk,
                           'fixturePurpose':'Runtime parity on development-known v2 display patients; not final evaluation'})
    write_json(OUT/'development-patients.json',development_patients,compact=True)
    write_json(OUT/'development-parity.json',parity)
    print('FROZEN; final IDs and held-out combination still ungenerated',flush=True)
    print(json.dumps(record),flush=True)


def decision_differences(labels,current_prob,baseline_prob,current_threshold,baseline_threshold,groups):
    """Paired identity bootstrap; correlated routine variants remain together."""
    ids=np.unique(groups)
    def counts(prob,threshold):
        return np.array([confusion_matrix(labels[groups==pi],prob[groups==pi]>=threshold,labels=[False,True]).ravel() for pi in ids])
    current,baseline=counts(current_prob,current_threshold),counts(baseline_prob,baseline_threshold)
    rng=np.random.default_rng(SEED+3000007)
    draws=rng.integers(0,len(ids),size=(1000,len(ids)))
    a,b=current[draws].sum(axis=1),baseline[draws].sum(axis=1)
    at,bt=current.sum(axis=0),baseline.sum(axis=0)
    values={'falsePositiveWindows':(float(at[1]-bt[1]),a[:,1]-b[:,1]),
            'falseNegativeWindows':(float(at[2]-bt[2]),a[:,2]-b[:,2]),
            'recall':(float(at[3]/max(1,at[2]+at[3])-bt[3]/max(1,bt[2]+bt[3])),
                      a[:,3]/np.maximum(1,a[:,2]+a[:,3])-b[:,3]/np.maximum(1,b[:,2]+b[:,3])),
            'precision':(float(at[3]/max(1,at[1]+at[3])-bt[3]/max(1,bt[1]+bt[3])),
                         a[:,3]/np.maximum(1,a[:,1]+a[:,3])-b[:,3]/np.maximum(1,b[:,1]+b[:,3]))}
    return {name:{'difference':value,'patientBootstrap95CI':np.quantile(samples,[.025,.975]).tolist(),
                   'direction':'v3 minus frozen v2; negative favors v3 for error counts, positive favors v3 for recall/precision'} for name,(value,samples) in values.items()}


def evaluate():
    """Fresh final evaluation after an explicit freeze gate; no refitting."""
    if (OUT/'evaluation-lock.json').exists():
        raise RuntimeError('Final evaluation has already been started. Preserve this run; do not retune and rerun final patients.')
    freeze_record=json.loads((OUT/'freeze.json').read_text())
    model_bytes=(OUT/'model.json').read_bytes()
    model=json.loads(model_bytes)
    model_hash=hashlib.sha256(model_bytes).hexdigest()
    if model_hash!=freeze_record['modelSHA256']:
        raise RuntimeError('Frozen model bytes changed.')
    if hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest()!=freeze_record['protocolSHA256']:
        raise RuntimeError('Frozen protocol changed.')
    with (WORK/'frozen.pkl').open('rb') as handle: frozen=pickle.load(handle)
    # The separately fingerprinted protocol is authoritative, including any
    # explicitly recorded pre-evaluation metadata clarification.
    p=json.loads((OUT/'protocol.json').read_text())
    if hashlib.sha256((ROOT/'ml'/'generate.py').read_bytes()).hexdigest()!=p['generatorSHA256']:
        raise RuntimeError('Generator changed after development freeze.')
    if frozen['modelSHA256']!=model_hash:
        raise RuntimeError('Estimator cache is not the frozen candidate.')
    events=[{'event':'model_calibration_threshold_and_intervals_frozen','at':freeze_record['at'],'modelSHA256':model_hash,'finalPatientsGenerated':False},
            {'event':'final_generation_started','at':timestamp(),'modelSHA256':model_hash,'finalPatientsGenerated':False}]
    write_json(OUT/'evaluation-lock.json',{'events':events})
    all_routines=ROUTINES+[UNSEEN]
    print('First generation of fresh final identities and held-out combination',flush=True)
    final=dataset(SPLITS['test'],routines=all_routines,stride=6,retain=True)
    predictions,probabilities,widths,policies={},{},{},{}
    for name,family in frozen['families'].items():
        x=final['x'][:,family['indices']]
        predictions[name]=np.column_stack([reg.predict(x) for reg in family['regressors']])
        raw=family['classifier'].decision_function(x)
        probabilities[name]=family['calibrator'].predict_proba(raw.reshape(-1,1))[:,1]
        widths[name]=family['widths'];policies[name]=family['policy']
    v2=json.loads((ROOT/'data'/'baseline-v2'/'model.json').read_bytes())
    predictions['legacyV2'],probabilities['legacyV2']=predict_export(v2,final['x'][:,:len(V2_FEATURES)])
    widths['legacyV2']=v2['interval']['halfWidths'];policies['legacyV2']=v2['alertPolicy']
    predictions['persistence']=np.tile(final['x'][:,FEATURES.index('glucose')][:,None],(1,4))
    probabilities['persistence']=(predictions['persistence'][:,-1]>=180).astype(float)
    policies['persistence']={'threshold':.5}
    labels=final['y'][:,-1]>=180
    current=final['x'][:,FEATURES.index('glucose')]
    primary=final['routines']<6
    def report(mask,include_mae_interval=True):
        output={}
        for name,pred in predictions.items():
            threshold=policies[name]['threshold']
            result=score(final['y'][mask],pred[mask],probabilities[name][mask],widths.get(name),threshold)
            result.update(threshold=threshold,calibration=bins(labels[mask],probabilities[name][mask]))
            if include_mae_interval:
                result['maePatientBootstrap95CI']=bootstrap(np.abs(final['y'][mask,-1]-pred[mask,-1]),final['groups'][mask])
            result['alertPolicy']={**policies[name],'testRecall':result['recall'],'testPrecision':result['precision'],
                                   'testF1':result['f1'],'testConfusionMatrix':result['confusionMatrix']}
            output[name]=result
        return output
    def comparisons(mask):
        paired={}
        for name in ['legacyV2','sensorOnly','persistence']:
            diff=np.abs(final['y'][mask,-1]-predictions['fused'][mask,-1])-np.abs(final['y'][mask,-1]-predictions[name][mask,-1])
            paired[name]={'meanDifference':float(diff.mean()),'patientBootstrap95CI':bootstrap(diff,final['groups'][mask]),
                          'direction':'v3 fused minus comparator MAE; negative favors v3'}
        return paired
    primary_models=report(primary)
    decisions=decision_differences(labels[primary],probabilities['fused'][primary],probabilities['legacyV2'][primary],
                                  policies['fused']['threshold'],policies['legacyV2']['threshold'],final['groups'][primary])
    cases=[]
    for ri,routine in enumerate(all_routines):
        mask=final['routines']==ri
        case={'id':routine['id'],'title':routine['title'],'parameters':routine['params'],'patients':120,'windows':int(mask.sum()),
              'trainingFamily':ri<6,'models':report(mask),'pairedDifferences':comparisons(mask),
              'pairedDecisionDifferences':decision_differences(labels[mask],probabilities['fused'][mask],probabilities['legacyV2'][mask],
                  policies['fused']['threshold'],policies['legacyV2']['threshold'],final['groups'][mask])}
        cases.append(case)
    slices=[]
    for name,title,mask in [('currently_below_180','Currently below180: future threshold event',primary&(current<180)),
                             ('currently_at_least_180','Already at or above180 at cutoff',primary&(current>=180)),
                             ('rising','Positive past30-minute CGM slope',primary&(final['x'][:,FEATURES.index('slope30')]>0)),
                             ('falling_or_flat','Nonpositive past30-minute CGM slope',primary&(final['x'][:,FEATURES.index('slope30')]<=0))]:
        slices.append({'id':name,'title':title,'windows':int(mask.sum()),'models':report(mask,include_mae_interval=False),
                       'uncertaintyNote':'MAE interval omitted: this observed-state slice has unequal window counts per patient.'})
    events.append({'event':'final_evaluation_completed','at':timestamp(),'modelSHA256':model_hash,'finalPatientsGenerated':True})
    limits=p['limitations']+['No future meal annotations, latent simulator terms, routine labels or absolute clock values are predictors.',
         'Synthetic HR includes contemporaneous meal response by simulator design; improved HR feature utility is not evidence of real-world meal detection.',
         'FP and FN counts are overlapping exact-horizon windows, not deduplicated events or alarms per patient-day.',
         'The alert threshold is an experimental error-tradeoff policy, not a clinically established action threshold.',
         'The variable-routine and unseen-combination results must be read separately; pooled improvements do not establish uniform gains.',
         'Confidence intervals resample identities and keep routine variants paired; they do not quantify simulator-to-clinic uncertainty.',
         'Scenario controls remain illustrative arithmetic, not learned treatment effects.']
    metrics={'schemaVersion':3,'seed':SEED,'syntheticOnly':True,'modelVersion':model['modelVersion'],'modelSHA256':model_hash,
             'modelKind':model['modelKind'],'featureSet':model['featureSet'],
             'target':'CGM glucose >=180 mg/dL at exactly +120 minutes; not any excursion within two hours',
             'cohort':{'patients':1064,'days':4,'routines':6,'heldOutStressRoutines':1,'cadenceMinutes':5,'windowStrideMinutes':30,
                       'trainPatients':768,'validationPatients':176,'selectionPatients':80,'calibrationPatients':96,'testPatients':120,
                       'windows':{'train':768*6*70,'selection':80*6*140,'calibration':96*6*140,'validation':176*6*140,'test':int(primary.sum()),'heldOutCombination':int((~primary).sum())},
                       'positiveRate':{'test':float(labels[primary].mean())}},
             'splits':{'train':p['splits']['train'],'validation':p['splits']['selection']+p['splits']['calibration'],'test':p['splits']['test']},
             'developmentSplits':{'selection':p['splits']['selection'],'calibration':p['splits']['calibration']},
             'models':primary_models,'probabilityThreshold':policies['fused']['threshold'],
             'aggregateWeighting':'Equal weights across six familiar routine families and120 fresh identities; the held-out combination is separate.',
             'pairedDecisionDifferences':decisions,'slices':slices,
             'environment':{'python':platform.python_version(),'numpy':np.__version__,'scikitLearn':sklearn.__version__},'limitations':limits}
    robustness={'schemaVersion':3,'syntheticOnly':True,'modelVersion':model['modelVersion'],'modelSHA256':model_hash,
                'protocol':p,'selection':frozen['development'],'events':events,
                'aggregate':{'models':primary_models,'pairedDifferences':comparisons(primary),'pairedDecisionDifferences':decisions,'patients':120,'windows':int(primary.sum()),'caseIds':[r['id'] for r in ROUTINES]},
                'aggregateWithStress':{'models':report(np.ones(len(labels),dtype=bool)),'patients':120,'windows':len(labels)},
                'cases':cases,'slices':slices,'limitations':limits}
    stress={'schemaVersion':3,'syntheticOnly':True,'modelVersion':model['modelVersion'],'modelSHA256':model_hash,
            'protocol':'Frozen v3 and frozen v2 on120 fresh identities; six training families plus a separately reported held-out parameter combination.',
            'target':metrics['target'],'alertThreshold':policies['fused']['threshold'],'testPatientIds':p['splits']['test'],
            'cases':[{'id':case['id'],'title':case['title'],'patients':120,'windows':case['windows'],**case['models']['fused'],
                      'persistenceMae':case['models']['persistence']['mae'],'legacyMae':case['models']['legacyV2']['mae']} for case in cases],'limitations':limits}
    display,parity=[],[]
    chosen=frozen['families']['fused']
    for di,pi in enumerate(SPLITS['test'][:8]):
        ri=[0,1,2,3,4,5,6,5][di]
        patient=display_patient(final['retained'][(pi,ri)],di)
        patient['defaultCursor']=810+12*di
        patient['routine']={'id':all_routines[ri]['id'],'label':all_routines[ri]['title']}
        patient['replayNote']='Fresh final-cohort synthetic identity. Routine and cutoff fixed without selecting favorable outcomes.'
        display.append(patient)
        for cursor in [patient['defaultCursor'],patient['defaultCursor']-30]:
            f=trajectory_features(patient,cursor);x=np.array([[f[n] for n in FEATURES]])
            pred=[float(reg.predict(x)[0]) for reg in chosen['regressors']]
            raw=chosen['classifier'].decision_function(x)
            risk=float(chosen['calibrator'].predict_proba(raw.reshape(-1,1))[0,1])
            parity.append({'id':patient['id'],'cursor':cursor,'routine':all_routines[ri]['id'],'features':f,'forecast':pred,'risk':risk})
    if (OUT/'model.json').read_bytes()!=model_bytes:
        raise AssertionError('Frozen model changed after final generation.')
    for name,payload in [('metrics.json',metrics),('robustness.json',robustness),('stress.json',stress),('patients.json',display),
                          ('parity.json',parity),('robustness-protocol.json',p),('training-audit.json',{'events':events}),
                          ('selection-results.json',frozen['development'])]:
        write_json(OUT/name,payload,compact=name=='patients.json')
    print(json.dumps({'primary':{name:{k:m[k] for k in ['mae','recall','precision','confusionMatrix','auroc','brier']} for name,m in primary_models.items()},
                     'pairedDecisions':decisions,'modelSHA256':model_hash}),flush=True)
    for case in cases:
        print(case['id'],json.dumps({name:{k:case['models'][name][k] for k in ['mae','recall','precision','confusionMatrix']} for name in ['fused','legacyV2']}),flush=True)


def develop():
    if (OUT/'freeze.json').exists():
        raise RuntimeError('This candidate is frozen. Use separate --output-dir and --work-dir paths for reproducible retraining.')
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    p=protocol()
    write_json(OUT/'protocol.json',p)
    started=time.time()
    training=cached_dataset('train',SPLITS['train'],12)
    selection=cached_dataset('selection',SPLITS['selection'],6)
    baseline=json.loads((ROOT/'data'/'baseline-v2'/'model.json').read_bytes())
    baseline_pred,baseline_prob=predict_export(baseline,selection['x'][:,:len(V2_FEATURES)])
    labels=selection['y'][:,-1]>=180
    reports=[]
    for candidate in CANDIDATES:
        options={k:v for k,v in candidate.items() if k not in ['id','irregularWeight']}
        options.update(max_bins=127,early_stopping=False,random_state=SEED)
        weights=np.where(training['routines']>=3,candidate['irregularWeight'],1.)
        path=WORK/f"{candidate['id']}.pkl"
        if path.exists():
            with path.open('rb') as handle: fitted=pickle.load(handle)
            if fitted.get('configuration')!=candidate or fitted.get('featureNames')!=FEATURES:
                raise RuntimeError('Candidate cache differs from the declared configuration/features; use a fresh --work-dir.')
        else:
            print(f"Fitting {candidate['id']}",flush=True)
            classifier=HistGradientBoostingClassifier(**options).fit(training['x'],training['y'][:,-1]>=180,sample_weight=weights)
            regressor=HistGradientBoostingRegressor(loss='absolute_error',**options).fit(training['x'],training['y'][:,-1],sample_weight=weights)
            fitted={'classifier':classifier,'regressor120':regressor,'configuration':candidate,'featureNames':FEATURES}
            with path.open('wb') as handle: pickle.dump(fitted,handle)
        pred=fitted['regressor120'].predict(selection['x'])
        prob=fitted['classifier'].predict_proba(selection['x'])[:,1]
        report={'candidate':candidate['id'],'mae':float(np.abs(selection['y'][:,-1]-pred).mean()),
                'auroc':float(roc_auc_score(labels,prob)),'brier':float(brier_score_loss(labels,prob)),
                'policy':choose_policy(labels,prob,baseline_prob,selection['routines'])}
        reports.append(report)
        write_json(OUT/'development-results.json',{'protocol':p,'candidates':reports,'finalGenerated':False,
                   'baselineV2':score(selection['y'],baseline_pred,baseline_prob,baseline['interval']['halfWidths'],baseline['alertPolicy']['threshold'])})
        print(json.dumps(report),flush=True)
    reg=min(reports,key=lambda item:item['mae'])
    clf=min(reports,key=lambda item:(item['policy']['worstCountRatioToV2'],item['policy']['meanCountRatioToV2'],item['brier']))
    result={'regressionChoice':reg['candidate'],'classificationChoice':clf['candidate'],
            'developmentSeconds':time.time()-started,'finalGenerated':False}
    write_json(OUT/'development-selection.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['develop','freeze','evaluate'],default='develop')
    parser.add_argument('--output-dir',type=Path,default=OUT,help='Separate destination for reproducible retraining; never use active data/.')
    parser.add_argument('--work-dir',type=Path,default=WORK,help='Local intermediate arrays and fitted estimators.')
    args=parser.parse_args()
    OUT=args.output_dir.resolve()
    WORK=args.work_dir.resolve()
    if OUT==(ROOT/'data').resolve() or OUT in [(ROOT/'data'/'baseline-v1').resolve(),(ROOT/'data'/'baseline-v2').resolve()]:
        parser.error('Choose a separate output directory; active and archived artifacts are protected.')
    {'develop':develop,'freeze':freeze,'evaluate':evaluate}[args.phase]()

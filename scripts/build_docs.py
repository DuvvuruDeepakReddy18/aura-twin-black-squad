"""Build current submission documents from frozen V3 artifacts."""
from pathlib import Path
import hashlib,json
from doc_layout import build

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'

def load(name): return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))
def pct(value): return f'{value*100:.2f}%'
def counts(result):
    (tn,fp),(fn,tp)=result['confusionMatrix']
    return tn,fp,fn,tp
def table(headings,rows):
    return '\n'.join(['| '+' | '.join(headings)+' |','|'+'|'.join('---' for _ in headings)+'|']+['| '+' | '.join(map(str,row))+' |' for row in rows])

def main():
    model=load('model.json'); m=load('metrics.json'); r=load('robustness.json')
    actual_hash=hashlib.sha256((ROOT/'data/model.json').read_bytes()).hexdigest()
    if model['modelVersion']!='aura-synthetic-3.0.0' or actual_hash!=m['modelSHA256'] or m['modelSHA256']!=r['modelSHA256']:
        raise RuntimeError('Review the document source against the frozen V3 artifact before building.')
    f=m['models']['fused']; old=m['models']['legacyV2']; p=f['alertPolicy']; u=next(x for x in r['cases'] if x['id']=='unseen_combination')
    _,fp,fn,_=counts(f); _,oldfp,oldfn,_=counts(old)
    uf=u['models']['fused']; ul=u['models']['legacyV2']; _,ufp,ufn,_=counts(uf); _,ulfp,ulfn,_=counts(ul)
    primary=[x for x in r['cases'] if x.get('trainingFamily',True)]
    short={'reference':'Regular','late_meals_2h':'Meals +2h','late_meals_4h':'Meals +4h','irregular_meals':'Jittered meals','day_varying_skips':'Daily changes + skips','variable_routine':'Variable sleep/activity'}
    fn_ci=m['pairedDecisionDifferences']['falseNegativeWindows']['patientBootstrap95CI']
    delta=('Primary counts improve; missed-window CI crosses zero' if fn<oldfn and fp<oldfp and fn_ci[0]<=0<=fn_ci[1] else 'Primary missed and false-positive counts are lower' if fn<oldfn and fp<oldfp else 'A mixed result: inspect both error counts')
    ctx={
        'model_version':model['modelVersion'],'feature_count':len(model['featureNames']),
        'algorithm_spoken':'histogram gradient boosting with separate probability calibration','algorithm_short':'Histogram gradient boosting',
        'mae_spoken':f"{f['mae']:.2f}",'auroc_spoken':f"{f['auroc']:.3f}",
        'threshold_spoken':f"{p['threshold']:.4f}",'recall_spoken':f"{f['recall']*100:.2f}",'precision_spoken':f"{f['precision']*100:.2f}",
        'false_negative_spoken':f'{fn:,}','false_positive_spoken':f'{fp:,}',
        'legacy_false_negative_spoken':f'{oldfn:,}','legacy_false_positive_spoken':f'{oldfp:,}',
        'sensor_mae_spoken':f"{m['models']['sensorOnly']['mae']:.2f}",'persistence_mae_spoken':f"{m['models']['persistence']['mae']:.2f}",
        'fusion_gain_spoken':f"{m['models']['sensorOnly']['mae']-f['mae']:.3f}",
        'coverage_spoken':f"{f['intervalCoverage']*100:.2f}",'width_spoken':f"{f['intervalMeanWidth']:.2f}",
        'unseen_result_spoken':f"On this separate case, current model error is {uf['mae']:.2f}, recall is {uf['recall']*100:.2f} percent, and precision is {uf['precision']*100:.2f} percent. Missed positive windows change from {ulfn:,} to {ufn:,}; false-positive windows change from {ulfp:,} to {ufp:,}.",
        'explanation_spoken':'Grouped sensitivity replaces one feature group with its training-median reference and reports the change in calibrated probability in percentage points. These changes are nonadditive, are not SHAP values, and may involve unrealistic reference combinations.',
        'decision_table':[[label,f"{v['threshold']:.4f}",pct(v['recall']),pct(v['precision']),f'{counts(v)[2]:,}',f'{counts(v)[1]:,}'] for label,v in [('Frozen v2',old),('Current v3',f)]],
        'decision_change':delta,
        'error_summary':f"V3 +120 MAE {f['mae']:.2f} mg/dL · AUROC {f['auroc']:.3f} · Brier {f['brier']:.4f}",
        'routine_table':[[short[x['id']],f"{counts(x['models']['legacyV2'])[2]:,} → {counts(x['models']['fused'])[2]:,}",f"{counts(x['models']['legacyV2'])[1]:,} → {counts(x['models']['fused'])[1]:,}",pct(x['models']['fused']['recall']),pct(x['models']['fused']['precision'])] for x in primary],
        'unseen_caption':f"Withheld combination: missed positives {ulfn:,} → {ufn:,} · false positives {ulfp:,} → {ufp:,}",
        'coverage_display':pct(f['intervalCoverage']),'width_display':f"{f['intervalMeanWidth']:.1f} mg/dL",'threshold_display':f"{p['threshold']:.4f}",
    }
    slides=json.loads((ROOT/'scripts/presentation_content.json').read_text(encoding='utf-8'))
    for slide in slides:slide['text']=slide['text'].format_map(ctx)
    build(slides,ctx,OUT)
    narration=[{k:s[k] for k in ('slide','title','text')} for s in slides]
    (OUT/'narration.json').write_text(json.dumps(narration,indent=2,ensure_ascii=False),encoding='utf-8')
    write_card(model,m,r)
    print(f"Built {len(slides)} presentation pages, 3 architecture pages and {sum(len(x['text'].split()) for x in slides)} narration words.")

def write_card(model,m,r):
    f=m['models']['fused']; p=f['alertPolicy']; c=m['cohort']; old=m['models']['legacyV2']; u=next(x for x in r['cases'] if x['id']=='unseen_combination')
    model_rows=[]
    for label,key in [('Current fused','fused'),('Frozen v2','legacyV2'),('Sensors only','sensorOnly'),('EHR only','staticOnly'),('Persistence','persistence')]:
        v=m['models'][key]; _,fp,fn,_=counts(v)
        model_rows.append([label,f"{v['mae']:.3f}",f"{v['auroc']:.4f}",f"{v['averagePrecision']:.4f}",f"{v['brier']:.4f}",f"{v['threshold']:.4f}",pct(v['recall']),pct(v['precision']),f'{fn:,}',f'{fp:,}'])
    model_table=table(['Model','+120 MAE','AUROC','AP','Brier','Policy','Recall','Precision','FN windows','FP windows'],model_rows)
    routine_rows=[]
    for x in r['cases']:
        v=x['models']['fused']; b=x['models']['legacyV2']; _,fp,fn,_=counts(v); _,bfp,bfn,_=counts(b)
        routine_rows.append([x['title'],f"{b['mae']:.2f} → {v['mae']:.2f}",f'{bfn:,} → {fn:,}',f'{bfp:,} → {fp:,}',pct(v['recall']),pct(v['precision']),pct(v['intervalCoverage'])])
    routine_table=table(['Routine','V2 → V3 MAE','V2 → V3 FN','V2 → V3 FP','V3 recall','V3 precision','V3 band coverage'],routine_rows)
    split_table=table(['Role','Identities','Windows','Use'],[
        ['Fit',c['trainPatients'],f"{c['windows']['train']:,}",'Candidate fitting; 60-minute stride'],
        ['Select',c['selectionPatients'],f"{c['windows']['selection']:,}",'Candidate choice; 30-minute stride'],
        ['Calibrate',c['calibrationPatients'],f"{c['windows']['calibration']:,}",'Probability mapping, residual bands and global policy'],
        ['Primary final',c['testPatients'],f"{c['windows']['test']:,}",'Six familiar families; reporting only'],
        ['Withheld combination',c['testPatients'],f"{c['windows']['heldOutCombination']:,}",'Same final identities; separate stress result']])
    decision_table=table(['V3 minus frozen V2','Observed difference','Patient-bootstrap 95% interval'],[[key,f"{v['difference']:.5f}",f"{v['patientBootstrap95CI'][0]:.5f} to {v['patientBootstrap95CI'][1]:.5f}"] for key,v in m['pairedDecisionDifferences'].items()])
    error_table=table(['Comparator','V3 minus comparator MAE','Patient-bootstrap 95% interval'],[[key,f"{v['meanDifference']:.4f}",f"{v['patientBootstrap95CI'][0]:.4f} to {v['patientBootstrap95CI'][1]:.4f}"] for key,v in r['aggregate']['pairedDifferences'].items()])
    horizon_table=table(['Horizon min','MAE mg/dL','RMSE mg/dL','Band coverage','Mean width mg/dL'],[[f"+{v['minutes']}",f"{v['mae']:.3f}",f"{v['rmse']:.3f}",pct(v['intervalCoverage']),f"{v['intervalMeanWidth']:.2f}"] for v in f['byHorizon']])
    slice_rows=[]
    for x in m['slices']:
        v=x['models']['fused']; b=x['models']['legacyV2']; _,fp,fn,_=counts(v); _,bfp,bfn,_=counts(b)
        slice_rows.append([x['id'],f"{x['windows']:,}",f'{bfn:,} → {fn:,}',f'{bfp:,} → {fp:,}',pct(v['recall']),pct(v['precision'])])
    slice_table=table(['Slice','Windows','V2 → V3 FN','V2 → V3 FP','V3 recall','V3 precision'],slice_rows)
    rc=model['trainingProtocol']['regressionConfiguration']; cc=model['trainingProtocol']['classificationConfiguration']
    hyper_table=table(['Setting','Four regressors','Event classifier'],[[key,rc[key],cc[key]] for key in ['id','max_iter','max_leaf_nodes','min_samples_leaf','learning_rate','l2_regularization','irregularWeight']])
    tn,fp,fn,tp=counts(f)
    body=f'''# AURA Twin — current model and data card

**Artifact:** `{model['modelVersion']}` · **Raw model-file SHA-256:** `{m['modelSHA256']}`.

Black Squad, Amrita Vishwa Vidyapeetham, Chennai. This card describes the current model. Historical artifacts remain in `data/baseline-v1/` and `data/baseline-v2/`. Historical scores must not be presented as current results.

## Purpose and data boundaries

Forecast glucose at +30, +60, +90 and +120 minutes from synthetic EHR context plus wearable history. The binary target is **glucose ≥180 mg/dL at exactly +120 minutes**, not any excursion during the interval or necessarily a new onset. Inclusive 180 is an engineering convention; individualized clinical targets are outside scope.

The repository's own seeded simulator supplies all data. No real patient records, PHI, device accounts, Synthea exports or MIMIC data are used. No diagnosis, dosing, treatment, emergency triage, clinical efficacy or legal-compliance certification is claimed.

Static predictors are age, BMI, HbA1c, LDL and diabetes duration. Dynamic observations are CGM, HR, HRV, interval steps and asleep/awake flags at five-minute cadence. Names, sex, diagnosis/medication text and arbitrary genetic markers are display context, not predictors. Sleep is not validated sleep-stage classification. HR includes a contemporaneous simulated meal-response term. That is available-time sensing, but it may favor multimodal inference under this designed generator; it does not validate meal detection with real consumer HR.

## Population, split and freeze

There are {c['patients']:,} distinct development/final identities, each generated for four days. Six familiar routine families are regular timing, meals delayed two hours, meals delayed four hours, 1.5-hour timing jitter, day-varying shifts/skips, and variable daily sleep/activity/meals. The separate withheld combination uses a three-hour meal shift, one-hour jitter, daily-shift SD 1.4 hours, skip probability 0.25 and variable sleep/activity. Its factors are familiar; that exact combination was absent from development. It is not unseen physiology.

{split_table}

Fit indices are 0–767; selection 1200–1279; calibration 1400–1495; final 2000–2119 (`SYN-2001` through `SYN-2120`). Every window and routine variant for one identity stays in that partition. The primary and withheld-combination results reuse the same 120 final identities; they are not 240 independent people. These final identities were not used in the earlier inspected v2 evaluation.

Model selection, calibration, policy and interval bytes are frozen and hashed before final identities and their withheld combination are generated. The audit checks the generator/protocol/model consistency. This is a locally auditable sequence, not third-party preregistration, secure blinding or an independent timestamp. No final result is used to choose a new model. See the [protocol](../data/robustness-protocol.json), [selection record](../data/selection-results.json), [freeze record](../data/model-freeze.json) and [training audit](../data/training-audit.json).

## Model selection and feature construction

The current model uses {len(model['featureNames'])} clock-free, strictly past-derived features. They include the earlier 53 features plus detailed lagged trajectories, fitted slopes, change direction/frequency, ranges, time since recent extrema, threshold occupancy, normalized HR/HRV and recent activity/wake history. Previous-day horizon-aligned observations are at t+h−24 hours: the +120-minute reference was measured 22 hours before the cutoff. No future meal, absolute clock value, hidden simulator state or routine label enters inference. Full feature order and definitions are in `data/SCHEMA.md` and `data/model.json`.

Three HGB candidate configurations are compared on selection identities. Regression minimizes +120-minute MAE. Classification minimizes the worst FP/FN count ratio to frozen v2 across overall, pooled irregular, and variable-routine windows, with one global threshold; ties use the average ratio then Brier score. This decision-aligned objective is a prototype design choice, not a clinically elicited cost function.

{hyper_table}

Regressors use absolute-error loss. Both chosen configurations use 127 histogram bins, disabled early stopping and the fixed experiment seed. Irregular sample weights apply to development routine families 3–5; they are fitting weights, not a routine label at inference. Candidate selection is followed by separate calibration identities. A Platt logistic map with C=100 calibrates raw classifier scores. The final single threshold minimizes the same worst FP/FN ratio on calibration identities over a 0.0025 grid. It is **{p['threshold']:.4f}**. Calibration and policy estimation share that calibration partition; final evaluation remains separate. A lower Brier score alone would not establish better calibration or fewer missed and false-positive windows.

Tree inference uses raw features and exported nodes; compatibility `mean`/`scale` fields do not standardize the trees. Training medians define explanation references. Python/JavaScript parity checks the exported calculation.

## Primary fresh final result

The primary comparison equally weights six familiar routine families and {c['testPatients']} fresh identities: **{c['windows']['test']:,} correlated windows**, with event prevalence **{pct(c['positiveRate']['test'])}**. Frozen v2 and all current ablations are evaluated on identical windows at their own frozen policies. Counts are windows, not deduplicated clinical events or alarms per day.

{model_table}

Current confusion matrix: TN {tn:,}; FP {fp:,}; FN {fn:,}; TP {tp:,}. The primary point estimates improve modestly, but the paired 95% interval for the FN difference includes zero. In the withheld combination, FN increases from {counts(u['models']['legacyV2'])[2]:,} to {counts(u['models']['fused'])[2]:,}. Therefore this is a mixed synthetic result, not uniform or statistically established missed-event improvement. Persistence copies current glucose and uses a hard 0/1 event prediction; its probability scores are not a calibration-equivalent comparator. Do not compare these results with an older model's original-cohort score as though the cohorts were identical.

Paired decision differences are current v3 minus frozen v2. Negative differences favor v3 for FP/FN counts; positive differences favor v3 for recall/precision. Recall/precision differences below are fractions, not percentage points. Patient bootstrap resamples identities and keeps all their routine variants and windows paired.

{decision_table}

{error_table}

The EHR fusion increment must be read from the sensor-only comparison; the requirements do not imply a large EHR gain. Synthetic confidence intervals do not quantify uncertainty about transfer to clinical data.

## Every routine, including the separate withheld combination

Each row has 16,800 windows from the same 120 final identities. The last row is excluded from the primary aggregate. Inspect both error types; aggregate gains do not establish improvement for every case or window.

{routine_table}

The withheld combination's per-model metrics and paired uncertainty are preserved in `data/robustness.json`. It is a held-out combination of familiar factors, not a real-world external validation dataset.

## Target-specific slices

{slice_table}

“Currently below 180” still means an exact +120-minute threshold outcome, not the time of first crossing. “Already high” can include persistence or resolution of an existing elevation. Rising/falling slices use past slope only. These slices overlap and are descriptive, not independent experiments.

## Residual bands and quality

The 90th percentile of absolute calibration errors defines a symmetric descriptive band at each horizon. Nominal 90% is a marginal target, not a guarantee for an individual, subgroup, routine or shifted population. Read width alongside coverage. No scenario-specific coverage is claimed for arithmetic what-if offsets.

{horizon_table}

Runtime forward-fills short continuous-sensor gaps and imputes missing interval steps/sleep as zero. It abstains for fewer than 24 hours of history, more than 20% missing channel values in recent two hours or trailing 24 hours, CGM older than 15 minutes, or HR/HRV older than 60 minutes. Null risk is not 0% risk. Plausible sensor bias can pass freshness checks. Missingness handling is a guardrail, not a trained fault detector.

## Explanation, scenarios and reproducibility

Group-reference sensitivity replaces every raw feature in one group with its training median and reports original minus reference calibrated probability in percentage points. It is nonadditive, is not SHAP, may form unrealistic reference combinations, and is not causal attribution. The meal/activity sandbox applies hand-authored arithmetic offsets while preserving trained baseline risk. It does not infer intervention efficacy or use actual future meals.

Challenge Lab freezes a truncated input and prediction before revealing original recorded futures. Clean, short-gap, dropout and biased-sensor cases expose different failure modes. Local sessions use bounded memory; hosted sessions use temporary authenticated encryption and allow only bundled synthetic patient IDs. The downloaded JSON omits the transport token. Raw model and canonical input hashes support offline consistency checking; they are not signatures or independent timestamps. See [deployment boundaries](DEPLOYMENT.md).

## Limits and reproduction

Unknown future meals remain difficult to anticipate. The simulator's physiology, EHR associations and sensor responses are authored assumptions. Medication effects, complex comorbidity, illness, pregnancy, real device behavior, clinical outcomes and usability benefits remain unvalidated. A better benchmark does not establish clinical robustness or safe treatment. No notification-cooldown policy is evaluated as a substitute for classifier improvement.

The current training/reproduction commands, artifact hashes and completed checks are in the README and [verification record](VERIFICATION.md). The recorded environment is Python {m['environment']['python']}, NumPy {m['environment']['numpy']}, scikit-learn {m['environment']['scikitLearn']}. Preserve archived baselines when reproducing the comparison.

Primary context: [NIDDK CGM target discussion](https://www.niddk.nih.gov/health-information/professionals/diabetes-discoveries-practice/clinical-targets-for-continuous-glucose-monitoring-data), [scikit-learn decision-threshold guidance](https://scikit-learn.org/stable/modules/classification_threshold.html), [probability calibration](https://scikit-learn.org/stable/modules/calibration.html), and [Ramkissoon et al. on unannounced-meal detection and tradeoffs](https://pmc.ncbi.nlm.nih.gov/articles/PMC5876595/). The meal-detection paper concerns observing a meal response, not predicting an unobserved future meal. [Synthea](https://synthetichealth.github.io/synthea/) is a possible future integration, not a source used here. None of these sources validates this prototype.
'''
    (OUT/'MODEL_DATA_CARD.md').write_text(body,encoding='utf-8')
    (ROOT/'ml/MODEL_CARD.md').write_text('# Current model card\n\nThe authoritative card is [docs/MODEL_DATA_CARD.md](../docs/MODEL_DATA_CARD.md), generated from the frozen V3 artifact and fresh final evaluation. Historical artifacts remain in `data/baseline-v1/` and `data/baseline-v2/`.\n',encoding='utf-8')

if __name__=='__main__':main()

"""Build the current architecture, full presentation, narration and model/data card."""
from pathlib import Path
import json,re
from doc_layout import build
from doc_text import clean_markdown

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'

def load(name): return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))
def pct(value): return f'{value*100:.2f}%'

def main():
    model=load('model.json'); metrics=load('metrics.json'); robustness=load('robustness.json')
    if model['modelVersion']!='aura-synthetic-2.0.0' or model['modelKind']!='hist_gradient_boosting':
        raise RuntimeError('This document source requires the frozen2.0.0 histogram-boosting artifact. Review content before changing versions.')
    fused=metrics['models']['fused']; policy=fused['alertPolicy']; cohort=metrics['cohort']
    names=[('Current fused','fused'),('Sensors only','sensorOnly'),('EHR only','staticOnly'),('Persistence','persistence'),('Frozen v1','legacyV1')]
    short={'reference':'Regular','late_meals_2h':'Meals +2h','late_meals_4h':'Meals +4h','irregular_meals':'Jittered meals','day_varying_skips':'Daily changes + skips','variable_routine':'Variable sleep/activity'}
    ctx={
        'model_version':model['modelVersion'],'feature_count':len(model['featureNames']),
        'algorithm_spoken':'histogram gradient boosting with separate probability calibration',
        'algorithm_short':'Histogram gradient boosting',
        'candidates_spoken':'a clock-free linear regression and logistic pipeline with a clock-free histogram gradient boosting pipeline',
        'mae_spoken':f"{fused['mae']:.2f}", 'auroc_spoken':f"{fused['auroc']:.3f}",
        'threshold_spoken':f"{policy['threshold']:.2f}", 'recall_spoken':f"{policy['testRecall']*100:.2f}", 'precision_spoken':f"{policy['testPrecision']*100:.2f}",
        'sensor_mae_spoken':f"{metrics['models']['sensorOnly']['mae']:.2f}", 'persistence_mae_spoken':f"{metrics['models']['persistence']['mae']:.2f}",
        'coverage_spoken':f"{fused['intervalCoverage']*100:.2f}", 'width_spoken':f"{fused['intervalMeanWidth']:.2f}",
        'explanation_spoken':'For the current tree model, grouped sensitivity replaces one feature group with its training-median reference and reports the change in calibrated probability in percentage points. These changes are nonadditive, are not SHAP values, and may involve unrealistic reference combinations.',
        'model_table':[[label,f"{metrics['models'][key]['mae']:.2f}",f"{metrics['models'][key]['auroc']:.3f}",f"{metrics['models'][key]['brier']:.4f}"] for label,key in names],
        'routine_table':[[short[case['id']],f"{case['models']['fused']['mae']:.2f}",f"{case['models']['legacyV1']['mae']:.2f}",f"{case['models']['persistence']['mae']:.2f}",pct(case['models']['fused']['intervalCoverage'])] for case in robustness['cases']],
        'policy_summary':f"Policy {policy['threshold']:.2f}: recall {policy['testRecall']*100:.1f}% · precision {policy['testPrecision']*100:.1f}%",
        'coverage_display':pct(fused['intervalCoverage']),'width_display':f"{fused['intervalMeanWidth']:.1f} mg/dL",'threshold_display':f"{policy['threshold']:.2f}",
    }
    slides=json.loads((ROOT/'scripts/presentation_content.json').read_text(encoding='utf-8'))
    for slide in slides: slide['text']=slide['text'].format_map(ctx)
    build(slides,ctx,OUT)
    narration=[{k:s[k] for k in ('slide','title','text')} for s in slides]
    (OUT/'narration.json').write_text(json.dumps(narration,indent=2,ensure_ascii=False),encoding='utf-8')
    write_card(model,metrics,robustness)
    print(f"Built {len(slides)} presentation pages,3 architecture pages, narration with {sum(len(s['text'].split()) for s in slides)} words.")

def write_card(model,m,r):
    f=m['models']['fused']; p=f['alertPolicy']; c=m['cohort']; protocol=r['protocol']
    names=[('Current fused','fused'),('Sensors only','sensorOnly'),('EHR only','staticOnly'),('Persistence','persistence'),('Frozen v1 on same new cases','legacyV1')]
    table='\n'.join(f"| {label} | {m['models'][key]['mae']:.4f} | {m['models'][key]['auroc']:.4f} | {m['models'][key]['averagePrecision']:.4f} | {m['models'][key]['brier']:.4f} |" for label,key in names)
    routines='\n'.join(f"| {case['title']} | {case['models']['fused']['mae']:.2f} | {case['models']['legacyV1']['mae']:.2f} | {case['models']['persistence']['mae']:.2f} | {pct(case['models']['fused']['intervalCoverage'])} | {pct(case['models']['fused']['recall'])} |" for case in r['cases'])
    horizon='\n'.join(f"| +{h['minutes']} | {h['mae']:.3f} | {h['rmse']:.3f} | {pct(h['intervalCoverage'])} | {h['intervalMeanWidth']:.2f} |" for h in f['byHorizon'])
    splits='\n'.join(f"| {label} | {count} | {c['windows'][key]:,} | {role} |" for label,count,key,role in [('Fit',256,'train','Fit candidates and ablations;60min stride'),('Select',48,'selection','Choose regression/classifier family;60min stride'),('Calibrate',48,'calibration','Platt mapping, residual bands, policy;30min stride'),('Final test',80,'test','Reporting only after freeze;30min stride')])
    paired='\n'.join(f"| {name} | {d['meanDifference']:.3f} | {d['patientBootstrap95CI'][0]:.3f} to {d['patientBootstrap95CI'][1]:.3f} |" for name,d in r['aggregate']['pairedDifferences'].items())
    tn,fp=p['testConfusionMatrix'][0];fn,tp=p['testConfusionMatrix'][1]
    body=f'''# AURA Twin — current model and data card

**Artifact:** `{model['modelVersion']}` · **Model SHA-256:** `{m['modelSHA256']}`.

This card describes the current robustness upgrade. Historical v1 results belong to `data/baseline-v1/`; its old10.95mg/dL result is not the current benchmark. No real patients, PHI, hospital data, Synthea output, MIMIC data or device accounts were used.

## Purpose and boundaries

Black Squad, Amrita Vishwa Vidyapeetham, Chennai, built a synthetic proof of concept of historical EHR/wearable fusion and clinician-oriented review. Forecasts are at+30,+60,+90,+120minutes; the event is **glucose≥180mg/dL at exactly+120minutes**, not any excursion during the next two hours. Inclusive180 is the prototype convention; individualized clinical targets are outside scope.

The model is not intended for diagnosis, dosing, treatment, emergency triage or autonomous clinical alerts. No clinical efficacy, safety or legal-compliance certification is claimed.

## Generated data and experiment

The repository's seeded simulator creates432 distinct identities, each with four days at five-minute cadence and six routine variants. There are2,592 patient/routine trajectories; variants are not independent people. The six families are regular timing, meals delayed2h, meals delayed4h, meal-time jitter1.5h SD, day-varying timing with skips, and variable daily sleep/activity/meals. All six families appear during development. The final result is **fresh-identity generalization within this declared mixture**, not validation on unseen routine families.

Static prediction inputs are age, BMI, HbA1c, LDL and diabetes duration. Dynamic observations are CGM, HR, HRV, interval steps and asleep/awake flags. Arbitrary genetic markers, diagnosis/medication text, names and sex are display context, not predictors. Sleep is not validated stage classification. HR contains a contemporaneous synthetic meal response; no future meal schedule or latent simulator state is provided to inference.

The generator and features were designed after inspecting v1 failures. Training identity indices0–255 can overlap earlier development identities. **Final indices1000–1079 (SYN-1001…SYN-1080) are new** and absent from the old cohort. Eight demo records and their default cutoffs are selected by a fixed rule, not by favorable final predictions.

## Partition and freeze protocol

| Role | Identities | Windows | Use |
|---|---:|---:|---|
{splits}

Every variant and window for one identity remains in its partition. Selection minimizes pooled+120min MAE for regression and uncalibrated Brier for classification on selection identities only. Separate calibration identities fit the probability mapping, residual widths and review policy. The exported model bytes and SHA-256 are recorded **before final identities are generated**; code asserts the model bytes remain unchanged after final evaluation. This is a locally auditable sequence, not independent preregistration or a trusted external timestamp.

See `data/robustness-protocol.json`, `data/selection-results.json`, and `data/training-audit.json`. There are{c['windows']['test']:,} final windows across80 identities and6 variants, equally weighted. Final event prevalence is{pct(c['positiveRate']['test'])}. Repeated windows and variants are correlated. Bootstrap intervals resample identities and preserve paired variants.

## Model and input construction

The selected model is histogram gradient boosting: four separate absolute-error regressors and one event classifier,160iterations,31leaves,0.07learning rate,60minimum samples per leaf, regularization strength10 and63 bins. Its comparator during selection was a clock-free StandardScaler+Ridge(alpha50)/logistic(C0.3) pipeline. The tree model consumes raw features; the exported `mean` and `scale` compatibility fields do not standardize tree inference.

There are{len(model['featureNames'])}clock-free features. They include glucose lags, short- and long-window summaries, slopes, acceleration, quantiles, EHR context, HR/HRV, steps/sleep, and previous-day observations aligned to each forecast horizon. `priorDay120` is observed at t−22h; it is not future knowledge. The recurrence assumption can fail after a routine change. Full order is `data/model.json.featureNames` and `data/SCHEMA.md`.

The event classifier uses Platt calibration (logistic C100) on separate calibration identities. Exact tree nodes, baseline predictions, calibrated probability parameters, reference medians and feature groups are exported for JavaScript inference. Future observations are labels only. Missingness handling is a runtime guardrail, not a trained sensor-fault model.

## Measured fresh final results

| Model | +120MAE mg/dL | AUROC | Average precision | Brier |
|---|---:|---:|---:|---:|
{table}

Persistence copies the current glucose and has a hard0/1 event output; its probability scores are not a calibration-equivalent comparator. The frozen v1 row above is evaluated on exactly the same new cases. Do not substitute its old regular-cohort result for this fair comparison.

Current fused MAE patient-bootstrap95% interval: **{f['maePatientBootstrap95CI'][0]:.3f}–{f['maePatientBootstrap95CI'][1]:.3f}mg/dL**. Paired mean-error differences use current fused minus comparator, so negative values favor current fused:

| Comparator | MAE difference | Patient-bootstrap95% interval |
|---|---:|---|
{paired}

## Routine-specific results

| Routine | Current MAE | Frozen v1 MAE | Persistence MAE | Nominal90% coverage | Recall at fixed policy |
|---|---:|---:|---:|---:|---:|
{routines}

These families were represented in training. No case is hidden or removed for underperformance. Per-case paired intervals and all ablations are in `data/robustness.json`.

## Review threshold and residual uncertainty

The fixed review threshold is **{p['threshold']:.2f}**, chosen as the highest0.01grid threshold meeting at least80% recall on calibration identities. Final recall is**{pct(p['testRecall'])}**, precision**{pct(p['testPrecision'])}**. Confusion counts are TN{tn:,}, FP{fp:,}, FN{fn:,}, TP{tp:,}. These are correlated windows, not deduplicated clinical events or alarms. Metrics at the conventional0.50threshold are also retained in `metrics.json`.

Per-horizon90th-percentile absolute calibration residuals define symmetric descriptive bands. They are marginal estimates, not individual coverage guarantees or formal clinical safety bounds. Width and coverage must be read together, particularly for irregular routines.

| Horizon min | MAE mg/dL | RMSE mg/dL | Final band coverage | Mean band width mg/dL |
|---|---:|---:|---:|---:|
{horizon}

## Explanation and scenario semantics

For the current tree model, drivers are **group-reference sensitivity**, not SHAP or additive log-odds attribution. Replace all raw features in a group with training medians, recompute calibrated probability, and report original minus reference risk in percentage points. Group effects do not sum to the output; reference combinations can be unrealistic. They are not causal treatment effects.

The meal/activity sandbox remains illustrative arithmetic. It does not provide actual future meals to the predictor; trained baseline probability is unchanged. Scenario-shifted bands have no measured scenario coverage. No medication guidance or learned intervention efficacy is produced.

## Quality gates and remaining failure modes

The runtime uses short-gap forward filling for CGM/HR/HRV and zero imputation for interval steps/sleep. It abstains for<24h history,>20% missing channel values in recent2h or trailing24h, CGM stale>15min, or HR/HRV stale>60min. Null risk must not become0% risk. Plausible CGM bias can pass these checks; future unannounced meals, real devices and clinical complexity remain unresolved.

The simulator is a designed model and may favor EHR fusion. Removing absolute clock features does not remove every recurrence cue. The final cohort is synthetic and from the same generator family. No independent clinical, medication, outcome, device, subgroup-efficacy or usability validation exists. Local notes/receipts are not a governed clinical record, and hashes are not signatures.

## Reproduce and review

Run `npm run train` or `python ml/train_robust.py` only when intentionally reproducing the current experiment. `npm run train:legacy` writes a separate baseline-retrained directory and cannot silently replace active artifacts. Run `npm test` and `npm run test:data`; consult `docs/VERIFICATION.md` for the completed checks. Recorded environment: Python{m['environment']['python']}, NumPy{m['environment']['numpy']}, scikit-learn{m['environment']['scikitLearn']}.

Primary context: [NIDDK CGM targets](https://www.niddk.nih.gov/health-information/professionals/diabetes-discoveries-practice/clinical-targets-for-continuous-glucose-monitoring-data). [Synthea](https://synthetichealth.github.io/synthea/) is a possible future integration, not a data source used here. Neither source validates this model.
'''
    body=clean_markdown(body)
    # Keep model/data documentation sourced from the same measured artifacts as the slides.
    (OUT/'MODEL_DATA_CARD.md').write_text(body,encoding='utf-8')
    (ROOT/'ml/MODEL_CARD.md').write_text('# Current model card\n\nThe authoritative current model and data card is [docs/MODEL_DATA_CARD.md](../docs/MODEL_DATA_CARD.md). It is generated from the frozen2.0.0 model, fresh final metrics and robustness report. Historical v1 artifacts are in `data/baseline-v1/`.\n',encoding='utf-8')

if __name__=='__main__': main()

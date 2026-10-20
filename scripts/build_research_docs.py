"""Build current research documents from frozen, evaluated numerical artifacts."""
from pathlib import Path
import argparse
import hashlib
import json
from research_doc_layout import build

ROOT = Path(__file__).resolve().parents[1]
DATA, DOCS = ROOT/'data', ROOT/'docs'


def read(name):
    return json.loads((DATA/name).read_text(encoding='utf-8'))


def number(value, digits=2):
    return 'unavailable' if value is None else f'{value:.{digits}f}'


def percent(value):
    return number(None if value is None else value*100)


def counts(metric):
    (tn, fp), (fn, tp) = metric['confusionMatrix']
    return tn, fp, fn, tp


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |',
                      '|'+'|'.join('---' for _ in headers)+'|']+
                     ['| '+' | '.join(map(str, row))+' |' for row in rows])


def v4_status():
    path = DATA/'synthetic-v4-experiment/results.json'
    if not path.exists():
        return ('Separate experiment in progress; no improvement claim.',
                'The separate experiment is still in progress. No final improvement or promotion is claimed.')
    result = json.loads(path.read_text(encoding='utf-8'))
    primary = result['primary']; old, new = primary['v3'], primary['v4']
    _, ofp, ofn, _ = counts(old); _, nfp, nfn, _ = counts(new)
    gate = result['promotionGate']['passed']
    status = 'Predeclared promotion gate passed; deployment is a separate verified step.' if gate else 'Predeclared promotion gate failed; not promoted.'
    spoken = (f"On the separate fresh synthetic cohort, false-negative windows changed from {ofn:,} to {nfn:,}, "
              f"and false-positive windows from {ofp:,} to {nfp:,}. {status} "
              "These results are not comparable with the open-research model's performance.")
    return status, spoken


def context(model, metrics, auth_status):
    f = metrics['models']['primary']; p = metrics['models']['persistence']
    _, fp, fn, _ = counts(f)
    target = model['target']
    if target['kind'] == 'rise':
        target_short = 'Research event: observed CGM rise ≥20 mg/dL at approximately +120 minutes'
        target_spoken = ('an observed glucose rise of at least twenty milligrams per deciliter from the latest '
                         'available current reading at approximately one hundred and twenty minutes')
        target_display = 'CGM rise ≥20 mg/dL<br/>at approximately t + 120 min<br/><br/>Relative to the latest available current reading.'
    else:
        target_short = 'Research event: observed CGM ≥180 mg/dL at approximately +120 minutes'
        target_spoken = 'observed glucose at or above one hundred and eighty milligrams per deciliter at approximately one hundred and twenty minutes'
        target_display = 'CGM ≥180 mg/dL<br/>at approximately t + 120 min<br/><br/>A specific future reading, not any excursion during the interval.'
    auth = {
        'not-configured': ('Integration implemented; provider not connected. Sign-in is unavailable.',
                           'the provider integration is implemented, but an identity provider is not yet connected, so account sign-in is unavailable'),
        'configured-unverified': ('Supabase connected. Email confirmation on; Google off. Account-flow verification pending.',
                                 'Supabase is connected with email confirmation enabled. Complete real account-flow verification remains pending. Google sign-in is disabled because its OAuth credentials are not configured, and public email delivery still depends on provider setup'),
        'verified': ('Configured provider-backed flows; see the verification record for tested paths.',
                     'configured provider-backed flows are available, with the exact paths actually tested listed in the verification record'),
    }[auth_status]
    v4_card, v4_spoken = v4_status()
    labels = {'cgmOnly':'CGM only', 'wearableOnly':'CGM + HR + RMSSD', 'matchedFusion':'Matched research fusion',
              'ehrOnly':'Unmatched EHR only', 'compositeFusion':'Unmatched composite', 'persistence':'Persistence'}
    rows = []
    for key in labels:
        v = metrics['models'][key]; _, vfp, vfn, _ = counts(v)
        rows.append([labels[key], number(v['mae']), percent(v['recall'])+'%', percent(v['precision'])+'%', f'{vfn:,} / {vfp:,}'])
    return {
        'model_version':model['modelVersion'], 'primary_family':model['familyLabel'],
        'feature_count':len(model['featureNames']), 'target_short':target_short,
        'target_spoken':target_spoken, 'target_display':target_display,
        'test_windows':f"{metrics['testWindows']:,}", 'test_participants':metrics['testParticipants'],
        'mae':number(f['mae']), 'persistence_mae':number(p['mae']),
        'auroc':number(f['auroc'], 3), 'auprc':number(f['auprc'], 3), 'brier':number(f['brier'], 4),
        'recall':percent(f['recall']), 'precision':percent(f['precision']),
        'false_negative':f'{fn:,}', 'false_positive':f'{fp:,}',
        'coverage':percent(f['intervalCoverage']), 'interval_width':number(f['intervalMeanWidth']),
        'threshold':number(f['threshold'], 3), 'auth_card':auth[0], 'auth_spoken':auth[1],
        'auth_detail':('Public email sign-up and password recovery are intentionally disabled until SMTP/email delivery is configured. Google OAuth is disabled pending provider credentials. Existing-account sign-in is provider-backed; no end-to-end account flow has been verified.'
                       if auth_status == 'configured-unverified' else ''),
        'v4_card':v4_card, 'v4_spoken':v4_spoken, 'model_rows':rows,
    }


def metric_rows(metrics):
    rows = []
    for key, v in metrics['models'].items():
        if key == 'primary':
            continue
        _, fp, fn, _ = counts(v)
        rows.append([v['label'], number(v['mae'], 3), number(v['participantMacroMae'], 3),
                     number(v['auroc'], 3), number(v['auprc'], 3), number(v['brier'], 4),
                     number(v['threshold'], 3), percent(v['recall'])+'%', percent(v['precision'])+'%', fn, fp])
    return rows


def write_card(model, metrics, freeze, ctx):
    selected = metrics['models']['primary']
    rows = table(['Family', '+120 MAE', 'Participant-macro MAE', 'AUROC', 'AP', 'Brier', 'Threshold', 'Recall', 'Precision', 'FN windows', 'FP windows'],
                 metric_rows(metrics))
    patients = table(['Final participant', 'Windows', '+120 MAE', 'Recall', 'Precision', 'Band coverage'],
                     [[v['participant'], v['windows'], number(v['mae']), percent(v['recall'])+'%',
                       percent(v['precision'])+'%', percent(v['intervalCoverage'])+'%'] for v in metrics['byParticipant']])
    horizons = table(['Nominal horizon', 'MAE mg/dL', 'RMSE mg/dL', 'Empirical band coverage', 'Mean band width mg/dL'],
                     [[f"+{v['minutes']} min", number(v['mae']), number(v['rmse']),
                       percent(v['intervalCoverage'])+'%', number(v['intervalMeanWidth'])] for v in selected['byHorizon']])
    text = f"""# AURA Twin — current research model and data card

**Current artifact:** `{model['modelVersion']}`
**Model-file SHA-256:** `{metrics['modelSHA256']}`
**Selected primary family:** {model['familyLabel']}
**Status:** Exploratory research prototype. No clinical validation, treatment recommendation or clinical deployment claim.

## Intended task and population

Forecast CGM at approximately +30, +60, +90 and +120 minutes from the preceding six hours of available observations. The current binary target is:

> {model['targetDefinition']}

Ground truth is the nearest actual recorded CGM observation within ±150 seconds of each nominal horizon. The actual timestamp is retained; outcomes are not interpolated. A rise label uses the latest available current reading, which may be up to 15 minutes old. Overlapping windows are not unique clinical episodes.

The target was chosen by the predeclared **training-only** support audit, not final-test performance. The absolute ≥180 target required at least 200 positive training windows, ≥5% prevalence and positives in at least five training participants. Otherwise, a ≥20 mg/dL rise required at least 100 positives across five participants. If neither rule passed, classification would be disabled. See [label audit](../data/research-label-audit.json).

## Sources and identity boundary

Dynamic observations come from [BIG IDEAs Lab Glycemic Variability and Wearable Device Data, v1.1.3](https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/) on PhysioNet, under the [Open Data Commons Attribution License 1.0](https://physionet.org/content/big-ideas-glycemic-wearable/view-license/1.1.3/). CGM, HR and IBI files are checked against published source checksums. HRV is derived RMSSD from accepted IBI pairs, not a clinical ECG measurement.

The EHR view uses [official Synthea sample records](https://synthetichealth.github.io/downloads.html), pinned to commit `2c7d489eb4c8bc967dbfab3499a0f573818880dc`, and filtered to a chosen 2019-01-01 historical cutoff. These are **different synthetic people**, assigned independently of wearable outcomes. The association is a Composite Research Twin, not matched clinical fusion. [Synthea provenance](SYNTHEA_PROVENANCE.md) documents nullable fields, source rows, selection and minimization.

Matched HbA1c and sex are separate metadata from the wearable study itself. Their association with the wearable participant is real, but the HbA1c measurement date is unspecified. Treating it as available baseline context is an assumption.

No sleep stages, step counts, activity or genetic markers are fabricated. Source timestamps are date-shifted with unspecified timezone; `Z` is a neutral sortable encoding, not proof of UTC collection.

## Patient-aware partitions

| Partition | Participants | IDs | Purpose |
|---|---:|---|---|
| Training | 9 | 001–009 | Fit candidate models and perform target support audit |
| Selection | 2 | 010–011 | Choose configurations and primary family |
| Calibration | 2 | 012–013 | Platt probability map, global F1 policy and residual bands |
| Final | 3 | 014–016 | Report-only evaluation after freeze |

All windows from an identity remain together. Candidate fitting weights participants equally. Candidate selection uses participant-macro metrics. The primary eligible family is selected by +120-minute MAE; classifier hyperparameters are selected by Brier score **within that family**, not by an independent cross-family classifier competition.

Only 16 people are available, with two for selection, two for calibration and three for final evaluation. Many correlated windows do not create a large independent cohort. These results do not support reliable population confidence intervals or broad clinical conclusions.

## Preprocessing and model

Input history is restricted to six hours before the cutoff. CGM alignment is backward-only with at most 15 minutes of carry-forward. Completed five-minute HR means require sufficient source samples; minute-rounded HR is conservatively delayed 60 seconds. RMSSD uses adjacent accepted IBI pairs within the same completed bin, a maximum 10-second pair gap and at least 20 accepted differences. Missing values remain missing and supported tree missing-value routes are used.

The selected histogram-gradient-boosting model uses **{len(model['featureNames'])} features**. Exact features, tree parameters, training references and model sources are in [research-model.json](../data/research-model.json). Two small configurations are compared for each model family. Unmatched Synthea-only and composite-fusion families are negative controls and cannot select the primary model. [Selection results](../data/research-selection.json) preserve all candidates.

Calibration uses Platt logistic mapping. A single threshold, **{ctx['threshold']}**, maximizes F1 on the calibration participants over the declared grid. The same two participants estimate mapping, policy and interval widths. This reuse and the small sample can produce unstable estimates. The policy is not a clinically elicited treatment trigger.

Nominal 90% bands use the calibration absolute-residual quantile separately for each horizon. Final +120-minute coverage is **{ctx['coverage']}%**, with mean width **{ctx['interval_width']} mg/dL**. These are empirical marginal bands, not guaranteed patient-specific or shifted-population coverage.

## Final results

The same **{ctx['test_windows']} eligible windows from three participants** are used for the comparisons below. A deterministic persistence flag is not described as a calibrated probability.

{rows}

### By horizon

{horizons}

### By final participant

{patients}

Further quality slices, calibration bins, ROC/precision-recall points and residual distributions are in [research-metrics.json](../data/research-metrics.json).

## Explanations and quality handling

Grouped reference sensitivity replaces a selected feature group with its training reference and recomputes calibrated risk. The reported percentage-point changes are nonadditive, may create unrealistic combinations, and are neither SHAP values nor causal effects. Displayed EHR fields are not necessarily prediction inputs. The exported feature list is authoritative.

Availability checks can detect some missing/stale data but cannot reliably detect plausible sensor bias. Scenario and robustness outputs are numerical sensitivity tests, not treatment-effect estimates. Future unannounced meals and activity are not inputs.

## Freeze, verification and reproducibility

The model was frozen before processing final participants. [Freeze record](../data/research-freeze.json), [protocol](../data/research-protocol.json), [manifest](../data/research-manifest.json), [source provenance](../data/research-provenance.json) and [validation audit](../data/research-validation.json) describe the sequence and hashes. Hashes are not signatures or independent timestamps.

The pipeline checks source integrity, participant disjointness, prefix truncation, source timestamps and target-time tolerance. Python/JavaScript parity verifies exported inference. See [verification](VERIFICATION.md) for the checks actually executed and any remaining gaps.

```bash
python -m pip install -r ml/requirements.txt
python scripts/ingest_synthea.py --download --as-of 2019-01-01
python scripts/ingest_wearable.py
npm run research:develop
npm run research:freeze
npm run research:evaluate
```

The npm reproduction commands write to isolated `work/reproduced-research` and `work/reproduced-research-cache` directories. Choose new output/work directories for an additional independent run: the trainer deliberately refuses to overwrite a frozen model or reopen a completed final evaluation. Raw data and fitted Python caches belong in ignored `work/`, not the public application bundle.

## Legacy and separate experiment

`aura-synthetic-3.0.0` is a historical simulator benchmark. Its scores must not be presented as current research scores. The independent synthetic V4 experiment uses unchanged simulator labels and fresh identities: {ctx['v4_spoken']}

## Limitations

""" + '\n'.join('- '+v for v in metrics['limitations']) + '\n'
    (DOCS/'MODEL_DATA_CARD.md').write_text(text, encoding='utf-8')


def write_readme(model, metrics, ctx):
    selected = metrics['models']['primary']
    rows = table(['Model family', '+120 MAE mg/dL', 'Recall', 'Precision', 'FN / FP windows'], ctx['model_rows'])
    text = f"""# AURA Twin

### See the patient. Understand what comes next.

**A clinician-oriented Composite Research Twin with actual open research wearables, authentic Synthea EHR context and an inspectable glucose forecast.** Built by **Black Squad**, Amrita Vishwa Vidyapeetham, Chennai.

**Current local rebuild:** `{model['modelVersion']}` · **Primary model:** {model['familyLabel']}. The EHR and wearable records belong to different people. Their target-blind association demonstrates ingestion and interaction, not physiologically matched clinical fusion.

> This is a research prototype, not clinical validation. The final evaluation has only **three participants**. No diagnosis, dosing, treatment or emergency triage recommendation is provided. Missing sensor channels are not invented.

![Current AURA research workspace](docs/assets/dashboard-research.png)

**[Live demo](https://aura-twin-black-squad.vercel.app)** · **[Public repository](https://github.com/DuvvuruDeepakReddy18/aura-twin-black-squad)**. Verification of the current public release is pending. Exact release checks, including the deployed model identity, are listed in [VERIFICATION.md](docs/VERIFICATION.md).

## Run locally

Requires Node.js **22.12 or newer**. The current hosted runtime is Node.js 24.

```bash
npm ci
npm run build
npm start
```

Open **http://localhost:4173**. The bundled research demo requires no account. Authentication status: **{ctx['auth_card']}** See [deployment and configuration](docs/DEPLOYMENT.md).

{ctx['auth_detail']}

```bash
npm test
python -m pip install -r ml/requirements.txt
npm run test:data
```

The final integration suite passed **58 JavaScript tests and 16 Python tests**. Current desktop and narrow-screen UI checks are complete; see the verification record for scope and remaining checks.

## Team

| Role | Name | Roll number |
|---|---|---|
| Leader | Banu Sreya V. | CH.EN.U4ECE23009 |
| Member | Duvvuru Deepak Reddy | CH.EN.U4ECE23015 |

**Team:** Black Squad · **College:** Amrita Vishwa Vidyapeetham, Chennai. Leader phone/email are for the submission platform and are not published in the repository.

## Problem and healthcare use case

A reviewer needs to understand current recorded physiology, possible future glucose and the limits of the prediction. AURA places source context, replay, quality, uncertainty, explanations and a freeze/reveal challenge in one workspace. The model predicts at approximately +30, +60, +90 and +120 minutes.

**Current event:** {model['targetDefinition']}

The target was selected by a predeclared **training-only** support audit. The actual future CGM sample must be within ±150 seconds of the nominal horizon; outcomes are not interpolated. It is not an arbitrary probability or a guaranteed new adverse episode.

## Data origins and identity boundary

- **Wearables:** [PhysioNet BIG IDEAs v1.1.3](https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/), 16 de-identified research participants, actual CGM/HR/IBI with publisher checksum verification.
- **EHR context:** Official Synthea sample CSV, pinned source commit, 16 adult profiles filtered to 2019-01-01. [Provenance and selection](docs/SYNTHEA_PROVENANCE.md).
- **Composite association:** Independent source-ID/UUID rank assignment. These are different people. Unmatched EHR model families are negative controls, excluded from primary selection.
- **Matched study context:** Source HbA1c and sex are linked to wearable participants; HbA1c measurement timing is unspecified and treated as a baseline assumption.
- **Unavailable:** Sleep stages, steps, activity and genetics are not fabricated. RMSSD is derived from accepted IBI differences, not clinical ECG HRV.

## Measured evidence

Participants are split **9 fit / 2 selection / 2 calibration / 3 final**, with all windows from one person kept together. Primary selection uses participant-macro +120-minute MAE. The model and policy are frozen before final evaluation.

{rows}

These results use the same **{ctx['test_windows']} final windows**. FN and FP are overlapping windows, not unique clinical events. Current +120-minute empirical interval coverage is **{ctx['coverage']}%** and mean width **{ctx['interval_width']} mg/dL**. The review threshold **{ctx['threshold']}** is selected on calibration participants, not final outcomes.

The small selection/calibration/final samples limit generalization. See the [current model and data card](docs/MODEL_DATA_CARD.md), [machine-readable metrics](data/research-metrics.json), [protocol](data/research-protocol.json), [freeze record](data/research-freeze.json) and [source manifest](data/research-manifest.json).

The separate [runtime perturbation audit](docs/ROBUSTNESS_AUDIT.md) samples 496 windows and includes withheld forecasts in its denominator. It is not the same evaluation as the 1,859-window model comparison.

## Product and technical stack

React, Vite, React Router, Three.js / React Three Fiber / Drei, a Node.js API, exported numerical tree inference, Python/scikit-learn training and ReportLab submission documents. Supabase authentication is configuration-dependent; demo access remains separate. The current UI exposes recorded sources and the prediction contract. Explanations are nonadditive reference sensitivity, not causal effects or SHAP.

Challenge Lab freezes a cutoff-bounded prediction, reveals original recorded truth, compares persistence and exports evidence. Hashes detect inconsistent artifacts; they do not provide trusted signatures or independent timestamps. The verification record lists exact implemented stress cases and tested UI flows.

## Legacy synthetic evidence

V3 synthetic artifacts remain historical engineering evidence and cannot be numerically compared with the new research target/cohort. The full earlier synthetic application is available locally at **http://localhost:4173/legacy/index.html**, clearly labelled legacy.

The independent V4 experiment has its own protocol and fresh synthetic identities. **{ctx['v4_card']}** It does not validate the open-research model. On the same fresh synthetic cohort it reduced false-positive windows but increased primary false-negative windows. [Same-cohort V4 comparison](docs/SYNTHETIC_V4_EXPERIMENT.md) · [Machine-readable results](data/synthetic-v4-experiment/results.json).

## Submission material

- [Architecture PDF](docs/AURA_Twin_Architecture.pdf)
- [Presentation PDF](docs/AURA_Twin_Presentation.pdf)
- [Timed demonstration runbook](docs/DEMO_RUNBOOK.md)
- [Current model/data card](docs/MODEL_DATA_CARD.md)
- [Source provenance](docs/SYNTHEA_PROVENANCE.md)
- [Verification record](docs/VERIFICATION.md)
- [Requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [Submission checklist](docs/SUBMISSION_CHECKLIST.md)

**[Current demonstration MP4](docs/AURA_Twin_Walkthrough.mp4): 23:52** (1,431.877687 seconds), with 22 chapters matching the current research edition. Duration and complete decoding are verified. The external unlisted video URL remains pending.

## License and attribution

Application code is under the [MIT License](LICENSE). Third-party datasets have their own terms: BIG IDEAs uses the [Open Data Commons Attribution License 1.0](https://physionet.org/content/big-ideas-glycemic-wearable/view-license/1.1.3/); official Synthea sample terms and the [Walonoski et al. citation](https://doi.org/10.1093/jamia/ocx079) are documented separately. [Complete source references](docs/SOURCE_REFERENCES.md) include the original wearable study and platform citations. Application licensing does not replace source-data attribution.
"""
    (ROOT/'README.md').write_text(text, encoding='utf-8')


def write_runbook(slides, ctx):
    segments = []
    elapsed = 0
    for slide in slides:
        duration = max(45, round(len(slide['text'].split())/145*60))
        def stamp(seconds):
            return f'{seconds//60:02}:{seconds%60:02}'
        segments.append([f'{stamp(elapsed)}–{stamp(elapsed+duration)}', slide['slide'], slide['title']])
        elapsed += duration
    text = """# AURA Twin — current research demonstration runbook

This script matches the research edition and its frozen numerical artifacts. Estimated speaking times are planning estimates; the delivered MP4 must be measured and decoded before claiming its duration. Record at least 20 minutes for the competition brief.

## Before recording

1. Build and run the current app. Confirm the model version and source mode.
2. Verify that any displayed account flows match actual provider configuration.
3. Open the presentation and current research UI, not historical synthetic screenshots.
4. Confirm source identity, replay cutoff, threshold and model hash.
5. Use only the bundled de-identified research and synthetic data. Keep private leader contact details and deployment secrets out of the recording.

## Speaking sequence

""" + table(['Estimated time', 'Slide', 'Topic'], segments) + """

The complete narration is in [narration.json](narration.json). Generated transcripts must come from that same file and the final chapter timings.

## 90-second jury path

- 00:00–00:30: Open demo, select a participant and identify composite provenance, research model version and cutoff.
- 00:30–01:00: Inspect forecast, uncertainty and actual inputs; freeze a prediction.
- 01:00–01:30: Reveal recorded outcomes, compare persistence, inspect a supported failure case and export evidence.

## Five-minute interactive path

1. Explain why Synthea context and the wearable participant are different identities.
2. Show one authentic EHR observation and one missing field.
3. Explain the current prediction target and target-time tolerance.
4. Change replay cutoff and inspect the model's available input boundary.
5. Freeze/reveal one prediction; report the result even if persistence wins.
6. Open model evidence and the participant-level limitations.
7. Demonstrate a supported quality/abstention case.
8. Explain which account/persistence flows are configured and verified.

## Recording guardrails

Do not call simulated playback live device monitoring. Do not compare research scores with legacy V3 scores as an improvement. Do not describe source-label events as diagnosed harm. Reference sensitivity is not causal or treatment advice. Missing sleep/steps/genetics must remain unavailable. The public dataset is not securely blinded by hiding the outcome in the UI.

An unlisted upload URL is pending until a real upload exists. The original guidelines require a minimum 20-minute video; satisfy that stricter requirement even though the form screenshot mentions 15–20 minutes.
"""
    (DOCS/'DEMO_RUNBOOK.md').write_text(text, encoding='utf-8')


def write_runtime_audit(model, metrics):
    path = DATA/'research-runtime-audit.json'
    if not path.exists():
        return
    audit = json.loads(path.read_text(encoding='utf-8'))
    if audit['modelSHA256'] != metrics['modelSHA256']:
        raise RuntimeError('Runtime audit belongs to a different model.')
    names = {
        'baseline':'Recorded stream', 'short_gap':'10-minute CGM gap',
        'cgm_dropout':'30-minute CGM gap', 'sensor_dropout':'Sensor dropout',
        'delayed_signal':'CGM values delayed 15 minutes', 'noise':'Alternating ±12 mg/dL noise',
        'missing_hrv':'Missing recent HRV', 'cgm_bias':'+30 mg/dL sensor drift',
        'outlier':'Latest CGM outlier',
    }
    rows = [[names.get(v['mode'], v['mode']), v['windows'], v['forecastAvailable'], v['withheld'],
             number(v['maeOnAvailable']), percent(v['intervalCoverageOnAvailable'])+'%' if v['intervalCoverageOnAvailable'] is not None else 'unavailable']
            for v in audit['cases']]
    body = f"""# Current research runtime perturbation audit

Model: `{model['modelVersion']}` · SHA-256: `{metrics['modelSHA256']}`.

This audit samples **496 windows from the three final participants at 60-minute stride**. It is separate from the main **1,859-window held-out evaluation**. It includes unsuitable inputs so that withheld forecasts remain part of the denominator. Error and interval coverage below are conditional on an available forecast; withholding is not silently counted as correct.

{table(['Input case', 'Windows', 'Available', 'Withheld', 'MAE on available', 'Band coverage on available'], rows)}

The 30-minute gap, two-hour multi-sensor dropout and latest-value outlier cause all sampled forecasts to be withheld. Missing HRV leaves the selected CGM-only model unchanged. Plausible +30 mg/dL bias still permits forecasts and worsens error. These outcomes describe the implemented quality boundary, not a universal sensor-error detector.

## Exact perturbation meanings

- **10-minute CGM gap:** hide the latest two aligned five-minute values; only sufficiently recent past source values may be carried forward.
- **30-minute CGM gap:** hide the latest six aligned values.
- **Sensor dropout:** hide CGM, HR and HRV for the last two hours.
- **CGM values delayed 15 minutes:** replace recent glucose values with readings from 15 minutes earlier while retaining reported timestamps, simulating an unrecognized delay.
- **Alternating noise:** add a deterministic alternating ±12 mg/dL error over the last two hours.
- **Missing recent HRV:** remove the last two hours of derived RMSSD.
- **Sensor drift:** add +30 mg/dL over the last two hours.
- **Latest outlier:** add 500 mg/dL to the latest value to test the range gate.

Original future observations and the **clean current reference** for the rise label remain fixed. The perturbed model can use a different current input, so its rise probability may refer to a different implied absolute future threshold. This distinction is exposed; a perturbation is not an intervention with a measured treatment effect.

Nominal residual bands are unchanged under perturbation. They have not been recalibrated or validated for those corruptions. The audit checks 15 full-history versus physically truncated-prefix outputs; automated tests additionally mutate future rows.

## What-if controls

The current what-if lab recomputes the actual numerical model after CGM offsets between −20 and +20 mg/dL or HR offsets between −20 and +20 bpm. It does not apply a hand-written meal/exercise treatment formula. An HR-only offset leaves the CGM-only primary model unchanged. Changed CGM reference values can change the implied absolute threshold behind a rise probability.

See [machine-readable audit](../data/research-runtime-audit.json), [current model card](MODEL_DATA_CARD.md) and [verification](VERIFICATION.md).
"""
    (DOCS/'ROBUSTNESS_AUDIT.md').write_text(body, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auth-status', choices=['not-configured', 'configured-unverified', 'verified'], default='not-configured')
    parser.add_argument('--no-pdf', action='store_true', help='Write truthful text/narration while final UI screenshots are pending.')
    parser.add_argument('--assets', type=Path, default=DOCS/'assets')
    args = parser.parse_args()
    model, metrics, freeze = read('research-model.json'), read('research-metrics.json'), read('research-freeze.json')
    sha = hashlib.sha256((DATA/'research-model.json').read_bytes()).hexdigest()
    if not (sha == metrics['modelSHA256'] == freeze['modelSHA256']):
        raise RuntimeError('Current research model, metrics and freeze hashes disagree.')
    if metrics['primaryFamily'] != model['primaryFamily']:
        raise RuntimeError('Research primary family disagreement.')
    ctx = context(model, metrics, args.auth_status)
    slides = json.loads((ROOT/'scripts/research_presentation_content.json').read_text(encoding='utf-8'))
    for slide in slides:
        for key in ['title', 'subtitle', 'text']:
            slide[key] = slide[key].format_map(ctx)
        slide['cards'] = [[value.format_map(ctx) for value in row] for row in slide['cards']]
    narration = [{key: slide[key] for key in ['slide', 'title', 'text']} for slide in slides]
    (DOCS/'narration.json').write_text(json.dumps(narration, indent=2, ensure_ascii=False), encoding='utf-8')
    supplement = [{**narration[index], 'slide': i+1} for i, index in enumerate([5, 9, 14, 15, 16, 18])]
    (DOCS/'narration-upgrade.json').write_text(json.dumps(supplement, indent=2, ensure_ascii=False), encoding='utf-8')
    write_card(model, metrics, freeze, ctx)
    write_readme(model, metrics, ctx)
    write_runbook(slides, ctx)
    write_runtime_audit(model, metrics)
    if not args.no_pdf:
        build(slides, ctx, DOCS, args.assets)
    print(f"Research documents: {len(slides)} slides, {sum(len(s['text'].split()) for s in slides):,} narration words.")
    print(f"Model: {model['modelVersion']} / {sha}")
    print(f"Authentication status: {args.auth_status}; screenshots: {args.assets}")


if __name__ == '__main__':
    main()

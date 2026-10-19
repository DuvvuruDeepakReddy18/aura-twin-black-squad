# AURA Twin

### See what comes next. Inspect the evidence.

**A working synthetic patient digital twin that fuses historical EHR context with wearable time series to forecast glucose two hours ahead.** Built by **Black Squad**, Amrita Vishwa Vidyapeetham, Chennai, for Happiest Health Phase 1.

**Current model: `aura-synthetic-2.0.0`.** We improved the actual model after finding routine-shift failures: clock-free history features, varied routine training, nonlinear boosting, separate selection/calibration identities, and 80 new final-test identities. On the same fresh cases, two-hour MAE improved from **18.30 to 11.62 mg/dL** (36.5% lower). All six routine families improved against frozen v1; they were represented during training. This is synthetic fresh-patient evidence, not clinical or unseen-routine validation.

![Current AURA Twin workspace](docs/assets/dashboard-current.png)

> Every patient and observation is generated. The app does not diagnose, prescribe or recommend treatment, and the model receives no future meal schedule. Public GitHub/video URLs remain pending until published and verified.

## Run locally

Requires **Node.js 20+**. No npm dependency installation, API key or internet connection is needed after downloading the package.

```bash
node server.mjs
```

Open **http://localhost:4173**. On Windows, double-click `START-DEMO.cmd`. The server binds to localhost by default; this is a research demo without clinical authentication.

```bash
npm test              # current JavaScript/model/API/receipt checks
npm run test:data     # Python generator and feature-contract checks
```

Optional Docker launch: `docker build -t aura-twin .`, then `docker run --rm -p 127.0.0.1:4173:4173 aura-twin`.

## Team and college

| Item | Detail |
| --- | --- |
| Team | Black Squad |
| College | Amrita Vishwa Vidyapeetham, Chennai |
| Leader | Banu Sreya V. |
| Member | Duvvuru Deepak Reddy |
| Project | AURA Twin — Multimodal Patient Digital Twin |

The leader's phone and email are provided separately for the submission platform, not published in the repository.

## Problem statement and healthcare use case

A current glucose reading lacks the historical context and recent trajectory needed to interpret a changing state. AURA combines the fictional patient's historical EHR with a simulated wearable stream, provides a future estimate, and lets a clinician inspect its evidence.

**Task:** numerical glucose at +30,+60,+90,+120 minutes and probability of **glucose ≥180 mg/dL at exactly +120 minutes**. It does not predict any excursion within the next two hours. Inclusive 180 is an explicit prototype convention; the common 70–180 mg/dL context comes from [NIDDK](https://www.niddk.nih.gov/health-information/professionals/diabetes-discoveries-practice/clinical-targets-for-continuous-glucose-monitoring-data). Individual clinical targets are outside scope.

## Implemented product

- Clinician overview, patient search/switching, record view, model evidence and Challenge Lab.
- Five-minute replay, pause/scrub controls, four-horizon forecasts and descriptive residual bands.
- Fusion through 53 clock-free, past-only predictors combining EHR, CGM, HR/HRV, activity, sleep and previous-day observations.
- Missing/stale-data checks with explicit degraded states and abstention.
- Group-reference sensitivity for the tree model: nonadditive changes in risk percentage points, not SHAP or causal effects.
- An illustrative meal/activity sandbox; arithmetic forecast adjustment, trained risk unchanged.
- Local notes, alert acknowledgements and downloadable patient summary.
- Freeze → reveal → compare model/persistence → export receipt, with clean replay, 10-minute gap, 30-minute dropout and plausible CGM bias.
- Offline receipt verification, reproducible training, fresh final evaluation and same-case baseline comparisons.

The interface is a conceptual clinician workflow implemented as a runnable prototype. No usability benefit or clinical outcome improvement has been measured.

## Synthetic data and privacy

Our own seeded [generator](ml/generate.py) creates historical EHR and five-minute glucose, HR, HRV, steps and asleep/awake observations. No real patient records, PHI, Synthea exports, MIMIC data or device accounts were used. Genetic-marker and medication-history text are display context only. Sleep is not clinical sleep-stage classification.

The current experiment uses 432 identities, four days per identity and six routine variants: regular, meals delayed 2 h/4 h, jittered meals, day-varying timing/skips, and variable sleep/activity/meals. Variants of a person are correlated and stay in the same partition. Eight demo records and default cutoffs follow a fixed selection rule rather than favorable final outcomes.

The simulator's future meal schedule and latent state are **not inference inputs**. Previous-day horizon-aligned glucose is already observed 22–23.5 hours earlier; it assumes some recurrence and cannot reveal today's unannounced meal. Historical relationships and contemporaneous HR meal effects are simulator assumptions that may favor prediction.

## Technical stack

| Layer | Current implementation |
| --- | --- |
| Frontend | HTML/CSS, vanilla JavaScript, SVG |
| Runtime | Native Node.js HTTP server; zero third-party runtime packages |
| Training | Python, NumPy, scikit-learn |
| Forecast | Four histogram gradient boosting absolute-error regressors |
| Event risk | Histogram gradient boosting classifier + separate Platt calibration |
| Inputs | 53 clock-free past-only features; no future meals |
| Uncertainty | Per-horizon 90th-percentile absolute residuals on calibration identities |
| Explanation | Group replacement by training medians; calibrated-risk sensitivity |
| Verification | Python/JavaScript parity, prefix/clock invariance, API/challenge/receipt tests |
| Documentation | Current PDFs, model/data card, protocol, narrated walkthrough and jury guides |

## Evaluation protocol

| Role | Identities | Windows | Purpose |
| --- | ---: | ---: | --- |
| Fit | 256 | 107,520 | Fit candidates/ablations; 60 min stride |
| Select | 48 | 20,160 | Choose regression/classifier family; 60 min stride |
| Calibrate | 48 | 40,320 | Probability mapping, bands and threshold; 30 min stride |
| Final test | 80 | 67,200 | Report after freeze; 30 min stride |

Final identities **SYN-1001–SYN-1080** were generated after the model/calibration/bands/threshold were frozen. The saved hash is checked unchanged after evaluation. This local code sequence is auditable; it is not external preregistration or a trusted timestamp. All six routine families occur in training. See [protocol](data/robustness-protocol.json), [selection evidence](data/selection-results.json), [audit sequence](data/training-audit.json), [full metrics](data/metrics.json) and [robustness report](data/robustness.json).

## Current measured outcome

| Model | +120 min MAE mg/dL↓ | AUROC↑ |
| --- | ---: | ---: |
| **Current fused** | 11.62 | 0.936 |
| Sensors only | 11.73 | 0.929 |
| EHR only | 18.48 | 0.834 |
| Persistence | 20.32 | 0.583 |
| Frozen v1 on same cases | 18.30 | 0.848 |

The added EHR MAE gain is **0.107 mg/dL**, about 0.9%, and is modest. The larger gain against v1 comes from changed history features, routine augmentation and nonlinear capacity. Paired patient-bootstrap intervals are reported; overlapping windows are not independent samples. Persistence's hard 0/1 event output is not a calibration-equivalent comparator.

Current fused MAE patient-bootstrap 95% interval: **11.01–12.21 mg/dL**. The review threshold is **0.16**, fixed on calibration data. Final recall is **78.73%**, precision **40.50%**, with 1,059 false-negative and 5,758 false-positive windows. Event prevalence is 7.41%. These are correlated windows, not distinct clinical alarm episodes.

| Routine | Current MAE | Frozen v1 MAE | Persistence MAE | Band coverage | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Regular routine | 10.06 | 10.88 | 21.68 | 92.28% | 85.84% | 50.26% |
| Meals delayed by 2 hours | 9.72 | 21.92 | 21.47 | 92.84% | 88.91% | 47.77% |
| Meals delayed by 4 hours | 9.29 | 22.92 | 19.57 | 93.34% | 89.60% | 43.09% |
| Irregular meal timing | 13.97 | 17.05 | 21.11 | 85.31% | 67.99% | 39.47% |
| Daily timing changes and skipped meals | 13.12 | 17.64 | 19.45 | 86.75% | 76.44% | 34.19% |
| Variable sleep, activity and meals | 13.57 | 19.39 | 18.65 | 86.01% | 63.93% | 29.37% |

At +120 min, nominal 90% bands have **89.42%** final marginal coverage and **61.66 mg/dL** mean width. Broader bands and weaker variable-routine recall remain limitations. Coverage is not guaranteed per patient or under distribution shift. See the [model/data card](docs/MODEL_DATA_CARD.md) and [current robustness audit](docs/STRESS_AUDIT.md). Historical v1 artifacts remain under `data/baseline-v1/`; the old 10.95 result is not the current aggregate.

## Challenge Lab and reproducible receipts

Choose a supported patient/cutoff/case, then **Freeze prediction → Reveal recorded future → Download receipt**. Inference receives a physically truncated, optionally perturbed prefix. The server snapshots original future readings only after inference; reveal compares the frozen output without recomputing it. The dataset is public, so this is a computation boundary, not secure study blinding.

Selected-window scores are distinct from cohort metrics. Persistence sees the same perturbed/carried-forward current value. Missing futures and abstention have no fabricated score. Plausible sensor bias can pass freshness checks.

```bash
node scripts/verify_receipt.mjs path/to/receipt.json
```

The verifier checks raw-model-byte SHA-256, canonical-prefix SHA-256 and recomputed predictions/reveals against packaged data. Hashes are not signatures, trusted timestamps or clinical audit certification. Sessions are memory-only, expire after one hour, and are capped at 128; downloaded receipts remain independently checkable.

## Reproduce training

Python is optional for the shipped dashboard. To reproduce development:

```bash
python -m venv .venv
# Activate the environment for your platform.
python -m pip install -r ml/requirements.txt
npm run train
npm test
npm run test:data
```

`npm run train` executes `ml/train_robust.py`. The fixed seed is 20261019. `npm run train:legacy` writes separately under `data/baseline-v1-retrained` and cannot overwrite the active model. Reproducing training after seeing the final results does not make those IDs an untouched new test set for subsequent tuning. A new development cycle requires another genuinely fresh final cohort.

## API and data contract

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Health/version and synthetic flag |
| GET | `/api/patients`, `/api/patients/:id` | Packaged fictional records |
| GET | `/api/metrics` | Current full evaluation |
| GET | `/api/robustness` | Same-case comparisons and paired intervals |
| GET | `/api/stress` | Current six-routine compact results |
| POST | `/api/predict` | Past-only prediction from stored or supplied record |
| GET | `/api/challenge/modes` | Sensor case definitions |
| POST | `/api/challenge` | Freeze patient/cursor/mode |
| POST | `/api/challenge/reveal` | Compare frozen prediction with recorded future |

Use `{"patientId":"<API patient ID>","cursor":600}` or `{"patient":<record>,"cursor":600}` for prediction. New input is validated in memory and not persisted. See [data/SCHEMA.md](data/SCHEMA.md).

## Required submission artifacts

- [Current architecture PDF](docs/AURA_Twin_Architecture.pdf)
- [Current 22-slide presentation PDF](docs/AURA_Twin_Presentation.pdf)
- [Current Challenge Lab/evidence supplement PDF](docs/AURA_Twin_Challenge_Lab.pdf)
- [Full walkthrough narration](docs/narration.json) and [video transcript](docs/VIDEO_TRANSCRIPT.md)
- [Demo runbook](docs/DEMO_RUNBOOK.md), [three-minute jury challenge](docs/JURY_CHALLENGE_SCRIPT.md), [differentiation and pitch](docs/DIFFERENTIATION.md)
- [Model/data card](docs/MODEL_DATA_CARD.md), [jury Q&A](docs/JUDGE_QA.md), [verification](docs/VERIFICATION.md)
- [Submission checklist](docs/SUBMISSION_CHECKLIST.md), [requirements map](docs/REQUIREMENTS_TRACEABILITY.md), [document/video source](scripts/README.md)
- [MIT license](LICENSE). Dependencies retain their own licenses.

**Current video:** [Full narrated walkthrough — 25 minutes 10.6 seconds](docs/AURA_Twin_Walkthrough.mp4). The current 22-slide recording includes the improved model, fresh-patient evidence and Challenge Lab. It uses actual current UI screenshots and a disclosed locally synthesized voice. Verified duration: 1,510.580957 seconds; full decoding passed. This single current recording exceeds the required 20-minute minimum and supersedes the historical clips. The public/unlisted upload URL is still pending.

**Public GitHub URL: PENDING. Public/unlisted video URL: PENDING.** Publish the repository as Public, upload the current video, insert real links, and test access while signed out. The local folder is `Black Squad_Amrita Vishwa Vidyapeetham Chennai`.

## Limits and related work

Synthetic improvement is not clinical robustness. Unannounced meals, abrupt changes, plausible sensor bias, different generators/devices, medication effects and real-world complexity remain unresolved. Local notes and acknowledgements are demo state. There is no clinical authentication, outcome study, compliance certification or treatment recommendation.

Prior glucose twin and counterfactual work exists, including [GlyTwin](https://arxiv.org/abs/2504.09846); we make no first-in-field claim or cross-dataset accuracy comparison. The [npj Digital Medicine VVUQ perspective](https://www.nature.com/articles/s41746-025-01447-y) motivates careful verification and validation; it does not certify this implementation. [Synthea](https://synthetichealth.github.io/synthea/) is an optional future integration, not a source used here.

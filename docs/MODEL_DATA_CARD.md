# AURA Twin — current model and data card

**Artifact:** `aura-synthetic-3.0.0` · **Raw model-file SHA-256:** `87fb0df0832c2db76b03c55c81298ab717200c3dc60048b9b4586dc7061d81b4`.

Black Squad, Amrita Vishwa Vidyapeetham, Chennai. This card describes the current model. Historical artifacts remain in `data/baseline-v1/` and `data/baseline-v2/`. Historical scores must not be presented as current results.

## Purpose and data boundaries

Forecast glucose at +30, +60, +90 and +120 minutes from synthetic EHR context plus wearable history. The binary target is **glucose ≥180 mg/dL at exactly +120 minutes**, not any excursion during the interval or necessarily a new onset. Inclusive 180 is an engineering convention; individualized clinical targets are outside scope.

The repository's own seeded simulator supplies all data. No real patient records, PHI, device accounts, Synthea exports or MIMIC data are used. No diagnosis, dosing, treatment, emergency triage, clinical efficacy or legal-compliance certification is claimed.

Static predictors are age, BMI, HbA1c, LDL and diabetes duration. Dynamic observations are CGM, HR, HRV, interval steps and asleep/awake flags at five-minute cadence. Names, sex, diagnosis/medication text and arbitrary genetic markers are display context, not predictors. Sleep is not validated sleep-stage classification. HR includes a contemporaneous simulated meal-response term. That is available-time sensing, but it may favor multimodal inference under this designed generator; it does not validate meal detection with real consumer HR.

## Population, split and freeze

There are 1,064 distinct development/final identities, each generated for four days. Six familiar routine families are regular timing, meals delayed two hours, meals delayed four hours, 1.5-hour timing jitter, day-varying shifts/skips, and variable daily sleep/activity/meals. The separate withheld combination uses a three-hour meal shift, one-hour jitter, daily-shift SD 1.4 hours, skip probability 0.25 and variable sleep/activity. Its factors are familiar; that exact combination was absent from development. It is not unseen physiology.

| Role | Identities | Windows | Use |
|---|---|---|---|
| Fit | 768 | 322,560 | Candidate fitting; 60-minute stride |
| Select | 80 | 67,200 | Candidate choice; 30-minute stride |
| Calibrate | 96 | 80,640 | Probability mapping, residual bands and global policy |
| Primary final | 120 | 100,800 | Six familiar families; reporting only |
| Withheld combination | 120 | 16,800 | Same final identities; separate stress result |

Fit indices are 0–767; selection 1200–1279; calibration 1400–1495; final 2000–2119 (`SYN-2001` through `SYN-2120`). Every window and routine variant for one identity stays in that partition. The primary and withheld-combination results reuse the same 120 final identities; they are not 240 independent people. These final identities were not used in the earlier inspected v2 evaluation.

Model selection, calibration, policy and interval bytes are frozen and hashed before final identities and their withheld combination are generated. The audit checks the generator/protocol/model consistency. This is a locally auditable sequence, not third-party preregistration, secure blinding or an independent timestamp. No final result is used to choose a new model. See the [protocol](../data/robustness-protocol.json), [selection record](../data/selection-results.json), [freeze record](../data/model-freeze.json) and [training audit](../data/training-audit.json).

## Model selection and feature construction

The current model uses 108 clock-free, strictly past-derived features. They include the earlier 53 features plus detailed lagged trajectories, fitted slopes, change direction/frequency, ranges, time since recent extrema, threshold occupancy, normalized HR/HRV and recent activity/wake history. Previous-day horizon-aligned observations are at t+h−24 hours: the +120-minute reference was measured 22 hours before the cutoff. No future meal, absolute clock value, hidden simulator state or routine label enters inference. Full feature order and definitions are in `data/SCHEMA.md` and `data/model.json`.

Three HGB candidate configurations are compared on selection identities. Regression minimizes +120-minute MAE. Classification minimizes the worst FP/FN count ratio to frozen v2 across overall, pooled irregular, and variable-routine windows, with one global threshold; ties use the average ratio then Brier score. This decision-aligned objective is a prototype design choice, not a clinically elicited cost function.

| Setting | Four regressors | Event classifier |
|---|---|---|
| id | rich_deep | rich_balanced |
| max_iter | 360 | 300 |
| max_leaf_nodes | 63 | 31 |
| min_samples_leaf | 100 | 80 |
| learning_rate | 0.05 | 0.05 |
| l2_regularization | 20.0 | 15.0 |
| irregularWeight | 2.0 | 2.0 |

Regressors use absolute-error loss. Both chosen configurations use 127 histogram bins, disabled early stopping and the fixed experiment seed. Irregular sample weights apply to development routine families 3–5; they are fitting weights, not a routine label at inference. Candidate selection is followed by separate calibration identities. A Platt logistic map with C=100 calibrates raw classifier scores. The final single threshold minimizes the same worst FP/FN ratio on calibration identities over a 0.0025 grid. It is **0.1550**. Calibration and policy estimation share that calibration partition; final evaluation remains separate. A lower Brier score alone would not establish better calibration or fewer missed and false-positive windows.

Tree inference uses raw features and exported nodes; compatibility `mean`/`scale` fields do not standardize the trees. Training medians define explanation references. Python/JavaScript parity checks the exported calculation.

## Primary fresh final result

The primary comparison equally weights six familiar routine families and 120 fresh identities: **100,800 correlated windows**, with event prevalence **6.49%**. Frozen v2 and all current ablations are evaluated on identical windows at their own frozen policies. Counts are windows, not deduplicated clinical events or alarms per day.

| Model | +120 MAE | AUROC | AP | Brier | Policy | Recall | Precision | FN windows | FP windows |
|---|---|---|---|---|---|---|---|---|---|
| Current fused | 10.850 | 0.9340 | 0.5648 | 0.0400 | 0.1550 | 74.47% | 37.34% | 1,669 | 8,170 |
| Frozen v2 | 11.392 | 0.9243 | 0.5211 | 0.0422 | 0.1600 | 73.36% | 35.46% | 1,742 | 8,730 |
| Sensors only | 10.925 | 0.9316 | 0.5546 | 0.0406 | 0.1475 | 75.41% | 35.99% | 1,608 | 8,770 |
| EHR only | 17.904 | 0.8199 | 0.1841 | 0.0555 | 0.1600 | 35.09% | 19.51% | 4,244 | 9,466 |
| Persistence | 20.081 | 0.5506 | 0.0800 | 0.1090 | 0.5000 | 15.94% | 15.96% | 5,496 | 5,487 |

Current confusion matrix: TN 86,092; FP 8,170; FN 1,669; TP 4,869. The primary point estimates improve modestly, but the paired 95% interval for the FN difference includes zero. In the withheld combination, FN increases from 324 to 330. Therefore this is a mixed synthetic result, not uniform or statistically established missed-event improvement. Persistence copies current glucose and uses a hard 0/1 event prediction; its probability scores are not a calibration-equivalent comparator. Do not compare these results with an older model's original-cohort score as though the cohorts were identical.

Paired decision differences are current v3 minus frozen v2. Negative differences favor v3 for FP/FN counts; positive differences favor v3 for recall/precision. Recall/precision differences below are fractions, not percentage points. Patient bootstrap resamples identities and keeps all their routine variants and windows paired.

| V3 minus frozen V2 | Observed difference | Patient-bootstrap 95% interval |
|---|---|---|
| falsePositiveWindows | -560.00000 | -980.02500 to -157.97500 |
| falseNegativeWindows | -73.00000 | -192.02500 to 27.02500 |
| recall | 0.01117 | -0.00495 to 0.02794 |
| precision | 0.01884 | 0.00966 to 0.02931 |

| Comparator | V3 minus comparator MAE | Patient-bootstrap 95% interval |
|---|---|---|
| legacyV2 | -0.5428 | -0.6039 to -0.4865 |
| sensorOnly | -0.0749 | -0.0971 to -0.0537 |
| persistence | -9.2310 | -9.7314 to -8.7552 |

The EHR fusion increment must be read from the sensor-only comparison; the requirements do not imply a large EHR gain. Synthetic confidence intervals do not quantify uncertainty about transfer to clinical data.

## Every routine, including the separate withheld combination

Each row has 16,800 windows from the same 120 final identities. The last row is excluded from the primary aggregate. Inspect both error types; aggregate gains do not establish improvement for every case or window.

| Routine | V2 → V3 MAE | V2 → V3 FN | V2 → V3 FP | V3 recall | V3 precision | V3 band coverage |
|---|---|---|---|---|---|---|
| Regular routine | 9.86 → 9.38 | 211 → 212 | 1,207 → 1,134 | 82.57% | 46.96% | 93.26% |
| Meals delayed by 2 hours | 9.52 → 9.10 | 164 → 159 | 1,366 → 1,370 | 85.64% | 40.90% | 93.80% |
| Meals delayed by 4 hours | 9.03 → 9.01 | 132 → 142 | 1,332 → 1,195 | 84.58% | 39.46% | 93.64% |
| Irregular meal timing | 13.77 → 13.05 | 491 → 452 | 1,541 → 1,384 | 65.26% | 38.02% | 86.76% |
| Daily timing changes and skipped meals | 12.80 → 11.97 | 324 → 313 | 1,627 → 1,490 | 69.13% | 31.99% | 88.52% |
| Variable sleep, activity and meals | 13.37 → 12.59 | 420 → 391 | 1,657 → 1,597 | 60.06% | 26.91% | 87.62% |
| Held-out combination of shifted and variable routines | 12.64 → 12.07 | 324 → 330 | 1,657 → 1,624 | 60.99% | 24.11% | 88.89% |

The withheld combination's per-model metrics and paired uncertainty are preserved in `data/robustness.json`. It is a held-out combination of familiar factors, not a real-world external validation dataset.

## Target-specific slices

| Slice | Windows | V2 → V3 FN | V2 → V3 FP | V3 recall | V3 precision |
|---|---|---|---|---|---|
| currently_below_180 | 94,271 | 1,500 → 1,460 | 7,969 → 7,469 | 73.44% | 35.08% |
| currently_at_least_180 | 6,529 | 242 → 209 | 761 → 701 | 79.94% | 54.30% |
| rising | 38,926 | 687 → 646 | 3,022 → 2,750 | 76.88% | 43.85% |
| falling_or_flat | 61,874 | 1,055 → 1,023 | 5,708 → 5,420 | 72.68% | 33.42% |

“Currently below 180” still means an exact +120-minute threshold outcome, not the time of first crossing. “Already high” can include persistence or resolution of an existing elevation. Rising/falling slices use past slope only. These slices overlap and are descriptive, not independent experiments.

## Residual bands and quality

The 90th percentile of absolute calibration errors defines a symmetric descriptive band at each horizon. Nominal 90% is a marginal target, not a guarantee for an individual, subgroup, routine or shifted population. Read width alongside coverage. No scenario-specific coverage is claimed for arithmetic what-if offsets.

| Horizon min | MAE mg/dL | RMSE mg/dL | Band coverage | Mean width mg/dL |
|---|---|---|---|---|
| +30 | 4.307 | 7.926 | 90.09% | 15.37 |
| +60 | 7.436 | 13.999 | 90.19% | 35.00 |
| +90 | 9.517 | 16.464 | 90.48% | 54.59 |
| +120 | 10.850 | 17.684 | 90.60% | 61.76 |

Runtime forward-fills short continuous-sensor gaps and imputes missing interval steps/sleep as zero. It abstains for fewer than 24 hours of history, more than 20% missing channel values in recent two hours or trailing 24 hours, CGM older than 15 minutes, or HR/HRV older than 60 minutes. Null risk is not 0% risk. Plausible sensor bias can pass freshness checks. Missingness handling is a guardrail, not a trained fault detector.

## Explanation, scenarios and reproducibility

Group-reference sensitivity replaces every raw feature in one group with its training median and reports original minus reference calibrated probability in percentage points. It is nonadditive, is not SHAP, may form unrealistic reference combinations, and is not causal attribution. The meal/activity sandbox applies hand-authored arithmetic offsets while preserving trained baseline risk. It does not infer intervention efficacy or use actual future meals.

Challenge Lab freezes a truncated input and prediction before revealing original recorded futures. Clean, short-gap, dropout and biased-sensor cases expose different failure modes. Local sessions use bounded memory; hosted sessions use temporary authenticated encryption and allow only bundled synthetic patient IDs. The downloaded JSON omits the transport token. Raw model and canonical input hashes support offline consistency checking; they are not signatures or independent timestamps. See [deployment boundaries](DEPLOYMENT.md).

## Limits and reproduction

Unknown future meals remain difficult to anticipate. The simulator's physiology, EHR associations and sensor responses are authored assumptions. Medication effects, complex comorbidity, illness, pregnancy, real device behavior, clinical outcomes and usability benefits remain unvalidated. A better benchmark does not establish clinical robustness or safe treatment. No notification-cooldown policy is evaluated as a substitute for classifier improvement.

The current training/reproduction commands, artifact hashes and completed checks are in the README and [verification record](VERIFICATION.md). The recorded environment is Python 3.12.2, NumPy 2.4.4, scikit-learn 1.9.0. Preserve archived baselines when reproducing the comparison.

Primary context: [NIDDK CGM target discussion](https://www.niddk.nih.gov/health-information/professionals/diabetes-discoveries-practice/clinical-targets-for-continuous-glucose-monitoring-data), [scikit-learn decision-threshold guidance](https://scikit-learn.org/stable/modules/classification_threshold.html), [probability calibration](https://scikit-learn.org/stable/modules/calibration.html), and [Ramkissoon et al. on unannounced-meal detection and tradeoffs](https://pmc.ncbi.nlm.nih.gov/articles/PMC5876595/). The meal-detection paper concerns observing a meal response, not predicting an unobserved future meal. [Synthea](https://synthetichealth.github.io/synthea/) is a possible future integration, not a source used here. None of these sources validates this prototype.

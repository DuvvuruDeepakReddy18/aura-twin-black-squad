# AURA Twin — current model and data card

**Artifact:** `aura-synthetic-2.0.0` · **Model SHA-256:** `a67d3a6abd84df76f3cbbbb30e35a10f0845417b7b12bbb09df83c398ef317a4`.

This card describes the current robustness upgrade. Historical v1 results belong to `data/baseline-v1/`; its old 10.95 mg/dL result is not the current benchmark. No real patients, PHI, hospital data, Synthea output, MIMIC data or device accounts were used.

## Purpose and boundaries

Black Squad, Amrita Vishwa Vidyapeetham, Chennai, built a synthetic proof of concept of historical EHR/wearable fusion and clinician-oriented review. Forecasts are at +30,+60,+90,+120 minutes; the event is **glucose ≥180 mg/dL at exactly +120 minutes**, not any excursion during the next two hours. Inclusive 180 is the prototype convention; individualized clinical targets are outside scope.

The model is not intended for diagnosis, dosing, treatment, emergency triage or autonomous clinical alerts. No clinical efficacy, safety or legal-compliance certification is claimed.

## Generated data and experiment

The repository's seeded simulator creates 432 distinct identities, each with four days at five-minute cadence and six routine variants. There are 2,592 patient/routine trajectories; variants are not independent people. The six families are regular timing, meals delayed 2 h, meals delayed 4 h, meal-time jitter 1.5 h SD, day-varying timing with skips, and variable daily sleep/activity/meals. All six families appear during development. The final result is **fresh-identity generalization within this declared mixture**, not validation on unseen routine families.

Static prediction inputs are age, BMI, HbA1c, LDL and diabetes duration. Dynamic observations are CGM, HR, HRV, interval steps and asleep/awake flags. Arbitrary genetic markers, diagnosis/medication text, names and sex are display context, not predictors. Sleep is not validated stage classification. HR contains a contemporaneous synthetic meal response; no future meal schedule or latent simulator state is provided to inference.

The generator and features were designed after inspecting v1 failures. Training identity indices 0–255 can overlap earlier development identities. **Final indices 1000–1079 (SYN-1001…SYN-1080) are new** and absent from the old cohort. Eight demo records and their default cutoffs are selected by a fixed rule, not by favorable final predictions.

## Partition and freeze protocol

| Role | Identities | Windows | Use |
| --- | ---: | ---: | --- |
| Fit | 256 | 107,520 | Fit candidates and ablations; 60 min stride |
| Select | 48 | 20,160 | Choose regression/classifier family; 60 min stride |
| Calibrate | 48 | 40,320 | Platt mapping, residual bands, policy; 30 min stride |
| Final test | 80 | 67,200 | Reporting only after freeze; 30 min stride |

Every variant and window for one identity remains in its partition. Selection minimizes pooled +120 min MAE for regression and uncalibrated Brier for classification on selection identities only. Separate calibration identities fit the probability mapping, residual widths and review policy. The exported model bytes and SHA-256 are recorded **before final identities are generated**; code asserts the model bytes remain unchanged after final evaluation. This is a locally auditable sequence, not independent preregistration or a trusted external timestamp.

See `data/robustness-protocol.json`, `data/selection-results.json`, and `data/training-audit.json`. There are 67,200 final windows across 80 identities and 6 variants, equally weighted. Final event prevalence is 7.41%. Repeated windows and variants are correlated. Bootstrap intervals resample identities and preserve paired variants.

## Model and input construction

The selected model is histogram gradient boosting: four separate absolute-error regressors and one event classifier, 160 iterations, 31 leaves, 0.07 learning rate, 60 minimum samples per leaf, regularization strength 10 and 63 bins. Its comparator during selection was a clock-free StandardScaler + Ridge (alpha 50) / logistic (C 0.3) pipeline. The tree model consumes raw features; the exported `mean` and `scale` compatibility fields do not standardize tree inference.

There are 53 clock-free features. They include glucose lags, short- and long-window summaries, slopes, acceleration, quantiles, EHR context, HR/HRV, steps/sleep, and previous-day observations aligned to each forecast horizon. `priorDay120` is observed at t−22 h; it is not future knowledge. The recurrence assumption can fail after a routine change. Full order is `data/model.json.featureNames` and `data/SCHEMA.md`.

The event classifier uses Platt calibration (logistic C 100) on separate calibration identities. Exact tree nodes, baseline predictions, calibrated probability parameters, reference medians and feature groups are exported for JavaScript inference. Future observations are labels only. Missingness handling is a runtime guardrail, not a trained sensor-fault model.

## Measured fresh final results

| Model | +120 MAE mg/dL | AUROC | Average precision | Brier |
| --- | ---: | ---: | ---: | ---: |
| Current fused | 11.6224 | 0.9363 | 0.5974 | 0.0436 |
| Sensors only | 11.7295 | 0.9292 | 0.5776 | 0.0448 |
| EHR only | 18.4828 | 0.8337 | 0.2138 | 0.0615 |
| Persistence | 20.3226 | 0.5833 | 0.1095 | 0.1138 |
| Frozen v1 on same new cases | 18.2976 | 0.8482 | 0.3246 | 0.0737 |

Persistence copies the current glucose and has a hard 0/1 event output; its probability scores are not a calibration-equivalent comparator. The frozen v1 row above is evaluated on exactly the same new cases. Do not substitute its old regular-cohort result for this fair comparison.

Current fused MAE patient-bootstrap 95% interval: **11.008–12.212 mg/dL**. Paired mean-error differences use current fused minus comparator, so negative values favor current fused:

| Comparator | MAE difference | Patient-bootstrap 95% interval |
| --- | ---: | --- |
| legacyV 1 | -6.675 | -7.153 to -6.177 |
| sensorOnly | -0.107 | -0.150 to -0.059 |
| persistence | -8.700 | -9.289 to -8.106 |

## Routine-specific results

| Routine | Current MAE | Frozen v1 MAE | Persistence MAE | Nominal 90% coverage | Recall at fixed policy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular routine | 10.06 | 10.88 | 21.68 | 92.28% | 85.84% |
| Meals delayed by 2 hours | 9.72 | 21.92 | 21.47 | 92.84% | 88.91% |
| Meals delayed by 4 hours | 9.29 | 22.92 | 19.57 | 93.34% | 89.60% |
| Irregular meal timing | 13.97 | 17.05 | 21.11 | 85.31% | 67.99% |
| Daily timing changes and skipped meals | 13.12 | 17.64 | 19.45 | 86.75% | 76.44% |
| Variable sleep, activity and meals | 13.57 | 19.39 | 18.65 | 86.01% | 63.93% |

These families were represented in training. No case is hidden or removed for underperformance. Per-case paired intervals and all ablations are in `data/robustness.json`.

## Review threshold and residual uncertainty

The fixed review threshold is **0.16**, chosen as the highest 0.01 grid threshold meeting at least 80% recall on calibration identities. Final recall is **78.73%**, precision **40.50%**. Confusion counts are TN 56,464, FP 5,758, FN 1,059, TP 3,919. These are correlated windows, not deduplicated clinical events or alarms. Metrics at the conventional 0.50 threshold are also retained in `metrics.json`.

Per-horizon 90th-percentile absolute calibration residuals define symmetric descriptive bands. They are marginal estimates, not individual coverage guarantees or formal clinical safety bounds. Width and coverage must be read together, particularly for irregular routines.

| Horizon min | MAE mg/dL | RMSE mg/dL | Final band coverage | Mean band width mg/dL |
| --- | ---: | ---: | ---: | ---: |
| +30 | 4.595 | 8.304 | 89.54% | 16.62 |
| +60 | 7.840 | 14.311 | 89.74% | 36.95 |
| +90 | 10.180 | 17.101 | 89.44% | 55.13 |
| +120 | 11.622 | 18.577 | 89.42% | 61.66 |

## Explanation and scenario semantics

For the current tree model, drivers are **group-reference sensitivity**, not SHAP or additive log-odds attribution. Replace all raw features in a group with training medians, recompute calibrated probability, and report original minus reference risk in percentage points. Group effects do not sum to the output; reference combinations can be unrealistic. They are not causal treatment effects.

The meal/activity sandbox remains illustrative arithmetic. It does not provide actual future meals to the predictor; trained baseline probability is unchanged. Scenario-shifted bands have no measured scenario coverage. No medication guidance or learned intervention efficacy is produced.

## Quality gates and remaining failure modes

The runtime uses short-gap forward filling for CGM/HR/HRV and zero imputation for interval steps/sleep. It abstains for<24 h history,>20% missing channel values in recent 2 h or trailing 24 h, CGM stale>15 min, or HR/HRV stale>60 min. Null risk must not become 0% risk. Plausible CGM bias can pass these checks; future unannounced meals, real devices and clinical complexity remain unresolved.

The simulator is a designed model and may favor EHR fusion. Removing absolute clock features does not remove every recurrence cue. The final cohort is synthetic and from the same generator family. No independent clinical, medication, outcome, device, subgroup-efficacy or usability validation exists. Local notes/receipts are not a governed clinical record, and hashes are not signatures.

## Reproduce and review

Run `npm run train` or `python ml/train_robust.py` only when intentionally reproducing the current experiment. `npm run train:legacy` writes a separate baseline-retrained directory and cannot silently replace active artifacts. Run `npm test` and `npm run test:data`; consult `docs/VERIFICATION.md` for the completed checks. Recorded environment: Python 3.12.2, NumPy 2.4.4, scikit-learn 1.9.0.

Primary context: [NIDDK CGM targets](https://www.niddk.nih.gov/health-information/professionals/diabetes-discoveries-practice/clinical-targets-for-continuous-glucose-monitoring-data). [Synthea](https://synthetichealth.github.io/synthea/) is a possible future integration, not a data source used here. Neither source validates this model.

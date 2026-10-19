# AURA Twin model card

**Version:** aura-synthetic-1.0.0. **Use:** a reproducible Digital Twin proof of concept for judges and developers. **Data:** 100% generated, fictional and nonclinical. **Excluded use:** diagnosis, treatment, medical monitoring or decisions concerning real people.

## Prediction task

The model fuses a static EHR profile with up to 24 hours of simulated CGM, heart rate, HRV, steps and sleep. Four ridge models predict observed glucose at exactly +30, +60, +90 and +120 minutes. A separate logistic classifier predicts the probability that observed glucose at exactly +120 minutes is at least 180 mg/dL. No claim is made about detecting every excursion during the two-hour interval. The 180 mg/dL cutoff is a prototype event definition, not a treatment instruction.

## Data provenance and simulator assumptions

`ml/generate.py` is the complete original simulator. It reads no external datasets and makes no network requests. It does not use Synthea, MIMIC, Apple Health, Google Fit or actual CGM exports. Numpy randomness uses seed `20261019`, with deterministic per-patient seeds.

The 240-person cohort has four days per person at five-minute cadence: 276,480 synthetic sensor rows. Age, BMI, HbA1c, LDL and diabetes duration are fabricated. Glucose is a baseline plus smooth meal responses, activity effects, circadian variation and autoregressive noise. Three meals have regular clock times with jitter; some meals are skipped and some snacks added. HbA1c and BMI influence the simulated baseline and meal kinetics. Steps contain a simulated walk; sleep is a regular overnight binary interval; HR and HRV respond to age, sleep, activity, meal response and noise. This is an engineering simulator, not a validated physiological or pharmacological model. No medication effects or real genetic relationships are modeled. Fictional genetic markers are display-only and excluded from all predictors.

Regular meals, repeated daily structure and HbA1c-dependent simulated dynamics make the benchmark easier than deployment and can advantage fused predictors. Similar train and test generators do not establish robustness to new hospitals, devices, populations, timezones or diets.

## Leakage controls and training

Patients are shuffled once with the fixed seed and split into 144 training, 48 validation and 48 test people. Every window from a person stays in one split. After 24 hours of history, windows are sampled every 30 minutes, retaining complete future labels: 20,160 training, 6,720 validation and 6,720 test windows. Patient IDs are saved in `data/metrics.json`.

Thirty-six predictors computed from historical information include five EHR fields; current CGM and 30/60/120-minute lags; two-hour mean and population standard deviation; 30/60-minute slopes; one-hour mean HR/HRV; one-hour and 24-hour steps; 24-hour hours asleep; four sine/cosine clock harmonics; and ten HbA1c interactions with CGM, slope and clock. There are no future meal, future sensor or outcome inputs. Features and all preprocessing use only the replay prefix.

`StandardScaler` fits only training patients. Four-output `Ridge(alpha=30)` fits glucose targets, while `LogisticRegression(C=0.3)` fits the event. A one-dimensional logistic calibration (`C=100`) fits validation logits and validation labels only. No test data chooses features, weights, interval widths or threshold. A causal forecast can still be inaccurate when future meals or behavior change unexpectedly.

The scalar alert threshold is chosen on a 0.01 grid as the highest value reaching at least 80% validation recall. It is frozen at **0.20** before test evaluation. It is a demo operating policy, not a clinically approved threshold. The common 0.50 threshold remains in the ablation metrics for an explicit comparison.

The forecasting band is prediction ± the 90th percentile of absolute validation residuals, separately for each horizon. It is a descriptive marginal residual interval. Correlated windows and subject variation mean this is not a formal per-patient coverage guarantee or uncertainty on the calibrated probability. No such guarantee is made for scenario-adjusted curves.

## Held-out measured results

The test set event prevalence is 8.04% (540 positive windows / 6,720). Metrics below were produced by the supplied script; they are not estimates of clinical performance.

| Model | +120 MAE mg/dL | +120 RMSE mg/dL | AUROC | Brier score | Recall at 0.50 |
|---|---:|---:|---:|---:|---:|
| Fused EHR + sensors | 10.946 | 14.721 | 0.9692 | 0.03723 | 54.81% |
| Sensors + clock only | 12.174 | 16.016 | 0.9586 | 0.04127 | 44.63% |
| EHR only | 19.312 | 24.087 | 0.8414 | 0.06526 | 0.00% |
| Persistence: current CGM | 22.098 | 28.937 | 0.5541 | 0.13155 | 17.96% |

The fused model improves MAE by about 10.1% relative to sensor-only and 50.5% relative to persistence on this simulator. The patient-bootstrap 95% interval for fused MAE is approximately 10.287–11.593 mg/dL (1,000 bootstrap resamples of test patients). The saved file contains full precision, all horizons, precision-recall area, confusion matrices and calibration bins. No confidence interval is claimed for AUROC or the ablation differences.

At the frozen **0.20** alert threshold, validation recall is 81.02%; test recall is **83.89%**, precision **53.23%** and F1 **65.13%**. Test counts are TP=453, FN=87, FP=398, TN=5,782. That policy misses 87 positive windows and about 47% of alerts are false positives, even in this designed synthetic world. At the common 0.50 threshold the model misses 244 of 540 positive windows. These are correlated window counts, not independent event or person counts; no event-level alarm burden is measured.

The nominal 90% residual band covers 89.97% of +120-minute test labels. Its width, horizon-specific coverage and calibration bins are in the metrics artifact. Persistence classification is a hard 0/1 forecast based on current glucose: its Brier score and AUROC are coarse references, not a calibrated-probability comparison.

## Runtime safeguards and interpretation

The inference engine checks schema and chronological order, aggregates only history, reports source freshness and abstains when history is insufficient. Short gaps use prior observations; steps/sleep gaps are zero-imputed and counted toward degraded quality. These rules are documented in `data/SCHEMA.md`. They require validation before any external dataset use.

Drivers are exact grouped linear contributions in calibrated log-odds relative to the training feature means. Correlated inputs and interaction terms make attribution unstable; a large contribution is an association within this fitted synthetic model, not a biological explanation or causal effect. Imported measurements outside the simulator distribution can pass structural validation yet still be out of distribution; drift detection is not implemented.

The optional meal/activity controls alter forecast curves with a disclosed hand-authored arithmetic offset. They leave the trained event probability unchanged. They do not establish what would happen if a real patient ate or exercised, and contain no treatment, dosing or medication advice.

## Reproduce and verify

From the repository root, with Python 3.12+ and Node.js 20+:

```bash
python -m pip install -r ml/requirements.txt
python ml/train.py
node --test tests/model.test.mjs
```

The actual Python/numpy/scikit-learn versions used are saved in `metrics.json`. Small cross-platform floating-point differences are possible. Training overwrites generated model, metrics, display patients and Python parity fixtures. The test suite checks patient isolation, Python/JavaScript numerical parity, future-data invariance, dependence on EHR, missingness abstention, malformed inputs, scenario labeling and locked alert thresholds. The eight display patients are curated replay examples from test people; choosing interesting display windows does not alter benchmark evaluation.

Technical references: [scikit-learn guidance on leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage), [grouped validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data), [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html). These are implementation references, not endorsements or clinical evidence.

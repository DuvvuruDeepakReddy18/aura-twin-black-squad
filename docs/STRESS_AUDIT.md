# Frozen-policy comparison and routine stress audit

Current model: `aura-synthetic-3.0.0`. Raw model-file SHA-256: `87fb0df0832c2db76b03c55c81298ab717200c3dc60048b9b4586dc7061d81b4`.

The gains are modest and mixed: the patient-bootstrap 95% interval for the FN difference includes zero, and the withheld combination has **324 → 330 missed positive windows**. This does not establish a reliable reduction in misses or improvement across every routine.

The current model and frozen v2 are evaluated on the same fresh identities, after model/calibration/policy/interval freeze. The simulator is unchanged. The primary aggregate contains six familiar routine families and 100,800 windows across 120 identities. The withheld parameter combination is separate: 16,800 windows for those same identities.

| Frozen policy | Threshold | Recall | Precision | FN windows | FP windows | +120 MAE mg/dL |
|---|---|---|---|---|---|---|
| Previous v2 | 0.1600 | 73.36% | 35.46% | 1,742 | 8,730 | 11.39 |
| Current v3 | 0.1550 | 74.47% | 37.34% | 1,669 | 8,170 | 10.85 |

| V3 minus V2 | Difference | Patient-bootstrap 95% interval |
|---|---|---|
| falsePositiveWindows | -560.0000 | -980.0250 to -157.9750 |
| falseNegativeWindows | -73.0000 | -192.0250 to 27.0250 |
| recall | 0.0112 | -0.0049 to 0.0279 |
| precision | 0.0188 | 0.0097 to 0.0293 |

| Routine | V2 → V3 FN | V2 → V3 FP | V3 recall | V3 precision | V3 MAE |
|---|---|---|---|---|---|
| Regular routine | 211 → 212 | 1,207 → 1,134 | 82.57% | 46.96% | 9.38 |
| Meals delayed by 2 hours | 164 → 159 | 1,366 → 1,370 | 85.64% | 40.90% | 9.10 |
| Meals delayed by 4 hours | 132 → 142 | 1,332 → 1,195 | 84.58% | 39.46% | 9.01 |
| Irregular meal timing | 491 → 452 | 1,541 → 1,384 | 65.26% | 38.02% | 13.05 |
| Daily timing changes and skipped meals | 324 → 313 | 1,627 → 1,490 | 69.13% | 31.99% | 11.97 |
| Variable sleep, activity and meals | 420 → 391 | 1,657 → 1,597 | 60.06% | 26.91% | 12.59 |
| Held-out combination of shifted and variable routines | 324 → 330 | 1,657 → 1,624 | 60.99% | 24.11% | 12.07 |

Differences are current minus frozen v2. Patient-level resampling retains all paired variants/windows. These are overlapping exact-horizon windows, not independent episodes, notifications or people. The last row is excluded from the primary aggregate. The separate withheld factor combination has 12.07 mg/dL MAE, 60.99% recall and 24.11% precision. FN changes 324 → 330; FP changes 1,657 → 1,624.

The withheld combination uses a three-hour meal delay, one-hour timing jitter, daily shift SD 1.4 hours, skip probability 0.25 and variable sleep/activity. Familiar ingredients were seen in development; the exact combination was not. This is not evidence of unseen physiology or clinical external validity.

The primary MAE is 10.850 mg/dL. Nominal 90% band coverage is 90.60%, with mean width 61.76 mg/dL. Width, coverage, recall and precision must be inspected together. Current-below-threshold and already-high slices remain distinct in `data/metrics.json`; neither changes the exact +120-minute label into a first-onset task.

Independent exported-JSON replay and final verification status are recorded in [VERIFICATION.md](VERIFICATION.md). Full per-model metrics, calibration bins and paired intervals are in [robustness.json](../data/robustness.json). The [model/data card](MODEL_DATA_CARD.md) gives protocol and limitations. Historical v1 and v2 reports stay in their archive folders and must not be substituted for this comparison.

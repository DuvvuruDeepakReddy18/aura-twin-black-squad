# Current robustness evaluation — `aura-synthetic-2.0.0`

This report supersedes the earlier post-hoc v1 shift audit for the active model. Historical artifacts remain in `data/baseline-v1/`. The original regular-cohort 10.95 mg/dL error must not be quoted as current performance.

## What changed and how it was evaluated

The current pipeline removes explicit clock features, uses 53 past-only history/EHR predictors, trains on six routine families, and selects histogram gradient boosting using separate selection identities. Probability calibration, residual widths and the 0.16 policy use separate calibration identities. The model bytes are saved and hashed before 80 fresh identities are generated. No final result changes the selected artifact.

The six families were represented during training. This tests fresh identities within a declared mixture, **not unseen routine families**. The model has no future meal schedule or latent simulator input. Previous-day observations are past data and can fail as recurrence cues.

## Same-case comparison

Each row has 80 identities and 11,200 overlapping windows. Variants remain paired by identity. All models receive the same final cases. Errors are mg/dL at exactly +120 minutes.

| Routine | Current MAE | Frozen v1 MAE | Persistence MAE | Band coverage | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Regular routine | 10.06 | 10.88 | 21.68 | 92.28% | 85.84% | 50.26% |
| Meals delayed by 2 hours | 9.72 | 21.92 | 21.47 | 92.84% | 88.91% | 47.77% |
| Meals delayed by 4 hours | 9.29 | 22.92 | 19.57 | 93.34% | 89.60% | 43.09% |
| Irregular meal timing | 13.97 | 17.05 | 21.11 | 85.31% | 67.99% | 39.47% |
| Daily timing changes and skipped meals | 13.12 | 17.64 | 19.45 | 86.75% | 76.44% | 34.19% |
| Variable sleep, activity and meals | 13.57 | 19.39 | 18.65 | 86.01% | 63.93% | 29.37% |

Aggregate current MAE: **11.622**; frozen v1 on the same cases: **18.298**; persistence: **20.323**. The current model improves all six MAE rows versus v1. This does not mean every individual prediction improves. Added EHR MAE gain over sensors is only **0.107 mg/dL**.

Nominal 90% bands have aggregate coverage 89.42% and mean width 61.66 mg/dL. Coverage and recall remain weaker for highly variable routines. Read width, precision and recall alongside error; no interval guarantees individual coverage.

## Reproducibility and evidential limits

`data/robustness.json` contains all ablations, paired patient-bootstrap intervals and routine-specific policy metrics. `data/robustness-protocol.json`, `data/selection-results.json`, and `data/training-audit.json` document the development sequence. `data/stress.json` is the compact runtime view. The unchanged model fingerprint is `a67d3a6abd84df76f3cbbbb30e35a10f0845417b7b12bbb09df83c398ef317a4`.

Run `npm run train` for the full current experiment; use the independent exported-artifact audit command documented by `ml/stress_test.py` for a frozen-model check. Neither a local timestamp nor a hash constitutes independent preregistration or an external signature. The test identities are fresh relative to earlier development, but the simulator and features were designed after inspecting v1 failures. No clinical or external-data validation is demonstrated.

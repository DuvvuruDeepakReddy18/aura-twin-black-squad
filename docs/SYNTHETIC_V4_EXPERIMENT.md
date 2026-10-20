# Synthetic V4 experiment — completed, not promoted

The predeclared promotion gate **failed**. The candidate reduces false-positive windows and improves forecasting error modestly, but increases missed-positive windows in the primary evaluation. V3 remains the legacy synthetic application model. The new open-research model is a separate experiment with different data and target; its metrics cannot be compared as an improvement over these scores.

## What changed

The experiment uses the unchanged four-day simulator and the same event: glucose ≥180 mg/dL at exactly +120 minutes. It fits HGB and ExtraTrees candidates on new development identities and adds 19 features to the original 108. The extra features include frozen V3 forecasts and summaries of **already resolved** historical forecast errors.

A forecast made at time q can contribute a residual only when q + 120 minutes is no later than the current cutoff. Forecasts begin after 24 hours of history, so the first two hours after that boundary have no resolved forecast errors. A count identifies that missing-history state. No future glucose or future meal schedule enters a feature.

Classification selects a 75% HGB / 25% ExtraTrees blend; regression selects an HGB correction to the V3 +120-minute forecast. Earlier horizons remain V3 forecasts. This is an actual model experiment, not an invented slider effect or only a threshold change.

## Partition and freeze

| Stage | Fresh simulator indices | Identities | Use |
|---|---|---:|---|
| Fit | 2500–3011 | 512 | Candidates; fitting windows at 60-minute stride |
| Select | 3200–3279 | 80 | Blend/correction choice, minimax FP/FN objective |
| Probability calibration | 3400–3447 | 48 | Platt map only |
| Policy and bands | 3448–3495 | 48 | Global threshold and residual widths |
| Final | 4000–4119 | 120 | Generated once after freeze, 30-minute evaluation stride |

The primary result contains 100,800 windows across six familiar families. The withheld combination adds 16,800 windows from the **same** 120 final identities: 2.5-hour meal shift, 1.8-hour timing jitter, one-hour day-shift SD, 0.30 meal-skip probability and variable sleep/activity. It is a new parameter combination, not unseen physiology.

Candidate selection minimizes the worst FP/FN count ratio to frozen V3 across overall, pooled irregular and variable-routine windows. One global policy is chosen on the policy-calibration identities. The final threshold is 0.155. No final result is used for retuning.

The gate requires both FP and FN to decrease in primary, variable and withheld results, plus both primary paired patient-bootstrap 95% intervals entirely below zero. The observed primary FN increase fails that rule.

## Same-cohort results: V3 → V4

| Case | +120 MAE mg/dL | FN windows | FP windows | Recall | Precision |
|---|---:|---:|---:|---:|---:|
| Primary: six families | 11.114 → 10.982 | 1,790 → 1,824 | 7,816 → 7,329 | 77.99% → 77.57% | 44.80% → 46.26% |
| reference | 9.582 → 9.436 | 204 → 218 | 1,082 → 983 | 86.05% → 85.09% | 53.76% → 55.86% |
| late_meals_2h | 9.276 → 9.075 | 169 → 181 | 1,227 → 1,146 | 88.03% → 87.18% | 50.32% → 51.79% |
| late_meals_4h | 9.262 → 9.100 | 172 → 178 | 1,159 → 1,083 | 85.62% → 85.12% | 46.91% → 48.45% |
| irregular_meals | 13.182 → 13.142 | 486 → 493 | 1,322 → 1,189 | 68.79% → 68.34% | 44.76% → 47.23% |
| day_varying_skips | 12.402 → 12.274 | 314 → 314 | 1,513 → 1,435 | 74.80% → 74.80% | 38.12% → 39.37% |
| variable_routine | 12.980 → 12.867 | 445 → 440 | 1,513 → 1,493 | 64.68% → 65.08% | 35.01% → 35.45% |
| new_shift_variable_combination | 12.817 → 12.682 | 425 → 404 | 1,678 → 1,645 | 62.12% → 63.99% | 29.35% → 30.39% |

Window counts overlap in time and are not unique clinical events. Old V3 scores from other cohorts are not used for this comparison.

## Paired decision differences: V4 minus V3

| Case | Count | Difference | Patient-bootstrap 95% interval |
|---|---|---:|---|
| Primary | falsePositiveWindows | -487 | [-947.0, -48.9] |
| Primary | falseNegativeWindows | +34 | [-92.0, 168.0] |
| Variable routine | falsePositiveWindows | -20 | [-116.0, 75.0] |
| Variable routine | falseNegativeWindows | -5 | [-34.0, 24.0] |
| Withheld combination | falsePositiveWindows | -33 | [-140.0, 71.0] |
| Withheld combination | falseNegativeWindows | -21 | [-47.0, 2.0] |

The bootstrap resamples 120 identities with all their windows and variants retained, for 2,000 draws. The primary false-positive reduction is supported by its interval, but missed-window improvement is not. Variable and withheld improvements are modest and their count intervals include zero.

## Reproduce and inspect

The trainer, protocol, development rankings, freeze record, final results and audit are retained. Fitted Python caches stay in ignored `work/`; this failed candidate is not an active app artifact.

```bash
python -m pip install -r ml/requirements.txt
python ml/train_v4_experiment.py --phase develop --base-model data/model.json --output-dir work/reproduced-v4 --work-dir work/reproduced-v4-cache
python ml/train_v4_experiment.py --phase freeze --base-model data/model.json --output-dir work/reproduced-v4 --work-dir work/reproduced-v4-cache
python ml/train_v4_experiment.py --phase evaluate --base-model data/model.json --output-dir work/reproduced-v4 --work-dir work/reproduced-v4-cache
python -m unittest ml/test_v4_features.py
```

Use a clean reproduction checkout/output directory. The supplied base model must have SHA-256 `87fb0df0832c2db76b03c55c81298ab717200c3dc60048b9b4586dc7061d81b4`; the script rejects a different artifact. It refuses to overwrite the frozen experiment or rerun a completed final evaluation. Three feature-contract tests passed: vectorized/scalar parity, prefix and matured-outcome invariance, and reserved-final-ID protection.

- [Protocol](../data/synthetic-v4-experiment/protocol.json)
- [Development rankings](../data/synthetic-v4-experiment/development.json)
- [Frozen estimator record](../data/synthetic-v4-experiment/freeze.json)
- [Final results](../data/synthetic-v4-experiment/results.json)
- [Evaluation sequence audit](../data/synthetic-v4-experiment/audit.json)
- [Reproducible trainer](../ml/train_v4_experiment.py)

This negative result is part of the engineering evidence. It does not justify claiming the earlier missed-event problem solved, promoting the candidate, or inferring clinical effectiveness.

# AURA Twin — current research model and data card

**Current artifact:** `aura-research-1.0.0`
**Model-file SHA-256:** `a4371ed5c7c768bf2d210917d6e7bf28ce89da7147ead0a98c14f48568abf432`
**Selected primary family:** CGM history only
**Status:** Exploratory research prototype. No clinical validation, treatment recommendation or clinical deployment claim.

## Intended task and population

Forecast CGM at approximately +30, +60, +90 and +120 minutes from the preceding six hours of available observations. The current binary target is:

> Observed CGM glucose rise >=20 mg/dL from the latest available current value by approximately +120 minutes (nearest measurement within ±150 seconds).

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

The selected histogram-gradient-boosting model uses **36 features**. Exact features, tree parameters, training references and model sources are in [research-model.json](../data/research-model.json). Two small configurations are compared for each model family. Unmatched Synthea-only and composite-fusion families are negative controls and cannot select the primary model. [Selection results](../data/research-selection.json) preserve all candidates.

Calibration uses Platt logistic mapping. A single threshold, **0.180**, maximizes F1 on the calibration participants over the declared grid. The same two participants estimate mapping, policy and interval widths. This reuse and the small sample can produce unstable estimates. The policy is not a clinically elicited treatment trigger.

Nominal 90% bands use the calibration absolute-residual quantile separately for each horizon. Final +120-minute coverage is **93.54%**, with mean width **71.68 mg/dL**. These are empirical marginal bands, not guaranteed patient-specific or shifted-population coverage.

## Final results

The same **1,859 eligible windows from three participants** are used for the comparisons below. A deterministic persistence flag is not described as a calibrated probability.

| Family | +120 MAE | Participant-macro MAE | AUROC | AP | Brier | Threshold | Recall | Precision | FN windows | FP windows |
|---|---|---|---|---|---|---|---|---|---|---|
| CGM history only | 13.309 | 12.982 | 0.672 | 0.294 | 0.1236 | 0.180 | 66.20% | 22.14% | 97 | 668 |
| CGM + HR + IBI-derived RMSSD | 13.698 | 13.407 | 0.690 | 0.318 | 0.1259 | 0.150 | 84.67% | 19.35% | 44 | 1013 |
| Matched research HbA1c/sex + wearables | 14.733 | 14.222 | 0.718 | 0.300 | 0.1214 | 0.160 | 82.93% | 22.88% | 49 | 802 |
| Unmatched Synthea EHR only (negative control) | 14.804 | 14.389 | 0.549 | 0.168 | 0.1410 | 0.180 | 100.00% | 15.44% | 0 | 1572 |
| Unmatched Synthea EHR + wearables (negative control) | 13.763 | 13.446 | 0.672 | 0.260 | 0.1261 | 0.155 | 76.66% | 20.52% | 67 | 852 |
| Latest glucose persistence (deterministic event baseline) | 16.346 | 15.837 | 0.500 | 0.154 | 0.1544 | 0.500 | 0.00% | 0.00% | 287 | 0 |

### By horizon

| Nominal horizon | MAE mg/dL | RMSE mg/dL | Empirical band coverage | Mean band width mg/dL |
|---|---|---|---|---|
| +30 min | 9.87 | 14.82 | 93.06% | 56.93 |
| +60 min | 12.20 | 17.81 | 93.65% | 68.57 |
| +90 min | 12.87 | 18.30 | 92.90% | 67.90 |
| +120 min | 13.31 | 18.84 | 93.54% | 71.68 |

### By final participant

| Final participant | Windows | +120 MAE | Recall | Precision | Band coverage |
|---|---|---|---|---|---|
| 014 | 715 | 15.54 | 55.47% | 24.74% | 90.49% |
| 015 | 451 | 10.71 | 69.57% | 15.09% | 97.56% |
| 016 | 693 | 12.70 | 76.99% | 24.23% | 94.08% |

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

`aura-synthetic-3.0.0` is a historical simulator benchmark. Its scores must not be presented as current research scores. The independent synthetic V4 experiment uses unchanged simulator labels and fresh identities: On the separate fresh synthetic cohort, false-negative windows changed from 1,790 to 1,824, and false-positive windows from 7,816 to 7,329. Predeclared promotion gate failed; not promoted. These results are not comparable with the open-research model's performance.

## Limitations

- Only16 research participants; final evaluation has3 and calibration2.
- Unmatched Synthea EHR belongs to a different simulated person and cannot establish clinical fusion.
- Matched HbA1c measurement time is unspecified; treating it as baseline is an assumption.
- Source HR timestamps may be minute-rounded; conservatively delayed to completed minute.
- No sleep stages, step counts or activity were imported; missing channels remain unavailable.
- Targets use nearest actual CGM observation within150seconds of nominal horizon; no target interpolation.
- Empirical residual intervals and Platt calibration are limited by the small calibration cohort.
- The primary eligible model was selected on two participants; model ranking may be unstable.
- Three held-out participants do not support reliable population confidence intervals or clinical claims.
- Window counts overlap in time and are not independent adverse episodes.
- No genuine clinical history is linked to the wearable participants beyond supplied research metadata.
- Unmatched EHR ablations test arbitrary composite assignment, not physiological fusion.
- The primary event is a predeclared research label chosen from train-only prevalence, not a medical diagnosis.
- Performance cannot be compared numerically with legacy synthetic v3 because cohort and possibly target differ.

# Data and inference contract

All supplied people, measurements, diagnoses and names are fictional. `patients.json` contains eight demonstration records from fresh final identities SYN-2001 onward, with routine/default-cutoff choices fixed independently of favorable outcomes. The current experiment has 1,064 distinct identities across fit/selection/calibration/final partitions. Six routine families support development and the primary final evaluation; an additional withheld factor combination is evaluated separately on the same 120 final identities. A display name has no connection to a real person. Each identity’s variants stay in its partition.

## Patient record

```json
{
  "id": "SYN-2001",
  "name": "Fictional display name",
  "initials": "FD",
  "sex": "Female",
  "age": 54,
  "color": "#6366f1",
  "synthetic": true,
  "ehr": {
    "age": 54,
    "bmi": 28.4,
    "hba1c": 7.2,
    "ldl": 118,
    "diabetesYears": 4.3,
    "diagnoses": ["Type 2 diabetes (simulated)"],
    "medications": ["Fictional medication history; no dose or treatment model"],
    "geneticMarker": "Fictional marker GT-SIM-1; descriptive only"
  },
  "series": [
    {"timestamp":"2026-10-12T00:00:00Z","glucose":123.4,"hr":68.2,"hrv":45.1,"steps":12,"sleep":0}
  ],
  "defaultCursor": 800,
  "routine": {"id":"reference","label":"Regular routine"},
  "replayNote": "Fresh final identity; display cutoff selected by a fixed rule."
}
```

The abbreviated example illustrates structure; inference needs at least 288 five-minute intervals (24 hours) of history. `defaultCursor` is a zero-based array index. Sex, name, diagnoses, medication text and genetic marker are descriptive and excluded from predictor inputs. The five modeled EHR fields are age (years), BMI (kg/m²), HbA1c (%), LDL (mg/dL) and diabetes duration (years).

| Stream field | Unit / interpretation | Missingness |
| --- | --- | --- |
| timestamp | ISO 8601 with timezone; increasing five-minute grid | Required |
| glucose | CGM mg/dL | `null` permitted; short gaps forward-fill |
| hr | beats/min | `null` permitted; short gaps forward-fill |
| hrv | synthetic HRV ms, conceptually RMSSD | `null` permitted; short gaps forward-fill |
| steps | Count during this five-minute interval | Missing intervals imputed as zero |
| sleep | 1 = asleep, 0 = awake in this interval | Missing intervals imputed as zero |

The generator uses UTC timestamps, but the current model has no absolute clock features. Timestamps support sequence validation, relative freshness, replay and display. Translating the whole timestamp sequence without changing observations does not change the current prediction. No device integration is included. Importer bounds are structural checks, not clinical reference ranges. The `routine` label is display context only; it is not a predictor or a future meal plan.

## Runtime API

```js
import {initializeModel, infer, validatePatient} from './lib/model.mjs';
initializeModel(modelJson);
const check = validatePatient(patient); // {valid, errors, warnings}
const output = infer(patient, patient.defaultCursor, {mealCarbs: 0, activityMinutes: 0});
```

`infer` reads only observations at or before the cursor, including during validation. Future data cannot change its output. Future observed values remain in the patient record for a **separate retrospective replay comparison**; they are not inference inputs. The label at +120 minutes is `series[cursor + 24].glucose >= 180` for the complete generated series. This is an exact-horizon event, not “any spike within the next two hours.”

| Output | Meaning |
| --- | --- |
| current | glucose, hr and hrv at replay cursor; **steps is trailing 24-hour total; sleep is trailing 24-hour hours asleep**; timestamp |
| risk | Calibrated probability of the exact +120-minute event; `null` when abstaining |
| forecast | Four rows: `minutes`, `glucose`, `lower`, `upper`, `baseline`, `illustrative`; glucose unit mg/dL |
| alert | `{triggered, threshold, label}`; fixed calibration-selected threshold 0.155 |
| drivers | Current tree model: grouped reference sensitivity; replace a group with training medians and report original minus reference calibrated risk in percentage points; nonadditive, noncausal, not SHAP |
| quality | `{score,missing,historicalMissing,stale,status,reasons,note}` |
| features | The 108 clock-free predictors computed from current and historical information |
| scenario | Explicit illustrative sensitivity metadata; trained risk remains unchanged |
| abstained | Boolean; if true, risk is null and forecast/drivers are empty |
| modelVersion | `aura-synthetic-3.0.0` |

Quality score is percent observed over the worse of the recent two-hour or trailing 24-hour feature window. `missing` and `historicalMissing` are fractions, not percentages. `stale` maps each sensor channel to minutes since its latest observed value (`null` if no observed value). Status is `good`, `degraded` or `insufficient`. Quality is evaluated relative to replay time rather than current wall time.

The model abstains for less than 24 hours of history, >20% missing channel values in the two-hour or 24-hour window, CGM stale >15 minutes, or HR/HRV stale >60 minutes. The API must never turn a null risk into “0%” or “low risk.” Missingness behavior is a software safeguard, not a validated clinical quality rule.

## Current model and evaluation artifacts

- `model.json`: `modelKind: hist_gradient_boosting`, 108 feature names, four exported regression ensembles and one classifier ensemble, separate Platt parameters, training-median references/groups, calibration residual half-widths and fixed review policy. Tree inference consumes raw features; compatibility `mean`/`scale` fields do not standardize the tree inputs.
- Each exported ensemble has a baseline and numerical trees. A node stores feature index, threshold, child indices, leaf value and missing-value direction. The JavaScript evaluator matches Python fixtures.
- `metrics.json`: fresh final aggregate comparisons, split counts/IDs, each model’s frozen-policy metrics, paired FP/FN differences, calibration bins and patient-bootstrap intervals.
- `robustness.json`: six familiar-family comparisons and one separately reported withheld combination on the same 120 final identities; all ablations, paired patient-bootstrap error/count differences, target slices, selection evidence and protocol.
- `robustness-protocol.json`, `selection-results.json`, `model-freeze.json`, `training-audit.json`: declared partitions/routines, candidate choice, calibration and local freeze-before-final-generation sequence. Hashes/timestamps are not independent authentication.
- `stress.json`: compact current seven-case view; independent exported-artifact audit metadata is added only after reproduction.
- `parity.json`: 16 reference windows across eight demo records, with all 108 feature values, four forecasts and risk for Python/JavaScript comparison.
- `baseline-v1/` and `baseline-v2/`: historical model/evidence artifacts. Frozen v2 is compared on the same fresh v3 final windows; its original final-cohort metrics are not substituted for that comparison.

The current `driverMethod` is `group_reference_sensitivity`. Each driver includes `contribution` in `percentage_points` and `referenceRisk`; replacing all raw features in one group may create an unrealistic combination. Sensitivities do not sum to risk and do not estimate an intervention effect. Legacy linear compatibility, when explicitly loading v1, retains its distinct additive-log-odds explanation.

Previous-day inputs are observed at `t + horizon - 1440 minutes`, so they are 22–23.5 hours old for the four horizons. They never read future glucose. The model does not receive future meals, meal annotations, or hidden simulator state. All feature names, in exact exported order:

`age`, `bmi`, `hba1c`, `ldl`, `diabetesYears`, `glucose`, `lag30`, `lag60`, `lag120`, `mean120`, `std120`, `slope30`, `slope60`, `hrMean60`, `hrvMean60`, `steps60`, `steps24h`, `sleep24h`, `lag15`, `lag45`, `lag90`, `lag180`, `lag240`, `lag360`, `mean30`, `std30`, `mean60`, `std60`, `mean360`, `std360`, `mean24h`, `std24h`, `min120`, `max120`, `q25_120`, `q75_120`, `q10_24h`, `q50_24h`, `q90_24h`, `slope15`, `slope120`, `acceleration30`, `priorDay30`, `priorDay60`, `priorDay90`, `priorDay120`, `priorDayMean120`, `hrSlope30`, `hrvSlope30`, `hrMean120`, `hrvMean120`, `steps120`, `sleepLast6h`, `lag5`, `lag10`, `lag20`, `lag25`, `lag35`, `lag40`, `lag50`, `lag75`, `lag105`, `lag150`, `lag210`, `lag300`, `olsSlope30`, `olsSlope60`, `olsSlope120`, `olsSlope240`, `meanDelta30_60`, `meanDelta60_120`, `riseFraction30`, `riseFraction60`, `riseFraction120`, `fallFraction60`, `meanAbsChange30`, `meanAbsChange60`, `meanAbsChange120`, `maxRise30`, `maxFall30`, `range30`, `range60`, `minutesSinceMax120`, `minutesSinceMin120`, `glucoseAboveQ10`, `glucoseAboveMedian`, `excessMean120`, `timeAbove180_120`, `timeAbove140_120`, `hrMean15`, `hrMean30`, `hrvMean15`, `hrvMean30`, `hrMean24h`, `hrvMean24h`, `hrStd24h`, `hrvStd24h`, `hrZ30`, `hrvZ30`, `steps15`, `steps30`, `sleepLast60`, `minutesSinceWake`, `minutesSinceActivity`, `awakeRestingHr24h`, `awakeRestingHr30`, `hrAboveResting30`, `glucoseMinusPriorDay120`

## V3 trajectory features

The first 53 features preserve the earlier clock-free history representation. The added 55 describe finer available-time trajectories:

- Additional glucose lags: 5, 10, 20, 25, 35, 40, 50, 75, 105, 150, 210 and 300 minutes.
- Ordinary-least-squares slopes over 30/60/120/240 minutes use only the trailing samples, with slope units mg/dL per minute.
- Rising/falling fractions, mean absolute five-minute changes, recent ranges, signed maximum rise/fall, and minutes since the most recent trailing extremum describe observed shape. Threshold occupancy is a fraction of past readings, not a future event label.
- Glucose relative to its trailing lower quantile/median and previous-day reading describes individual baseline context.
- HR/HRV short means, 24-hour mean/standard deviation and normalized changes use a denominator of at least 1. These are simulator-derived features, not validated physiological biomarkers.
- Time since the latest observed asleep-to-awake transition or interval with at least 50 steps uses a 1,440-minute sentinel if none occurred in the trailing history. “Awake resting HR” uses awake intervals with fewer than 20 steps, with a local mean fallback; it is an operational definition rather than a clinical resting measurement.

Exact definitions are in `ml/train_v3.py:trajectory_features` and `lib/model.mjs`. No centered filter, future interpolation, future meal annotation or routine label enters these features. The physical input prefix is preserved by Challenge Lab.

## Hosted and local transport

The hosted adapter accepts bundled `patientId` values only and rejects arbitrary `patient` objects. Local development retains schema-validated synthetic-record input. The hosted freeze response additionally contains `challengeToken`, an authenticated encrypted snapshot for reveal across function instances. Reveal requires the same challenge identifier and token, a valid one-hour lifetime and the matching current model hash. It compares the saved prediction, not a recomputed output.

Receipt downloads omit `challengeToken`. The JSON export envelope is `{schemaVersion: 1, challenge: <frozen result without token>, reveal: <comparison or null>}`. Its receipt hashes are raw model-file bytes and sorted-key canonical JSON for `{patientId,cursor,ehr,series:<perturbed prefix>}`; arrays preserve order. This reproducibility contract is distinct from hosted transport authentication. See `docs/DEPLOYMENT.md` and `scripts/verify_receipt.mjs`.

## Illustrative sensitivity

`mealCarbs` accepts 0–150 g; `activityMinutes` accepts 0–90 minutes. The displayed forecast offset is:

```
(0.55 * mealCarbs - 0.30 * activityMinutes) * (horizonMinutes / 60)
    * exp(1 - horizonMinutes / 60)
```

These coefficients are hand-authored display assumptions. They are **not learned, causal, patient-specific or a treatment recommendation**. Trained event probability stays at its baseline value. Shifted interval bands have no measured scenario coverage. Restore both controls to zero to recover the trained forecast exactly.

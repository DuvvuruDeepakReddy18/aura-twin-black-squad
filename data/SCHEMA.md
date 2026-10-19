# Data and inference contract

All supplied people, measurements, diagnoses and names are fictional. `patients.json` is an array of eight curated demonstration patients from the held-out test split. The full 240-person cohort is regenerated in memory by `python ml/train.py`. A displayed name has no connection to a real person.

## Patient record

```json
{
  "id": "SYN-001",
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
  "replayNote": "Curated synthetic demonstration window from a held-out test patient."
}
```

The abbreviated example illustrates structure; inference needs at least 288 five-minute intervals (24 hours) of history. `defaultCursor` is a zero-based array index. Sex, name, diagnoses, medication text and genetic marker are descriptive and excluded from predictor inputs. The five modeled EHR fields are age (years), BMI (kg/m²), HbA1c (%), LDL (mg/dL) and diabetes duration (years).

| Stream field | Unit / interpretation | Missingness |
|---|---|---|
| timestamp | ISO 8601 with timezone; increasing five-minute grid | Required |
| glucose | CGM mg/dL | `null` permitted; short gaps forward-fill |
| hr | beats/min | `null` permitted; short gaps forward-fill |
| hrv | synthetic HRV ms, conceptually RMSSD | `null` permitted; short gaps forward-fill |
| steps | Count during this five-minute interval | Missing intervals imputed as zero |
| sleep | 1 = asleep, 0 = awake in this interval | Missing intervals imputed as zero |

The generator uses UTC as its artificial circadian clock. External timezone-aware timestamps are converted to UTC for model clock features; this simulator-specific convention must be revisited before any real-world work. No device integration is included or implied. Limits accepted by the importer are broad structural checks, not clinical reference ranges.

## Runtime API

```js
import {initializeModel, infer, validatePatient} from './lib/model.mjs';
initializeModel(modelJson);
const check = validatePatient(patient); // {valid, errors, warnings}
const output = infer(patient, patient.defaultCursor, {mealCarbs: 0, activityMinutes: 0});
```

`infer` reads only observations at or before the cursor, including during validation. Future data cannot change its output. Future observed values remain in the patient record for a **separate retrospective replay comparison**; they are not inference inputs. The label at +120 minutes is `series[cursor + 24].glucose >= 180` for the complete generated series. This is an exact-horizon event, not “any spike within the next two hours.”

| Output | Meaning |
|---|---|
| current | glucose, hr and hrv at replay cursor; **steps is trailing 24-hour total; sleep is trailing 24-hour hours asleep**; timestamp |
| risk | Calibrated probability of the exact +120-minute event; `null` when abstaining |
| forecast | Four rows: `minutes`, `glucose`, `lower`, `upper`, `baseline`, `illustrative`; glucose unit mg/dL |
| alert | `{triggered, threshold, label}`; fixed validation-selected threshold 0.20 |
| drivers | Grouped additive calibrated log-odds contributions relative to training feature means; not causal effect percentages |
| quality | `{score,missing,historicalMissing,stale,status,reasons,note}` |
| features | The 36 named predictors computed from historical information |
| scenario | Explicit illustrative sensitivity metadata; trained risk remains unchanged |
| abstained | Boolean; if true, risk is null and forecast/drivers are empty |
| modelVersion | `aura-synthetic-1.0.0` |

Quality score is percent observed over the worse of the recent two-hour or trailing 24-hour feature window. `missing` and `historicalMissing` are fractions, not percentages. `stale` maps each sensor channel to minutes since its latest observed value (`null` if no observed value). Status is `good`, `degraded` or `insufficient`. Quality is evaluated relative to replay time rather than current wall time.

The model abstains for less than 24 hours of history, >20% missing channel values in the two-hour or 24-hour window, CGM stale >15 minutes, or HR/HRV stale >60 minutes. The API must never turn a null risk into “0%” or “low risk.” Missingness behavior is a software safeguard, not a validated clinical quality rule.

## Saved model and evaluation artifacts

- `model.json`: feature order, train-only scaler, ridge weights at four horizons, logistic classifier weights, validation Platt calibration, residual interval half-widths and frozen alert policy.
- `metrics.json`: train/validation/test patient IDs, counts, positive rates, held-out model comparisons, fixed-0.5 classification metrics, separate alert-policy metrics and calibration bins.
- `parity.json`: eight Python reference predictions and feature vectors used to check JavaScript inference against the trained pipeline.

## Illustrative sensitivity

`mealCarbs` accepts 0–150 g; `activityMinutes` accepts 0–90 minutes. The displayed forecast offset is:

```
(0.55 * mealCarbs - 0.30 * activityMinutes) * (horizonMinutes / 60)
    * exp(1 - horizonMinutes / 60)
```

These coefficients are hand-authored display assumptions. They are **not learned, causal, patient-specific or a treatment recommendation**. Trained event probability stays at its baseline value. Shifted interval bands have no measured scenario coverage. Restore both controls to zero to recover the trained forecast exactly.

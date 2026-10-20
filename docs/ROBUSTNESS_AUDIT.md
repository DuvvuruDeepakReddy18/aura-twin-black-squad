# Current research runtime perturbation audit

Model: `aura-research-1.0.0` · SHA-256: `a4371ed5c7c768bf2d210917d6e7bf28ce89da7147ead0a98c14f48568abf432`.

This audit samples **496 windows from the three final participants at 60-minute stride**. It is separate from the main **1,859-window held-out evaluation**. It includes unsuitable inputs so that withheld forecasts remain part of the denominator. Error and interval coverage below are conditional on an available forecast; withholding is not silently counted as correct.

| Input case | Windows | Available | Withheld | MAE on available | Band coverage on available |
|---|---|---|---|---|---|
| Recorded stream | 496 | 468 | 28 | 13.36 | 94.44% |
| 10-minute CGM gap | 496 | 468 | 28 | 13.38 | 93.59% |
| 30-minute CGM gap | 496 | 0 | 496 | unavailable | unavailable |
| Sensor dropout | 496 | 0 | 496 | unavailable | unavailable |
| Missing recent HRV | 496 | 468 | 28 | 13.36 | 94.44% |
| CGM values delayed 15 minutes | 496 | 469 | 27 | 13.71 | 93.82% |
| Alternating ±12 mg/dL noise | 496 | 468 | 28 | 13.51 | 94.02% |
| +30 mg/dL sensor drift | 496 | 468 | 28 | 17.59 | 93.38% |
| Latest CGM outlier | 496 | 0 | 496 | unavailable | unavailable |

The 30-minute gap, two-hour multi-sensor dropout and latest-value outlier cause all sampled forecasts to be withheld. Missing HRV leaves the selected CGM-only model unchanged. Plausible +30 mg/dL bias still permits forecasts and worsens error. These outcomes describe the implemented quality boundary, not a universal sensor-error detector.

## Exact perturbation meanings

- **10-minute CGM gap:** hide the latest two aligned five-minute values; only sufficiently recent past source values may be carried forward.
- **30-minute CGM gap:** hide the latest six aligned values.
- **Sensor dropout:** hide CGM, HR and HRV for the last two hours.
- **CGM values delayed 15 minutes:** replace recent glucose values with readings from 15 minutes earlier while retaining reported timestamps, simulating an unrecognized delay.
- **Alternating noise:** add a deterministic alternating ±12 mg/dL error over the last two hours.
- **Missing recent HRV:** remove the last two hours of derived RMSSD.
- **Sensor drift:** add +30 mg/dL over the last two hours.
- **Latest outlier:** add 500 mg/dL to the latest value to test the range gate.

Original future observations and the **clean current reference** for the rise label remain fixed. The perturbed model can use a different current input, so its rise probability may refer to a different implied absolute future threshold. This distinction is exposed; a perturbation is not an intervention with a measured treatment effect.

Nominal residual bands are unchanged under perturbation. They have not been recalibrated or validated for those corruptions. The audit checks 15 full-history versus physically truncated-prefix outputs; automated tests additionally mutate future rows.

## What-if controls

The current what-if lab recomputes the actual numerical model after CGM offsets between −20 and +20 mg/dL or HR offsets between −20 and +20 bpm. It does not apply a hand-written meal/exercise treatment formula. An HR-only offset leaves the CGM-only primary model unchanged. Changed CGM reference values can change the implied absolute threshold behind a rise probability.

See [machine-readable audit](../data/research-runtime-audit.json), [current model card](MODEL_DATA_CARD.md) and [verification](VERIFICATION.md).

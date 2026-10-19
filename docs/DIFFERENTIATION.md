# A digital twin the jury can challenge

AURA Twin's differentiation is an inspectable experiment attached to a working clinician dashboard. It combines historical EHR and changing sensor state, reports a precisely defined future outcome, and lets the jury reproduce a selected prediction. This is a positioning choice against common prototype patterns, not a claim about unseen competing teams or a first-in-field invention.

| Common prototype pattern | What AURA implements |
|---|---|
| Attractive fixed dashboard | Runnable search, replay, context, risk, uncertainty and exports |
| One aggregate accuracy figure | Same-window frozen baseline comparison, FP/FN, calibration, per-routine results and patient bootstrap |
| A convenient regular schedule | Varied routines, fresh final identities and a separate withheld factor combination |
| A perfect example | Jury-selected cutoff, freeze/reveal, local error and persistence comparison |
| Missing input hidden by a score | Explicit degraded data or abstention; plausible bias exposed as a blind spot |
| Screenshot as proof | Portable JSON receipt and offline reproduction |

## Two-minute pitch

“We are Black Squad from Amrita Vishwa Vidyapeetham, Chennai. AURA Twin joins a fictional patient's EHR context with a changing wearable stream to predict glucose and a precisely defined high-glucose outcome two hours ahead.

We built a clinician-style review screen, but the stronger part is what happens when you question it. Choose a patient and time. Freeze the prediction before revealing the recorded future. Compare it with persistence, inspect the band, and take a receipt you can verify offline.

Our earlier model exposed routine dependence and a difficult alert tradeoff. This edition selects for missed-positive and false-positive windows together, then freezes calibration and one global policy before generating new final identities. The frozen v3 policy at 0.1550 has 74.47% recall and 37.34% precision, with 1,669 false-negative and 8,170 false-positive windows. Frozen v2 on the same cases has 1,742 FN and 8,730 FP. The primary missed-window reduction is uncertain, and misses increase slightly on the withheld combination. We show the entire routine table, uncertainty and remaining errors. These are synthetic windows, not proven clinical events or treatment benefits.

The system also knows when its inputs are too stale to issue a forecast, while demonstrating that a plausible bias can still fool freshness checks. The what-if controls are clearly illustrative, not causal treatment guidance.

Our claim is a complete, reproducible proof of concept with evidence you can challenge. We invite the jury to choose a window, reveal the result and verify the receipt.”

## Claims to avoid

Do not say first digital twin, clinically accurate, guaranteed early warning, proven prevention, HIPAA/DPDP certified, or zero false alerts. Do not describe a threshold change as improved discrimination. Do not call overlapping windows unique events. Do not compare v3 with a different older cohort as a paired improvement. Do not describe the withheld combination as wholly unseen physiology.

Prior work includes [GlyTwin](https://arxiv.org/abs/2504.09846). The [VVUQ perspective](https://www.nature.com/articles/s41746-025-01447-y) supports careful verification/validation as a research principle; it does not certify AURA. See the [model/data card](MODEL_DATA_CARD.md) for the measured claim and its limits.

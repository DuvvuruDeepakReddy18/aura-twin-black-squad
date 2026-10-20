# What distinguishes AURA Twin

**A digital twin the jury can challenge.** The distinction is a coherent, inspectable demonstration: authentic source files, explicit identity boundaries, available-time prediction, visible failure handling and reproducible receipts. It is not a claim to invent digital twins, counterfactual forecasting, source provenance or uncertainty estimation.

## The concrete demonstration

| Common prototype shortcut | AURA's implemented approach | Honest boundary |
|---|---|---|
| Plausible-looking generated values | Actual published CGM/HR/IBI and official Synthea exports, with hashes | Sources describe different people |
| Every displayed field implies fusion | Exact selected input list and separate negative-control ablations | CGM-only won the primary forecast comparison |
| One impressive aggregate metric | Participant split, persistence, calibration, horizon and participant results | Only three final participants |
| A probability without an event | Train-audited rise20 target, horizon tolerance and current-value reference | A research label, not necessarily adverse harm |
| A forecast with no way to challenge it | Freeze, reveal original truth, compare persistence and export a receipt | Public data are not securely blinded |
| Missing values silently completed | Nullable EHR, unavailable channels and actual quality/abstention states | Plausible bias can still pass checks |
| A slider labelled treatment simulation | Actual model input sensitivity with noncausal wording | Not intervention efficacy or dosing |
| A success-only model story | Failed V4 promotion gate and its full same-cohort results retained | Earlier missed-event problem is not claimed solved |

These are comparisons with design patterns, not factual claims about specific competing teams.

## Two-minute pitch

AURA Twin lets a reviewer see the recorded patient state, inspect a forecast and test the evidence behind it. We import authentic Synthea records and actual open research wearable data. Because they are different people, the interface explicitly calls the association a Composite Research Twin.

The model predicts glucose at four horizons using only the recorded past. We audited event support on training participants, kept all windows from each person together and froze the model before final evaluation. The selected model uses CGM history only because adding wearable or matched-study context did not win the primary forecasting criterion. We show that result rather than claiming fusion always helps.

On three final participants, the current model has 13.31 mg/dL two-hour MAE versus 16.35 for persistence. The event classifier has 66.20% recall and 22.14% precision at its frozen policy, so it is not a clinical alert system. Its uncertainty bands are broad, and we display that limitation.

The jury can select a cutoff, freeze a prediction, reveal the original outcome, compare persistence and verify an exported receipt. They can also test missing or corrupted inputs and see when the application degrades or abstains. A separate synthetic V4 experiment reduced false flags but increased primary missed positives and failed its promotion gate. We retained that negative result. Our contribution is a working, transparent engineering proof of concept whose claims can be checked.

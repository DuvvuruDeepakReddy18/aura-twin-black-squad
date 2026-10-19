# Jury questions and defensible answers

**What exactly is predicted?** Numerical glucose at +30/+60/+90/+120 minutes and probability of glucose ≥180 mg/dL at exactly +120 minutes. Not any crossing in the interval, and not necessarily a new onset.

**Where is the digital twin?** The current patient state joins a static fictional EHR with a time-indexed wearable prefix. It updates under replay and drives the forecast, quality state and review interface. It is a narrow computational twin, not a complete physiological replica.

**Did you improve both misses and false alerts?** The frozen v3 policy at 0.1550 has 74.47% recall and 37.34% precision, with 1,669 false-negative and 8,170 false-positive windows. Frozen v2 on the same cases has 1,742 FN and 8,730 FP. The gains are modest and mixed: the patient-bootstrap 95% interval for the FN difference includes zero, and the withheld combination has **324 → 330 missed positive windows**. This does not establish a reliable reduction in misses or improvement across every routine. Compare the two policies on the same fresh windows. The full paired uncertainty is in the model card; per-routine and withheld-combination results must also be read. Counts are correlated windows, not deduplicated alerts.

**Did you just lower the threshold?** Candidate choice is based on the worst FP/FN ratio to frozen v2 over specified development groups. Calibration fixes one global threshold of 0.1550 before final generation. Ranking/probability metrics and paired final counts are also reported; a threshold change alone leaves the underlying precision–recall curve unchanged.

**Is the test genuinely new?** Final identities SYN-2001–SYN-2120 are generated after model/policy freeze and were not used in earlier inspected final results. The familiar families are seen during development. The exact withheld factor combination is not. Local hashes and code order are auditable but not independently timestamped preregistration.

**Can you foresee an unannounced meal?** Not before any predictive evidence exists. Inputs contain only observed history. Previous-day values are already in the past, and future simulator meal schedules are excluded. The simulated HR meal-response term may favor the model; it does not prove meal inference from real wearables.

**Does EHR fusion add value?** Sensor-only minus fused MAE is 0.075 mg/dL on the primary final comparison. Read the paired interval. We do not attribute all improvement to EHR or promise a large fusion effect.

**What does the uncertainty band mean?** A symmetric per-horizon band from the 90th percentile of absolute calibration errors. Primary +120 coverage is 90.60%, with width 61.76 mg/dL. It is a marginal descriptive result, not a per-patient or shifted-population guarantee.

**Are explanations causal?** No. A group is replaced with its training-median reference and risk is recomputed. The percentage-point changes are nonadditive, not SHAP, and may involve unrealistic feature combinations. Scenario controls are hand-authored arithmetic; trained baseline risk stays unchanged.

**What happens when a sensor fails?** A short gap can be carried forward with a degraded state. Excessive missingness or stale CGM/HR/HRV causes abstention. A plausible bias can pass those gates, which the challenge intentionally exposes.

**Can reveal change the earlier answer?** Reveal uses the frozen prediction; it does not rerun inference. Hosted sessions carry an authenticated encrypted snapshot across instances. Offline receipts exclude that transport token and can be reproduced against the packaged data/model. Hashes are not signatures or trusted timestamps.

**What is public and private?** The public app accepts bundled synthetic IDs, and the repository contains generated records only. Care notes remain browser-local demo state. Team leader contact details belong in the submission platform, not the public repo. No real patient upload, clinical authentication or production health-record system is provided.

**What remains unproven?** External/clinical validity, medication response, unfamiliar physiology/devices, clinical benefit, usability, treatment safety and compliance certification. A prospective silent evaluation and episode-level notification analysis would be separate work.

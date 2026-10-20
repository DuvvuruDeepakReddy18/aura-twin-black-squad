# AURA Twin — research-edition judge questions

**Are the EHR and wearable records from the same person?**
No. They are explicitly a **Composite Research Twin**. Sixteen synthetic EHR profiles are independently assigned to sixteen research participant identifiers by rank. The assignment is target-blind. It demonstrates ingestion and UI integration, not physiological matching.

**Does fusion improve the model?**
Not on the selected forecasting criterion in this cohort. The primary model is **CGM history only**, chosen by selection-participant macro MAE. Final +120-minute MAE is 13.31 mg/dL, compared with 13.70 for CGM/HR/RMSSD and 14.73 for matched-study HbA1c/sex fusion. The matched fusion classifier has different strengths and a different frozen policy, but it was not the selected primary forecasting family. Unmatched Synthea fusion is a negative control, not evidence of clinical fusion benefit.

**What is the event behind the probability?**
An observed CGM rise of at least 20 mg/dL from the latest available current reading at approximately +120 minutes. The future observation must be within ±150 seconds of the nominal time. The training-only support audit did not support the original absolute ≥180 event sufficiently, so the declared fallback was used. A rise of 20 is a research label; it is not necessarily an adverse clinical event.

**How accurate is it?**
The final set has 1,859 overlapping windows from only three participants, including 287 positive rise windows. Primary MAE is 13.31 mg/dL versus 16.35 for persistence. At the frozen 0.18 threshold, recall is 66.20%, precision 22.14%, with 97 false-negative and 668 false-positive windows. Low precision is a substantial limitation; this is not a deployable clinical alert policy.

**Do thousands of windows make the evaluation large?**
No. Windows overlap and are correlated. The partition is 9 training / 2 selection / 2 calibration / 3 final people. Participant-level results are reported. The sample does not support strong population claims or reliable population confidence intervals.

**How do you prevent future leakage?**
Features use at most the historical six-hour prefix. CGM is aligned backward with at most 15 minutes of carry-forward. Minute-rounded HR is delayed 60 seconds and aggregated only in completed bins. IBI-derived RMSSD uses accepted adjacent pairs within completed bins. Tests compare complete-record and truncated-prefix features. Future samples enter only evaluation/reveal.

**Is matched HbA1c definitely available before replay?**
The study links HbA1c and sex to the wearable participant but supplies no lab timestamp. Availability as baseline context is an explicit assumption, not a proven pre-replay EHR result.

**What do uncertainty bands mean?**
They use nominal 90th-percentile absolute residuals from two calibration participants. Final +120-minute coverage is 93.54% and mean width is 71.68 mg/dL. The bands are broad and empirical. They do not guarantee coverage for each patient or a changed population.

**Are explanations causal?**
No. Grouped reference sensitivity replaces a feature group with training-reference values and recomputes probability. Changes are nonadditive, can involve unrealistic combinations, and are not SHAP values or treatment effects. Displayed context is not automatically a model input.

**Can the model predict an unannounced future meal?**
It receives no future meal or activity information. Such events are an important source of forecast uncertainty. Better performance on a designed simulator would not show that unknown real events can be anticipated.

**Why are sleep, steps and genetics missing?**
They are not available in the imported sources. The app keeps them unavailable. HRV here is derived from source IBI pairs, not a clinical ECG measurement.

**Does Freeze/Reveal constitute secure blinding?**
No. The dataset is public. It enforces a computation boundary: freeze the cutoff-bounded output, then compare it with original observed truth without recomputing. The receipt supports numerical verification, not clinical study blinding.

**What do receipt hashes prove?**
They bind an input representation and model artifact and help detect inconsistent changes. The offline verifier recomputes forecast and recorded-future scores. They are not signatures, independently trusted timestamps or evidence of authorship.

```bash
node scripts/verify_research_receipt.mjs path/to/receipt.json
```

**What happened to older synthetic scores?**
They are legacy evidence under a different population and target. The separate V4 experiment uses the unchanged simulator, fresh identities and a predeclared promotion gate. Its result is reported independently and cannot improve the apparent research-model accuracy.

**Is authentication complete?**
Demo mode requires no account. Provider-backed authentication is a separate configuration and verification task. Consult [VERIFICATION.md](VERIFICATION.md); an unconfigured form is not presented as successful login.

**What would justify clinical use?**
A substantially larger, genuinely matched dataset, prospectively defined clinical use, externally evaluated calibration and operating costs, human-factors work and appropriate clinical oversight. None is claimed complete.

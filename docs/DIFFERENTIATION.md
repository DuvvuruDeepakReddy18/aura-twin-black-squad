# AURA Twin — a digital twin the jury can challenge

**Release:** v2 Challenge Lab upgrade.  
**Implementation verification:** 25 automated tests pass. Core Challenge Lab workflows, sensor cases and phone interactions checked locally; see [verification report](VERIFICATION.md).
**Positioning:** a working synthetic glucose twin whose prediction, errors, failure handling and provenance can be inspected in one interactive experiment.

## The strongest defensible distinction

Lead with **“Choose a patient. Freeze the outlook. Reveal the future. Inspect where it fails.”**

The original prototype already fuses two streams, forecasts glucose and provides a clinician interface. The upgrade makes the evidence itself interactive. A jury member can choose a synthetic patient, timestamp and sensor condition; freeze the available-history prediction; reveal the recorded held-out future; compare the model with persistence; and export a receipt identifying the experiment.

This is an implementation and evaluation distinction. It is not a claim that glucose prediction, digital twins, counterfactual interfaces, uncertainty bands or validation methods were invented here. It also does not establish clinical usefulness.

## What the jury can inspect

| Question | Observable proof in the upgrade | Important boundary |
|---|---|---|
| What did the model know when it predicted? | Inference receives a physically truncated input prefix; the freeze response identifies the cutoff/model/input but omits future values | The dataset is public; this is not a secure blinded trial |
| Was this prediction accurate? | Reveal the recorded future at +30/+60/+90/+120 minutes and its errors | One selected window is an example, not a cohort metric |
| Is the model better than carrying the last value forward? | Model and persistence errors are shown on the same revealed future | Persistence is a benchmark; an individual result can favor either method |
| Does the uncertainty band include the outcome? | Per-horizon interval hits are shown beside the frozen intervals | Four horizon hits are not a coverage estimate for a clinical population |
| What happens to imperfect data? | Clean replay, a 10-minute CGM gap, a 30-minute dropout and an undetected +30 mg/dL sensor bias can be challenged | Gap handling is a prototype rule; plausible bias can pass freshness checks |
| Can the experiment be inspected later? | Download a JSON receipt; an offline verifier checks hashes and recomputes the prediction/reveal from the packaged artifacts | A hash is not a digital signature, trusted timestamp or clinical audit certification |
| Does performance survive changed routines? | Separate stress-test results compare the frozen model under changed synthetic meal timing | Designed synthetic stress tests are not external clinical validation |

## Comparison with common prototype patterns

This table describes design patterns, **not claims about actual competing teams or products**.

| Common presentation pattern | AURA's reviewable alternative |
|---|---|
| A dashboard displays a future line | Freeze the line before exposing recorded future values, then show the error |
| A headline accuracy value stands alone | State the exact endpoint, cohort split, prevalence, threshold, missed windows and false-positive windows |
| A smooth demo uses only clean signals | Let the evaluator select a gap, dropout or plausible sensor bias |
| A guardrail is described in a slide | Show when the model abstains and when a blind spot still passes |
| A what-if chart suggests benefit | Label arithmetic sensitivity separately from causal treatment effects |
| A screenshot is the only evidence | Provide executable code, held-out artifacts, a reproducible experiment and a downloadable receipt |

## Four experiments, four different lessons

1. **Clean replay:** establish the baseline for the chosen held-out synthetic patient and timestamp. Freeze first; reveal second. Read the actual outcome even when the model loses to persistence.
2. **10-minute CGM gap:** expose degraded input and the imputation/freshness behavior. A continuing prediction is not proof that missing data are harmless.
3. **30-minute dropout:** demonstrate the abstention boundary for stale or insufficient observations. Show the withheld prediction instead of treating abstention as a demo failure.
4. **Undetected sensor bias:** add +30 mg/dL to the observed CGM input and inspect the result. Plausible biased values can look fresh and complete. Passing quality checks does not certify sensor correctness; this case deliberately exposes that gap.

The 10-minute gap removes the final two CGM samples; the dropout removes the final six. The bias adds 30 mg/dL to the final 25 CGM samples (two hours including the cutoff), capped at 500 mg/dL. Perturbations affect the experiment's input copy. The recorded future remains the original synthetic reference. Persistence uses the same perturbed or carried-forward current glucose as the model. Reveal scores the frozen output without recomputing it; unavailable futures and abstained predictions are not assigned fabricated scores.

## The stress result we should show, not conceal

The frozen-model post-hoc audit changes main-meal timing while holding coefficients, scaling, calibration, intervals and the 0.20 alert threshold fixed. Each case uses the same 48 held-out synthetic patient identities and 6,720 correlated windows. It is separate from the per-window Challenge Lab and from the original benchmark.

| Main-meal timing | +120 min MAE | Persistence MAE | Nominal 90% interval coverage | Recall at 0.20 |
|---|---:|---:|---:|---:|
| Original | 10.95 | 22.10 | 90.0% | 83.9% |
| Delayed +2 hours | 21.62 | 21.66 | 61.7% | 28.7% |
| Delayed +4 hours | 22.78 | 19.99 | 61.3% | 21.7% |
| Irregular, 1.5-hour SD | 16.60 | 21.64 | 76.5% | 57.3% |

MAE values are mg/dL. The +4-hour model loses to persistence. This shows substantial dependence on the development simulator's timing patterns. The upgrade exposes this limitation; it does not repair the model or establish robustness. Cases were chosen after inspecting clock features, so this is a transparent **post-hoc synthetic audit**, not a preregistered or independent clinical benchmark. See `STRESS_AUDIT.md` and `data/stress.json` for the protocol and complete results.

## What a receipt proves

HTTP receipts fingerprint the **raw bytes of `data/model.json`** and the **sorted-key canonical JSON input** `{patientId, cursor, ehr, series}` after perturbation/truncation. Chronological array order is preserved. Metadata declares each encoding. The receipt can be checked without a running server:

```bash
node scripts/verify_receipt.mjs path/to/receipt.json
```

The verifier compares fingerprints and recomputes the frozen prediction and any revealed results against the packaged dataset. Passing means consistency with those local artifacts. It does not establish trusted authorship, independent time, medical validity or protection against someone replacing all artifacts and creating a matching receipt. Server experiments are temporary: one-hour expiry, 128-session capacity, and loss on restart/eviction. The downloaded file is the portable record.

## Two-minute opening pitch

Approximately 260 words; rehearse at a natural pace.

“We are Black Squad from Amrita Vishwa Vidyapeetham, Chennai. AURA Twin combines a synthetic health history with a changing wearable stream to forecast glucose at four horizons and estimate high glucose at exactly two hours.

Our central promise is a digital twin the jury can challenge. Choose a patient and a moment in their day. Freeze the prediction using only the history available then. Reveal the recorded future and inspect the error, the uncertainty band, and a simple persistence baseline. The evidence is part of the product experience.

Then change the quality of the input. A short glucose gap demonstrates degraded data. A longer dropout demonstrates abstention. A plausible sensor bias demonstrates something equally important: our freshness checks can pass while the input is wrong. We expose that blind spot so the reviewer can understand the limit of the system.

The model has a reproducible patient-level evaluation. Our separate stress experiment exposes a real weakness: delayed meals substantially worsen error and coverage. We show that result. Each challenge produces a receipt whose hashes and predictions can be checked with an offline verifier. This makes the experiment reproducible; it is not a clinical audit signature.

Glucose twins and counterfactual tools already exist. Our contribution is this complete, inspectable demonstration loop: two streams, an explicit prediction, a revealed outcome, visible failure behavior and a traceable experiment. All data are generated, and no clinical validation or treatment benefit is claimed. We invite the jury to operate the experiment and judge both the result and how honestly the system handles its limits.”

## Related work and novelty boundary

[GlyTwin](https://arxiv.org/abs/2504.09846) is prior work on glucose digital twins with patient-centered counterfactual behavioral scenarios. AURA does not claim priority for glucose twins or what-if interaction. GlyTwin's data, modeling scope and reported evaluation differ from this synthetic prototype, so their headline results must not be compared directly with AURA's metrics.

The [2025 npj Digital Medicine perspective on verification, validation and uncertainty quantification](https://www.nature.com/articles/s41746-025-01447-y) motivates scrutiny of digital-twin evidence as data and models change. Our Challenge Lab is a practical demonstration of some of those concerns. It is not a formal VVUQ certification or fulfillment of the paper's complete research agenda.

The [organizer's challenge description](https://api.unstop.com/hackathons/digital-twin-challenge-2026-happiest-health-1757873) asks for dual-stream fusion, an adverse-event prediction example and a clinician UI. The Challenge Lab extends that core submission by making prediction and failure behavior inspectable during evaluation. The rules also require a public repository and accessible presentation/video artifacts; these publishing tasks remain separate from technical differentiation.

## Claims to use and avoid

| Use | Avoid |
|---|---|
| “A jury can freeze and evaluate a synthetic prediction.” | “The first digital twin that predicts glucose.” |
| “Patient-disjoint synthetic evaluation and a separate stress experiment.” | “Clinically validated” or “proven to prevent spikes.” |
| “Abstention under documented poor-data conditions.” | “The system detects every sensor fault.” |
| “SHA-256 fingerprints help identify the experiment artifacts.” | “Tamper-proof,” “signed,” “blockchain-verified” or “regulatory-grade audit.” |
| “Hypothetical arithmetic sensitivity.” | “Personalized treatment optimization.” |
| “An implementation the jury can inspect.” | “Guaranteed winner,” “better than all competitors,” or a promised job offer. |

Keep the strongest claim tied to an action the evaluator can perform. The distinction is strongest when the demo includes an inconvenient result, not only a favorable example.

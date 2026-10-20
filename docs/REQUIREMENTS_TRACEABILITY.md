# Research rebuild — requirements traceability

| Requirement | Current implementation/evidence | Boundary or pending check |
|---|---|---|
| Team/college/roll IDs | README team table | Private phone/email remain outside public repository |
| Authentic static data | Pinned official Synthea importer and manifests | Different person from wearable source; nullable labs retained |
| Actual dynamic data | PhysioNet BIG IDEAs 1.1.3 CGM/HR/IBI | No invented steps, sleep stages, activity or genetics |
| Fusion and ablations | CGM, wearables, matched-study fusion and unmatched EHR negative controls | CGM-only won primary forecasting selection; no fusion-benefit claim |
| Working event forecast | Four horizons and a trained research rise classifier | Approximately +120 ±150 seconds; rise20 is not necessarily adverse harm |
| Future-data boundary | Six-hour prefix, backward CGM, completed HR/IBI bins, separate truth | Automated source/prefix audits and numerical parity |
| Participant-aware evaluation | 9/2/2/3 split, train-only label audit and frozen final sequence | Only three final participants; overlapping windows |
| Premium clinician UI | React/Vite, navigation, replay, record, physiology, forecast, evidence and trust | Browser checks listed separately in verification |
| 3D/2D visualization | Lazy React Three Fiber schematic with fallback | Illustrative anatomy, not a measured anatomical digital twin |
| Scenarios | Input offsets recompute the actual numerical model | Sensitivity, not causal treatment effect; excluded channels may have zero impact |
| Robustness Lab | Implemented sensor perturbation cases and aggregate audit | Perturbation audit is distinct from 1,859-window final evaluation |
| Freeze/reveal | Preserved cutoff-bound output and original observed truth | Public-data computation boundary, not secure blinding |
| Receipt | Schema-v2 research export and offline verifier | No signatures or independently trusted timestamps |
| Authentication | Supabase-backed integration, demo separate | Supabase configured; account-flow verification pending; Google disabled; no fake success |
| Judge Mode | Ten-step guided interface path | Final browser QA pending |
| Legacy synthetic model | Retained at `/legacy/index.html` | Old evidence explicitly historical |
| Synthetic improvement request | Separate V4 ensemble/residual-history experiment | Gate failed; candidate not promoted; full comparison disclosed |
| Current documentation | README, card, provenance, PDFs and runbook | Screenshots/video to finalize after UI freeze |
| Minimum 20-minute video | Current 22-chapter narration prepared | Actual current recording duration/decode pending |
| Public repository and deployment | Existing GitHub/Vercel project | Current release/access checks pending |
| License | MIT application; separate ODC/Synthea attribution | Dataset terms do not become MIT |

See [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md), [VERIFICATION.md](VERIFICATION.md), [MODEL_DATA_CARD.md](MODEL_DATA_CARD.md) and [SYNTHETIC_V4_EXPERIMENT.md](SYNTHETIC_V4_EXPERIMENT.md).

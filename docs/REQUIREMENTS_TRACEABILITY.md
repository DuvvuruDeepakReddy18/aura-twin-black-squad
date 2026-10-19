# Requirement-to-evidence map

This map separates implemented local artifacts from publishing actions still requiring completion. Read the root README for launch instructions.

| Phase 1 requirement | Implementation or artifact | Evidence boundary |
|---|---|---|
| Digital Twin proof of concept | Patient-specific historical profile fused with a changing wearable state; predictions update during replay | Narrow data-driven twin; not a whole-body physiological model |
| Static / historical EHR stream | Generated age, BMI, HbA1c, LDL and diabetes-duration context | Entirely synthetic; genetic markers are excluded from prediction |
| Dynamic / real-time stream | Five-minute generated CGM, heart rate, HRV, steps and sleep replay | Simulated stream; no real wearable account or device connection |
| Algorithm predicts an adverse-event example | Probability of CGM glucose ≥180 mg/dL at exactly +120 minutes; numerical forecasts at four horizons | Exact endpoint, not any excursion during the interval; no clinical validation |
| Demonstrate data fusion | Fused versus sensor-only, static-only and persistence ablations on held-out patients | Generator assumptions can favor fusion; external utility unproven |
| Conceptual clinician dashboard | Runnable Overview, Patient record, Model evidence and Challenge lab views with replay, explanation, hypothetical scenarios and local review/export | Prototype workflow; no production clinical identity or record governance |
| Privacy-safe training data | Repository's seeded synthetic generator; no real patient records | Synthetic development is not a legal compliance certification |
| Team and college details | Root README and presentation | Black Squad; Amrita Vishwa Vidyapeetham, Chennai |
| Title, problem, use case, stack/model | Root README, `docs/MODEL_DATA_CARD.md`, source and training files | Claims are bound to the submitted version |
| Architecture PDF/PPT | `docs/AURA_Twin_Architecture.pdf`; v2 flow in `docs/AURA_Twin_Challenge_Lab.pdf` | Core data flow plus the truncated-history / freeze / reveal / receipt sequence |
| Presentation PDF/PPT | `docs/AURA_Twin_Presentation.pdf`; separate `docs/AURA_Twin_Challenge_Lab.pdf` | Original twenty-page presentation plus a six-page upgrade supplement |
| Added differentiation: challengeable prediction | Freeze, reveal, four sensor cases, persistence comparison and receipt export | Selected-window demonstrations, not clinical validation or secure blinding |
| Added differentiation: reproducibility | `scripts/verify_receipt.mjs` checks hashes and recomputes results | Consistency with packaged artifacts, not signature/authenticity proof |
| Added differentiation: failure evidence | `docs/STRESS_AUDIT.md` and `data/stress.json` | Post-hoc changed-meal-timing synthetic audit exposes substantial degradation |
| Open-source license | Root `LICENSE` | MIT for project content; dependencies retain their own licenses |
| Minimum 20-minute video | v1 `docs/AURA_Twin_Walkthrough.mp4`, approximately 21:54; `docs/VIDEO_TRANSCRIPT.md` contains its timed script; `docs/DEMO_RUNBOOK.md` and `docs/JURY_CHALLENGE_SCRIPT.md` support an updated recording | Original video predates Challenge Lab; add a clearly labeled supplement. A short v2 clip alone does not meet the minimum. |
| Public GitHub link | Team publishes the local project and inserts actual URL | Pending until public link is tested signed out |
| Publicly accessible video and files | Team inserts actual video URL and tests all README links | Pending until independently accessible |
| Portal submission | Leader name, phone, email and public GitHub URL | Team action; personal contact details omitted from public docs |

The required project folder name is `Black Squad_Amrita Vishwa Vidyapeetham Chennai`. Do not mark a portal checkbox complete merely because this map lists the requirement; verify the associated file or public link.


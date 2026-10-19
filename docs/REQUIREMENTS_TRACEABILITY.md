# Requirement-to-evidence map

This map separates implemented local artifacts from publishing actions still requiring completion. Read the root README for launch instructions.

| Phase 1 requirement | Implementation or artifact | Evidence boundary |
|---|---|---|
| Digital Twin proof of concept | Patient-specific historical profile fused with a changing wearable state; predictions update during replay | Narrow data-driven twin; not a whole-body physiological model |
| Static / historical EHR stream | Generated age, BMI, HbA1c, LDL and diabetes-duration context | Entirely synthetic; genetic markers are excluded from prediction |
| Dynamic / real-time stream | Five-minute generated CGM, heart rate, HRV, steps and sleep replay | Simulated stream; no real wearable account or device connection |
| Algorithm predicts an adverse-event example | Probability of CGM glucose ≥180 mg/dL at exactly +120 minutes; numerical forecasts at four horizons | Exact endpoint, not any excursion during the interval; no clinical validation |
| Demonstrate data fusion | Fused versus sensor-only, static-only and persistence ablations on held-out patients | Generator assumptions can favor fusion; external utility unproven |
| Conceptual clinician dashboard | Runnable Overview, Patient record and Model evidence views with replay, explanation, hypothetical scenarios and local review/export | Prototype workflow; no production clinical identity or record governance |
| Privacy-safe training data | Repository's seeded synthetic generator; no real patient records | Synthetic development is not a legal compliance certification |
| Team and college details | Root README and presentation | Black Squad; Amrita Vishwa Vidyapeetham, Chennai |
| Title, problem, use case, stack/model | Root README, `docs/MODEL_DATA_CARD.md`, source and training files | Claims are bound to the submitted version |
| Architecture PDF/PPT | `docs/AURA_Twin_Architecture.pdf` | Two pages: inference/data flow and evaluation boundaries |
| Presentation PDF/PPT | `docs/AURA_Twin_Presentation.pdf` | Twenty pages with measured synthetic results and limitations |
| Open-source license | Root `LICENSE` | MIT for project content; dependencies retain their own licenses |
| Minimum 20-minute video | `docs/AURA_Twin_Walkthrough.mp4`, approximately 21:53; `docs/VIDEO_TRANSCRIPT.md` contains its timed script; `docs/DEMO_RUNBOOK.md` provides a human-led alternative | Synthesized-voice presentation with actual prototype screenshots; verify playback and upload the real video, since scripts alone are insufficient |
| Public GitHub link | Team publishes the local project and inserts actual URL | Pending until public link is tested signed out |
| Publicly accessible video and files | Team inserts actual video URL and tests all README links | Pending until independently accessible |
| Portal submission | Leader name, phone, email and public GitHub URL | Team action; personal contact details omitted from public docs |

The required project folder name is `Black Squad_Amrita Vishwa Vidyapeetham Chennai`. Do not mark a portal checkbox complete merely because this map lists the requirement; verify the associated file or public link.


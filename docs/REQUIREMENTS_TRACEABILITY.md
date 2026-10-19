# Requirement-to-evidence map — current model

| Phase 1 requirement | Current artifact | Evidence boundary |
| --- | --- | --- |
| Digital twin proof of concept | Patient-specific EHR + wearable state; past-only forecasts update with replay | Narrow predictive twin, not a whole-body model |
| Historical/EHR stream | Generated age, BMI, HbA1c, LDL and diabetes duration | Synthetic only; arbitrary genetic markers excluded |
| Dynamic sensor stream | Five-minute CGM, HR, HRV, steps and asleep/awake replay | Simulated, no device account or live clinical feed |
| Working adverse-event algorithm | Current boosting model forecasts four horizons and exact +120 min glucose ≥180 probability | Exact endpoint, not any excursion; no clinical validation |
| Demonstrate fusion | Fused/sensor/static/persistence/legacy comparisons on same new cases | EHR increment is modest 0.107 mg/dL; generator assumptions apply |
| Clinician UI | Overview, record, evidence, replay, scenarios, notes, exports, Challenge Lab | Conceptual workflow; no measured clinical usability benefit |
| Data constraints | Own seeded synthetic generator; no PHI | Not a compliance certification |
| Team/college/title/problem/use case/stack/model | README and current presentation/model card | Black Squad; Amrita Vishwa Vidyapeetham, Chennai |
| Architecture PDF/PPT | `AURA_Twin_Architecture.pdf`, three current pages | Runtime, partition/freeze protocol, Challenge Lab |
| Presentation PDF/PPT | `AURA_Twin_Presentation.pdf`,22 current pages; six-page lab supplement | Current model 2.0.0 evidence |
| Minimum 20-minute video | Current narration and regenerated full walkthrough | Verify actual current MP4 duration/playback; old recordings are historical |
| Open-source license | Root `LICENSE` | MIT; dependency licenses separate |
| Robustness improvement | `data/robustness.json`, protocol/selection/audit files and `STRESS_AUDIT.md` | Fresh identities within six seen routine families; not unseen-routine validation |
| Reproducible experiments | Freeze/reveal, JSON receipt, `scripts/verify_receipt.mjs` | Hash consistency, not trusted signatures or clinical audit certification |
| Public repository link | Publish local repository and insert actual URL | Pending signed-out accessibility check |
| Public video/files | Upload current video and test every README link | Pending upload and verification |
| Submission platform fields | Leader name, phone, email, public GitHub URL | Contact details are outside public repo |

Required folder: `Black Squad_Amrita Vishwa Vidyapeetham Chennai`. A listed artifact is not proof that an external publication step has been completed.

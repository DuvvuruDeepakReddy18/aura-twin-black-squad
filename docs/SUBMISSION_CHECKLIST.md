# AURA Twin — current rebuild submission checklist

Local verification of the research rebuild is complete within the scope below. Verification of the current public release is pending. Existing public links may still serve the earlier edition until release checks are completed.

| Requirement | Current status / evidence |
|---|---|
| Team and college | Black Squad; Amrita Vishwa Vidyapeetham, Chennai |
| Team members | Banu Sreya V. — CH.EN.U4ECE23009; Duvvuru Deepak Reddy — CH.EN.U4ECE23015 |
| Folder | `Black Squad_Amrita Vishwa Vidyapeetham Chennai` |
| Title, problem and use case | Current README |
| Static stream | Authentic pinned Synthea sample profiles, historical cutoff and nullable fields |
| Dynamic stream | Actual PhysioNet BIG IDEAs v1.1.3 CGM, HR and IBI |
| Identity boundary | Composite Research Twin; unmatched source people; no clinical fusion claim |
| Working algorithm | Frozen `aura-research-1.0.0`, current metrics and model/data card |
| Event | Train-only audit selected rise ≥20 mg/dL at approximately +120 min; research label, not necessarily adverse harm |
| Technical/model details | README, current card, protocol, selection and freeze records |
| Architecture | Current [architecture PDF](AURA_Twin_Architecture.pdf) |
| Presentation | Current [presentation PDF](AURA_Twin_Presentation.pdf) |
| At least 20-minute video | Current [MP4](AURA_Twin_Walkthrough.mp4): **23:52** (1,431.877687 seconds), 22 matching chapters; duration and full decoding verified |
| External video link | Pending actual unlisted upload |
| License | Application MIT; separate dataset attribution and terms |
| Automated tests and UI QA | **58 JavaScript / 16 Python tests passed**; current desktop and narrow-screen UI checks complete |
| Authentication | Supabase connected; signup/recovery disabled pending SMTP/email delivery; Google disabled pending OAuth credentials; no end-to-end account verification |
| Public GitHub current edition | Pending current release |
| Public links accessible | Check after current release |
| Submission fields | Leader name, phone, email and public repository URL; private contacts stay outside this repository |

The original brief requires a **minimum 20-minute video**. Meet that stricter requirement rather than relying on the form screenshot's 15–20-minute wording.

Before submission, confirm that screenshots, video, README, PDFs, model hash and deployed model refer to the same research edition. Historical synthetic metrics remain labelled. The V4 experiment failed its promotion gate and must not be described as solving the missed-event problem.

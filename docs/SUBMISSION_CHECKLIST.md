# AURA Twin — current rebuild submission checklist

The current research release is public and verified at commit `664bc5e7be882153285c31281d2e4c9c25157ecc`. Production checks confirmed the current frontend/model identity, public PDFs/MP4 and API freeze/reveal receipt. Remaining manual export, authentication and submission steps are listed below.

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
| Authentication | Supabase connected; signup/recovery disabled pending SMTP/email delivery; Google sign-in, profile display and session persistence after reload verified; email/password flows, sign-out and token refresh unverified |
| Public GitHub current edition | Release commit `664bc5e7be882153285c31281d2e4c9c25157ecc`; CI run 39391935412 succeeded |
| Public links accessible | Canonical Vercel site, current PDFs and MP4 verified anonymously |
| Production receipt | [API receipt](SAMPLE_RESEARCH_RECEIPT.json) reproduced offline, including recorded future truth; browser-download file still unconfirmed |
| Patient summary | Live button displayed a download-success toast; actual payload/file opening remains unverified |
| Submission fields | Leader name, phone, email and public repository URL; private contacts stay outside this repository |

Recording note: the current PDFs and video retain their earlier Google-unconfigured status. [Current authentication configuration](DEPLOYMENT.md#authentication-configuration) is authoritative; Google sign-in, profile display and persistence after reload are now verified.

The original brief requires a **minimum 20-minute video**. Meet that stricter requirement rather than relying on the form screenshot's 15–20-minute wording.

Before submission, confirm that screenshots, video, README, PDFs, model hash and deployed model refer to the same research edition. Historical synthetic metrics remain labelled. The V4 experiment failed its promotion gate and must not be described as solving the missed-event problem.

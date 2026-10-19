# Full demonstration runbook

Current model: `aura-synthetic-3.0.0`. Target a clear 24–27-minute presentation. The minimum requested recording is 20 minutes; do not use silent padding. The current 22-slide narration is [narration.json](narration.json). A local synthesized-voice rendering is disclosed as such; team members can record their own narration using this guide.

| Segment | Slides | Target | Demonstration |
|---|---|---|---|
| Team, problem and label | 1–3 | 0:00–3:00 | Name team/college; define exact +120 target and synthetic scope |
| Data, information boundary, architecture | 4–6 | 3:00–6:30 | Explain six families and withheld combination; no future meal inputs |
| Split, selection and evidence | 7–11 | 6:30–12:30 | Separate fit/select/calibrate/final; compare frozen FN/FP and show uncertainty |
| Doctor-facing interface | 12–15 | 12:30–17:00 | Patient search, chart/replay, record, group sensitivity, illustrative sandbox |
| Live challenge and receipt | 16–18 | 17:00–21:00 | Freeze/reveal, persistence, gap/dropout/bias and offline verification |
| Reproduction, limits and handoff | 19–22 | 21:00–25:30 | Code/tests, remaining unknown behavior, next validation, submission links |

## Before recording

Run the current app and confirm `/api/health` identifies the intended model. Reset demo notes and scenarios. Verify the PDF, narration and active model agree. Confirm no real patient data, leader phone/email, secrets, account tokens or personal paths appear on screen. Keep the generated patient label visible.

## Evidence wording

On the same 100,800 fresh final windows, missed positives changed from **1,742 to 1,669**, and false-positive flags from **8,730 to 8,170**. The frozen v3 policy at 0.1550 has 74.47% recall and 37.34% precision, with 1,669 false-negative and 8,170 false-positive windows. Frozen v2 on the same cases has 1,742 FN and 8,730 FP. The gains are modest and mixed: the patient-bootstrap 95% interval for the FN difference includes zero, and the withheld combination has **324 → 330 missed positive windows**. This does not establish a reliable reduction in misses or improvement across every routine.

The primary test has 100,800 windows across 120 new identities and six familiar families. The withheld combination uses those same identities and is separate. The separate withheld factor combination has 12.07 mg/dL MAE, 60.99% recall and 24.11% precision. FN changes 324 → 330; FP changes 1,657 → 1,624. Show all families, including weak cases. Do not replace the current results with an older model's original-cohort score.

Distinguish exact-horizon threshold prediction from new-event detection; window counts from episodes; descriptive bands from guarantees; grouped sensitivity from causality; arithmetic what-if controls from treatment simulation; receipt hashes from signatures; transport encryption from clinical certification.

## Live interaction sequence

Select any demo patient, inspect the timestamp and units, pause and scrub replay, then open the record and evidence tabs. Apply and reset a hypothetical scenario while showing that trained risk remains unchanged. Add a clearly fictional note and export the patient summary if useful.

Follow [JURY_CHALLENGE_SCRIPT.md](JURY_CHALLENGE_SCRIPT.md) for the challenge. Freeze first, reveal second. Allow the model to lose to persistence. Demonstrate the dropout abstention and bias blind spot. Download a receipt without its hosted transport token and run the verifier locally.

## Recording and accessibility

Use legible screen magnification, a 16:9 recording, clear speech and captions/transcript. A slide narration with actual interface screenshots is a presentation walkthrough; do not describe it as a live clinical trial or live device stream. After rendering, probe the actual duration, decode the full video, check every chapter boundary and test the public file in a signed-out browser. Record the verified result in [VERIFICATION.md](VERIFICATION.md) and the README.

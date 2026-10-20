# AURA Twin — current research demonstration runbook

This script matches the research edition and its frozen numerical artifacts. Estimated speaking times are planning estimates; the delivered MP4 must be measured and decoded before claiming its duration. Record at least 20 minutes for the competition brief.

## Before recording

1. Build and run the current app. Confirm the model version and source mode.
2. Verify that any displayed account flows match actual provider configuration.
3. Open the presentation and current research UI, not historical synthetic screenshots.
4. Confirm source identity, replay cutoff, threshold and model hash.
5. Use only the bundled de-identified research and synthetic data. Keep private leader contact details and deployment secrets out of the recording.

## Speaking sequence

| Estimated time | Slide | Topic |
|---|---|---|
| 00:00–01:12 | 1 | See the patient. Understand what comes next. |
| 01:12–02:27 | 2 | A useful forecast must also be inspectable |
| 02:27–03:40 | 3 | Two sources. Two identities. One honest boundary. |
| 03:40–04:55 | 4 | Missing information stays missing |
| 04:55–06:12 | 5 | A traceable path from source to prediction |
| 06:12–07:39 | 6 | State the event before showing a probability |
| 07:39–08:55 | 7 | Separate people before evaluating windows |
| 08:55–10:14 | 8 | The model only receives the recorded past |
| 10:14–11:30 | 9 | Compare fusion with honest alternatives |
| 11:30–12:42 | 10 | Measured research results, with their denominator |
| 12:42–13:57 | 11 | Confidence should be measured, not decorated |
| 13:57–15:12 | 12 | A clinician-oriented workspace |
| 15:12–16:27 | 13 | The record view keeps provenance close |
| 16:27–17:45 | 14 | Explain the computation without claiming causality |
| 17:45–19:01 | 15 | Freeze first. Reveal later. Compare honestly. |
| 19:01–20:18 | 16 | Test the failure boundary |
| 20:18–21:35 | 17 | Keep the evidence beside the experience |
| 21:35–23:03 | 18 | A working demo does not require a fake login |
| 23:03–24:33 | 19 | Separate research evidence from simulator progress |
| 24:33–25:51 | 20 | Verification follows the claims |
| 25:51–27:07 | 21 | A short, reproducible jury walkthrough |
| 27:07–28:24 | 22 | A forecast you can question. |

The complete narration is in [narration.json](narration.json). Generated transcripts must come from that same file and the final chapter timings.

## 90-second jury path

- 00:00–00:30: Open demo, select a participant and identify composite provenance, research model version and cutoff.
- 00:30–01:00: Inspect forecast, uncertainty and actual inputs; freeze a prediction.
- 01:00–01:30: Reveal recorded outcomes, compare persistence, inspect a supported failure case and export evidence.

## Five-minute interactive path

1. Explain why Synthea context and the wearable participant are different identities.
2. Show one authentic EHR observation and one missing field.
3. Explain the current prediction target and target-time tolerance.
4. Change replay cutoff and inspect the model's available input boundary.
5. Freeze/reveal one prediction; report the result even if persistence wins.
6. Open model evidence and the participant-level limitations.
7. Demonstrate a supported quality/abstention case.
8. Explain which account/persistence flows are configured and verified.

## Recording guardrails

Do not call simulated playback live device monitoring. Do not compare research scores with legacy V3 scores as an improvement. Do not describe source-label events as diagnosed harm. Reference sensitivity is not causal or treatment advice. Missing sleep/steps/genetics must remain unavailable. The public dataset is not securely blinded by hiding the outcome in the UI.

An unlisted upload URL is pending until a real upload exists. The original guidelines require a minimum 20-minute video; satisfy that stricter requirement even though the form screenshot mentions 15–20 minutes.

# Prototype verification

Verified locally on 19 October 2026. This is software verification and synthetic evaluation, not clinical validation.

## Automated checks

`npm test`: **16 passed, 0 failed**.

- Exported predictions and all feature values match Python reference fixtures for eight held-out patients.
- Future data changes cannot alter a prediction at the current replay cursor.
- Changing historical EHR context while holding sensors fixed changes the fused forecast.
- Insufficient history and stale glucose abstain; short sensor gaps report degraded quality.
- Scenarios preserve baseline risk and use the documented illustrative formula.
- Frozen alert threshold and forecast interval metadata are consistent.
- Invalid timestamps, malformed EHR/sensor payloads, invalid cursor/scenario inputs and invalid JSON are rejected.
- API health, prediction, direct two-stream ingestion, metrics and static routes respond correctly.
- Static path traversal and attempts to retrieve server/config source fail.

JavaScript syntax checks passed. The suite uses temporary local HTTP sockets; a sandbox that blocks loopback networking must allow those connections for the API tests.

## Browser workflow checks

Checked in Chrome with the actual local app and trained model artifacts:

- Patient search filters the list; selecting a patient changes EHR, sensor values and forecast.
- Moving the timeline advances from 12:00 to 12:05 and recomputes the prediction.
- Scenario input shifts the curve, leaves baseline risk unchanged and resets to the original curve.
- Notes persist across a new browser tab; acknowledgement is stored for the selected patient/replay moment.
- Export creates a real HTML summary; the verified example is `SAMPLE_PATIENT_REPORT.html`.
- Record, evidence and guide views open and show their intended content.
- A 390 CSS-pixel phone viewport has no horizontal page overflow; the patient drawer opens, permits selection and closes.
- No browser console errors were observed in the tested workflows.

The mobile navigation is hidden from focus/accessibility when closed. This was a targeted usability check, not an exhaustive accessibility audit.

## Document and video checks

- 20 presentation pages and 2 architecture pages rendered and inspected.
- Numerical claims were cross-checked against `data/metrics.json`.
- Relative README artifact links checked for existence.
- MP4 duration: **1,313.828 seconds** (21 minutes 53.8 seconds).
- MP4: H.264 video at 1280 × 720, AAC audio; approximately 20.4 MB.
- The complete MP4 decoded without errors; a frame was inspected against the matching slide.
- Narration uses a disclosed local synthesized voice; actual app screenshots illustrate the presentation.

Public GitHub publication, unlisted video upload, signed-out link verification and portal submission have not been performed.


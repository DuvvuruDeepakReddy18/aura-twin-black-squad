# Prototype verification

Verified locally on 19 October 2026. This is software verification and synthetic evaluation, not clinical validation.

## Automated checks

`npm test`: **25 passed, 0 failed** for app version 1.1.0.

- Exported predictions and all feature values match Python reference fixtures for eight held-out patients.
- Future data changes cannot alter a prediction at the current replay cursor.
- Changing historical EHR context while holding sensors fixed changes the fused forecast.
- Insufficient history and stale glucose abstain; short sensor gaps report degraded quality.
- Scenarios preserve baseline risk and use the documented illustrative formula.
- Frozen alert threshold and forecast interval metadata are consistent.
- Invalid timestamps, malformed EHR/sensor payloads, invalid cursor/scenario inputs and invalid JSON are rejected.
- API health, prediction, direct two-stream ingestion, metrics and static routes respond correctly.
- Static path traversal and attempts to retrieve server/config source fail.
- Challenge predictions receive a physically truncated input prefix. Reveal reads frozen outputs and never reruns inference.
- Clean, short-gap, dropout and biased-input cases preserve the original patient data and future truth.
- Challenge sessions enforce expiry, capacity, input validation and explicit missing-future handling.
- Offline receipt verification reproduces all four modes and detects changed predictions, outcomes, inputs, cursor/mode or model-file bytes.
- The frozen-model meal-timing audit reproduces the reference benchmark and evaluates all 6,720 windows in each of four specified synthetic conditions. No fitting occurs in the audit.

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

### Challenge Lab integration

- Clean replay froze before reveal and displayed original future values, per-horizon errors, persistence and interval hits.
- Ten-minute CGM gap produced a degraded-data result. Thirty-minute dropout withheld numeric forecasts and risk; reveal did not assign it a zero error.
- The +30 mg/dL CGM bias passed completeness/freshness checks and was explicitly labeled an undetected blind spot.
- Changing the cutoff cleared the frozen result. Switching patients updated the context and actual recorded diagnosis.
- At a 390 CSS-pixel phone viewport, freeze/reveal worked with no horizontal page overflow; opening the drawer and selecting another patient updated the view and closed the drawer.
- No console errors were observed. The receipt download action was initiated; browser-managed file delivery was not independently confirmed in this automation session.
- A real API-generated receipt is saved as [`SAMPLE_CHALLENGE_RECEIPT.json`](SAMPLE_CHALLENGE_RECEIPT.json). `node scripts/verify_receipt.mjs docs/SAMPLE_CHALLENGE_RECEIPT.json` successfully reproduced its input fingerprint, forecast and revealed comparison offline.

## Document and video checks

- 20 presentation pages and 2 architecture pages rendered and inspected.
- Numerical claims were cross-checked against `data/metrics.json`.
- Relative README artifact links checked for existence.
- MP4 duration: **1,313.828 seconds** (21 minutes 53.8 seconds).
- MP4: H.264 video at 1280 × 720, AAC audio; approximately 20.4 MB.
- The complete MP4 decoded without errors; a frame was inspected against the matching slide.
- Narration uses a disclosed local synthesized voice; actual app screenshots illustrate the presentation.
- The six-page Challenge Lab supplement was rendered and visually inspected. Its separate MP4 runs **230.4 seconds** (3 minutes 50 seconds), H.264 1280 × 720 with AAC audio, and decoded without errors. The original 21:54 video remains the main submission walkthrough.

Public GitHub publication, unlisted video upload, signed-out link verification and portal submission have not been performed.


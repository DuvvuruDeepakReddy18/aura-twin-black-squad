# Current prototype verification

Verified locally on 19 October 2026 for model `aura-synthetic-2.0.0`. This is software verification and synthetic evaluation, not clinical validation.

## Automated and artifact checks

- **31 JavaScript tests passed, 0 failed** via `npm test`.
- **4 Python data-contract tests passed** via `npm run test:data`.
- All 53 feature values, four forecasts and risk match 16 Python fixtures across eight current demo records; feature tolerance 1e-8 and risk tolerance 1e-10.
- Past-prefix invariance and clock-translation invariance protect the current information boundary. Previous-day indices refer only to already observed readings.
- EHR sensitivity, quality/abstention, short gaps, scenario reset and preserved baseline risk are checked.
- API validation, direct two-stream ingestion, health/current evidence and static-route restrictions are checked.
- Challenge freeze physically truncates history; reveal uses the frozen output. All four modes preserve original patient/future data. Expiry, capacity and unavailable-future behavior are checked.
- Offline receipt verification reproduces experiments and detects changed predictions, outcomes, hashes and model bytes.
- **Independent exported-JSON audit passed all six current cases**, matching MAE, AUROC, Brier, interval coverage, recall and precision to 1e-10 without fitting or recalibration. The archived v1 four-case audit also reproduced its historical results.
- The current model's raw SHA-256 is `a67d3a6abd84df76f3cbbbb30e35a10f0845417b7b12bbb09df83c398ef317a4`. The artifact is saved before final patient generation and checked unchanged afterward.

These 35 automated checks plus the separate exported-model audit verify specified behavior. They do not establish clinical performance, complete security or independence from simulator design.

## Current browser evidence

- Current model/evidence values, all six routine rows, interval widths/coverage and policy precision/recall matched artifacts in the actual local browser.
- Updated patient routine context was visible; selecting the variable-routine Rohan record worked.
- Maya's actual Challenge Lab freeze/reveal at the checked cutoff showed four available horizons, model MAE 6.883 versus persistence 34.28, and four interval hits. This is one selected window, not a cohort metric.
- A fresh v2 API receipt for SYN-1001, cursor 810 was exported and verified offline.
- Current screenshots captured overview, patient record, evidence, robustness table and Challenge Lab.
- Current 390 px mobile layout was checked: 367 px body width, with a 301 px robustness-table container scrolling its 910 px content internally rather than overflowing the page. Variable-routine Rohan freeze/reveal worked; 30-minute CGM dropout withheld probability and forecast. Desktop current views were checked. The actual browser HTML export was downloaded and copied to `SAMPLE_PATIENT_REPORT.html`: Rohan (SYN-1006), 15 October 00:30 UTC, cursor 870, current model 2.0.0, glucose 157.5 mg/dL, +120 forecast 126.1 with band 95.3–156.9 mg/dL, probability 0.1% and threshold 16%. Its explanation states nonadditive group-reference sensitivity.

## Document and video checks

- Current 22-page presentation, three-page architecture and six-page supplement were regenerated from current artifacts. All 22 presentation pages were rendered and visually inspected; the supplement/architecture reuse those checked pages.
- The current narration has 4,286 words and matches the 22-slide presentation, including the modest EHR gain and remaining limitations.
- Current full video: 1,510.580957 seconds (25:10.6), 22 chapters, H.264 at 1280 × 720 with AAC audio, 23,156,428 bytes. Complete decoding passed. This current recording supersedes the historical clips and exceeds the 20-minute minimum.
- Public GitHub publication, video upload, signed-out accessibility and portal submission have not been performed.

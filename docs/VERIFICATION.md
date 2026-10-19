# Current verification record

Model: `aura-synthetic-3.0.0`. Raw model-file SHA-256: `87fb0df0832c2db76b03c55c81298ab717200c3dc60048b9b4586dc7061d81b4`.

The frozen V3 artifact passed **36 JavaScript tests and 5 Python data-contract tests**. An independent exported-JSON inference audit reproduced all **seven current routine cases**, including the withheld combination, without fitting or recalibration. Audit metadata is recorded in `data/stress.json`. Final browser/media and production-link checks are listed separately below; earlier V2 checks are not silently reused.

## Completed implementation and evidence checks

- JavaScript tests: Python/export parity, 108-feature prefix invariance, clock translation, sensor-quality states, API validation, challenge freeze/reveal, receipt consistency and hosted portable-token behavior.
- Python data-contract tests: deterministic generator behavior, paired routine perturbations, sleep-wrap behavior and prefix-derived features.
- Independent exported-JSON audit of every current routine, including the withheld combination, without fitting or retuning.
- All current Markdown artifact links resolve. Code fences and localhost URL formatting remain intact.
- Current narration contains 4,442 words across 22 chapters and identifies the frozen model. Its text is the source for the current audio; ordinary text-file newline normalization does not alter that spoken content.
- Current desktop views were checked against the active V3 model. Five fresh screenshots are supplied in `docs/assets/`; the presentation embeds the overview, replay and record views and presents evidence/Challenge Lab as readable tables and diagrams. The 22-page presentation, three-page architecture and six-page supplement received visual inspection.
- The current API challenge receipt for SYN-2001 passed offline verification. The patient-summary HTML was downloaded through the browser's actual Export patient summary action and records `aura-synthetic-3.0.0` with the 15.50% decision threshold.
- The current main MP4 is **26:24.11** (1,584.109961 seconds), with H.264 video at 1280 × 720, AAC audio and 22 matching chapters. A full FFmpeg decode completed successfully. Both transcripts were regenerated from the current narration; the main transcript includes the matching chapter times.
- Anonymous production requests to [aura-twin-black-squad.vercel.app](https://aura-twin-black-squad.vercel.app) returned HTTP 200 for the homepage, current-model health endpoint, presentation, architecture and 24,418,262-byte main MP4. The health endpoint reported `aura-synthetic-3.0.0`.
- Anonymous hosted freeze/reveal completed successfully. Its exported token-free receipt, supplied as `docs/SAMPLE_CHALLENGE_RECEIPT.json`, passed offline reproduction against the frozen model hash above.

## Final publication checks still in progress

- Browser playback of the public MP4 and publication of the final repository revision.

Fresh V3 mobile-browser verification is not claimed: the attempted viewport override did not change the browser's actual viewport. Earlier mobile checks belong to the prior revision.

## Privacy review already completed

Before V3 additions, targeted scans covered four commits and 121 unique text blobs, plus PDF text/metadata and MP4 metadata. The final tracked/unignored text scan covered 104 files, including V3 additions. No private contact/path/credential finding remained; Python matrix multiplication caused three reviewed false positives. This is a targeted review, not a comprehensive security audit or clinical compliance certification.

## Evidence boundaries

The frozen v3 policy at 0.1550 has 74.47% recall and 37.34% precision, with 1,669 false-negative and 8,170 false-positive windows. Frozen v2 on the same cases has 1,742 FN and 8,730 FP. The separate withheld factor combination has 12.07 mg/dL MAE, 60.99% recall and 24.11% precision. FN changes 324 → 330; FP changes 1,657 → 1,624. The final test is synthetic; repeated windows and variants are correlated. Passing implementation tests does not establish clinical safety, real-device validity, treatment efficacy or secure study blinding. Receipt hashes are not signatures. Hosted snapshot encryption protects transport integrity, not clinical validity.

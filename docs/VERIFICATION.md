# Current research-edition verification record

**Model:** `aura-research-1.0.0`

**Raw model-file SHA-256:** `a4371ed5c7c768bf2d210917d6e7bf28ce89da7147ead0a98c14f48568abf432`

This record distinguishes current research checks from older synthetic-edition checks. The current 23:52 recording replaces the historical 26:24 synthetic recording. The current public release was verified on 20 October 2026, including its frontend bundle, model hash, public artifacts and API freeze/reveal receipt.

## Completed data and methodology checks

- Official Synthea archive pinned by source commit and SHA-256; checksum verified before publication of transformed records.
- Three Synthea importer tests passed: future observation/resolution exclusion, missing/private field handling and checksum rejection.
- Sixteen profiles selected and assigned without sensor/outcome matching. Missing labs remain null. Earliest wearable date is 2020-02-13, later than the chosen 2019-01-01 Synthea snapshot; the sources remain different people.
- Research source files checked against publisher checksums. Source manifest and preprocessing audits supplied.
- Research participant partitions disjoint; label audit training-only; numerical model frozen before final-participant evaluation.
- Historical prefix invariance, source availability timestamps and actual future target timestamps within ±150 seconds checked by the research leakage audit.
- Final results, negative controls and participant-level breakdown saved without retuning on the three final participants.
- Final integration suite passed **58 JavaScript tests and 16 Python tests**.
- Independent runtime audit sampled 496 actual-target windows across the three final participants, with 15 physical-prefix comparisons. Its forecast-availability denominator is distinct from the main 1,859-window evaluation.
- New navy presentation has 22 pages, architecture four pages and challenge supplement six pages. Rendered tables and final screenshot pages were visually inspected. Four actual current UI captures are embedded; the record capture uses PDF clipping to exclude blank capture padding, preserving the original image.
- Separate synthetic V4 experiment completed on fresh identities and failed its predeclared promotion gate. Its three feature-contract tests passed; candidate is not promoted.
- Current desktop and narrow-screen interaction checks completed on the React research workspace.
- The current [demonstration MP4](AURA_Twin_Walkthrough.mp4) is **23:52** (1,431.877687 seconds), with 22 chapters matching the current research narration. Duration probing and complete decoding passed.

## Verified public release

- Release commit: [`664bc5e7be882153285c31281d2e4c9c25157ecc`](https://github.com/DuvvuruDeepakReddy18/aura-twin-black-squad/commit/664bc5e7be882153285c31281d2e4c9c25157ecc).
- [GitHub CI run 39391935412](https://github.com/DuvvuruDeepakReddy18/aura-twin-black-squad/actions/runs/39391935412) succeeded with **58 JavaScript and 16 Python tests**.
- Vercel deployment `dpl_2L1qRGTATeVAU46JcDg5kgsnyUKF` reached READY. The [canonical site](https://aura-twin-black-squad.vercel.app) served frontend `index-CUQ3klm5.js` and the research model hash above.
- Anonymous checks returned HTTP 200 for the homepage, legacy route, current presentation PDF, architecture PDF and **20,888,332-byte** current MP4. The production check recorded 16 bundled research participants and five ablation models.
- A Vercel error-level log scan covering **2026-10-20 08:09:50–08:19:50 UTC** returned **zero records**. This is limited to that severity filter and time window; it does not establish that all requests or user flows were error-free.
- An actual production API freeze/reveal for `research-001` at cutoff `2020-02-13T23:25:00Z` produced a token-free receipt. The [supplied receipt](SAMPLE_RESEARCH_RECEIPT.json) passed offline reproduction of inputs, forecasts and the exact recorded future comparison (`revealVerified: true`).
- Live browser QA loaded the deployed research twin with participant 001, the current model and its 3D scene. Clicking **Generate review summary** produced the UI toast “Structured review summary downloaded.” The resulting payload, filesystem file and file opening were not verified.

The API-produced receipt was copied byte-for-byte into the repository and independently rechecked. The browser's receipt button was exercised, but its resulting file was not confirmed on the filesystem; that separate UI-download check is not claimed complete.

## Remaining manual checks

- Confirm the browser receipt-download file on the filesystem.
- Confirm and open the current patient-summary file; the button's success toast alone does not verify its payload or download.
- End-to-end account-flow verification after the required provider configuration.

Supabase public configuration is connected, with email confirmation enabled. Public email sign-up and recovery are intentionally disabled pending SMTP/email delivery. The Supabase Google provider is now enabled, confirmed through its public provider settings after secure credential configuration. The public Google feature flag is enabled for Vercel production and preview. Existing-account sign-in is provider-backed, but no end-to-end account flow, including Google sign-in, has been verified. Demo access requires no account.

## Reproduction

```bash
npm test
python -m pip install -r ml/requirements.txt
npm run test:data
node scripts/verify_research_receipt.mjs path/to/receipt.json
node scripts/verify_research_receipt.mjs docs/SAMPLE_RESEARCH_RECEIPT.json
python scripts/build_research_docs.py --auth-status configured-unverified
```

Change authentication status only when supported by configuration and verification evidence. The current PDFs and 23:52 recording were produced before Google configuration; their Google-unconfigured wording is historical. The current status in this record and [deployment documentation](DEPLOYMENT.md#authentication-configuration) is authoritative. The frozen scientific content, PDFs and video remain unchanged; future regenerated assets should use the then-current verified status.

## Scope

Source integrity and numerical tests do not establish clinical safety, population validity or causal explanations. Hashes are not signatures or independent timestamps. Public data are not securely blinded by hiding the future. Plausible sensor bias can pass freshness checks. Perturbation comparisons preserve original future truth and the clean current reference for the rise label; the perturbed model probability may use a different current input. Residual bands are not recalibrated or guaranteed under perturbation.

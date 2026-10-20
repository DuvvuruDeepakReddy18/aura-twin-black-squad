# Current research-edition verification record

**Model:** `aura-research-1.0.0`

**Raw model-file SHA-256:** `a4371ed5c7c768bf2d210917d6e7bf28ce89da7147ead0a98c14f48568abf432`

This record distinguishes current research checks from older synthetic-edition checks. The current 23:52 recording replaces the historical 26:24 synthetic recording. Verification of the current public release remains pending; earlier production checks do not establish its deployed model identity.

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

## Final product verification pending

- Actual research receipt export and offline reproduction.
- Current patient-summary export.
- End-to-end account-flow verification after the required provider configuration.
- Anonymous current-release links and deployed model hash.

Supabase public configuration is connected, with email confirmation enabled. Public email sign-up and recovery are intentionally disabled pending SMTP/email delivery. Google sign-in is disabled pending OAuth credentials. Existing-account sign-in is provider-backed, but no end-to-end account flow has been verified. Demo access requires no account.

## Reproduction

```bash
npm test
python -m pip install -r ml/requirements.txt
npm run test:data
node scripts/verify_research_receipt.mjs path/to/receipt.json
python scripts/build_research_docs.py --auth-status configured-unverified
```

Change authentication status only when supported by configuration and verification evidence. Narration and PDFs must be regenerated together after a material model or status change.

## Scope

Source integrity and numerical tests do not establish clinical safety, population validity or causal explanations. Hashes are not signatures or independent timestamps. Public data are not securely blinded by hiding the future. Plausible sensor bias can pass freshness checks. Perturbation comparisons preserve original future truth and the clean current reference for the rise label; the perturbed model probability may use a different current input. Residual bands are not recalibrated or guaranteed under perturbation.

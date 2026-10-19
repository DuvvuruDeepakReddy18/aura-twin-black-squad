# AURA Twin — three-minute jury challenge

**Release:** v2 Challenge Lab.  
**Implementation verification:** challenge API and receipt-verifier checks passed; consult `VERIFICATION.md` for the final browser checks.  
**Purpose:** demonstrate an inspectable prediction and its failure boundaries in three minutes. This supplements the original 21:54 narrated walkthrough, which covers the v1 prototype.

## Setup before the jury session

1. Launch the application using the root README. Open **Challenge lab**.
2. Select a held-out synthetic patient and a cutoff with a complete recorded +120-minute future. Use the same patient and cutoff for the sensor-condition comparison. The jury may choose another supported patient/time; do not require a favorable preselected result.
3. Keep the separate stress-test result file available. Read its exact protocol and results before presenting. Do not replace the main held-out metrics with the stress metrics or merge the populations.
4. Rehearse **Freeze prediction**, **Reveal recorded future**, **Download receipt** and **Reset experiment**. Save a receipt once and inspect its structure before the live session.
5. Explain that “freeze” preserves a server-side in-memory experiment snapshot. Inference receives a physically truncated past-only input; the freeze response omits future readings. The recorded future is in the public synthetic dataset, so this is not a cryptographically secured or prospectively blinded trial.

## 00:00–00:20 · Give the jury control

**Action:** open **Challenge lab**; show the selected patient, cutoff and **Clean replay** case.

**Say:** “This is a held-out synthetic patient. You can choose the patient, time and signal condition. We will freeze what the model can infer from the past, then reveal the recorded future. The exact event is glucose at least 180 milligrams per deciliter at the two-hour endpoint.”

## 00:20–00:50 · Freeze before revealing

**Action:** click **Freeze prediction**. Point out the frozen cutoff, quality state, forecast and probability.

**Say:** “This snapshot identifies the input history, model and sensor condition. Later replay changes do not silently rewrite this experiment. The future has not yet been revealed in this view. We can now assess this fixed result.”

Do not claim that browser users cannot inspect packaged future data or modify local code.

## 00:50–01:20 · Reveal the outcome, including a miss

**Action:** click **Reveal recorded future**. Show the per-horizon table, model error, persistence error, interval hits and exact +120-minute event.

**Say:** “These are the recorded synthetic future readings. We show the numerical error and compare the same outcome with carrying the last available value forward. If persistence wins, or a future reading falls outside the interval, that result stays visible. This is one selected window; the full cohort evaluation remains separate.”

Use the values actually on screen. Never read a memorized success case after the jury changes the patient or cutoff.

## 01:20–01:40 · Challenge a short gap

**Action:** reset the experiment, select **10-minute CGM gap**, freeze, and inspect quality. Reveal if a forecast is available.

**Say:** “A short gap tests our documented freshness and imputation behavior. The model may continue with degraded data, which is a qualified output rather than evidence that a gap is harmless.”

## 01:40–02:00 · Make abstention visible

**Action:** reset, select **30-minute dropout**, and freeze.

**Say:** “Here the input violates the quality rule, so a forecast and risk are withheld. Abstention is an observable response. These rules are prototype guardrails, not a clinically validated safety system.”

If the final case implementation reports a different specific reason, read that reason directly from the UI rather than inventing one.

## 02:00–02:25 · Expose the blind spot

**Action:** reset, select **Undetected sensor bias**, freeze and reveal.

**Say:** “This case adds thirty milligrams per deciliter to observed glucose. The values can still look complete, fresh and plausible. Quality checks may pass while the forecast becomes less reliable. The case deliberately demonstrates a fault that our current checks cannot certify away.”

Do not claim that the model detects bias. Do not claim every biased-window error must increase; show the chosen window's actual result.

## 02:25–02:45 · Export a reviewable receipt

**Action:** click **Download receipt** and show its experiment identifiers and SHA-256 fingerprints.

**Say:** “The receipt identifies the prediction snapshot and the result we revealed. Hashes help compare the artifacts used for this experiment. They do not authenticate a clinician, establish an independent timestamp, or prevent someone from editing a file and computing a new hash.”

If time permits, run `node scripts/verify_receipt.mjs path/to/receipt.json` to check the fingerprints and recomputed results against the packaged artifacts. The verifier can run without the server or an active experiment session.

## 02:45–03:00 · Close on evidence

**Action:** point to the separate routine-shift stress results, without starting a second full demo.

**Say:** “Delaying synthetic meals by four hours increases our two-hour error from 10.95 to 22.78, worse than persistence at 19.99. The audit exposes clock dependence. Our contribution is evidence the jury can inspect; clinical validity remains future work.”

## If the jury asks for a deeper demonstration

- **Five more minutes:** select a different patient and cutoff; compare all four cases on the same underlying reference future; inspect the receipt fields in the source.
- **Reproducibility:** run the documented model and API checks, then the separate stress-evaluation command from the root README.
- **Privacy:** show the generator and synthetic-data flag; do not import personal health data during the presentation.
- **Novelty:** acknowledge related glucose-twin work and explain that this release's distinction is an inspectable product-and-evidence loop, not a new clinical theory or the invention of glucose prediction.

## A useful response to an unfavorable result

“That is a valid failure for this selected window. The full test metrics quantify performance across the defined cohort, and this experiment exposes one of the local outcomes that a summary statistic hides. We preserve the failed prediction in the receipt and use it to guide further testing.”

Avoid switching immediately to another patient to recover a favorable screenshot. Explain the failure first.

## Video supplement

Record this challenge sequence as a short supplement after the original narrated walkthrough, or include it in a new team-led recording. The original video should remain labeled **v1** until a replacement actually includes the upgrade. A v2 PDF appendix alone does not demonstrate the new interactions in the old video. Keep the combined submission video at or above the organizer's required minimum and test the final public link while signed out.

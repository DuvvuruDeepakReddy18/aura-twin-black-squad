# Current six-page supplement narration

This is source narration for the current Challenge Lab/evidence PDF. No separate supplementary video is required or represented here; the current 25-minute full walkthrough includes these topics. These paragraphs describe model `aura-synthetic-2.0.0`, not the historical unchanged-model upgrade.

[Current supplement PDF](AURA_Twin_Challenge_Lab.pdf) · [Full current walkthrough](AURA_Twin_Walkthrough.mp4)

## Page 1 — A patient’s history. A more adaptable outlook.

Welcome to AURA Twin, a digital twin proof of concept by Black Squad from Amrita Vishwa Vidyapeetham, Chennai. Our team members are Banu Sreya V., the team leader, and Duvvuru Deepak Reddy. This walkthrough covers the current model, the working clinician dashboard, and the evidence behind our improvement for irregular routines.

The central task is specific: combine a synthetic historical health record with a changing wearable stream to forecast glucose at four future horizons and estimate high glucose exactly two hours ahead. We built the complete path, from generation and model selection to local inference, review, and a reproducible challenge protocol.

An earlier model performed well on regular synthetic routines but failed when meal timing changed. We treated that failure as a development signal. The current pipeline reduces its dependence on clock patterns, trains on a broader declared routine mixture, and evaluates a frozen model on new patient identities. We will show both improvement and remaining errors. All patients and measurements are generated. None of these results establish clinical efficacy, diagnosis, or treatment safety.

## Page 2 — Freeze the prediction. Then reveal the outcome.

Challenge Lab gives the jury a repeatable way to question the model. Choose a synthetic patient, a cutoff, and one of the supported sensor conditions. Freeze prediction copies the patient state, physically truncates the wearable history at the cutoff, applies the selected perturbation, and runs inference. The returned frozen object contains the forecast, event probability, quality state, and provenance information. It does not include future outcomes.

After inference completes, the server snapshots the original recorded future at the four horizons. Reveal recorded future compares those observations with the already frozen output. It does not recompute the model after seeing the answer. The comparison includes numerical error, the persistence baseline, interval hits, and the exact two-hour threshold outcome.

This protocol is inspectable, but it is not a secure blinded clinical study. The synthetic dataset is public, and the team can read it. Its value is enforcing the computation's information boundary and making a selected prediction falsifiable. The selected-window table is not an estimate of cohort-wide performance. Missing future observations and abstained predictions do not receive invented scores. If a forecast loses to persistence, the result stays visible.

## Page 3 — Four sensor cases expose different failure modes.

The four Challenge Lab cases answer different questions. Clean replay establishes the baseline at the chosen cutoff. The ten-minute CGM gap removes the final two glucose samples. Within the permitted freshness limit, the pipeline can carry the last available value forward and mark the input as degraded. This demonstrates a known handling policy, not proof that the imputation is accurate.

The thirty-minute dropout removes the final six glucose samples. The last available glucose is too old for the quality gate, so the model withholds its forecast and probability. A reviewer sees abstention rather than a fabricated confident answer. Acknowledging that state does not make the missing data safe or restore a prediction.

The final case introduces a plausible positive glucose bias over the recent input window. These values can remain fresh and numerically plausible, so basic quality checks may pass even though the forecast is wrong. This is a deliberate blind spot in the demonstration. The reference future remains unchanged, and persistence receives the same perturbed current observation as the model. Together, these cases separate missingness handling from bias detection and make clear that quality status is not a certificate of sensor truth.

## Page 4 — Compare models on the same fresh routine cases.

To assess the improvement fairly, we compare models on the same new patient identities and routine cases. The comparison includes the current fused model, a sensor-only ablation, a static-only ablation, persistence, and the frozen earlier model where reported. Persistence predicts that the current glucose value will remain the same at the forecast horizon. It is simple, useful, and can beat a more complicated model on particular windows.

The current fused two-hour error is 11.62. Sensor-only error is 11.73, and persistence error is 20.32. The added EHR benefit over sensors is modest: about zero point one one milligrams per deciliter, or roughly one percent. The larger improvement comes from the changed history features, routine-augmented training, and nonlinear model. The routine table also separates regular timing, two- and four-hour delays, jittered timing, day-varying meals, and variable sleep or activity. A pooled improvement can hide a weak routine family, so these separate rows are part of the evidence rather than an optional appendix.

Do not compare the current mixture directly with the original ten-point-nine-five result as if the cohorts and tasks were identical. The original result came from a narrower generator and different people. The valid improvement comparison uses the same new cases. Even a consistent gain over the old model establishes only a synthetic benchmark improvement. It does not validate performance for real patients, unfamiliar devices, medications, or unmodeled behavior.

## Page 5 — Make the experiment reproducible offline.

Download receipt exports the frozen experiment and any revealed outcome comparison as a JSON document. The receipt includes a SHA-two-fifty-six fingerprint of the exact model file and a fingerprint of the canonical perturbed input prefix. The model hash covers raw file bytes. The input hash uses a defined sorted-key JSON representation while preserving array order. That distinction matters when reproducing the experiment across environments.

The repository includes an offline verifier. It reconstructs the input from packaged data, checks the hashes, reruns the prediction, and compares the revealed values and scores. It can work after the live server session expires. The tests also alter forecasts, hashes, outcomes, or model bytes to check that mismatches are detected.

This is consistency verification, not trusted authorship. A hash is not a digital signature, an independent timestamp, or a clinical audit certification. Replacing every local artifact is outside its authenticity guarantee. Server sessions are memory-only and have bounded capacity and lifetime. The receipt is useful because a reviewer can take a concrete experiment away and reproduce it, rather than relying solely on a screenshot or a verbal claim.

## Page 6 — A complete local prototype, with evidence attached.

AURA Twin combines the two required streams in a working local application. The historical profile and changing wearable state produce four numerical forecasts and a precisely defined two-hour event probability. The clinician interface makes context, replay, uncertainty, model evidence, and local review accessible. Challenge Lab lets a reviewer freeze an estimate, inspect the recorded outcome, compare persistence, and verify a downloaded experiment offline.

The current robustness upgrade follows a visible chain of evidence. We observed a routine-shift failure, changed the feature and training strategy, separated development roles, and evaluated the frozen model on new patient identities. The result is a measured synthetic improvement with stated limits, rather than a claim that irregular human behavior has become predictable.

The local package includes source, model and data artifacts, architecture and presentation PDFs, technical documentation, tests, and this narrated demonstration. Before submission, the team must publish the repository as public, upload the actual video, add accessible links to the README, and verify them while signed out. The team leader's contact details belong in the submission platform. Thank you for reviewing Black Squad's AURA Twin. The repository and live challenge are designed to let you inspect both the forecast and the evidence behind it.

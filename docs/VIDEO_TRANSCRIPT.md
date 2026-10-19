# Current walkthrough transcript

Model: `aura-synthetic-3.0.0`.

Current recording duration: 26:24.1 (1584.109961 seconds). Chapter starts below match the current narrated slides. Narration uses Microsoft Zira, a locally synthesized voice.

## 1. A forecast measured by its missed and false flags. — 00:00.0

Welcome to AURA Twin, a digital twin proof of concept by Black Squad from Amrita Vishwa Vidyapeetham, Chennai. Our team members are Banu Sreya V., the team leader, and Duvvuru Deepak Reddy. This walkthrough covers the current model, the working clinician dashboard, and the evidence behind an explicit goal: reduce both missed positive windows and false review flags for irregular routines.

The central task is specific. We combine a synthetic historical health record with a changing wearable stream to forecast glucose at four future horizons and estimate high glucose exactly two hours ahead. The system connects generation, model selection, portable inference, clinical-style review, and a reproducible challenge protocol.

Earlier iterations taught us two lessons. A regular schedule can make a model look stronger than it is, and a lower average glucose error does not necessarily resolve the alert tradeoff. This edition therefore uses a selection objective aligned with the requested decision, more past-derived features, and a new final cohort. The evaluation compares the frozen previous model with the current model on identical new windows. The primary error counts improve modestly, but the reduction in misses is uncertain and misses rise slightly for the withheld combination. We will show that mixed outcome and its limits. All patients and measurements are generated. None of these results establishes clinical efficacy, diagnosis, or treatment safety.

## 2. Give changing signals their historical context. — 01:13.2

Consider two kinds of information that describe a patient. A historical record can include age, prior diagnoses, laboratory measurements, and the duration of a condition. These values help establish context, but a record alone does not show a change that began twenty minutes ago. A wearable stream offers a different view: recent glucose, heart rate, sleep, and activity can describe what is happening now, but the stream alone does not carry the full historical profile.

AURA Twin brings these perspectives together for a specific review task. The intended user is a clinician exploring a synthetic patient's trajectory, inspecting the forecast, and understanding the model's inputs. The workflow begins with patient selection, moves through context and temporal evidence, and ends with a local review or an exported summary.

We have not measured whether this workflow saves clinical time or improves outcomes. Those are future evaluation questions. The current contribution is an implemented proof of concept that makes the integration tangible. A reviewer can see which patient is selected, what information is available at a timestamp, what the model predicts, and how the result changes as the simulated stream advances.

## 3. Predict a defined event, at a defined time. — 02:14.5

A prediction task needs a precise label. Our binary event is a glucose reading greater than or equal to one hundred and eighty milligrams per deciliter at exactly one hundred and twenty minutes after the prediction time. That final phrase matters. We are not labeling any excursion during the next two hours. A short high reading after forty minutes that resolves before the two-hour point would not be a positive example for this label.

We also predict numerical glucose at thirty, sixty, ninety, and one hundred and twenty minutes. These forecasts and the binary event probability are related outputs, but they are not interchangeable. The probability describes the chance of the defined event under the fitted model; the numerical forecast describes a future glucose value.

The National Institute of Diabetes and Digestive and Kidney Diseases describes seventy to one hundred and eighty as a common continuous-glucose-monitoring range context. Our inclusive one hundred and eighty boundary is an explicit engineering convention. It is not an individualized clinical target. This definition is consistent across the generator, training labels, exported model, documentation, and dashboard.

## 4. Synthetic data with deliberately varied routines. — 03:13.5

Every record in this demonstration comes from our own seeded simulator. We do not use real patient records, anonymized hospital records, live wearable accounts, Synthea exports, or the MIMIC database. Names, diagnoses, histories, and measurements are fictional. Synthetic generation makes the experiment reproducible without requiring identifiable health information, but it does not make the physiological assumptions realistic by default.

Development includes six declared routine families: regular timing, two-hour and four-hour meal delays, substantial meal-time jitter, day-varying timing with skipped meals, and variable daily sleep and activity. The primary final comparison uses new identities in those six families. A separate test combines a three-hour shift, one-hour jitter, day-to-day variation, skipped meals and variable sleep or activity. This exact combination was excluded from development. Its ingredients are familiar factors, not wholly new physiology.

Historical inputs include age, body mass index, glycated hemoglobin, LDL cholesterol, and diabetes duration. Wearable observations include glucose, heart rate, heart-rate variability, steps, and asleep-or-awake flags at five-minute intervals. Diagnosis text and arbitrary genetic markers are display context only. The simulator is unchanged for the model comparison. Its future meal schedule and latent states never become predictor inputs. Future glucose is an evaluation target, not an observation available at the cutoff.

## 5. Only the available past enters the prediction. — 04:33.1

A prediction is meaningful only if its information boundary is clear. At a selected timestamp, the model receives the historical patient profile and wearable observations up to that timestamp. It does not read the next meal, the next activity period, the future glucose trajectory, or a hidden simulator state. This matters because knowing a future meal would make the forecasting task artificially easy.

The current feature pipeline uses 108 past-derived inputs. It includes current and lagged glucose, recent slopes and variability, sensor summaries, historical context, and observations from matching times on the previous day. A previous-day reading aligned with a future horizon is still an observation from the past: for a two-hour forecast, that corresponding reading is twenty-two hours before the current cutoff. It can describe recurrence, but it does not reveal today's future.

That distinction also exposes a limitation. Yesterday's pattern may be a poor guide after a major routine change. Past-only features prevent information leakage; they do not make an unpredictable future predictable. In the app, advancing replay moves the cutoff, rebuilds the available state, and recomputes the forecast. Tests mutate future observations and verify that the frozen prediction does not change.

## 6. Two streams. One inspectable inference path. — 05:40.1

The system has an offline development path and an interactive application path. Offline, Python generates historical records and wearable sequences. Feature construction converts available history into a fixed numerical representation. Separate patient partitions support fitting, candidate selection, calibration and final reporting.

The selected predictive pipeline is histogram gradient boosting with separate probability calibration. Learned parameters are exported to a readable JSON artifact. A Node.js service evaluates that artifact in JavaScript. The browser requests predictions and renders patient context, forecast horizons, probability, quality and evidence. Local use requires no external model account or health-provider connection. The public hosted demo uses the same inference code and accepts only bundled synthetic patient identifiers.

This separation makes reproducibility practical. A reviewer can inspect the generator, features, model and measured results. Numerical fixtures compare Python and JavaScript outputs. Challenge Lab physically truncates history before inference, preserves the returned prediction, and reveals recorded future comparisons afterward. Local sessions use bounded memory. Hosted sessions carry an authenticated encrypted snapshot so a later request can reach a different function instance without recomputing the forecast. The hosting key protects that transport; it is not a clinical certification. Neither deployment provides governed clinical records, real device connections or patient identity management.

## 7. Freeze the policy before generating fresh final patients. — 07:01.6

We changed the final cohort because the earlier results had already informed development. Reusing those inspected patients as an untouched test would overstate independence. The current final cohort therefore uses one hundred and twenty new identities, with generator indices two thousand through two thousand one hundred and nineteen. The frozen previous model is evaluated on exactly these same new observations.

Development has separate roles. Seven hundred and sixty-eight identities support fitting. Eighty separate identities support candidate selection. Another ninety-six support calibration and the final review policy. All routine variants and repeated windows for an identity stay in that person's partition. A model cannot see one person's regular routine during fitting and then count that same person's delayed routine as a new final patient.

The model, calibration and policy are frozen before final generation and scoring. The primary six-family comparison has one hundred thousand eight hundred windows. The withheld combination is reported separately with sixteen thousand eight hundred windows. Both use the same one hundred and twenty final identities, so they are not independent patient cohorts. Paired uncertainty resamples identities while preserving their repeated windows and variants. The recorded hash and code order make the experiment locally auditable. They are not an independent registration or a trusted external timestamp.

## 8. Select for the actual missed-versus-false tradeoff. — 08:13.4

This edition changes the objective from selecting a classifier mainly by average probability error to selecting for the actual review tradeoff. The candidate experiment evaluates richer histogram gradient boosting models using only the available past. It compares false-positive and false-negative counts against the frozen previous model, including the pooled cohort, irregular routines, and the variable-routine family.

The chosen rule is a single global probability threshold, not a special threshold that knows the patient's future routine. Candidate choice belongs to the selection identities. Calibration then fixes the probability mapping and operating policy before final reporting. Exact settings and candidate scores are recorded in the artifact files. A disappointing final result is not followed by another tuning round on the same final patients.

The feature set contains 108 strictly past-derived inputs. More detailed histories can help distinguish rising, stable and falling trajectories, but they cannot expose a meal that has not happened or been logged. A threshold change alone moves along an existing precision–recall tradeoff. It cannot establish that a model learned a better ranking. That is why the evidence reports ranking and probability metrics as well as paired operating-policy counts, and why the previous model is evaluated on the same fresh final windows.

## 9. Measure error and the review-policy tradeoff. — 09:21.6

The current model's two-hour mean absolute error on the primary fresh final mixture is 10.85 milligrams per deciliter. Its event area under the receiver operating characteristic curve is 0.934. Numerical error measures forecast distance from the observed glucose value. Ranking scores evaluate whether higher-risk windows tend to receive higher probabilities. Neither score alone tells us how many review flags are incorrect.

At the frozen probability threshold of 0.1550, the final policy recall is 74.47 percent and precision is 37.34 percent. The measured confusion counts are 1,669 missed positive windows and 8,170 false-positive windows. The previous frozen policy, evaluated on the same cases, has 1,742 missed positive windows and 8,730 false-positive windows. The paired evaluation, rather than a comparison with an older cohort, determines what we can claim. The patient-bootstrap interval for the missed-window difference includes zero, so this result does not establish a reliable reduction in misses.

Recall is the fraction of positive windows that receive a flag. Precision is the fraction of flagged windows that are positive. The complete evidence also includes prevalence, average precision, Brier score, paired patient-level uncertainty and calibrated-policy results. Repeated windows are correlated. These counts are not deduplicated clinical episodes or independent notifications. The working dashboard exposes errors and does not turn a strong summary statistic into a promise of clinical safety.

## 10. Compare fixed policies on identical new windows. — 10:47.5

A fair comparison gives the previous model and the new model the same patient history and the same future labels. The table separates all six familiar routine families. It also preserves persistence, which simply copies the current glucose value into the future. Persistence can beat a complex model on individual windows; a fair demonstration must allow that result to remain visible.

The current fused model's two-hour error is 10.85. Sensor-only error is 10.92, and persistence error is 20.08. The EHR ablation is included because two-stream fusion is a requirement, not because a large fusion benefit should be assumed. Its measured incremental effect is 0.075 milligrams per deciliter. The complete report keeps the sensor-only and static-only comparisons rather than attributing all improvement to historical records.

The withheld combination is reported separately. On this separate case, current model error is 12.07, recall is 60.99 percent, and precision is 24.11 percent. Missed positive windows change from 324 to 330; false-positive windows change from 1,657 to 1,624. Missed positives increase slightly in this withheld case, despite fewer false-positive windows. The result is mixed. Its exact configuration was absent from development, but the individual perturbation types were represented. This is a useful distribution-shift test, not validation of arbitrary unfamiliar human behavior. Per-routine recall, precision, error, band coverage and width show whether an aggregate gain hides a weak family. Patient-paired intervals acknowledge repeated observations. Clinical performance cannot be inferred from a designed simulator, even when the new policy performs better than the old one on fresh synthetic identities.

## 11. Show uncertainty without promising coverage. — 12:25.3

A point forecast compresses many possible futures into one value. We therefore show a descriptive residual band at each horizon. Its width is estimated from absolute errors on the separate calibration patients, after the predictive model is selected. The nominal target is ninety percent marginal coverage; the final cohort is then used to measure how often observed glucose actually falls inside the band.

At two hours, measured final coverage is 90.60 percent, and the mean width is 61.76 milligrams per deciliter. The routine-specific coverage table matters because an overall percentage can hide undercoverage for one family. These intervals are not a guarantee for a patient, a subgroup, or a future population. They are not confidence intervals for the patient's true physiological state, and a wider band should not be interpreted as a recommendation.

The error band, event probability, and data-quality state are separate signals. A clean sensor history does not ensure a narrow or correct forecast. A plausible sensor bias may pass freshness checks. A severe gap can make the system abstain entirely. During the demonstration, we show the actual band and actual quality state rather than suppressing an inconvenient range. Uncertainty is useful only when its assumptions and observed performance remain visible.

## 12. An overview designed for a clinical review. — 13:32.5

The clinician overview is designed around a clear question: what should a reviewer inspect about this synthetic patient now? The patient panel provides search and selection. The main workspace places historical glucose beside the forecast, while the surrounding cards summarize current state and risk. Context and model evidence are kept close enough that a reviewer can investigate the result without treating a single large number as the whole story.

In the application, select a patient and inspect the displayed units, replay timestamp, and synthetic-data label. The current glucose value is different from the two-hour forecast. A probability is different from a glucose measurement, and the interface labels these quantities separately. The forecast includes a band to communicate model error rather than presenting the line as exact.

The application also offers a patient-record view and a model-evidence view. These make the historical inputs and evaluation results accessible during the same review. This narrated presentation documents the implemented interface; the runnable application in the repository allows the evaluator to operate it directly. We have not completed a clinician usability study, so design intent should not be confused with measured usability or reduced workload.

## 13. Replay makes the information boundary tangible. — 14:34.9

The replay controls let a reviewer pause the simulated stream and choose a past timestamp. The chart separates recorded history from the projected trajectory at thirty, sixty, ninety, and one hundred and twenty minutes. Units and timestamp labels remain visible, so a projected value is not mistaken for a measurement. Advancing the cursor updates the available history and produces a new estimate.

This is retrospective replay of an already generated sequence. The full dataset exists in the repository, but the inference function receives only the allowed prefix. The training and test protocol uses future readings as targets; the dashboard's forecast path does not. The Challenge Lab uses the same principle with an explicit freeze action and a separate reveal action.

A useful demonstration is to stop before a rise, inspect the numerical forecast and band, then advance through the recorded future. Do not select only windows where the prediction looks good. A missed rise, an inaccurate decline, or a band that excludes the outcome reveals a real model limitation. Replay is a way to inspect those errors and the response to new information. It is not a prospective clinical evaluation, even when the animation resembles a live stream.

## 14. Inspect context without turning it into a cause. — 15:38.0

The patient record view exposes the historical and sensor inputs behind the computational state. Age, body mass index, glycated hemoglobin, LDL, and diabetes duration describe the synthetic EHR. The recent glucose trajectory, variability, heart rate, heart-rate variability, steps, and sleep describe changing observations. Keeping these inputs visible helps a reviewer understand what the model actually receives.

The interface's explanation must match the model being served. Grouped sensitivity replaces one feature group with its training-median reference and reports the change in calibrated probability in percentage points. These changes are nonadditive, are not SHAP values, and may involve unrealistic reference combinations. Explanations describe the fitted mathematical model and the chosen reference. They do not show that changing a particular feature would cause the patient to improve. Correlated inputs, interaction terms, and simplified simulator relationships can all complicate interpretation.

The fictional genetic marker is displayed as background context and excluded from prediction. Assigning it a biological effect without evidence would create an unsupported claim. Medication text is also descriptive; the model does not simulate dose-response effects. This distinction between available context and active model inputs is part of the submission. A polished record screen is useful only if the reviewer can tell which facts contribute to the prediction, which are merely displayed, and which clinically important factors are not modeled.

## 15. Explore an assumption. Do not infer a treatment. — 16:57.1

The hypothetical sensitivity sandbox lets a user change assumptions about meal carbohydrate and activity. Applying a scenario changes the displayed numerical forecast through a simplified arithmetic adjustment. Reset returns to the baseline. This interaction can help demonstrate how a dashboard separates a baseline prediction from an exploratory scenario.

The trained event probability stays at the baseline model output. The sandbox is not a learned treatment-effect model. It has not been trained on randomized interventions, and it has not been evaluated to predict how a specific person's glucose would respond to eating differently, exercising, or taking medication. It should never be presented as evidence that a proposed intervention will prevent an event.

This distinction is deliberate. An attractive what-if interface can easily imply more knowledge than the system contains. We label the operation as hypothetical sensitivity and keep it separate from the measured prediction evidence. There is no medication dosing, treatment recommendation, or clinical action plan. For a genuine intervention simulator, we would need a defensible causal model, appropriate data and assumptions, independent validation, and a much more demanding safety and governance process. Those capabilities are future research, not features of this prototype.

## 16. Freeze the prediction. Then reveal the outcome. — 18:04.6

Challenge Lab gives the jury a repeatable way to question the model. Choose a synthetic patient, a cutoff, and one of the supported sensor conditions. Freeze prediction copies the patient state, physically truncates the wearable history at the cutoff, applies the selected perturbation, and runs inference. The returned frozen object contains the forecast, event probability, quality state, and provenance information. It does not include future outcomes.

After inference completes, the server snapshots the original recorded future at the four horizons. Reveal recorded future compares those observations with the already frozen output. It does not recompute the model after seeing the answer. The comparison includes numerical error, the persistence baseline, interval hits, and the exact two-hour threshold outcome.

This protocol is inspectable, but it is not a secure blinded clinical study. The synthetic dataset is public, and the team can read it. Its value is enforcing the computation's information boundary and making a selected prediction falsifiable. The selected-window table is not an estimate of cohort-wide performance. Missing future observations and abstained predictions do not receive invented scores. If a forecast loses to persistence, the result stays visible.

## 17. Four sensor cases expose different failure modes. — 19:10.9

The four Challenge Lab cases answer different questions. Clean replay establishes the baseline at the chosen cutoff. The ten-minute CGM gap removes the final two glucose samples. Within the permitted freshness limit, the pipeline can carry the last available value forward and mark the input as degraded. This demonstrates a known handling policy, not proof that the imputation is accurate.

The thirty-minute dropout removes the final six glucose samples. The last available glucose is too old for the quality gate, so the model withholds its forecast and probability. A reviewer sees abstention rather than a fabricated confident answer. Acknowledging that state does not make the missing data safe or restore a prediction.

The final case introduces a plausible positive glucose bias over the recent input window. These values can remain fresh and numerically plausible, so basic quality checks may pass even though the forecast is wrong. This is a deliberate blind spot in the demonstration. The reference future remains unchanged, and persistence receives the same perturbed current observation as the model. Together, these cases separate missingness handling from bias detection and make clear that quality status is not a certificate of sensor truth.

## 18. Make the experiment reproducible offline. — 20:13.9

Download receipt exports the frozen experiment and any revealed outcome comparison as a JSON document. It contains a SHA-two-fifty-six fingerprint of the exact model file and a fingerprint of the canonical perturbed input prefix. The model hash covers raw file bytes. The input hash uses a defined sorted-key JSON representation while preserving array order.

The offline verifier reconstructs that input from packaged data, checks hashes, reruns the prediction, and compares the revealed observations and scores. It works after the interactive session expires. Tests alter forecasts, hashes, outcomes or model bytes to verify that mismatches are detected. The exported receipt excludes the hosted transport token.

There are two distinct integrity mechanisms. The hosted application encrypts and authenticates a temporary frozen snapshot with a deployment secret, allowing reveal across serverless instances without rerunning inference. The downloadable receipt is a reproducibility record that anyone with the same artifacts can check. Its hashes are not digital signatures, independent timestamps or proof of authorship. Replacing every artifact is outside that authenticity guarantee. Local sessions use bounded memory; hosted snapshots expire after one hour and are invalidated when the key or model changes. Neither mechanism makes the public dataset a secure blinded study.

## 19. The evidence travels with the implementation. — 21:25.5

The submission contains the generator, training pipeline, model export, evaluation artifacts, and application inference code. The current model version is aura-synthetic-3.0.0. Its protocol separates fitting, selection, calibration, and final reporting. The fresh final patient IDs and routine definitions are recorded with the metrics, so a reviewer can verify what was evaluated.

For the working dashboard, only Node.js is required. The application uses native HTTP handling, vanilla JavaScript, and SVG charts, with no runtime package installation or external model service. Python and the documented numerical dependencies are needed only to reproduce training or document generation. Exact commands and environment versions are in the README and artifacts.

Verification covers more than a successful page load. Numerical fixtures check Python and JavaScript parity. Prefix tests protect against future leakage. Challenge tests inspect freeze, reveal, degraded input, abstention, and receipt consistency. These tests protect specified behavior; they do not establish clinical performance or complete security. Browser review checks that the patient selection, replay, charts, evidence, exports, and mobile interactions work in the actual interface. The final verification record identifies what was checked for this version and separates older evidence from current results.

## 20. A better benchmark is still a bounded claim. — 22:42.0

The model is designed to address a measured decision tradeoff, but it does not solve general glucose prediction. Unexpected future meals can remain invisible at the cutoff. Better history features cannot guarantee advance knowledge of behavior. A clock-free model can still use recurrent information from sleep, activity, heart rate and previous-day glucose.

The generator is a designed approximation. In particular, simulated heart rate includes a contemporaneous meal-response component. That is available-time information rather than future leakage, but it can make multimodal prediction easier under this simulator than with a real consumer device. EHR relationships are also authored assumptions. Medication effects, complex comorbidity, illness, pregnancy and real sensor physics are not validated.

The results retain missed positive windows, false-positive windows and uncertainty. A lower count in a paired benchmark would not eliminate review burden or prove that interventions improve outcomes. Basic freshness gates can miss plausible sensor bias. Local notes and acknowledgements are demonstration state, not a governed clinical record. Our claim is bounded by the recorded evaluation: a working fusion pipeline, a fixed operating policy, fresh synthetic comparisons and a reproducible way to inspect errors. Clinical benefit, workflow efficiency, regulatory compliance and autonomous-care readiness would each require separate evidence.

## 21. Use the remaining failures to guide validation. — 23:54.8

The next validation step is broader evidence, not another claim based on the same final patients. Independent synthetic generators can challenge different assumptions about physiology and behavior. Longer histories, unfamiliar missingness mechanisms, sensor drift and genuinely new routine families would test boundaries beyond the current familiar families and withheld combination. These studies should define their protocol before looking at final outcomes.

Appropriately permitted real-world datasets would then be needed to examine external validity. That work includes calibration, device differences, subgroups and uncertainty. A prospective silent-mode study could measure performance and potential review burden without allowing the model to direct care. Episode-level alert analysis is essential because correlated positive windows do not equal independent clinical events. A notification policy with persistence rules or a cooldown could reduce duplicate notifications, but it must be evaluated separately and must not be portrayed as a better classifier.

Clinical participation is also needed to assess workflow design. Review ownership, escalation rules, access control, consent, audit logging and retention cannot be inferred from an attractive dashboard. The hosted demo's synthetic-only boundary and encrypted temporary snapshots are practical engineering controls. They do not replace a production clinical governance system. The current contribution is a transparent baseline from which those more demanding studies can be designed.

## 22. A working application, with its evidence attached. — 25:10.5

AURA Twin combines the two required streams in a working application. Historical context and changing wearable state produce four numerical forecasts and a precisely defined two-hour event probability. The clinician interface exposes patient context, replay, uncertainty, model evidence and local review. Challenge Lab lets the jury freeze an estimate, reveal the recorded outcome, compare persistence and verify the experiment offline.

This edition uses a decision-aligned development protocol. The prior model remains frozen for comparison. Candidate choice, calibration and policy selection are completed before new final patient identities are generated. The familiar routine mixture and the held-out combination are reported separately. What matters is the observed paired result, including failures, rather than a more impressive model name or a threshold chosen after seeing the answers.

The package contains source, generated data, exported model, architecture and presentation PDFs, documentation, tests and this narrated demonstration. The public repository and hosted application are linked from the README once verified. The team must still ensure the submission platform has the correct leader details and accessible required links. Those private contact details do not belong in this public repository. Thank you for reviewing Black Squad's AURA Twin. We invite you to inspect both the prediction and the evidence behind it.

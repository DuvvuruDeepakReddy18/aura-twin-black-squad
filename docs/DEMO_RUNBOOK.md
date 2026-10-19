# AURA Twin — 23-minute prototype demonstration

**Team:** Black Squad  
**College:** Amrita Vishwa Vidyapeetham, Chennai  
**Presenters:** Banu Sreya V. (team leader), Duvvuru Deepak Reddy  
**Public video link:** **PENDING — upload the included narrated walkthrough (or a team-recorded replacement) and add its accessible URL to the repository README.**  
**Narrated walkthrough:** `AURA_Twin_Walkthrough.mp4` is included in the docs folder; its narration is approximately **21 minutes 53 seconds**, using a locally synthesized Microsoft Zira voice. Verify the final MP4's playback and duration before uploading. See `VIDEO_TRANSCRIPT.md` for its timed transcript.  
**Human-led option:** use the plan below to record your own voice and live interactions; this is optional if the supplied presentation recording meets the organizer's final rules.

This runbook is a speaking and demonstration guide, not itself a video. For a human-led replacement, aim for **23–25 minutes of meaningful content**. The supplied written brief says a minimum of 20 minutes, while the screenshot says 15–20 minutes; this plan follows the stricter written requirement. Verify the final rules on the organizer's portal before submitting. The supplied narrated presentation uses actual prototype screenshots and conceptual diagrams; it is not a live screen recording of every interaction.

## Presenter fact sheet

Use these values only for the included `aura-synthetic-1.0.0` artifacts; regenerate this cue sheet if the model changes.

- **Test cohort:** 48 held-out synthetic patients, 6,720 correlated windows; 540 positive windows (8.04%).
- **+120-minute MAE:** 10.95 mg/dL; patient-bootstrap 95% interval 10.29–11.59 mg/dL.
- **Classifier:** AUROC 0.969; average precision 0.723; Brier 0.0372.
- **Dashboard alert threshold:** 0.20, selected on validation patients to reach at least 80% recall. Test recall 83.89%, precision 53.23%; 87 false-negative and 398 false-positive windows. These are not deduplicated clinical episodes.
- **Fixed 0.50 comparison:** recall 54.81%, precision 72.20%. This is the default comparison in `metrics.json`, not the dashboard's selected alert threshold; its policy is in `model.json`.
- **Ablation MAE:** fused 10.95; sensor-only 12.17; static-only 19.31; persistence 22.10 mg/dL. Fusion improves MAE by 10.1% versus sensors under this simulator.
- **What-if:** an arithmetic forecast sensitivity; the trained risk probability stays at baseline.
- **Evidence boundary:** generated data only; no independent clinical validation, causal treatment estimate, or medical recommendation.

## Before recording

1. Run the application following the root README. Open the local clinician dashboard in a modern browser. Keep the terminal, repository README, `data/metrics.json`, `data/model.json`, `ml/train.py`, and `docs/AURA_Twin_Presentation.pdf` available.
2. Run the documented verification commands. Do not state that a check passed if it has not been run on the submitted version.
3. Test screen capture and microphone for 30 seconds. Record at 1920 × 1080 if available; use 100% browser zoom and show the pointer. Disable unrelated notifications. No personal patient data should appear anywhere.
4. Select a synthetic patient with an interesting changing risk trajectory. Rehearse moving the replay slider, pausing the stream, reading a hover point, viewing the record, applying and resetting a hypothetical scenario, and opening Model evidence.
5. Clear old local notes and acknowledgements if you want a clean demo. These are local prototype interactions; do not present them as a shared clinical record.
6. Open the PDFs to ensure every page renders. Read the final metric values from the checked-in result file; do not substitute earlier screenshots or rounded recollections.

## Timed script and actions

The suggested words below are prompts. Explain the artifact on screen in your own words. Leave time to show the result of each action. The segment durations total **23 minutes**; expanding the technical sections is better than adding dead time.

### 00:00–01:15 · Team and the problem · 1 min 15 sec

**Screen:** presentation cover, then problem slide.

**Suggested narration:** “We are Black Squad from Amrita Vishwa Vidyapeetham, Chennai. I am Banu Sreya V., the team leader, presenting with Duvvuru Deepak Reddy. Our prototype is AURA Twin. We explore a focused question: can a virtual patient combine a historical health profile and a changing wearable stream to estimate elevated glucose two hours ahead? This is a synthetic proof of concept for clinician review. It does not diagnose, prescribe, or establish clinical accuracy.”

Explain the fragmentation problem: a medical history provides context, while a sensor curve describes what is changing now. One without the other can miss important context. Frame the desired workflow as prioritizing review and inspecting evidence.

### 01:15–02:45 · Define success precisely · 1 min 30 sec

**Screen:** event definition slide.

**Suggested narration:** “Our risk label is glucose greater than or equal to 180 milligrams per deciliter at exactly 120 minutes after the prediction time. We also forecast numerical glucose at 30, 60, 90, and 120 minutes. An event occurring briefly at minute 40 and resolving by minute 120 is not a positive label for this model. This precise definition keeps our claims aligned with our code.”

Explain that NIDDK describes a common 70–180 mg/dL time-in-range context. The inclusive 180 boundary here is an engineering convention, not an individualized clinical target. Distinguish probability from the future glucose estimate and from uncertainty around the estimate.

### 02:45–04:45 · The two streams and the sandbox · 2 min

**Screen:** data slide, then a synthetic patient record and sensor panel.

Show the historical inputs: age, BMI, HbA1c, LDL, and diabetes duration. Explain that demographic and historical context stays fixed within a replay. Show dynamic CGM, heart rate, heart rate variability, steps, and sleep. Explain five-minute timestamps and time alignment.

**Suggested narration:** “All patient records and sensor readings in this repository are generated by our own seeded simulator. We did not use Synthea, MIMIC-IV, hospital records, or real device accounts for these results. Synthea is a possible future import path. The simulation includes simplified routines, noise, and person-to-person variation. Because the generator embeds dependencies, strong performance may partly reflect how we designed the simulator.”

Do not call synthetic data “anonymized clinical data.” Synthetic means it was generated; anonymization describes a different process.

### 04:45–06:45 · Architecture and data fusion · 2 min

**Screen:** `docs/AURA_Twin_Architecture.pdf`, page 1.

Trace the flow: synthetic EHR plus wearable time series → causal feature extraction → exported model → local inference → clinician dashboard. Explain that future values become training labels only. They must not be included in the prediction inputs.

**Suggested narration:** “The digital twin is a patient-specific computational state that we update as the simulated stream advances. We pair stable clinical context with the time-local sensor state, then use both to compute a new forecast and risk score. Our implementation is deliberately inspectable: model coefficients, preprocessing statistics, and evaluation artifacts are readable files.”

Name the actual technology from the README: Python/scikit-learn training, exported JSON model, Node.js local server, vanilla JavaScript dashboard. Do not claim FHIR integration, cloud deployment, live device connectivity, authentication, or a production EHR connection.

### 06:45–08:15 · Start the clinician workflow · 1 min 30 sec

**Screen:** dashboard Overview.

Search for a synthetic patient and select them. Point out patient identity, simulated mode, signal summary, and the historical curve. Explain the intended clinician sequence: select → inspect context → inspect forecast → understand evidence → document a review.

Show responsive navigation if useful. Keep the cursor on the control you are describing. Mention that color is reinforced by labels, and that visible numbers and units are essential for avoiding ambiguity.

### 08:15–10:15 · Replay and forecasting · 2 min

**Screen:** historical curve and replay controls.

Pause replay. Hover a history point; read the timestamp and glucose. Move the replay slider to an earlier time and show the observed history, projected points, and uncertainty band. Advance one or more ticks. State that this is playback of synthetic data, not a connected real-time medical device.

**Suggested narration:** “At each replay position, the model has access only to the data at or before this point. The dashed future portion is a forecast. The band is based on held-out validation residuals. It is descriptive model uncertainty under our simulator; it is not a guarantee that a real patient's glucose lies inside it.”

Explain the difference between the +120-minute value and the risk that the +120-minute reading meets the binary threshold. Describe one changing example visible on screen without inventing exact values in advance.

### 10:15–11:45 · Context and interpretable evidence · 1 min 30 sec

**Screen:** Patient record, then risk drivers.

Show the EHR fields and the current wearable features together. Explain how age/BMI/HbA1c/LDL/diabetes duration differ from current glucose, slope, variability, HRV, sleep, and activity.

**Suggested narration:** “The driver display explains the fitted model's scoring behavior. A positive contribution increases the model's log-odds relative to its baseline; a negative contribution decreases them. This is not evidence that a feature causes the event, and a contribution is not a percentage-point change in risk.”

If the final UI uses a different explanation label, describe exactly what it displays. Do not claim SHAP, attention maps, or a validated causal explanation if these are not implemented.

### 11:45–13:15 · Hypothetical sensitivity sandbox · 1 min 30 sec

**Screen:** scenario controls.

Change one control, apply it, read the scenario label and change in forecast, then reset. Repeat with the other control if time permits.

**Suggested narration:** “This is an illustrative sensitivity sandbox. It changes assumptions in the displayed scenario; it has not learned the causal effect of eating differently, exercising, or taking medication. These outputs must not be interpreted as a treatment recommendation or as a prediction of intervention benefit.”

Show that reset returns to the baseline. Explicitly point out that the trained risk probability stays unchanged while the hypothetical forecast changes. This separation is intentional: the scenario controls do not define a causal probability model.

### 13:15–14:30 · Review actions and export · 1 min 15 sec

**Screen:** alert acknowledgement, local care note, export.

Acknowledge an alert if present. Add a short synthetic note such as “Demo review: inspect signal quality and historical context.” Download the clinician summary and open it. Explain which fields it contains and whether notes survive refresh on this browser.

**Suggested narration:** “These interactions demonstrate a review workflow. Acknowledgement means a demo user has seen the alert; it does not verify that the patient is safe. The prototype's notes and acknowledgement state are local. We have not implemented clinical authentication, audit governance, or a multi-user record system.”

### 14:30–16:30 · Evaluation that can be inspected · 2 min

**Screen:** Model evidence, then `data/metrics.json`.

Show the training/validation/test cohort counts and the final measured metrics. Explain that patients are split before modeling, so records from a test patient do not enter training. Explain why a random row split could otherwise overstate generalization.

Report the exact +120-minute MAE, AUROC, average precision, and Brier score if present in the final result. State the event prevalence. If showing precision/recall, also show the operating threshold and how it was selected. Compare performance with persistence, sensor-only, and static-only baselines. Say “synthetic held-out patients,” not “patients in a clinical study.”

Spend enough time on one metric: “MAE is the average absolute difference between a predicted value and the held-out future reading, in mg/dL. It does not tell us whether every dangerous event is detected.”

### 16:30–18:00 · Reproducibility walkthrough · 1 min 30 sec

**Screen:** source files and documented commands.

Show the generator seed, train-only preprocessing, patient-disjoint split, and exported artifact paths. Point to the requirements and test command. Run the lightweight verification during the recording if practical; rerun training only if its duration fits the presentation.

**Suggested narration:** “The repository contains the code that produced these metrics. A reviewer can regenerate data and models, run checks, and launch the same application. The UI is backed by the exported model artifacts rather than fixed numbers drawn into a mockup.”

If regeneration has numerical differences across library versions, explain the pinned dependencies and tolerances documented in the repository. Do not imply bitwise reproducibility on every platform unless verified.

### 18:00–20:00 · Failure modes and limits · 2 min

**Screen:** limitations slide; architecture page 2 if useful.

Discuss simulator bias, unseen clinical populations, sensor drift/missingness, unusual meals and routines, medication effects, correlated repeated windows, calibration drift, and subgroup reliability. Show the actual missing-data behavior in code or UI if implemented. Do not claim a safeguard that is only planned.

**Suggested narration:** “The main result is a working fusion-and-forecast pipeline with a reviewable clinician interface. We have not demonstrated clinical efficacy. External validation, clinician-led requirements, secure identity and audit logging, device integration, and prospective evaluation are prerequisites for real deployment.”

Explain that synthetic-only development reduces the need to process real sensitive records in this prototype, but it is not proof of DPDP, HIPAA, medical-device, or other regulatory compliance.

### 20:00–21:30 · What we would validate next · 1 min 30 sec

**Screen:** staged validation roadmap.

Describe a sequence: broaden synthetic stress tests → consented/anonymized independent evaluation with required permissions → prospective silent-mode study → clinician workflow/usability study → monitored deployment only after the appropriate approvals. Keep each step marked future work.

Explain the distinction between a good-looking dashboard and demonstrated utility. A future study must measure alert burden, missed events, calibration, subgroup performance, workload, and actual outcomes. No clinical benefit number is claimed today.

### 21:30–23:00 · Submission tour and close · 1 min 30 sec

**Screen:** README with artifact links; PDFs; repository file tree.

Show team and college details, project title, problem/use case, stack/model details, MIT license, architecture PDF, presentation PDF, source code, evaluation artifacts, and this runbook. After upload, show the public GitHub page and the real video link if those steps are complete. If recording before publishing, state those publishing tasks are pending.

**Suggested narration:** “AURA Twin delivers a reproducible synthetic proof of concept: two data streams, a measurable two-hour target, an inspectable predictive model, and a clinician-oriented interaction flow. We have shown the working system and the boundaries of its evidence. Thank you.”

## Recording and link checklist

- [ ] Final recording duration is at least 20 minutes; target 23–25 minutes.
- [ ] The screen and voice are legible; captions reviewed if used.
- [ ] No secrets, private tabs, or unrelated personal information appear.
- [ ] The model/data version shown matches the submitted repository.
- [ ] The actual video is uploaded as an unlisted YouTube video or another permitted accessible format.
- [ ] `README.md` contains the working video URL and duration, replacing the pending marker.
- [ ] The link works in a signed-out/private browser, with no access request.
- [ ] The final public repository includes the PDFs and all source files.

This runbook alone does not establish a playable video, public repository, public accessibility test, or competition submission. Verify the included MP4 and complete the publishing checks.


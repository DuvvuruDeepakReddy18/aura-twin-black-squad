# AURA Twin — a prediction the jury can challenge

**Current model:** `aura-synthetic-2.0.0`. **Positioning:** a working synthetic glucose twin that responds to a measured failure with a reproducible model improvement, then makes the new predictions and remaining limits inspectable.

Lead with: **“We found where the first model broke, improved it on a broader training design, and tested the frozen replacement on new patients. Now you can challenge the prediction yourself.”**

## What is distinct in this submission

| Typical prototype pattern, not a claim about actual competitors | What AURA implements | Limit |
| --- | --- | --- |
| Attractive forecast screen | Runtime EHR/wearable fusion, current model artifacts and replay | Synthetic local prototype |
| One headline metric | Five same-case model comparisons, six routine rows, paired patient intervals | Same generator family; not clinical |
| Failure described as future work | Clock-free, routine-augmented boosting evaluated after model freeze | Routine families occur in training |
| Prepared success screenshot | Jury-selected cutoff, freeze, reveal, persistence and interval comparison | Selected window is not cohort evidence |
| “Safe” quality badge | Degraded gap, abstaining dropout and explicitly undetected bias | Not a validated clinical safety gate |
| Screenshot evidence only | Downloaded receipt and offline recomputation | Hash consistency, not signatures |

The same-case aggregate two-hour MAE improves from 18.30 to 11.62 mg/dL (36.5%). All six MAE rows improve against the frozen earlier model. The EHR increment is modest: 0.107 mg/dL (~0.9%) beyond sensors, so the larger claim belongs to the changed temporal features, augmentation and nonlinear model. Final recall 78.73% and precision 40.50% at 0.16 remain imperfect.

## Two-minute pitch

“AURA Twin combines a patient's historical health context and changing wearable state into an inspectable two-hour glucose forecast. The records and sensors are wholly synthetic. We predict a precise endpoint, not an ambiguous claim that any spike will be detected.

Our first model had a weakness: it learned regular meal timing and degraded when routines changed. We did not stop at documenting that weakness. We removed explicit clock features, added richer past-only history, trained on varied routines, and compared a linear model with boosting on separate selection patients. We calibrated the winner separately, froze it, and only then generated eighty new final patient identities.

On those same fresh cases, mean absolute error fell from 18.30 to 11.62 milligrams per deciliter. All six routine-family errors improved against the frozen old model. Those families were present in training, and future meals are never supplied. This is a measured synthetic improvement, not a claim that unknown human behavior is solved.

Now choose a patient and cutoff. Freeze the prediction, reveal the recorded future, and compare the model with persistence. Remove readings to see degraded quality or abstention. Add a plausible bias to see a blind spot. Download the receipt and verify it offline.

The contribution is a working model, an honest improvement cycle, and evidence a reviewer can inspect. Real-world clinical validation remains the next challenge.”

## Prior work and claim boundaries

[GlyTwin](https://arxiv.org/abs/2504.09846) already explores glucose digital twins and behavioral counterfactual scenarios. We claim no first-in-field invention, no direct accuracy superiority across unlike datasets, and no learned causal treatment effects. The [npj Digital Medicine VVUQ perspective](https://www.nature.com/articles/s41746-025-01447-y) motivates explicit verification/validation/uncertainty concerns; it does not validate this prototype.

Use “fresh-patient synthetic evaluation,” “same-case improvement,” and “offline-verifiable experiment.” Avoid “clinically accurate,” “knows future meals,” “tamper-proof,” “guaranteed 90% coverage,” or “robust to every routine.”

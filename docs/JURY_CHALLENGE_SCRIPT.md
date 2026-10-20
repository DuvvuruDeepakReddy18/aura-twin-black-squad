# Three-minute research Challenge Lab talk track

## 00:00–00:35 — Establish the contract

Open the current research demo. Identify the participant, Composite Research Twin label, model version and cutoff. Say: “The Synthea EHR is a different synthetic person. These wearable observations are real de-identified research data. This replay is not a live device connection.”

Show the current event: rise ≥20 mg/dL at approximately +120 minutes, relative to the latest available current reading. Explain that the training-only support audit selected this research label; it is not necessarily an adverse clinical event.

## 00:35–01:20 — Freeze and reveal

Select a valid cutoff. Open the input details and show the six-hour boundary. Freeze the prediction. Point out the model hash and preserved forecast before revealing the future. Reveal the recorded outcome; compare the model with persistence and show interval hits. Report whichever model wins this window.

## 01:20–02:05 — Stress the observation stream

Choose one supported missing/stale case and one plausible bias case. Explain that source-quality checks can withhold a prediction for insufficient history but may not detect fresh biased data. Reference truth and the clean current rise-label reference remain fixed during the comparison. Perturbed probabilities may use a different current input; this is an audit of sensitivity, not a causal intervention experiment. Bands are not recalibrated for the corruption.

## 02:05–02:40 — Inspect evidence

Open model evidence. Show CGM-only as the selected primary family, all ablations, the three-participant denominator and the low precision. Distinguish a single challenge window from the 1,859-window held-out evaluation and the separate sampled runtime perturbation audit.

## 02:40–03:00 — Export and conclude

Download the research receipt and explain that an offline command recomputes its numerical result:

```bash
node scripts/verify_research_receipt.mjs path/to/receipt.json
```

A checksum is not a signature or independent timestamp. The public dataset is not securely blinded. Finish with: “The product makes the forecast, inputs, outcomes and limitations available for inspection.”

If a selected window lacks eligible future observations or inference abstains, demonstrate that state honestly instead of switching silently to a favorable result.

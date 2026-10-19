# Current demonstration runbook

Use the current 22-slide presentation and `narration.json`, which contains roughly 4,286 words. At a normal speaking pace this supports about 24–27 minutes. Do not speed it below the required 20 minutes. A team-delivered recording can replace the disclosed synthesized narration.

## Preparation

1. Run the current local app and confirm model`aura-synthetic-2.0.0` in evidence.
2. Confirm current MAE 11.62 and fresh final 80 identities. Old 10.95/0.20 policy materials are historical.
3. Keep the current PDF, README, model/data card and a terminal open. Use fictional notes only.
4. Test patient selection, replay, scenario reset, Challenge Lab and receipt download before recording.
5. Record screen and clear audio. Explain that this is synthetic replay, not a real patient/device feed.

## Full speaking sequence

The schedule below is a minimum one-minute allocation per slide. Spend additional time operating the dashboard on slides 12–18; the full narration normally takes longer than 22 minutes.

| Slide | Minimum time block | Topic |
| --- | --- | --- |
| 1 | 00:00–01:00 | A patient’s history. A more adaptable outlook. |
| 2 | 01:00–02:00 | Give changing signals their historical context. |
| 3 | 02:00–03:00 | Predict a defined event, at a defined time. |
| 4 | 03:00–04:00 | Synthetic data with deliberately varied routines. |
| 5 | 04:00–05:00 | Only the available past enters the prediction. |
| 6 | 05:00–06:00 | Two streams. One inspectable inference path. |
| 7 | 06:00–07:00 | Select and calibrate before opening the final cohort. |
| 8 | 07:00–08:00 | A clock-free candidate earns the final evaluation. |
| 9 | 08:00–09:00 | Measure error and the review-policy tradeoff. |
| 10 | 09:00–10:00 | Compare models on the same fresh routine cases. |
| 11 | 10:00–11:00 | Show uncertainty without promising coverage. |
| 12 | 11:00–12:00 | An overview designed for a clinical review. |
| 13 | 12:00–13:00 | Replay makes the information boundary tangible. |
| 14 | 13:00–14:00 | Inspect context without turning it into a cause. |
| 15 | 14:00–15:00 | Explore an assumption. Do not infer a treatment. |
| 16 | 15:00–16:00 | Freeze the prediction. Then reveal the outcome. |
| 17 | 16:00–17:00 | Four sensor cases expose different failure modes. |
| 18 | 17:00–18:00 | Make the experiment reproducible offline. |
| 19 | 18:00–19:00 | The evidence travels with the implementation. |
| 20 | 19:00–20:00 | Improved synthetic robustness still has limits. |
| 21 | 20:00–21:00 | Use the remaining failures to guide validation. |
| 22 | 21:00–22:00 | A complete local prototype, with evidence attached. |

## Live operations to show during the relevant chapters

- Slide 12: search/switch patient; point to synthetic label, routine, current value and two-hour forecast.
- Slide 13: pause and scrub replay; distinguish measured history from projected future and band.
- Slide 14: inspect patient record and grouped risk sensitivity; explain nonadditive/noncausal reference changes.
- Slide 15: apply then reset a hypothetical meal/activity assumption; show trained event probability stays at baseline.
- Slides 16–18: freeze/reveal a clean case, compare persistence, demonstrate short gap, abstaining dropout and plausible bias; export and verify a receipt.
- Slide 19: inspect current metrics/protocol and run tests or show the recorded verification results.

At the end, show actual repository contents and accessible artifact links. Acknowledge that public publication/upload/portal steps remain pending until completed. Do not fabricate a public video URL or imply the recording is a clinical study.

## Content checks before upload

- Exact target is glucose ≥180 at exactly +120 minutes, not any crossing.
- Fresh final identities are held out; all six routine families occur in training.
- EHR's added MAE benefit is modest (~0.107 mg/dL), not the whole model improvement.
- Policy 0.16 final recall 78.73%, precision 40.50%; correlated windows, not clinical episodes.
- Bands have 89.42% marginal coverage and 61.66 mg/dL width; no individual guarantee.
- Future meals are not input. Previous-day signals are past observations.
- Tree sensitivities are nonadditive risk-percentage-point reference changes, not SHAP or treatment effects.
- Show failures honestly, verify the actual exported receipt, and confirm the final MP4 lasts≥20 minutes.

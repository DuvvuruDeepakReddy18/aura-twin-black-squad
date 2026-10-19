# Three-minute live jury challenge — current model

**Model:** `aura-synthetic-2.0.0`. Open `http://localhost:4173`, confirm model evidence shows current 11.62 aggregate MAE, and choose a supported patient/cutoff. Do not use an old screenshot or old receipt as current evidence.

| Time | Action | Talk track |
| --- | --- | --- |
| 0:00–0:20 | Show current model evidence | “We improved same-case MAE from 18.30 to 11.62 after an earlier routine-shift failure. Final patients are new; routine families were in training.” |
| 0:20–0:45 | Challenge lab → Clean replay → Freeze prediction | “The model receives only the available prefix. This result is frozen before outcome comparison.” |
| 0:45–1:10 | Reveal recorded future | “Compare all four horizons with persistence and the interval. This selected window is not a cohort score.” |
| 1:10–1:30 | 10-minute CGM gap → Freeze/reveal | “Short missingness is forward-filled and marked degraded. That does not guarantee accurate imputation.” |
| 1:30–1:50 | 30-minute dropout → Freeze | “The system abstains because glucose is stale. Null risk is not zero risk.” |
| 1:50–2:15 | Undetected sensor bias → Freeze/reveal | “Plausible fresh values can still be biased. The quality gate does not detect every wrong input.” |
| 2:15–2:40 | Download receipt; optionally run verifier | “The receipt can be recomputed offline. Hashes prove local consistency, not trusted authorship.” |
| 2:40–3:00 | Return to routine evidence | “All six MAE rows improve, but variable-routine recall/precision and band coverage remain weaker. No future meal schedule is supplied.” |

If the model loses to persistence or misses a positive window, explain that failure before choosing another example. Do not turn a favorable case into a clinical performance claim. The underlying synthetic dataset is public; freeze/reveal is not secure study blinding.

Offline command: `node scripts/verify_receipt.mjs path/to/receipt.json`.

This short live challenge supplements the full current≥20-minute video. It does not replace the organizer's minimum video duration. Use `DEMO_RUNBOOK.md` for the complete presentation.

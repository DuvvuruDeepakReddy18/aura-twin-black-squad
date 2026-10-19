# Three-minute jury challenge

Use the current model `aura-synthetic-3.0.0`. Let the reviewer choose a synthetic patient and cutoff; do not search for a favorable outcome. The public dataset is not securely blinded.

| Time | Action | Say |
|---|---|---|
| 0:00–0:25 | Show patient, cutoff and synthetic banner | “This joins the fictional EHR with only the wearable history available now.” |
| 0:25–0:50 | Open Challenge lab; choose Clean replay; Freeze prediction | “This prediction is frozen before we reveal its recorded future.” |
| 0:50–1:15 | Reveal recorded future | “Compare four horizon errors, persistence and interval hits. A local loss stays visible.” |
| 1:15–1:40 | Reset; select 10-minute CGM gap; freeze | “Short gaps can be forward-filled and marked degraded; imputation is not proof of accuracy.” |
| 1:40–2:00 | Select 30-minute dropout; freeze | “The glucose is too stale. The system withholds risk and forecast.” |
| 2:00–2:20 | Select Undetected sensor bias; freeze/reveal | “Freshness checks can miss plausible bias. This is a deliberate blind spot.” |
| 2:20–2:45 | Download receipt; show verification command | “The receipt can reproduce this model and input. Hashes do not prove authorship or time.” |
| 2:45–3:00 | Show current evidence table | “The frozen policies are compared on the same fresh windows. Inspect both missed and false-positive counts.” |

Primary summary if asked: The frozen v3 policy at 0.1550 has 74.47% recall and 37.34% precision, with 1,669 false-negative and 8,170 false-positive windows. Frozen v2 on the same cases has 1,742 FN and 8,730 FP. The gains are modest and mixed: the patient-bootstrap 95% interval for the FN difference includes zero, and the withheld combination has **324 → 330 missed positive windows**. This does not establish a reliable reduction in misses or improvement across every routine. The separate withheld factor combination has 12.07 mg/dL MAE, 60.99% recall and 24.11% precision. FN changes 324 → 330; FP changes 1,657 → 1,624.

```sh
node scripts/verify_receipt.mjs path/to/receipt.json
```

Hosted sessions work across instances through a temporary authenticated encrypted snapshot. Local sessions use bounded memory. Neither path reruns the prediction on reveal. If the session expired or model changed, start a new challenge and state that clearly.

"""Audit the frozen model under specified synthetic meal-timing shifts.

No fitting, threshold selection, or recalibration occurs here. Uses the original
48 test identities, including ALL eligible 30-minute-stride windows, not just the
eight curated dashboard examples. Run: python ml/stress_test.py
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from sklearn.metrics import mean_absolute_error, roc_auc_score, brier_score_loss, precision_score, recall_score
from generate import generate_patient, SEED
from train import features

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("reference", "Original meal schedule", 0., .38),
    ("late_meals_2h", "Meals delayed by 2 hours", 2., .38),
    ("late_meals_4h", "Meals delayed by 4 hours", 4., .38),
    ("irregular_meals", "Irregular meal timing", 0., 1.5),
]


def evaluate(model, patients):
    rows, actual, current, groups = [], [], [], []
    horizons = model["horizons"]
    for patient in patients:
        for cursor in range(288, len(patient["series"])-24, 6):
            f = features(patient, cursor)
            rows.append([f[name] for name in model["featureNames"]])
            actual.append([patient["series"][cursor+h//5]["glucose"] for h in horizons])
            current.append(patient["series"][cursor]["glucose"])
            groups.append(patient["id"])
    x, y, groups = np.array(rows), np.array(actual), np.array(groups)
    z = (x-np.array(model["mean"]))/np.array(model["scale"])
    prediction = z @ np.array(model["regression"]["coefficients"]).T + model["regression"]["intercepts"]
    c = model["classification"]
    logits = (z @ c["coefficients"] + c["intercept"]) * c["calibrationSlope"] + c["calibrationIntercept"]
    probability = 1/(1+np.exp(-np.clip(logits, -700, 700)))
    labels = y[:, -1] >= model["event"]["thresholdMgDl"]
    flagged = probability >= model["alertPolicy"]["threshold"]
    residual = np.abs(y-prediction)
    coverage = residual <= model["interval"]["halfWidths"]
    patient_mae = np.array([residual[groups == p["id"], -1].mean() for p in patients])
    rng = np.random.default_rng(SEED + 9001)
    bootstrap = rng.choice(patient_mae, size=(1000, len(patient_mae)), replace=True).mean(axis=1)
    return {
        "patients": len(patients), "windows": len(rows), "positiveRate": float(labels.mean()),
        "mae": float(residual[:, -1].mean()), "maePatientBootstrap95CI": np.quantile(bootstrap, [.025,.975]).tolist(),
        "persistenceMae": float(mean_absolute_error(y[:, -1], current)),
        "auroc": float(roc_auc_score(labels, probability)) if len(np.unique(labels)) == 2 else None,
        "brier": float(brier_score_loss(labels, probability)),
        "recall": float(recall_score(labels, flagged, zero_division=0)),
        "precision": float(precision_score(labels, flagged, zero_division=0)),
        "intervalCoverage": float(coverage[:, -1].mean()),
        "byHorizon": [{"minutes": h, "mae": float(residual[:, i].mean()), "intervalCoverage": float(coverage[:, i].mean())} for i,h in enumerate(horizons)],
    }


def main():
    model_bytes = (ROOT/"data/model.json").read_bytes()
    model = json.loads(model_bytes)
    metrics = json.loads((ROOT/"data/metrics.json").read_text())
    indices = [int(pid.split("-")[-1])-1 for pid in metrics["splits"]["test"]]
    cases = []
    for case_id, title, shift, jitter in CASES:
        cohort = [generate_patient(index, metrics["cohort"]["days"], meal_shift_hours=shift, meal_jitter_hours=jitter) for index in indices]
        result = evaluate(model, cohort)
        cases.append({"id": case_id, "title": title, "mealShiftHours": shift, "mealJitterHoursSD": jitter, **result})
        print(f"{title}: MAE {result['mae']:.2f} mg/dL; coverage {result['intervalCoverage']:.1%}; recall {result['recall']:.1%}")
    # Audit prevents accidentally presenting a changed evaluation as the reference.
    for key in ["mae", "auroc", "brier", "intervalCoverage"]:
        if not np.isclose(cases[0][key], metrics["models"]["fused"][key], atol=1e-9):
            raise AssertionError(f"Reference does not reproduce held-out {key}")
    if (ROOT/"data/model.json").read_bytes() != model_bytes:
        raise AssertionError("Model artifact changed during a frozen-model audit")
    report = {
        "schemaVersion": 1, "syntheticOnly": True, "modelVersion": model["modelVersion"],
        "modelSHA256": hashlib.sha256(model_bytes).hexdigest(), "seed": SEED,
        "protocol": "Frozen coefficients, scaling, calibration, intervals and alert threshold. Same held-out patient identities; all eligible 30-minute-stride windows. Only main-meal timing is altered; snack, activity and noise draw sequences remain unchanged.",
        "target": metrics["target"], "alertThreshold": model["alertPolicy"]["threshold"],
        "testPatientIds": metrics["splits"]["test"], "cases": cases,
        "limitations": [
            "Synthetic sensitivity audit, not external or clinical validation.",
            "These stress cases were specified after examining the model's clock features; this is a transparent post-hoc audit, not a preregistered benchmark.",
            "The same test patients recur across cases, so comparisons are paired and observations are not independent.",
            "The model is not retrained on stress cases. No automatic drift detector is claimed.",
            "A nominal 90% interval is not guaranteed to retain coverage under distribution shift.",
            "Missing-sensor handling is exercised separately in Challenge lab; plausible CGM bias is a known undetected failure mode.",
        ],
    }
    (ROOT/"data/stress.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    lines = ["# Frozen-model stress audit", "", "Generated by `python ml/stress_test.py`. All results below are synthetic. The trained model was not changed.", "", report["protocol"], "", "| Case | +120 min MAE (mg/dL) | Persistence MAE | 90% interval coverage | Recall at fixed 20% threshold | AUROC |", "|---|---:|---:|---:|---:|---:|"]
    for c in cases:
        lines.append(f"| {c['title']} | {c['mae']:.2f} | {c['persistenceMae']:.2f} | {c['intervalCoverage']:.1%} | {c['recall']:.1%} | {c['auroc']:.4f} |")
    lines += ["", f"Each case uses **{cases[0]['patients']} held-out synthetic patients and {cases[0]['windows']:,} correlated windows**. Target: glucose >=180 mg/dL at exactly +120 minutes. Confidence intervals and all horizons are in [`data/stress.json`](../data/stress.json).", "", "## Interpretation", "", "Regular meal timing makes this simulator easier to predict. Delaying or varying meals challenges the clock features and can sharply reduce interval coverage and event recall. A good score on the original generator does not establish robustness. The product exposes this limitation rather than silently treating its interval as a safety guarantee.", "", "## Protocol and limits", ""]
    lines += [f"- {line}" for line in report["limitations"]]
    lines += ["", f"Frozen model file SHA-256: `{report['modelSHA256']}`. This is an artifact fingerprint, not a digital signature or authenticity guarantee.", ""]
    (ROOT/"docs/STRESS_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

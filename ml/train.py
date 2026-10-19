"""Train, evaluate and export small, auditable models for zero-dependency JS inference.

Run from repository root: python ml/train.py
All metrics are synthetic benchmark results, not clinical validation.
"""
from pathlib import Path
import argparse
import json
import platform
import numpy as np
import sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import (mean_absolute_error, mean_squared_error, roc_auc_score,
                             average_precision_score, brier_score_loss,
                             precision_score, recall_score, f1_score, confusion_matrix)
from generate import generate_patient, display_patient, SEED

ROOT = Path(__file__).resolve().parents[1]
STATIC = ["age", "bmi", "hba1c", "ldl", "diabetesYears"]
DYNAMIC = ["glucose", "lag30", "lag60", "lag120", "mean120", "std120", "slope30", "slope60",
           "hrMean60", "hrvMean60", "steps60", "steps24h", "sleep24h"]
CLOCK = [f"clock{k}{s}" for k in range(1, 5) for s in ["Sin", "Cos"]]
INTERACTIONS = ["hba1cGlucose", "hba1cSlope"] + [f"hba1cClock{k}{s}" for k in range(1, 5) for s in ["Sin", "Cos"]]
FEATURES = STATIC + DYNAMIC + CLOCK + INTERACTIONS
HORIZONS = [30, 60, 90, 120]


def features(patient, cursor):
    points = patient["series"]
    segment = points[cursor-287:cursor+1]
    g = [p["glucose"] for p in points[cursor-24:cursor+1]]
    recent = points[cursor-11:cursor+1]
    now = g[-1]
    hour = (cursor * 5 / 60) % 24
    f = {k: float(patient["ehr"][k]) for k in STATIC}
    f.update(glucose=now, lag30=g[-7], lag60=g[-13], lag120=g[0],
             mean120=float(np.mean(g)), std120=float(np.std(g)),
             slope30=(now-g[-7])/30, slope60=(now-g[-13])/60,
             hrMean60=float(np.mean([p["hr"] for p in recent])),
             hrvMean60=float(np.mean([p["hrv"] for p in recent])),
             steps60=sum(p["steps"] for p in recent), steps24h=sum(p["steps"] for p in segment),
             sleep24h=sum(p["sleep"] for p in segment)/12)
    for k in range(1, 5):
        f[f"clock{k}Sin"] = float(np.sin(k * 2 * np.pi * hour / 24))
        f[f"clock{k}Cos"] = float(np.cos(k * 2 * np.pi * hour / 24))
        for s in ["Sin", "Cos"]:
            f[f"hba1cClock{k}{s}"] = (f["hba1c"]-6.5) * f[f"clock{k}{s}"]
    f["hba1cGlucose"] = (f["hba1c"]-6.5)*(now-120)
    f["hba1cSlope"] = (f["hba1c"]-6.5)*f["slope30"]
    return f


def score(y, predicted, labels, probability, halfwidth=None):
    flagged = probability >= .5
    result = {"mae": float(mean_absolute_error(y[:, -1], predicted[:, -1])),
              "rmse": float(np.sqrt(mean_squared_error(y[:, -1], predicted[:, -1]))),
              "auroc": float(roc_auc_score(labels, probability)),
              "averagePrecision": float(average_precision_score(labels, probability)),
              "brier": float(brier_score_loss(labels, probability)),
              "precision": float(precision_score(labels, flagged, zero_division=0)),
              "recall": float(recall_score(labels, flagged, zero_division=0)),
              "f1": float(f1_score(labels, flagged, zero_division=0)),
              "confusionMatrix": confusion_matrix(labels, flagged).tolist(),
              "byHorizon": [{"minutes": h, "mae": float(mean_absolute_error(y[:, i], predicted[:, i])),
                             "rmse": float(np.sqrt(mean_squared_error(y[:, i], predicted[:, i])))} for i, h in enumerate(HORIZONS)]}
    if halfwidth is not None:
        result["intervalCoverage"] = float(np.mean(np.abs(y[:, -1]-predicted[:, -1]) <= halfwidth[-1]))
        result["intervalMeanWidth"] = float(2*halfwidth[-1])
        for i, row in enumerate(result["byHorizon"]):
            row["intervalCoverage"] = float(np.mean(np.abs(y[:, i]-predicted[:, i]) <= halfwidth[i]))
    return result


def calibration_bins(labels, probabilities):
    bins = []
    for low in np.arange(0, 1, .1):
        mask = (probabilities >= low) & (probabilities < low+.1)
        bins.append({"lower": float(low), "upper": float(low+.1), "count": int(mask.sum()),
                     "predicted": float(np.mean(probabilities[mask])) if mask.any() else None,
                     "observed": float(np.mean(labels[mask])) if mask.any() else None})
    return bins


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients", type=int, default=240)
    parser.add_argument("--days", type=int, default=4)
    args = parser.parse_args()
    if args.patients < 80 or args.days < 3:
        parser.error("Use at least 80 patients and 3 days for all splits and display examples.")
    cohort = [generate_patient(i, args.days) for i in range(args.patients)]
    rng = np.random.default_rng(SEED)
    shuffled = rng.permutation(args.patients)
    ntrain, nval = int(args.patients*.6), int(args.patients*.2)
    split_ids = {"train": shuffled[:ntrain], "validation": shuffled[ntrain:ntrain+nval], "test": shuffled[ntrain+nval:]}
    rows, targets, groups, cursors = [], [], [], []
    for pi, patient in enumerate(cohort):
        for cursor in range(288, len(patient["series"])-24, 6):
            f = features(patient, cursor)
            rows.append([f[name] for name in FEATURES])
            targets.append([patient["series"][cursor+h//5]["glucose"] for h in HORIZONS])
            groups.append(pi)
            cursors.append(cursor)
    x, y, groups = np.array(rows), np.array(targets), np.array(groups)
    labels = (y[:, -1] >= 180).astype(int)
    masks = {name: np.isin(groups, ids) for name, ids in split_ids.items()}
    train, val, test = [masks[k] for k in ["train", "validation", "test"]]
    model_results, exported = {}, None
    for name, feature_names in {"fused": FEATURES, "sensorOnly": DYNAMIC+CLOCK, "staticOnly": STATIC}.items():
        indices = [FEATURES.index(f) for f in feature_names]
        inputs = x[:, indices]
        scaler = StandardScaler().fit(inputs[train])
        z = scaler.transform(inputs)
        regression = Ridge(alpha=30).fit(z[train], y[train])
        classifier = LogisticRegression(C=.3, max_iter=1500, random_state=SEED).fit(z[train], labels[train])
        # Calibrate on held-out patients; test outcomes never choose coefficients or thresholds.
        val_logit = classifier.decision_function(z[val]).reshape(-1, 1)
        calibrator = LogisticRegression(C=100, max_iter=1000).fit(val_logit, labels[val])
        probability = calibrator.predict_proba(classifier.decision_function(z[test]).reshape(-1, 1))[:, 1]
        prediction = regression.predict(z[test])
        residual = np.abs(y[val] - regression.predict(z[val]))
        widths = np.quantile(residual, .9, axis=0, method="higher")
        result = score(y[test], prediction, labels[test], probability, widths)
        result["calibration"] = calibration_bins(labels[test], probability)
        model_results[name] = result
        if name == "fused":
            validation_probability = calibrator.predict_proba(val_logit)[:, 1]
            thresholds = np.arange(.05, .951, .01)
            # The highest threshold meeting 80% validation sensitivity is fixed before test scoring.
            eligible = [t for t in thresholds if recall_score(labels[val], validation_probability >= t) >= .8]
            alert_threshold = round(float(max(eligible)), 2) if eligible else .05
            alert_policy = {"threshold": alert_threshold,
                            "selection": "Highest threshold on 0.01 grid achieving >=80% recall on validation patients",
                            "validationRecall": float(recall_score(labels[val], validation_probability >= alert_threshold)),
                            "testPrecision": float(precision_score(labels[test], probability >= alert_threshold, zero_division=0)),
                            "testRecall": float(recall_score(labels[test], probability >= alert_threshold)),
                            "testF1": float(f1_score(labels[test], probability >= alert_threshold)),
                            "testConfusionMatrix": confusion_matrix(labels[test], probability >= alert_threshold).tolist()}
            result["alertPolicy"] = alert_policy
            exported = {"modelVersion": "aura-synthetic-1.0.0", "seed": SEED,
                        "algorithm": "StandardScaler + Ridge / LogisticRegression + validation Platt calibration",
                        "featureNames": feature_names, "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
                        "horizons": HORIZONS, "regression": {"coefficients": regression.coef_.tolist(), "intercepts": regression.intercept_.tolist()},
                        "classification": {"coefficients": classifier.coef_[0].tolist(), "intercept": float(classifier.intercept_[0]),
                                           "calibrationSlope": float(calibrator.coef_[0,0]), "calibrationIntercept": float(calibrator.intercept_[0])},
                        "interval": {"nominalCoverage": .9, "halfWidths": widths.tolist(), "method": "90th percentile absolute residuals on validation patients; marginal descriptive interval"},
                        "event": {"horizonMinutes": 120, "thresholdMgDl": 180, "operator": ">=", "probabilityThreshold": .5},
                        "alertPolicy": alert_policy,
                        "limits": {"minHistoryPoints": 288, "maxGlucoseStalenessMinutes": 15, "maxMissingFraction": .2},
                        "disclaimer": "Synthetic research prototype. Not clinically validated and not for diagnosis or treatment."}
    persistence = np.tile(x[test, FEATURES.index("glucose")][:, None], (1, 4))
    persistence_probability = (persistence[:, -1] >= 180).astype(float)
    model_results["persistence"] = score(y[test], persistence, labels[test], persistence_probability)
    # Separate bootstrap units are patients, not correlated windows.
    fused_mae_samples = []
    test_groups = groups[test]
    testx = (x[test]-np.array(exported["mean"]))/np.array(exported["scale"])
    pred = testx @ np.array(exported["regression"]["coefficients"]).T + exported["regression"]["intercepts"]
    patient_mae = np.array([np.mean(np.abs(y[test][test_groups == i,-1]-pred[test_groups == i,-1])) for i in split_ids["test"]])
    for _ in range(1000):
        fused_mae_samples.append(float(np.mean(rng.choice(patient_mae, len(patient_mae), replace=True))))
    model_results["fused"]["maePatientBootstrap95CI"] = np.quantile(fused_mae_samples, [.025,.975]).tolist()
    metrics = {"schemaVersion": 1, "seed": SEED, "syntheticOnly": True,
               "target": "CGM glucose >=180 mg/dL at exactly +120 minutes; not any excursion within two hours",
               "cohort": {"patients": args.patients, "days": args.days, "cadenceMinutes": 5, "windowStrideMinutes": 30,
                          "trainPatients": ntrain, "validationPatients": nval, "testPatients": args.patients-ntrain-nval,
                          "windows": {k: int(v.sum()) for k,v in masks.items()},
                          "positiveRate": {k: float(labels[v].mean()) for k,v in masks.items()}},
               "splits": {k: [cohort[int(i)]["id"] for i in ids] for k,ids in split_ids.items()},
               "models": model_results, "probabilityThreshold": .5,
               "environment": {"python": platform.python_version(), "numpy": np.__version__, "scikitLearn": sklearn.__version__},
               "limitations": ["All results measure a designed synthetic generator, not real-world clinical performance.",
                               "Regular simulated meals and HbA1c-dependent physiology may advantage fusion.",
                               "Overlapping windows are correlated; only MAE has patient-bootstrap uncertainty.",
                               "Residual intervals are descriptive marginal intervals; coverage is not guaranteed per patient or under shift.",
                               "No external validation, medication effects, device validation, or treatment recommendation.",
                               "Persistence probability is a hard 0/1 forecast; its Brier/AUROC are not probabilistic calibration comparators."]}
    display = []
    parity = []
    for di, pi in enumerate(split_ids["test"][:8]):
        patient = display_patient(cohort[int(pi)], di)
        candidates = list(range(288, len(patient["series"])-24, 6))
        # Curated examples are labeled as such; this selection does not change evaluation.
        candidate_features = np.array([[features(patient,c)[n] for n in FEATURES] for c in candidates])
        z = (candidate_features-np.array(exported["mean"]))/np.array(exported["scale"])
        logits = z @ np.array(exported["classification"]["coefficients"]) + exported["classification"]["intercept"]
        probabilities = 1/(1+np.exp(-(logits*exported["classification"]["calibrationSlope"]+exported["classification"]["calibrationIntercept"])))
        rising = np.array([patient["series"][c]["glucose"] < 180 for c in candidates])
        chosen = int(np.argmax(np.where(rising, probabilities, -1))) if di < 3 else len(candidates)-10-di*3
        cursor = candidates[chosen]
        patient["defaultCursor"] = cursor
        patient["replayNote"] = "Curated synthetic demonstration window from a held-out test patient. Future observations are visible only in retrospective replay."
        display.append(patient)
        f = features(patient, cursor)
        zz = (np.array([f[n] for n in FEATURES])-np.array(exported["mean"]))/np.array(exported["scale"])
        preds = zz @ np.array(exported["regression"]["coefficients"]).T + exported["regression"]["intercepts"]
        parity.append({"id":patient["id"], "cursor":cursor, "features":f, "forecast":preds.tolist(), "risk":float(probabilities[chosen])})
    # Lead with the selected high-risk example while keeping stable patient IDs.
    display.sort(key=lambda p: -next(v["risk"] for v in parity if v["id"]==p["id"]))
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    for filename, payload in [("model.json",exported), ("metrics.json",metrics), ("patients.json",display), ("parity.json",parity)]:
        (data/filename).write_text(json.dumps(payload, indent=2 if filename!="patients.json" else None, allow_nan=False), encoding="utf-8")
    print(json.dumps({"cohort":metrics["cohort"],"models":{k:{kk:v[kk] for kk in ["mae","auroc","brier","recall"]} for k,v in model_results.items()}},indent=2))


if __name__ == "__main__":
    main()

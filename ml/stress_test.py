"""Reproduce routine scores from exported JSON only: no fitting or recalibration.

python ml/stress_test.py            # current model, fresh final identities
python ml/stress_test.py --legacy   # archived v1, original 48 test identities
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import numpy as np
from generate import generate_patient
from train import features as legacy_features
from train_robust import robust_features, score, bootstrap

ROOT = Path(__file__).resolve().parents[1]


def predict_tree(ensemble, x):
    """Independent vectorized traversal of exported numerical sklearn trees."""
    output = np.full(len(x), ensemble['baseline'], dtype=float)
    for tree in ensemble['trees']:
        nodes = tree['nodes']
        stack = [(0, np.arange(len(x)))]
        while stack:
            index, rows = stack.pop()
            if not len(rows):
                continue
            feature, threshold, left, right, value, missing_left = nodes[index]
            if feature == -1:
                output[rows] += value
                continue
            observed = x[rows, feature]
            choose_left = np.where(np.isfinite(observed), observed <= threshold, missing_left)
            stack.append((left, rows[choose_left]))
            stack.append((right, rows[~choose_left]))
    return output


def predict_export(model, x):
    z = (x-np.asarray(model['mean']))/np.asarray(model['scale'])
    regression, classifier = model['regression'], model['classification']
    prediction = (np.column_stack([predict_tree(tree, x) for tree in regression['models']])
                  if 'models' in regression else z@np.asarray(regression['coefficients']).T+regression['intercepts'])
    raw = (predict_tree(classifier, x) if 'trees' in classifier
           else z@np.asarray(classifier['coefficients'])+classifier['intercept'])
    logit = raw*classifier['calibrationSlope']+classifier['calibrationIntercept']
    return prediction, 1/(1+np.exp(-np.clip(logit, -700, 700)))


def evaluate(model, ids, params, days):
    rows, targets, current, groups = [], [], [], []
    extractor = robust_features if 'priorDayMean120' in model['featureNames'] else legacy_features
    for patient_id in ids:
        patient = generate_patient(int(patient_id.split('-')[1])-1, days, **params)
        for cursor in range(288, len(patient['series'])-24, 6):
            features = extractor(patient, cursor)
            rows.append([features[name] for name in model['featureNames']])
            targets.append([patient['series'][cursor+h//5]['glucose'] for h in model['horizons']])
            current.append(patient['series'][cursor]['glucose'])
            groups.append(patient_id)
    x, y, groups = np.asarray(rows), np.asarray(targets), np.asarray(groups)
    prediction, probability = predict_export(model, x)
    result = score(y, prediction, probability, model['interval']['halfWidths'], model['alertPolicy']['threshold'])
    result.update(patients=len(ids), windows=len(rows),
                  persistenceMae=float(np.mean(np.abs(y[:, -1]-np.asarray(current)))),
                  maePatientBootstrap95CI=bootstrap(np.abs(y[:, -1]-prediction[:, -1]), groups))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy', action='store_true')
    args = parser.parse_args()
    folder = ROOT/'data'/('baseline-v1' if args.legacy else '')
    model_bytes = (folder/'model.json').read_bytes()
    model = json.loads(model_bytes)
    model_hash = hashlib.sha256(model_bytes).hexdigest()
    if args.legacy:
        metrics = json.loads((folder/'metrics.json').read_text(encoding='utf8'))
        ids, days = metrics['splits']['test'], metrics['cohort']['days']
        routines = [
            {'id':'reference', 'title':'Original meal schedule', 'params':{}},
            {'id':'late_meals_2h', 'title':'Meals delayed by 2 hours', 'params':{'meal_shift_hours':2}},
            {'id':'late_meals_4h', 'title':'Meals delayed by 4 hours', 'params':{'meal_shift_hours':4}},
            {'id':'irregular_meals', 'title':'Irregular meal timing', 'params':{'meal_jitter_hours':1.5}},
        ]
        expected = {case['id']:case for case in json.loads((folder/'stress.json').read_text(encoding='utf8'))['cases']}
        report = {'schemaVersion':1, 'syntheticOnly':True, 'modelVersion':model['modelVersion'],
                  'modelSHA256':model_hash, 'testPatientIds':ids,
                  'protocol':'Reproduction of archived v1 post-hoc audit. Frozen JSON coefficients, calibration, threshold and interval widths.',
                  'target':metrics['target'], 'alertThreshold':model['alertPolicy']['threshold']}
        output = folder/'stress-reproduced.json'
    else:
        if model['modelVersion'] != 'aura-synthetic-2.0.0':
            raise RuntimeError('Train and freeze v2 before running the current audit; use --legacy for archived v1.')
        protocol = json.loads((folder/'robustness-protocol.json').read_text(encoding='utf8'))
        robustness = json.loads((folder/'robustness.json').read_text(encoding='utf8'))
        if robustness['modelSHA256'] != model_hash:
            raise RuntimeError('Current model does not match the recorded final evaluation fingerprint.')
        ids, days, routines = protocol['splits']['test'], protocol['days'], protocol['routines']
        expected = {case['id']:case['models']['fused'] for case in robustness['cases']}
        report = json.loads((folder/'stress.json').read_text(encoding='utf8'))
        output = folder/'stress.json'
    reproduced = []
    existing = {case['id']:case for case in report.get('cases', [])}
    for routine in routines:
        result = evaluate(model, ids, routine['params'], days)
        reference = expected[routine['id']]
        for key in ['mae', 'auroc', 'brier', 'intervalCoverage', 'recall', 'precision']:
            if not np.isclose(result[key], reference[key], atol=1e-10, rtol=1e-10):
                raise AssertionError(f"{routine['id']} {key}: exported JSON {result[key]} differs from recorded {reference[key]}")
        reproduced.append({**existing.get(routine['id'], {}), 'id':routine['id'], 'title':routine['title'], **result})
        print(f"{routine['title']}: MAE {result['mae']:.3f}; coverage {result['intervalCoverage']:.1%}; recall {result['recall']:.1%}; reproduced", flush=True)
    if (folder/'model.json').read_bytes() != model_bytes:
        raise AssertionError('Model changed during the audit.')
    report.update(cases=reproduced, reproduction={
        'at':datetime.now(timezone.utc).isoformat(), 'modelSHA256':model_hash,
        'method':'Independent traversal of the exported JSON; no estimator objects, fitting, threshold changes or recalibration.',
        'matchedMetrics':['mae','auroc','brier','intervalCoverage','recall','precision']})
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(f'PASS: all {len(routines)} cases reproduce; {output}', flush=True)


if __name__ == '__main__':
    main()

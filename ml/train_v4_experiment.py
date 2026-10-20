"""Independent synthetic V4 experiment: resolved forecast history, HGB + ExtraTrees.

This never replaces the active model or the separate open-research experiment.
Phases: develop -> freeze -> evaluate. Final identities are generated only after
the frozen estimator, calibration, decision policy and protocol are fingerprinted.
"""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('LOKY_MAX_CPU_COUNT', '4')
import argparse
import hashlib
import inspect
import json
import pickle
import platform
import time
import numpy as np
import sklearn
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              ExtraTreesClassifier, ExtraTreesRegressor)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss
from generate import generate_patient, SEED
from train_v3 import trajectory_features, FEATURES as V3_FEATURES, EXTRA_LAGS
from train_robust import ROUTINES, HORIZONS, score, bins, timestamp, write_json
from stress_test import predict_export

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = '87fb0df0832c2db76b03c55c81298ab717200c3dc60048b9b4586dc7061d81b4'
SPLITS = {'train': list(range(2500, 3012)), 'selection': list(range(3200, 3280)),
          'probabilityCalibration': list(range(3400, 3448)),
          'policyCalibration': list(range(3448, 3496)), 'test': list(range(4000, 4120))}
UNSEEN = {'id': 'new_shift_variable_combination', 'title': 'New held-out shifted variable combination',
          'params': {'meal_shift_hours': 2.5, 'meal_jitter_hours': 1.8,
                     'day_shift_hours_sd': 1.0, 'meal_skip_probability': .30, 'variable_routine': True}}
MEMORY_NAMES = ['v3Forecast30', 'v3Forecast60', 'v3Forecast90', 'v3Forecast120', 'v3Logit',
                'resolvedForecastCount', 'resolvedResidualLast', 'resolvedResidualMean3',
                'resolvedResidualMean6', 'resolvedResidualMean12', 'resolvedResidualMean24',
                'resolvedResidualStd12', 'resolvedAbsoluteErrorMean12',
                'resolvedEventRate12', 'resolvedExpectedEventRate12', 'resolvedProbabilityBias12',
                'resolvedResidualTrend6', 'resolvedResidualQ25_12', 'resolvedResidualQ75_12']
FEATURES = V3_FEATURES + MEMORY_NAMES
CLASSIFIER_CANDIDATES = [{'hgbWeight': w, 'baseWeight': b} for b in [0., .25] for w in [0., .25, .5, .75, 1.]]
REGRESSION_CANDIDATES = [{'hgbWeight': w, 'correctionWeight': a} for a in [0., .5, 1.] for w in [0., .5, 1.]]
WORK = ROOT / 'work/synthetic-v4'
OUT = ROOT / 'data/synthetic-v4-experiment'
BASE_PATH = ROOT / 'data/model.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def base_model():
    if digest(BASE_PATH) != BASE_SHA:
        raise RuntimeError('The base model must be the unchanged frozen V3 artifact. Supply --base-model if archived.')
    return json.loads(BASE_PATH.read_bytes())


def fast_features(patient, cursors):
    """Vectorized equivalent of the 108 exported V3 past-only features."""
    cursors = np.asarray(cursors, dtype=int)
    if len(cursors) == 0 or cursors.min() < 287 or cursors.max() >= len(patient['series']):
        raise ValueError('Invalid cursor grid for 24-hour feature history.')
    arr = np.asarray([[row[k] for k in ['glucose', 'hr', 'hrv', 'steps', 'sleep']]
                      for row in patient['series']], dtype=float)
    ix = cursors[:, None] + np.arange(-287, 1)[None, :]
    g, hr, hrv, steps, sleep = [arr[ix, j] for j in range(5)]
    n = len(cursors)
    f = {key: np.full(n, float(patient['ehr'][key])) for key in ['age', 'bmi', 'hba1c', 'ldl', 'diabetesYears']}
    lag = lambda minutes: arr[cursors - minutes // 5, 0]
    f.update(glucose=g[:, -1], mean120=g[:, -25:].mean(1), std120=g[:, -25:].std(1),
             slope30=(g[:, -1] - lag(30)) / 30, slope60=(g[:, -1] - lag(60)) / 60,
             hrMean60=hr[:, -12:].mean(1), hrvMean60=hrv[:, -12:].mean(1),
             steps60=steps[:, -12:].sum(1), steps24h=steps.sum(1), sleep24h=sleep.sum(1) / 12)
    for minutes in sorted(set([15, 30, 45, 60, 90, 120, 180, 240, 360] + EXTRA_LAGS)):
        f[f'lag{minutes}'] = lag(minutes)
    for name, count in [('30', 7), ('60', 13), ('360', 73), ('24h', 288)]:
        f[f'mean{name}'], f[f'std{name}'] = g[:, -count:].mean(1), g[:, -count:].std(1)
    f.update(min120=g[:, -25:].min(1), max120=g[:, -25:].max(1),
             q25_120=np.quantile(g[:, -25:], .25, axis=1), q75_120=np.quantile(g[:, -25:], .75, axis=1),
             q10_24h=np.quantile(g, .1, axis=1), q50_24h=np.quantile(g, .5, axis=1), q90_24h=np.quantile(g, .9, axis=1),
             slope15=(g[:, -1] - lag(15)) / 15, slope120=(g[:, -1] - lag(120)) / 120,
             acceleration30=(g[:, -1] - lag(30)) / 30 - (lag(30) - lag(60)) / 30,
             priorDayMean120=g[:, :24].mean(1), hrSlope30=(hr[:, -1] - hr[:, -7]) / 30,
             hrvSlope30=(hrv[:, -1] - hrv[:, -7]) / 30, hrMean120=hr[:, -24:].mean(1),
             hrvMean120=hrv[:, -24:].mean(1), steps120=steps[:, -24:].sum(1), sleepLast6h=sleep[:, -72:].sum(1) / 12)
    for horizon in HORIZONS:
        f[f'priorDay{horizon}'] = lag(1440 - horizon)
    for minutes in [30, 60, 120, 240]:
        values = g[:, -(minutes // 5 + 1):]
        axis = np.arange(values.shape[1]) * 5.
        axis -= axis.mean()
        f[f'olsSlope{minutes}'] = ((values - values.mean(1)[:, None]) * axis).sum(1) / (axis ** 2).sum()
    f.update(meanDelta30_60=f['mean30'] - f['mean60'], meanDelta60_120=f['mean60'] - f['mean120'])
    for minutes in [30, 60, 120]:
        changes = np.diff(g[:, -(minutes // 5 + 1):], axis=1)
        f[f'riseFraction{minutes}'] = (changes > 0).mean(1)
        f[f'meanAbsChange{minutes}'] = np.abs(changes).mean(1)
    f.update(fallFraction60=(np.diff(g[:, -13:], axis=1) < 0).mean(1),
             maxRise30=np.diff(g[:, -7:], axis=1).max(1), maxFall30=np.diff(g[:, -7:], axis=1).min(1),
             range30=np.ptp(g[:, -7:], axis=1), range60=np.ptp(g[:, -13:], axis=1),
             minutesSinceMax120=np.argmax(g[:, -25:][:, ::-1], axis=1) * 5,
             minutesSinceMin120=np.argmin(g[:, -25:][:, ::-1], axis=1) * 5,
             glucoseAboveQ10=g[:, -1] - f['q10_24h'], glucoseAboveMedian=g[:, -1] - f['q50_24h'],
             excessMean120=np.maximum(0, g[:, -25:] - f['q10_24h'][:, None]).mean(1),
             timeAbove180_120=(g[:, -25:] >= 180).mean(1), timeAbove140_120=(g[:, -25:] >= 140).mean(1))
    for name, values in [('hr', hr), ('hrv', hrv)]:
        f[f'{name}Mean15'], f[f'{name}Mean30'] = values[:, -3:].mean(1), values[:, -6:].mean(1)
        f[f'{name}Mean24h'], f[f'{name}Std24h'] = values.mean(1), values.std(1)
        f[f'{name}Z30'] = (f[f'{name}Mean30'] - f[f'{name}Mean24h']) / np.maximum(1, f[f'{name}Std24h'])
    wake = (sleep[:, :-1] > 0) & (sleep[:, 1:] == 0)
    waking_at = np.where(wake, np.arange(1, 288)[None, :], -1).max(1)
    activity_at = np.where(steps >= 50, np.arange(288)[None, :], -1).max(1)
    resting = (sleep == 0) & (steps < 20)
    f.update(steps15=steps[:, -3:].sum(1), steps30=steps[:, -6:].sum(1), sleepLast60=sleep[:, -12:].sum(1) / 12,
             minutesSinceWake=np.where(waking_at >= 0, (287 - waking_at) * 5, 1440),
             minutesSinceActivity=np.where(activity_at >= 0, (287 - activity_at) * 5, 1440),
             awakeRestingHr24h=np.where(resting.any(1), (hr * resting).sum(1) / np.maximum(1, resting.sum(1)), hr.mean(1)),
             awakeRestingHr30=np.where(resting[:, -6:].any(1), (hr[:, -6:] * resting[:, -6:]).sum(1) / np.maximum(1, resting[:, -6:].sum(1)), hr[:, -6:].mean(1)),
             glucoseMinusPriorDay120=g[:, -1] - f['priorDay120'])
    f['hrAboveResting30'] = f['awakeRestingHr30'] - f['awakeRestingHr24h']
    return np.column_stack([f[key] for key in V3_FEATURES])


def memory_features(x, prediction, probability, groups, regimes, cursors):
    """Uses current/past X only; never reads training targets Y.

    A forecast issued at q can contribute its residual at t only if q+120 <= t.
    Observed truth comes from the already-observed glucose row at q+120.
    """
    output = np.zeros((len(x), len(MEMORY_NAMES)), dtype=float)
    output[:, :4] = prediction
    clipped = np.clip(probability, 1e-7, 1 - 1e-7)
    output[:, 4] = np.log(clipped / (1 - clipped))
    glucose = x[:, V3_FEATURES.index('glucose')]
    pairs = np.column_stack([groups, regimes])
    for group, regime in np.unique(pairs, axis=0):
        rows = np.flatnonzero((groups == group) & (regimes == regime))
        rows = rows[np.argsort(cursors[rows])]
        cursor_to_row = {int(cursors[row]): int(row) for row in rows}
        for row in rows:
            matured = [int(q) for q in rows if cursors[q] + 24 <= cursors[row]
                       and int(cursors[q] + 24) in cursor_to_row]
            if not matured:
                continue
            mature = np.asarray(matured)
            actual_rows = np.asarray([cursor_to_row[int(cursors[q] + 24)] for q in mature])
            if np.any(cursors[actual_rows] > cursors[row]):
                raise AssertionError('Unresolved future target entered memory features.')
            residual = glucose[actual_rows] - prediction[mature, -1]
            last = residual[-12:]
            observed_events = (glucose[actual_rows[-12:]] >= 180).mean()
            expected_events = probability[mature[-12:]].mean()
            trend = (residual[-1] - residual[-min(6, len(residual))]) / max(1, min(5, len(residual) - 1))
            output[row, 5:] = [len(mature), residual[-1], residual[-3:].mean(), residual[-6:].mean(),
                               last.mean(), residual[-24:].mean(), last.std(), np.abs(last).mean(),
                               observed_events, expected_events, observed_events - expected_events,
                               trend, np.quantile(last, .25), np.quantile(last, .75)]
    return np.column_stack([x, output])


def protocol():
    return {'experimentVersion': 'aura-synthetic-v4-experiment-1.0.0', 'seed': SEED + 4,
            'createdAt': timestamp(), 'syntheticOnly': True, 'activeModelReplaced': False,
            'target': 'Glucose >=180 mg/dL at exactly +120 minutes; overlapping windows, not unique episodes.',
            'baseModelVersion': 'aura-synthetic-3.0.0', 'baseModelSHA256': BASE_SHA,
            'generatorSHA256': digest(ROOT / 'ml/generate.py'), 'generatorUnchanged': True,
            'experimentSourceSHA256': digest(__file__), 'days': 4, 'splits': SPLITS,
            'routines': ROUTINES, 'heldOutCombination': UNSEEN, 'features': FEATURES,
            'history': 'V3 24h history plus available matured V3 forecast residuals; no future target values, clocks or routine labels as inputs.',
            'trainingStrideMinutes': 60, 'memoryAndEvaluationStrideMinutes': 30,
            'classifierCandidates': CLASSIFIER_CANDIDATES, 'regressionCandidates': REGRESSION_CANDIDATES,
            'classifierSelection': 'Minimize worst FP/FN count ratio against frozen V3 across overall, irregular and variable-routine selection windows; one global threshold; mean ratio then AP tie break.',
            'regressionSelection': 'Lowest selection +120-minute MAE from predeclared HGB/ExtraTrees residual blends; earlier horizons remain the frozen V3 forecast.',
            'calibration': '48 new identities fit Platt mapping; separate 48 identities choose global policy and residual bands.',
            'finalGate': 'No IDs >=4000 or held-out combination generated before frozen estimator, calibrator, threshold, bands and protocol are SHA-256 recorded.',
            'promotionGate': 'Both FP and FN lower than V3 in primary, variable and held-out groups, with primary paired FN/FP 95% intervals entirely below zero; no automatic promotion.',
            'limitations': ['Synthetic experiment only, separate from open-research model evaluation.',
                           'Unannounced future meals remain partly unpredictable.',
                           'Personalization only uses already resolved historical forecasts; it does not fit on future test outcomes.',
                           'Routine families appear in training; one new factor combination is held out.']}


def dataset(name, ids, routines, allow_final=False):
    if any(i >= 4000 for i in ids) and not allow_final:
        raise RuntimeError('Final identity generation is prohibited before the explicit evaluation gate.')
    signature = hashlib.sha256(json.dumps({'ids': ids, 'routines': routines, 'base': BASE_SHA,
                                           'generator': digest(ROOT / 'ml/generate.py'),
                                           'fastFeatures': inspect.getsource(fast_features),
                                           'memoryFeatures': inspect.getsource(memory_features)}, sort_keys=True).encode()).hexdigest()
    cache = WORK / f'{name}.npz'
    if cache.exists():
        data = dict(np.load(cache))
        if str(data.pop('signature').item()) != signature:
            raise RuntimeError('Cache provenance changed; use a fresh output/work directory.')
        print(f'Loaded {name}: {len(data["x"])} windows', flush=True)
        return data
    rows, targets, groups, regimes, cursors = [], [], [], [], []
    started = time.time()
    for ri, routine in enumerate(routines):
        for index in ids:
            patient = generate_patient(index, **routine['params'])
            grid = np.arange(288, len(patient['series']) - 24, 6)
            rows.append(fast_features(patient, grid))
            g = np.asarray([r['glucose'] for r in patient['series']])
            targets.append(g[grid[:, None] + np.asarray(HORIZONS)[None, :] // 5])
            groups.extend([index] * len(grid)); regimes.extend([ri] * len(grid)); cursors.extend(grid)
        print(f'{name}: {routine["id"]}, {len(ids)} identities, {time.time()-started:.1f}s', flush=True)
    x, y = np.vstack(rows), np.vstack(targets)
    groups, regimes, cursors = np.asarray(groups), np.asarray(regimes), np.asarray(cursors)
    print(f'{name}: evaluating frozen V3 JSON for {len(x)} rows', flush=True)
    prediction, probability = predict_export(base_model(), x)
    print(f'{name}: constructing resolved-history features', flush=True)
    enriched = memory_features(x, prediction, probability, groups, regimes, cursors)
    data = {'x': enriched, 'y': y, 'groups': groups, 'regimes': regimes, 'cursors': cursors,
            'basePrediction': prediction, 'baseProbability': probability}
    WORK.mkdir(parents=True, exist_ok=True)
    np.savez(cache, signature=np.asarray(signature), **data)
    return data


def count_errors(labels, probability, threshold, mask):
    flag = probability[mask] >= threshold
    truth = labels[mask]
    tp, fp = int(np.sum(flag & truth)), int(np.sum(flag & ~truth))
    fn, tn = int(np.sum(~flag & truth)), int(np.sum(~flag & ~truth))
    return {'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp,
            'recall': tp / max(1, tp + fn), 'precision': tp / max(1, tp + fp)}


def choose_policy(labels, probability, baseline, regimes):
    masks = {'overall': np.ones(len(labels), dtype=bool), 'irregular': regimes >= 3, 'variable': regimes == 5}
    reference = {name: count_errors(labels, baseline, .155, mask) for name, mask in masks.items()}
    best = None
    for threshold in np.arange(.01, .801, .0025):
        counts = {name: count_errors(labels, probability, threshold, mask) for name, mask in masks.items()}
        ratios = [counts[name][kind] / max(1, reference[name][kind]) for name in masks for kind in ['fp', 'fn']]
        candidate = (max(ratios), float(np.mean(ratios)), float(threshold), counts)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return {'threshold': best[2], 'worstCountRatio': best[0], 'meanCountRatio': best[1],
            'counts': best[3], 'baselineCounts': reference,
            'method': 'Global calibration-only threshold; worst overall/irregular/variable FP/FN ratio to fixed V3 policy.'}


def classifier_mix(hgb, extra, base, candidate):
    learned = candidate['hgbWeight'] * hgb + (1 - candidate['hgbWeight']) * extra
    return (1 - candidate['baseWeight']) * learned + candidate['baseWeight'] * base


def regression_mix(hgb, extra, base, candidate):
    correction = candidate['hgbWeight'] * hgb + (1 - candidate['hgbWeight']) * extra
    output = base.copy()
    output[:, -1] += candidate['correctionWeight'] * correction
    return output


def logit(values):
    p = np.clip(values, 1e-7, 1 - 1e-7)
    return np.log(p / (1 - p))


def save_pickle(path, obj):
    path.write_bytes(pickle.dumps(obj, protocol=5))


def load_pickle(path):
    # Only loads artifacts generated locally by this experiment, never downloads.
    return pickle.loads(path.read_bytes())


def develop():
    if (OUT / 'freeze.json').exists():
        raise RuntimeError('Frozen experiment cannot be developed again.')
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    base_model()
    write_json(OUT / 'protocol.json', protocol())
    train = dataset('train', SPLITS['train'], ROUTINES)
    selection = dataset('selection', SPLITS['selection'], ROUTINES)
    keep = train['cursors'] % 12 == 0
    x, y = train['x'][keep], train['y'][keep, -1]
    weight = np.where(train['regimes'][keep] >= 3, 2., 1.)
    print(f'Fitting HGB and ExtraTrees on {len(x)} new-identity windows', flush=True)
    estimators = {
        'hgbClassifier': HistGradientBoostingClassifier(max_iter=260, max_leaf_nodes=31,
            min_samples_leaf=80, learning_rate=.05, l2_regularization=15, max_bins=127,
            early_stopping=False, random_state=SEED+4),
        'extraClassifier': ExtraTreesClassifier(n_estimators=220, min_samples_leaf=30,
            max_depth=24, max_features=.85, n_jobs=4, random_state=SEED+4),
        'hgbResidual': HistGradientBoostingRegressor(loss='absolute_error', max_iter=240,
            max_leaf_nodes=31, min_samples_leaf=80, learning_rate=.05, l2_regularization=15,
            max_bins=127, early_stopping=False, random_state=SEED+4),
        'extraResidual': ExtraTreesRegressor(n_estimators=180, min_samples_leaf=30,
            max_depth=24, max_features=.85, n_jobs=4, random_state=SEED+4),
    }
    for name, estimator in estimators.items():
        started = time.time()
        target = y >= 180 if 'Classifier' in name else y - train['basePrediction'][keep, -1]
        estimator.fit(x, target, sample_weight=weight)
        print(f'{name} fit in {time.time()-started:.1f}s', flush=True)
    sx = selection['x']; labels = selection['y'][:, -1] >= 180
    hc, ec = [estimators[name].predict_proba(sx)[:, 1] for name in ['hgbClassifier', 'extraClassifier']]
    hr, er = [estimators[name].predict(sx) for name in ['hgbResidual', 'extraResidual']]
    classification = []
    for candidate in CLASSIFIER_CANDIDATES:
        prob = classifier_mix(hc, ec, selection['baseProbability'], candidate)
        policy = choose_policy(labels, prob, selection['baseProbability'], selection['regimes'])
        classification.append({'candidate': candidate, 'policy': policy,
                               'averagePrecision': float(average_precision_score(labels, prob)),
                               'auroc': float(roc_auc_score(labels, prob)), 'brier': float(brier_score_loss(labels, prob))})
    classification.sort(key=lambda row: (row['policy']['worstCountRatio'], row['policy']['meanCountRatio'], -row['averagePrecision']))
    regression = []
    for candidate in REGRESSION_CANDIDATES:
        pred = regression_mix(hr, er, selection['basePrediction'], candidate)
        regression.append({'candidate': candidate, 'mae': float(np.abs(selection['y'][:, -1] - pred[:, -1]).mean())})
    regression.sort(key=lambda row: row['mae'])
    report = {'status': 'development_only', 'classification': classification, 'regression': regression,
              'chosenClassifier': classification[0]['candidate'], 'chosenRegressor': regression[0]['candidate'],
              'baselineSelection': score(selection['y'], selection['basePrediction'], selection['baseProbability'],
                                         base_model()['interval']['halfWidths'], .155)}
    save_pickle(WORK / 'developed.pkl', {'estimators': estimators, 'report': report, 'featureNames': FEATURES})
    write_json(OUT / 'development.json', report)
    print(json.dumps({'chosen': classification[0], 'regression': regression[0]}), flush=True)


def predictions(data, artifact):
    e, report = artifact['estimators'], artifact['report']
    x = data['x']
    prob = classifier_mix(e['hgbClassifier'].predict_proba(x)[:, 1], e['extraClassifier'].predict_proba(x)[:, 1],
                          data['baseProbability'], report['chosenClassifier'])
    pred = regression_mix(e['hgbResidual'].predict(x), e['extraResidual'].predict(x),
                          data['basePrediction'], report['chosenRegressor'])
    return pred, prob


def freeze():
    if (OUT / 'freeze.json').exists():
        raise RuntimeError('Experiment is already frozen.')
    p = json.loads((OUT / 'protocol.json').read_bytes())
    if p['experimentSourceSHA256'] != digest(__file__) or p['generatorSHA256'] != digest(ROOT / 'ml/generate.py'):
        raise RuntimeError('Protocol source changed after development.')
    artifact = load_pickle(WORK / 'developed.pkl')
    mapping_data = dataset('probability-calibration', SPLITS['probabilityCalibration'], ROUTINES)
    policy_data = dataset('policy-calibration', SPLITS['policyCalibration'], ROUTINES)
    _, map_prob = predictions(mapping_data, artifact)
    calibration = LogisticRegression(C=100, max_iter=1500).fit(logit(map_prob)[:, None], mapping_data['y'][:, -1] >= 180)
    pred, raw_prob = predictions(policy_data, artifact)
    probability = calibration.predict_proba(logit(raw_prob)[:, None])[:, 1]
    policy = choose_policy(policy_data['y'][:, -1] >= 180, probability,
                           policy_data['baseProbability'], policy_data['regimes'])
    widths = np.quantile(np.abs(policy_data['y'] - pred), .9, axis=0, method='higher')
    artifact.update(calibrator=calibration, policy=policy, widths=widths, baseModelSHA256=BASE_SHA,
                    protocolSHA256=digest(OUT / 'protocol.json'))
    save_pickle(WORK / 'frozen.pkl', artifact)
    record = {'at': timestamp(), 'finalPatientsGenerated': False, 'baseModelSHA256': BASE_SHA,
              'frozenEstimatorSHA256': digest(WORK / 'frozen.pkl'), 'protocolSHA256': artifact['protocolSHA256'],
              'generatorSHA256': p['generatorSHA256'], 'policy': policy, 'intervalHalfWidths': widths.tolist(),
              'calibration': {'method': 'Platt logistic on the logit of the selected probability mixture',
                              'slope': float(calibration.coef_[0, 0]), 'intercept': float(calibration.intercept_[0]),
                              'fitPatients': 48, 'policyPatients': 48},
              'artifactNote': 'Research estimator cache is local in work; not an active app model or a signed artifact.'}
    write_json(OUT / 'freeze.json', record)
    print(json.dumps(record), flush=True)


def paired_decisions(y, current, baseline, threshold, groups):
    rows = []
    for group in np.unique(groups):
        mask = groups == group
        a, b = count_errors(y, current, threshold, mask), count_errors(y, baseline, .155, mask)
        rows.append([a['fp'], a['fn'], a['tp'], b['fp'], b['fn'], b['tp']])
    rows = np.asarray(rows)
    rng = np.random.default_rng(SEED + 40007)
    draws = rows[rng.integers(0, len(rows), (2000, len(rows)))].sum(1)
    total = rows.sum(0)
    result = {}
    for key, a, b in [('falsePositiveWindows', 0, 3), ('falseNegativeWindows', 1, 4)]:
        result[key] = {'difference': int(total[a] - total[b]),
                       'patientBootstrap95CI': np.quantile(draws[:, a] - draws[:, b], [.025, .975]).tolist()}
    return result


def evaluate():
    lock = OUT / 'evaluation-lock.json'
    if lock.exists():
        raise RuntimeError('Final evaluation already started; no retuning or re-evaluation is allowed.')
    frozen = json.loads((OUT / 'freeze.json').read_bytes())
    p = json.loads((OUT / 'protocol.json').read_bytes())
    for actual, expected in [(digest(WORK / 'frozen.pkl'), frozen['frozenEstimatorSHA256']),
                             (digest(OUT / 'protocol.json'), frozen['protocolSHA256']),
                             (digest(ROOT / 'ml/generate.py'), frozen['generatorSHA256']),
                             (digest(__file__), p['experimentSourceSHA256'])]:
        if actual != expected:
            raise RuntimeError('Frozen artifact/protocol/source changed before final evaluation.')
    base = base_model()
    artifact = load_pickle(WORK / 'frozen.pkl')
    events = [{'event': 'estimator_calibrator_policy_and_intervals_frozen', 'at': frozen['at']},
              {'event': 'fresh_final_generation_started', 'at': timestamp()}]
    write_json(lock, {'events': events, 'finalIds': SPLITS['test']})
    data = dataset('final', SPLITS['test'], ROUTINES + [UNSEEN], allow_final=True)
    pred, raw = predictions(data, artifact)
    probability = artifact['calibrator'].predict_proba(logit(raw)[:, None])[:, 1]
    labels = data['y'][:, -1] >= 180
    threshold = artifact['policy']['threshold']
    def report(mask):
        current = score(data['y'][mask], pred[mask], probability[mask], artifact['widths'], threshold)
        previous = score(data['y'][mask], data['basePrediction'][mask], data['baseProbability'][mask], base['interval']['halfWidths'], .155)
        current['calibration'], previous['calibration'] = bins(labels[mask], probability[mask]), bins(labels[mask], data['baseProbability'][mask])
        current['threshold'], previous['threshold'] = threshold, .155
        return {'windows': int(mask.sum()), 'patients': int(len(np.unique(data['groups'][mask]))),
                'positiveWindows': int(labels[mask].sum()), 'v4': current, 'v3': previous,
                'pairedDecisionDifferences': paired_decisions(labels[mask], probability[mask],
                    data['baseProbability'][mask], threshold, data['groups'][mask])}
    primary = report(data['regimes'] < 6)
    cases = [{**routine, **report(data['regimes'] == ri)} for ri, routine in enumerate(ROUTINES + [UNSEEN])]
    gates = [primary, cases[5], cases[6]]
    lower = all(group['pairedDecisionDifferences'][key]['difference'] < 0
                for group in gates for key in ['falsePositiveWindows', 'falseNegativeWindows'])
    supported = all(primary['pairedDecisionDifferences'][key]['patientBootstrap95CI'][1] < 0
                    for key in ['falsePositiveWindows', 'falseNegativeWindows'])
    result = {'schemaVersion': 1, 'experimentVersion': p['experimentVersion'], 'syntheticOnly': True,
              'activeModelReplaced': False, 'baseModelSHA256': BASE_SHA,
              'frozenEstimatorSHA256': frozen['frozenEstimatorSHA256'], 'protocol': p,
              'primary': primary, 'cases': cases,
              'promotionGate': {'passed': lower and supported, 'bothCountsLowerInPrimaryVariableAndHeldOut': lower,
                                'bothPrimaryCountIntervalsBelowZero': supported,
                                'automaticPromotion': False},
              'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__},
              'limitations': p['limitations'] + ['This experiment does not modify or validate the open-research model.',
                  'No clinical or real-device robustness claim follows from these synthetic results.',
                  'Changing an alert policy alone is not considered a successful new model.']}
    events.append({'event': 'final_evaluation_completed', 'at': timestamp()})
    write_json(OUT / 'results.json', result)
    write_json(OUT / 'audit.json', {'events': events, 'freeze': frozen})
    for case in [{'id': 'primary', **primary}] + cases:
        print(case['id'], json.dumps({name: {k: case[name][k] for k in ['mae', 'recall', 'precision', 'auroc', 'averagePrecision', 'confusionMatrix']} for name in ['v3', 'v4']}), flush=True)
    print('Promotion gate:', result['promotionGate'], flush=True)


def main():
    global WORK, OUT, BASE_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['develop', 'freeze', 'evaluate'], required=True)
    parser.add_argument('--work-dir', type=Path, default=WORK)
    parser.add_argument('--output-dir', type=Path, default=OUT)
    parser.add_argument('--base-model', type=Path, default=BASE_PATH)
    args = parser.parse_args()
    WORK, OUT, BASE_PATH = args.work_dir, args.output_dir, args.base_model
    {'develop': develop, 'freeze': freeze, 'evaluate': evaluate}[args.phase]()


if __name__ == '__main__':
    main()

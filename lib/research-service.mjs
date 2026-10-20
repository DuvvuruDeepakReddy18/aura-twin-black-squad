import {createHash, randomUUID} from 'node:crypto';
import {hashCanonicalJson} from './challenge.mjs';
import {ResearchError, selectCursor, prefixAt, qualityAt, personalBaseline, inputsAt, perturbResearch, RESEARCH_MODES} from './research-data.mjs';

const finite = value => typeof value === 'number' && Number.isFinite(value);
const round = value => Math.round(value * 1000) / 1000;
const HORIZONS = [30, 60, 90, 120];
const DISCLAIMERS = [
  'Research prototype — not for diagnosis or treatment.',
  'Recorded, date-shifted wearable data and arbitrarily paired synthetic EHR are different people. This composite is not a linked longitudinal patient record.',
  'This audit describes one recorded window; it does not establish cohort performance.',
  'Input and model SHA-256 hashes identify bytes. They are not signatures or independent timestamping. The public research dataset is not secret.',
];
const only = (body, keys) => {
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw new ResearchError('Request must be a JSON object.');
  const extra = Object.keys(body).find(key => !keys.includes(key));
  if (extra) throw new ResearchError(`Unknown input: ${extra}.`);
};

/** Participant and model are supplied by the frozen artifact loader, never by an HTTP client. */
export function createResearchService({patients, truth, model, modelBytes, metrics, provenance, manifest, runtime, ablationRuntimes = {}, sessionCodec, now = Date.now}) {
  const registered = new Map(patients.map(patient => [patient.id, patient]));
  const modelSHA256 = createHash('sha256').update(modelBytes).digest('hex');
  const sessions = new Map();
  const summaryCache = new Map();
  if (!truth || patients.some(patient => !Array.isArray(truth[patient.sourceParticipantId]))) {
    throw new Error('Exact recorded CGM outcomes must be bundled separately from model inputs.');
  }
  function patientFor(id) {
    if (typeof id !== 'string' || !registered.has(id)) throw new ResearchError('Research participant not found.', 404);
    return registered.get(id);
  }
  function predictPatient(patient, cursor) {
    // The runtime never receives future rows, even if its own feature code changes.
    const prefix = prefixAt(patient, cursor);
    const result = runtime.infer(prefix, cursor);
    const abstained = result.abstained ?? result.available === false;
    const threshold = result.riskThreshold ?? result.alert?.threshold ?? null;
    const alert = typeof result.alert === 'object' ? result.alert : {triggered: Boolean(result.alert), threshold,
      label: abstained ? 'Forecast unavailable' : result.alert ? 'Review suggested' : 'Below review threshold'};
    return {...result, alert, patientId: patient.id, cursor, abstained, available: !abstained,
      modelVersion: model.modelVersion, modelSHA256, inputTimestamp: prefix.series.at(-1).timestamp,
      dataQuality: qualityAt(prefix, cursor), baseline: personalBaseline(prefix, cursor),
      researchPrototype: true, replay: true};
  }
  function predict(body) {
    only(body, ['patientId', 'cursor']);
    const patient = patientFor(body.patientId), cursor = selectCursor(patient, body.cursor);
    return predictPatient(patient, cursor);
  }
  function summary(patient, requestedCursor) {
    const cursor = selectCursor(patient, requestedCursor), cacheKey = `${patient.id}:${cursor}`;
    if (summaryCache.has(cacheKey)) return summaryCache.get(cacheKey);
    const prediction = predictPatient(patient, cursor);
    const prefix = prefixAt(patient, cursor);
    const latest = Object.fromEntries(['glucose', 'hr', 'hrv'].map(key => {
      const row = [...prefix.series].reverse().find(p => finite(p[key]));
      const timestamp = row ? (key === 'glucose' ? row.sourceTimestamp ?? row.timestamp : row.timestamp) : null;
      return [key, row ? {value: row[key], timestamp, alignedTimestamp: row.timestamp,
        carriedForward: key === 'glucose' && Date.parse(timestamp) < Date.parse(row.timestamp),
        minutesSinceObservation: (Date.parse(prefix.series.at(-1).timestamp) - Date.parse(timestamp)) / 60000}
        : {value: null, timestamp: null, alignedTimestamp: null, carriedForward: false, minutesSinceObservation: null}];
    }));
    const threshold = prediction.riskThreshold ?? prediction.alert?.threshold ?? null;
    const state = prediction.abstained ? 'Forecast unavailable' : prediction.dataQuality.status === 'poor' ? 'Data gap'
      : finite(prediction.risk) && finite(threshold) && prediction.risk >= threshold ? 'Review'
        : prediction.dataQuality.status !== 'good' ? 'Attention' : 'Stable';
    const value = {id: patient.id, name: patient.name ?? `Research participant ${patient.sourceParticipantId ?? patient.id}`,
      sourceParticipantId: patient.sourceParticipantId, defaultCursor: selectCursor(patient), cursor, seriesLength: patient.series.length,
      firstObservation: patient.series[0]?.timestamp, lastObservation: patient.series.at(-1)?.timestamp,
      replayTimestamp: prefix.series.at(-1).timestamp, latest, state, prediction, ehr: patient.ehr, researchContext: patient.researchContext,
      provenance: patient.provenance ?? provenance, sparkline: prefix.series.slice(-72).map(row => ({timestamp: row.timestamp, glucose: row.glucose}))};
    if (summaryCache.size >= 128) summaryCache.delete(summaryCache.keys().next().value);
    summaryCache.set(cacheKey, value);
    return value;
  }
  function list() {
    const summaries = patients.map(patient => summary(patient));
    return {patients: summaries, datasetVersion: model.datasetVersion ?? provenance.datasetVersion, modelVersion: model.modelVersion,
      counts: {participants: summaries.length, review: summaries.filter(p => p.state === 'Review').length,
        forecastsAvailable: summaries.filter(p => !p.prediction.abstained).length,
        streamsGood: summaries.filter(p => p.prediction.dataQuality.status === 'good').length},
      mode: 'Research replay', disclaimer: DISCLAIMERS[0]};
  }
  function scenario(body) {
    only(body, ['patientId', 'cursor', 'scenario']);
    const patient = patientFor(body.patientId), cursor = selectCursor(patient, body.cursor);
    const specification = body.scenario ?? {};
    only(specification, ['glucoseOffset', 'hrOffset']);
    for (const value of Object.values(specification)) if (!finite(value) || Math.abs(value) > 20) {
      throw new ResearchError('Observed-input offsets must be finite numbers between −20 and +20.');
    }
    const changed = structuredClone(prefixAt(patient, cursor));
    for (const row of changed.series.slice(-12)) {
      if (finite(row.glucose)) row.glucose += specification.glucoseOffset ?? 0;
      if (finite(row.hr)) row.hr += specification.hrOffset ?? 0;
    }
    return {baseline: predictPatient(patient, cursor), scenario: predictPatient(changed, cursor), specification,
      label: 'Model sensitivity to altered recent observations',
      uncertaintyValidated: false,
      note: 'The last 60 minutes of recorded CGM/HR inputs are shifted and the same trained model is rerun. This is an artificial input sensitivity test, not a meal, activity, treatment, or causal prediction. Scenario interval coverage has not been evaluated.'};
  }
  function ablation(body) {
    only(body, ['patientId', 'cursor']);
    const patient = patientFor(body.patientId), cursor = selectCursor(patient, body.cursor);
    const prefix = prefixAt(patient, cursor);
    return {patientId: patient.id, cursor, timestamp: prefix.series.at(-1).timestamp, primaryFamily: model.primaryFamily,
      models: Object.fromEntries(Object.entries(ablationRuntimes).map(([family, candidate]) => [family, {
        ...candidate.infer(prefix, cursor), family, label: candidate.artifact.familyLabel,
        selectedPrimary: family === model.primaryFamily,
      }])),
      note: 'Every model receives the same available-time observations. Unmatched synthetic EHR is a negative control, not linked clinical history. These are individual-window outputs; held-out accuracy is reported separately.'};
  }
  function truthAt(patient, cursor) {
    const timestamp = Date.parse(patient.series[cursor].timestamp);
    const tolerance = (model.targetTimestampToleranceSeconds ?? 150) * 1000;
    return HORIZONS.map(minutes => {
      const target = timestamp + minutes * 60000;
      let best = null, distance = Infinity;
      for (const row of truth[patient.sourceParticipantId]) {
        if (Date.parse(row.timestamp) <= timestamp) continue;
        const gap = Math.abs(Date.parse(row.timestamp) - target);
        if (finite(row.glucose) && gap <= tolerance && gap < distance) { best = row; distance = gap; }
      }
      return {minutes, timestamp: new Date(target).toISOString(), observedTimestamp: best?.timestamp ?? null,
        observed: best?.glucose ?? null, targetToleranceSeconds: tolerance / 1000};
    });
  }
  function freeze(body) {
    only(body, ['patientId', 'cursor', 'mode']);
    const patient = patientFor(body.patientId), cursor = selectCursor(patient, body.cursor), mode = body.mode ?? 'baseline';
    const {patient: changed, perturbation} = perturbResearch(patient, cursor, mode);
    const prediction = predictPatient(changed, cursor);
    const baseline = mode === 'baseline' ? prediction : predictPatient(patient, cursor);
    const time = now();
    const receipt = {schemaVersion: 2, dataKind: 'open-research-composite', patientId: patient.id, cursor,
      cutoffTimestamp: changed.series.at(-1).timestamp, modelVersion: model.modelVersion, modelSHA256,
      inputSHA256: hashCanonicalJson({patientId: patient.id, ehr: changed.ehr ?? null, researchContext: changed.researchContext ?? null, series: changed.series}),
      hashEncoding: {model: 'raw-file-bytes', input: 'canonical-json-sorted-keys-v1'},
      createdAt: new Date(time).toISOString(), expiresAt: new Date(time + 3600000).toISOString(),
      targetDefinition: prediction.contract?.target ?? model.targetDefinition ?? null,
      latestUsedTimestamp: changed.series.at(-1).timestamp,
      limitations: DISCLAIMERS};
    const result = {challengeId: randomUUID(), mode, modeLabel: RESEARCH_MODES.find(item => item.id === mode)?.label,
      perturbation, prediction, baseline, receipt, inputWindow: changed.series.slice(-25)};
    // Consult outcomes only after both predictions are fixed.
    const truth = truthAt(patient, cursor);
    result.revealAvailable = truth.some(row => finite(row.observed));
    const entry = {kind: 'research-v1', result, truth, expires: time + 3600000};
    if (sessionCodec) return {...result, challengeToken: sessionCodec.seal(entry)};
    for (const [id, saved] of sessions) if (saved.expires <= time) sessions.delete(id);
    while (sessions.size >= 128) sessions.delete(sessions.keys().next().value);
    sessions.set(result.challengeId, entry);
    return structuredClone(result);
  }
  function reveal(body) {
    only(body, ['challengeId', 'challengeToken']);
    if (typeof body.challengeId !== 'string' || !/^[0-9a-f-]{36}$/i.test(body.challengeId)) throw new ResearchError('A frozen challenge ID is required.');
    let entry;
    if (sessionCodec) {
      try { entry = sessionCodec.open(body.challengeToken); } catch { throw new ResearchError('Invalid frozen research token. Freeze a new prediction.'); }
    } else entry = sessions.get(body.challengeId);
    if (!entry || entry.kind !== 'research-v1' || entry.result?.challengeId !== body.challengeId) throw new ResearchError('Frozen research prediction not found.', 404);
    if (entry.expires <= now()) throw new ResearchError('Frozen research prediction expired.', 410);
    if (entry.result.receipt.modelSHA256 !== modelSHA256) throw new ResearchError('Model changed after this prediction was frozen.', 409);
    const prediction = entry.result.prediction;
    const comparisons = prediction.abstained ? [] : entry.truth.flatMap(row => {
      const forecast = prediction.forecast.find(point => point.minutes === row.minutes);
      if (!forecast || !finite(row.observed)) return [];
      const persistence = prediction.current?.glucose;
      return [{...row, predicted: forecast.glucose ?? forecast.value, lower: forecast.lower ?? forecast.low, upper: forecast.upper ?? forecast.high,
        absoluteError: round(Math.abs((forecast.glucose ?? forecast.value) - row.observed)),
        covered: row.observed >= (forecast.lower ?? forecast.low) && row.observed <= (forecast.upper ?? forecast.high),
        persistence: finite(persistence) ? persistence : null,
        persistenceAbsoluteError: finite(persistence) ? round(Math.abs(persistence - row.observed)) : null}];
    });
    const baseline = entry.result.baseline;
    const target = baseline.eventDefinition ?? baseline.contract?.target ?? model.target;
    const eventTruth = entry.truth.find(row => row.minutes === (target?.horizonMinutes ?? 120));
    const referenceGlucose = baseline.current?.glucose;
    const modelInputReferenceGlucose = prediction.current?.glucose;
    const supportedTarget = target?.kind === 'rise' || target?.kind === 'absolute';
    let event = null;
    if (!prediction.abstained && !baseline.abstained && supportedTarget && finite(target.threshold)
      && finite(eventTruth?.observed) && (target.kind !== 'rise' || finite(referenceGlucose))) {
      const outcome = target.kind === 'rise' ? eventTruth.observed - referenceGlucose >= target.threshold
        : eventTruth.observed >= target.threshold;
      event = {risk: baseline.risk, riskSource: 'Frozen unmodified baseline prediction', outcome,
        threshold: baseline.riskThreshold, alert: baseline.alert?.triggered ?? null,
        targetDefinition: target, minutes: eventTruth.minutes, observed: eventTruth.observed,
        targetTimestamp: eventTruth.timestamp, observedTimestamp: eventTruth.observedTimestamp,
        referenceGlucose, referenceSourceTimestamp: baseline.current?.sourceTimestamp ?? null,
        observedChange: finite(referenceGlucose) ? eventTruth.observed - referenceGlucose : null,
        perturbedRisk: prediction.risk, modelInputReferenceGlucose,
        perturbedReferenceOutcome: target.kind === 'rise'
          ? finite(modelInputReferenceGlucose) ? eventTruth.observed - modelInputReferenceGlucose >= target.threshold : null
          : outcome,
        note: 'The recorded event uses the unmodified baseline current glucose as its fixed rise reference. The altered-input probability remains frozen separately; changing current glucose also changes the rise reference understood by that model input. Neither one outcome nor an artificial perturbation establishes calibration.'};
    }
    return {challengeId: body.challengeId, mode: entry.result.mode, receipt: entry.result.receipt, abstained: prediction.abstained,
      status: prediction.abstained ? 'abstained' : comparisons.length ? 'revealed' : 'future_unavailable',
      comparisons, event, summary: {availableHorizons: comparisons.length,
        mae: comparisons.length ? round(comparisons.reduce((sum, row) => sum + row.absoluteError, 0) / comparisons.length) : null,
        persistenceMae: comparisons.length && comparisons.every(row => finite(row.persistenceAbsoluteError))
          ? round(comparisons.reduce((sum, row) => sum + row.persistenceAbsoluteError, 0) / comparisons.length) : null,
        intervalCoverage: comparisons.length ? comparisons.filter(row => row.covered).length / comparisons.length : null},
      limitations: DISCLAIMERS, comparisonNote: 'Frozen prediction compared with recorded future observations; no inference is rerun during reveal. Persistence uses the same possibly altered current glucose available to the frozen forecast. Event outcome separately uses the unmodified baseline current glucose as its fixed reference.'};
  }
  function patientRoute(id, action, query) {
    const patient = patientFor(id);
    const raw = query.get('cursor');
    const cursor = selectCursor(patient, raw === null ? undefined : Number(raw));
    switch (action) {
      case undefined: return patient;
      case 'summary': return summary(patient, cursor);
      case 'quality': case 'data-quality': return qualityAt(patient, cursor);
      case 'baseline': return personalBaseline(patient, cursor);
      case 'inputs': return {...inputsAt(patient, cursor, model.inputHistoryMinutes ?? 360),
        usedFeatureNames: model.featureNames ?? [], inputSources: model.inputSources ?? [],
        syntheticEhrUsed: (model.featureNames ?? []).some(name => name.startsWith('synthetic')),
        matchedResearchContextUsed: (model.featureNames ?? []).some(name => name.startsWith('research')),
        matchedContextTimingAssumption: patient.researchContext?.timingAssumption ?? null};
      case 'timeline': case 'signals': case 'replay': {
        const hours = Number(query.get('hours') ?? 24);
        if (![24, 168, 720].includes(hours)) throw new ResearchError('Time range must be 24, 168, or 720 hours.');
        const prefix = prefixAt(patient, cursor), end = Date.parse(prefix.series.at(-1).timestamp);
        return {patientId: id, timestamp: prefix.series.at(-1).timestamp, requestedHours: hours,
          availableHours: Math.min(hours, (end - Date.parse(prefix.series[0].timestamp)) / 3600000),
          series: prefix.series.filter(row => Date.parse(row.timestamp) > end - hours * 3600000),
          note: 'Recorded observations only. A longer selected range does not create additional history.'};
      }
      default: throw new ResearchError('Research endpoint not found.', 404);
    }
  }
  return {list, predict, scenario, ablation, freeze, reveal, patientRoute, metrics, provenance, manifest,
    modes: () => ({modes: RESEARCH_MODES}), modelSHA256,
    card: () => ({...model.card, modelVersion: model.modelVersion, modelSHA256, targetDefinition: model.targetDefinition,
      inputHistoryMinutes: model.inputHistoryMinutes, featureNames: model.featureNames,
      modelKind: model.modelKind, primaryFamily: model.primaryFamily, familyLabel: model.familyLabel,
      target: model.target, inputSources: model.inputSources, split: model.split, alertPolicy: model.alertPolicy,
      intendedUse: 'Reproducible research forecasting and recorded replay.',
      outOfScope: 'Diagnosis, treatment, autonomous monitoring, causal treatment decisions, and claims of clinical validation.',
      limitations: [...DISCLAIMERS, ...(model.limitations ?? [])]}),
    health: () => ({status: 'ok', name: 'AURA Twin', mode: 'research-replay', synthetic: false, composite: true,
      modelVersion: model.modelVersion, modelSHA256, participants: patients.length})};
}

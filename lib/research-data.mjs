const finite = value => typeof value === 'number' && Number.isFinite(value);
const mean = values => values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
const round = value => value === null ? null : Math.round(value * 1000) / 1000;
export const RESEARCH_CHANNELS = Object.freeze([
  {key: 'glucose', label: 'Interstitial glucose', unit: 'mg/dL', provenance: 'OPEN RESEARCH DATA', minimum: 40, maximum: 400},
  {key: 'hr', label: 'Heart rate', unit: 'bpm', provenance: 'OPEN RESEARCH DATA', minimum: 30, maximum: 220},
  {key: 'hrv', label: 'IBI-derived RMSSD', unit: 'ms', provenance: 'DERIVED FEATURE', minimum: 0, maximum: 500},
]);
export class ResearchError extends Error {
  constructor(message, status = 400) { super(message); this.status = status; }
}
export function selectCursor(patient, requested) {
  const cursor = requested ?? patient.defaultCursor ?? patient.series.length - 1;
  if (!Number.isInteger(cursor) || cursor < 0 || cursor >= patient.series.length) {
    throw new ResearchError('Cursor must be an integer within this participant’s recorded series.');
  }
  return cursor;
}
export function prefixAt(patient, cursor) {
  selectCursor(patient, cursor);
  const cutoff = Date.parse(patient.series[cursor].timestamp);
  if (!Number.isFinite(cutoff)) throw new ResearchError('Invalid prediction timestamp.');
  const series = patient.series.slice(0, cursor + 1);
  if (series.some((row, index) => !Number.isFinite(Date.parse(row.timestamp))
    || Date.parse(row.timestamp) > cutoff || (index > 0 && Date.parse(row.timestamp) <= Date.parse(series[index - 1].timestamp)))) {
    throw new ResearchError('Research input timestamps must be valid, unique, increasing, and no later than prediction time.');
  }
  return {...patient, series};
}
export function qualityAt(patient, cursor) {
  const prefix = prefixAt(patient, cursor);
  const now = Date.parse(prefix.series.at(-1).timestamp);
  const recent = prefix.series.filter(row => Date.parse(row.timestamp) > now - 120 * 60000);
  const expected = 24;
  const streams = RESEARCH_CHANNELS.map(channel => {
    const valid = recent.filter(row => finite(row[channel.key]));
    const latest = [...prefix.series].reverse().find(row => finite(row[channel.key]));
    const outliers = valid.filter(row => row[channel.key] < channel.minimum || row[channel.key] > channel.maximum);
    const latestTime = latest ? (channel.key === 'glucose' ? latest.sourceTimestamp ?? latest.timestamp : latest.timestamp) : null;
    const minutesSinceObservation = latestTime ? (now - Date.parse(latestTime)) / 60000 : null;
    const coverage = Math.min(1, valid.length / expected);
    const sourceObservationCount = channel.key === 'glucose'
      ? new Set(valid.map(row => row.sourceTimestamp ?? row.timestamp)).size : null;
    return {...channel, observed: valid.length, expected, coverage: round(coverage), missingness: round(1 - coverage),
      observationSemantics: 'Available aligned grid values; not independent raw sample counts.',
      sourceObservationCount,
      latestObservation: latestTime, minutesSinceObservation, outliers: outliers.length,
      status: !latest ? 'unavailable' : outliers.length || minutesSinceObservation > (channel.key === 'glucose' ? 15 : 60) ? 'poor'
        : coverage < .8 ? 'reduced' : 'good'};
  });
  return {windowMinutes: 120, timestamp: prefix.series.at(-1).timestamp, streams,
    unavailable: ['Sleep-stage data unavailable in the selected research source.', 'Activity and step measurements are not included in this processed subset.'],
    note: 'Coverage counts finite aligned values against a 5-minute grid, including CGM carried forward from sufficiently recent source observations. SourceObservationCount counts distinct CGM source timestamps. Recency is relative to replay time. Range checks are data plausibility checks, not clinical diagnoses.',
    status: streams[0].status === 'poor' || streams[0].status === 'unavailable' ? 'poor' : streams.some(s => s.status !== 'good') ? 'reduced' : 'good'};
}
export function personalBaseline(patient, cursor) {
  const prefix = prefixAt(patient, cursor);
  const now = Date.parse(prefix.series.at(-1).timestamp);
  const baselineRows = prefix.series.filter(row => Date.parse(row.timestamp) > now - 24 * 60 * 60000 && Date.parse(row.timestamp) <= now - 120 * 60000);
  const recentRows = prefix.series.filter(row => Date.parse(row.timestamp) > now - 120 * 60000);
  return {method: 'Recent two-hour mean versus preceding available history, up to 24 hours. No future observations used.',
    timestamp: prefix.series.at(-1).timestamp,
    values: RESEARCH_CHANNELS.map(channel => {
      const previous = baselineRows.map(row => row[channel.key]).filter(finite);
      const current = recentRows.map(row => row[channel.key]).filter(finite);
      const baseline = mean(previous), recent = mean(current);
      return {key: channel.key, label: channel.label, unit: channel.unit, provenance: 'DERIVED FEATURE',
        baseline: round(baseline), current: round(recent), delta: baseline !== null && recent !== null ? round(recent - baseline) : null,
        baselineObservations: previous.length, currentObservations: current.length};
    })};
}
export function inputsAt(patient, cursor, windowMinutes = 1440) {
  const prefix = prefixAt(patient, cursor);
  const timestamp = prefix.series.at(-1).timestamp;
  const start = Date.parse(timestamp) - windowMinutes * 60000;
  // CGM lag360 and inclusive window summaries use the t−360 endpoint.
  const rows = prefix.series.filter(row => Date.parse(row.timestamp) >= start);
  const preprocessingContext = prefix.series.filter(row => Date.parse(row.timestamp) >= start - 15 * 60000
    && Date.parse(row.timestamp) < start);
  return {patientId: patient.id, timestamp, windowMinutes, latestUsedTimestamp: timestamp,
    futureObservationsUsed: false, observations: rows, preprocessingContext,
    researchContext: patient.researchContext ?? null, ehr: patient.ehr ?? null,
    ehrNote: 'Synthetic EHR context belongs to a different generated person. Pairing is arbitrary; it is not a linked clinical record.',
    note: 'Observations include both endpoints of the feature window. PreprocessingContext provides up to 15 additional past minutes for causal CGM carry-forward at the window start. These are aligned recorded values, not independent raw samples. Actual feature and context inclusion is specified by usedFeatureNames and the model card.'};
}
export function perturbResearch(patient, cursor, mode) {
  const copy = structuredClone(prefixAt(patient, cursor));
  const start = Math.max(0, copy.series.length - 24);
  const changed = [];
  const hide = (channel, count) => {
    for (let i = Math.max(0, copy.series.length - count); i < copy.series.length; i++) {
      if (finite(copy.series[i][channel])) changed.push({timestamp: copy.series[i].timestamp, channel});
      copy.series[i][channel] = null;
    }
  };
  switch (mode) {
    case 'baseline': break;
    case 'short_gap': hide('glucose', 2); break;
    case 'cgm_dropout': hide('glucose', 6); break;
    case 'sensor_dropout':
      for (const channel of ['glucose', 'hr', 'hrv']) hide(channel, 24);
      break;
    case 'missing_hrv': hide('hrv', 24); break;
    case 'delayed_signal': {
      const original = structuredClone(copy.series);
      for (let i = start; i < copy.series.length; i++) {
        copy.series[i].glucose = i >= 3 ? original[i - 3].glucose : null;
        changed.push({timestamp: copy.series[i].timestamp, channel: 'glucose'});
      }
      break;
    }
    case 'noise':
    case 'cgm_bias':
    case 'outlier':
      for (let i = mode === 'outlier' ? copy.series.length - 1 : start; i < copy.series.length; i++) {
        if (!finite(copy.series[i].glucose)) continue;
        copy.series[i].glucose += mode === 'outlier' ? 500 : mode === 'cgm_bias' ? 30 : (i % 2 ? -12 : 12);
        changed.push({timestamp: copy.series[i].timestamp, channel: 'glucose'});
      }
      break;
    default: throw new ResearchError('Unknown research perturbation.');
  }
  return {patient: copy, perturbation: {mode, description: RESEARCH_MODES.find(item => item.id === mode)?.description, changedPoints: changed.length,
    note: 'Deterministic, artificial alteration of recorded inputs. Future observations remain unchanged. This selected-window experiment is not an aggregate robustness estimate.'}};
}
export const RESEARCH_MODES = [
  {id: 'baseline', label: 'Recorded stream', description: 'Use the recorded aligned inputs without an artificial alteration.'},
  {id: 'short_gap', label: '10-minute CGM gap', description: 'Hide the latest two five-minute CGM grid values. Only sufficiently recent past measurements may be carried forward.'},
  {id: 'cgm_dropout', label: '30-minute CGM gap', description: 'Hide the latest six CGM grid values and inspect the freshness-based abstention.'},
  {id: 'sensor_dropout', label: 'Sensor dropout', description: 'Hide CGM, HR and HRV for the last two hours.'},
  {id: 'delayed_signal', label: 'CGM values delayed 15 minutes', description: 'Replace the last two hours of glucose values with values from 15 minutes earlier, retaining the reported timestamps to simulate an unrecognized delay.'},
  {id: 'noise', label: 'Alternating ±12 mg/dL noise', description: 'Add a deterministic alternating error to the last two hours of glucose. This is an artificial noise pattern.'},
  {id: 'missing_hrv', label: 'Missing recent HRV', description: 'Remove the last two hours of derived RMSSD values.'},
  {id: 'cgm_bias', label: '+30 mg/dL sensor drift', description: 'Offset the last two hours of glucose by 30 mg/dL. Plausible bias can pass range checks.'},
  {id: 'outlier', label: 'Latest CGM outlier', description: 'Add 500 mg/dL to the latest available glucose value to test the input-range gate.'},
];

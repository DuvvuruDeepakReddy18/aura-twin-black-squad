/** Post-freeze audit: no fitting, calibration, threshold selection, or simulator. */
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createResearchModel} from '../lib/research-model.mjs';
import {perturbResearch} from '../lib/research-data.mjs';

const root = new URL('../', import.meta.url);
const bytes = await readFile(new URL('data/research-model.json', root));
const model = JSON.parse(bytes);
const modelSHA256 = createHash('sha256').update(bytes).digest('hex');
const patients = JSON.parse(await readFile(new URL('data/research-patients.json', root)));
const truthByParticipant = JSON.parse(await readFile(new URL('data/research-truth.json', root)));
const protocol = JSON.parse(await readFile(new URL('data/research-protocol.json', root)));
const testIds = new Set(protocol.splits.test);
const final = patients.filter(patient => testIds.has(patient.sourceParticipantId));
if (final.length !== testIds.size) throw Error('All declared final participants must be present for the audit.');
const runtime = createResearchModel(model);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const stats = rows => {
  const eligible = rows.filter(row => finite(row.error));
  return {windows: rows.length, forecastAvailable: eligible.length, withheld: rows.length - eligible.length,
    forecastAvailability: rows.length ? eligible.length / rows.length : null,
    maeOnAvailable: eligible.length ? eligible.reduce((s, row) => s + row.error, 0) / eligible.length : null,
    intervalCoverageOnAvailable: eligible.length ? eligible.filter(row => row.covered).length / eligible.length : null,
    meanWidthOnAvailable: eligible.length ? eligible.reduce((s, row) => s + row.width, 0) / eligible.length : null};
};
const modes = ['baseline', 'short_gap', 'cgm_dropout', 'sensor_dropout', 'missing_hrv', 'delayed_signal', 'noise', 'cgm_bias', 'outlier'];
const records = Object.fromEntries(modes.map(mode => [mode, []]));
let leakageChecks = 0;
for (const patient of final) {
  const indexed = patient.series.map(row => ({...row, time: Date.parse(row.timestamp)}));
  const actual = truthByParticipant[patient.sourceParticipantId].map(row => ({...row, time: Date.parse(row.timestamp)}));
  let participantLeakageChecks = 0;
  // Lower-cost 60-minute audit grid, separate from the primary evaluation grid.
  for (let cursor = 72; cursor < indexed.length - 24; cursor += 12) {
    const targetTime = indexed[cursor].time + 120 * 60000;
    const truth = actual.filter(row => row.time > indexed[cursor].time && finite(row.glucose)
      && Math.abs(row.time - targetTime) <= 150000)
      .sort((a, b) => Math.abs(a.time - targetTime) - Math.abs(b.time - targetTime))[0];
    if (!truth) continue;
    if (participantLeakageChecks < 5) {
      const full = runtime.infer(patient, cursor);
      const prefix = runtime.infer({...patient, series: patient.series.slice(0, cursor + 1)}, cursor);
      if (JSON.stringify(full) !== JSON.stringify(prefix)) throw Error(`Future access detected for ${patient.id}/${cursor}`);
      leakageChecks++;
      participantLeakageChecks++;
    }
    for (const mode of modes) {
      const changed = perturbResearch(patient, cursor, mode);
      const prediction = runtime.infer(changed.patient, cursor);
      const point = prediction.available ? prediction.forecast.find(row => row.minutes === 120) : null;
      records[mode].push({participant: patient.sourceParticipantId, cursor,
        error: point ? Math.abs(point.glucose - truth.glucose) : null,
        covered: point ? truth.glucose >= point.lower && truth.glucose <= point.upper : null,
        width: point ? point.upper - point.lower : null, quality: prediction.quality.status});
    }
  }
  console.log(`Audited recorded participant ${patient.sourceParticipantId}`);
}
const report = {
  auditVersion: 'research-runtime-1.0.0', evaluatedAt: new Date().toISOString(), modelVersion: model.modelVersion, modelSHA256,
  participants: final.map(patient => patient.sourceParticipantId), strideMinutes: 60, target: 'Recorded glucose at +120 minutes, within ±150 seconds.',
  leakageAudit: {status: 'passed', fullHistoryVsPhysicalPrefixChecks: leakageChecks,
    scope: 'Outputs match for full recorded history versus physically truncated inputs on audited final windows. Additional automated tests cover changed future values.'},
  cases: modes.map(mode => ({mode, ...stats(records[mode]), byParticipant: final.map(patient => ({
    participant: patient.sourceParticipantId, ...stats(records[mode].filter(row => row.participant === patient.sourceParticipantId)),
  }))})),
  limitations: [
    'This post-freeze perturbation audit never fits or changes the model. It uses a separate 60-minute grid and must not replace the primary test metrics.',
    'All modes retain the same target windows. Withheld predictions count in availability, not as successful forecasts. Conditional errors among available forecasts have a different denominator when abstention changes.',
    'Perturbations are artificial sensor faults applied to real recorded inputs; they are not new real-device cohorts.',
    'Prediction intervals are unchanged calibration bands. Their empirical coverage under each perturbation is measured here, not guaranteed.',
    'Only three test participants. No clinical validation or unseen population generalization is established.',
  ],
};
await writeFile(new URL('data/research-runtime-audit.json', root), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({modelSHA256, leakageChecks, cases: report.cases.map(({byParticipant, ...rest}) => rest)}, null, 2));

/** Reproduce recorded-data receipts locally. No account, token, or network is required. */
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {createResearchModel} from '../lib/research-model.mjs';
import {createResearchService} from '../lib/research-service.mjs';

export function verifyResearchReceipt(payload, {patients, truth, modelBytes, runtime}) {
  if (payload?.schemaVersion !== 2 || payload.challenge?.receipt?.dataKind !== 'open-research-composite') {
    throw Error('Expected a version 2 research receipt export.');
  }
  const supplied = payload.challenge, receipt = supplied.receipt;
  const model = JSON.parse(modelBytes.toString('utf8'));
  const modelSHA256 = createHash('sha256').update(modelBytes).digest('hex');
  if (receipt.modelSHA256 !== modelSHA256) throw Error('Model fingerprint differs. Use the research-model.json bundled with this receipt.');
  const patient = patients.find(row => row.id === receipt.patientId);
  if (!patient) throw Error('The receipt participant is not in the packaged research cohort.');
  if (!Number.isInteger(receipt.cursor) || patient.series[receipt.cursor]?.timestamp !== receipt.cutoffTimestamp) {
    throw Error('Receipt cursor and recorded cutoff differ.');
  }
  const service = createResearchService({patients, truth, model, modelBytes, metrics: {}, provenance: {}, manifest: {},
    runtime: runtime ?? createResearchModel(model)});
  const reproduced = service.freeze({patientId: patient.id, cursor: receipt.cursor, mode: supplied.mode});
  for (const key of ['schemaVersion', 'dataKind', 'patientId', 'cursor', 'cutoffTimestamp', 'modelVersion', 'modelSHA256',
    'inputSHA256', 'hashEncoding', 'targetDefinition', 'latestUsedTimestamp']) {
    if (!isDeepStrictEqual(receipt[key], reproduced.receipt[key])) throw Error(`Receipt ${key} does not reproduce.`);
  }
  for (const key of ['mode', 'modeLabel', 'prediction', 'baseline', 'perturbation', 'inputWindow', 'revealAvailable']) {
    if (!isDeepStrictEqual(supplied[key], reproduced[key])) throw Error(`Frozen ${key} differs from the offline calculation.`);
  }
  if (payload.reveal != null) {
    if (payload.reveal.challengeId !== supplied.challengeId || !isDeepStrictEqual(payload.reveal.receipt, receipt)) {
      throw Error('Revealed outcome belongs to a different frozen receipt.');
    }
    const revealed = service.reveal({challengeId: reproduced.challengeId});
    for (const key of ['mode', 'abstained', 'status', 'comparisons', 'event', 'summary']) {
      if (!isDeepStrictEqual(payload.reveal[key], revealed[key])) throw Error(`Revealed ${key} differs from the exact recorded outcomes.`);
    }
  }
  return {verified: true, patientId: patient.id, cutoffTimestamp: receipt.cutoffTimestamp, mode: supplied.mode,
    modelSHA256, revealVerified: payload.reveal != null,
    note: 'Reproduces inputs, forecasts and any recorded outcomes. Does not authenticate the author or creation time, hide public future data, or establish clinical accuracy.'};
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    if (!process.argv[2]) throw Error('Usage: node scripts/verify_research_receipt.mjs "path/to/AURA-research-receipt.json"');
    const bytes = readFileSync(resolve(process.argv[2]));
    if (bytes.length > 2_000_000) throw Error('Receipt exceeds the 2 MB limit.');
    const data = name => readFileSync(new URL(`../data/research-${name}.json`, import.meta.url));
    const verified = verifyResearchReceipt(JSON.parse(bytes), {patients: JSON.parse(data('patients')),
      truth: JSON.parse(data('truth')), modelBytes: data('model')});
    console.log(JSON.stringify(verified, null, 2));
  } catch (error) { console.error(`Research receipt verification failed: ${error.message}`); process.exitCode = 1; }
}

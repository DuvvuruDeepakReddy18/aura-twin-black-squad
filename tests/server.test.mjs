import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import { createAppServer } from '../server.mjs';

let server, origin, patient;
before(async () => {
  server = createAppServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  const response = await fetch(`${origin}/api/patients`);
  ({ patients: [patient] } = await response.json());
});
after(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); });
const predict = (body, options = {}) => fetch(`${origin}/api/predict`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), ...options });

test('health exposes synthetic prototype state', async () => {
  const response = await fetch(`${origin}/api/health`);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).synthetic, true);
});
test('API predicts from a real stored EHR and sensor window', async () => {
  const response = await predict({ patientId: patient.id, cursor: patient.defaultCursor });
  assert.equal(response.status, 200);
  const result = await response.json();
  assert.ok(result.risk >= 0 && result.risk <= 1);
  assert.equal(result.forecast.length, 4);
  assert.equal(result.forecast.at(-1).minutes, 120);
  assert.ok(result.forecast.every(point => point.lower <= point.glucose && point.upper >= point.glucose));
  assert.equal(result.patientId, patient.id);
});
test('ingestion accepts a provided synthetic patient with the same deterministic result', async () => {
  const stored = await (await predict({ patientId: patient.id })).json();
  const uploaded = await (await predict({ patient })).json();
  assert.deepEqual(uploaded.forecast, stored.forecast);
  assert.equal(uploaded.risk, stored.risk);
});
test('bad input fails explicitly, without silent fallback to a demo patient', async () => {
  for (const body of [
    { patientId: patient.id, cursor: -1 },
    { patientId: patient.id, cursor: 1.5 },
    { patientId: patient.id, cursor: patient.series.length },
    { patientId: patient.id, scenario: { mealCarbs: -10 } },
    { patientId: patient.id, scenario: { activityMinutes: 999 } },
    { patientId: patient.id, scenario: { mealCarbs: '50' } },
    { patientId: patient.id, scenario: { insulin: 20 } },
    { patient: {} },
  ]) {
    const response = await predict(body);
    assert.equal(response.status, 400, JSON.stringify(body).slice(0, 80));
    assert.ok((await response.json()).error);
  }
  assert.equal((await predict({ patientId: 'missing' })).status, 404);
});
test('JSON boundary rejects malformed body and wrong content type', async () => {
  assert.equal((await predict({}, { body: '{bad' })).status, 400);
  assert.equal((await predict({}, { headers: { 'Content-Type': 'text/plain' } })).status, 415);
});
test('model metrics are accessible while server source is not', async () => {
  assert.equal((await fetch(`${origin}/api/metrics`)).status, 200);
  for (const path of ['/server.mjs', '/.env', '/data/model.json', '/docs/..%2fserver.mjs', '/..%5cserver.mjs']) {
    assert.equal((await fetch(`${origin}${path}`)).status, 404, path);
  }
});
test('routine evaluation belongs to the model actually served by the API', async () => {
  const response=await fetch(`${origin}/api/robustness`);
  assert.equal(response.status,200);
  const report=await response.json();
  const health=await(await fetch(`${origin}/api/health`)).json();
  const bytes=readFileSync(new URL('../data/model.json',import.meta.url));
  assert.equal(report.modelVersion,health.modelVersion);
  assert.equal(report.modelSHA256,createHash('sha256').update(bytes).digest('hex'));
  assert.equal(report.syntheticOnly,true);
  assert(report.cases.length>=6);
});
test('static dashboard is served with correct type and browser safeguards', async () => {
  const response = await fetch(origin);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type'), /text\/html/);
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  assert.ok(response.headers.get('content-security-policy').includes("frame-ancestors 'none'"));
});

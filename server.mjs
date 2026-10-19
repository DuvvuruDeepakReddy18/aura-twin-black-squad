import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, extname, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { initializeModel, infer, validatePatient } from './lib/model.mjs';
import { createChallengeLab } from './lib/challenge.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const [model, patients, metrics] = await Promise.all(
  ['model', 'patients', 'metrics'].map(name => readFile(resolve(ROOT, `data/${name}.json`), 'utf8').then(JSON.parse)),
);
initializeModel(model);
const modelFileBytes = await readFile(resolve(ROOT, 'data/model.json'));
const patientById = new Map(patients.map(patient => [patient.id, patient]));
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.pdf': 'application/pdf', '.mp4': 'video/mp4', '.md': 'text/plain; charset=utf-8', '.json': 'application/json; charset=utf-8' };
const headers = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
};
class RequestError extends Error {
  constructor(message, status = 400) { super(message); this.status = status; }
}
function json(res, status, payload) {
  res.writeHead(status, { ...headers, 'Content-Type': types['.json'], 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(payload));
}
async function readJson(req) {
  if (!req.headers['content-type']?.toLowerCase().startsWith('application/json')) throw new RequestError('Content-Type must be application/json.', 415);
  const chunks = []; let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 2_000_000) throw new RequestError('Payload exceeds the 2 MB limit.', 413);
    chunks.push(chunk);
  }
  try {
    const value = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error();
    return value;
  } catch { throw new RequestError('Request body must be a valid JSON object.'); }
}
function makePrediction(body) {
  const patient = body.patient ?? patientById.get(body.patientId);
  if (!patient) throw new RequestError('Patient not found.', 404);
  if (body.patient) {
    try {
      const validation = validatePatient(patient);
      if (validation && !validation.valid) throw new RequestError(validation.errors.join(' '));
    } catch (err) { throw new RequestError(err.message); }
  }
  const cursor = body.cursor ?? patient.defaultCursor ?? patient.series.length - 1;
  if (!Number.isInteger(cursor) || cursor < 0 || cursor >= patient.series.length) throw new RequestError('Cursor must be an integer within this patient’s series.');
  const scenario = body.scenario ?? {};
  if (!scenario || typeof scenario !== 'object' || Array.isArray(scenario)) throw new RequestError('Scenario must be an object.');
  for (const [key, value] of Object.entries(scenario)) {
    if (!['mealCarbs', 'activityMinutes'].includes(key)) throw new RequestError(`Unknown scenario input: ${key}.`);
    const maximum = key === 'mealCarbs' ? 150 : 90;
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > maximum) throw new RequestError(`${key} must be a number between 0 and ${maximum}.`);
  }
  try { return { patientId: patient.id, cursor, ...infer(patient, cursor, scenario) }; }
  catch (err) { throw new RequestError(err.message); }
}
export function createAppServer() {
  const challengeLab = createChallengeLab({patients, model, modelFileBytes});
  return createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      const pathname = decodeURIComponent(url.pathname);
      if (req.method === 'GET' && pathname === '/api/health') return json(res, 200, { status: 'ok', name: 'AURA Twin', synthetic: true, version: '2.0.0', modelVersion: model.modelVersion });
      if (req.method === 'GET' && pathname === '/api/patients') return json(res, 200, { patients });
      if (req.method === 'GET' && pathname.startsWith('/api/patients/')) {
        const patient = patientById.get(pathname.slice('/api/patients/'.length));
        return json(res, patient ? 200 : 404, patient ?? { error: 'Patient not found.' });
      }
      if (req.method === 'GET' && pathname === '/api/metrics') return json(res, 200, metrics);
      if (req.method === 'GET' && pathname === '/api/stress') {
        try { return json(res, 200, JSON.parse(await readFile(resolve(ROOT, 'data/stress.json'), 'utf8'))); }
        catch (err) { if (err.code === 'ENOENT') throw new RequestError('Stress audit has not been generated.', 404); throw err; }
      }
      if (req.method === 'GET' && pathname === '/api/robustness') {
        try { return json(res, 200, JSON.parse(await readFile(resolve(ROOT, 'data/robustness.json'), 'utf8'))); }
        catch (err) { if (err.code === 'ENOENT') throw new RequestError('Routine robustness evaluation has not been generated.', 404); throw err; }
      }
      if (req.method === 'POST' && pathname === '/api/predict') return json(res, 200, makePrediction(await readJson(req)));
      if (req.method === 'GET' && pathname === '/api/challenge/modes') return json(res, 200, challengeLab.modes());
      if (req.method === 'POST' && pathname === '/api/challenge') return json(res, 200, challengeLab.create(await readJson(req)));
      if (req.method === 'POST' && pathname === '/api/challenge/reveal') return json(res, 200, challengeLab.reveal(await readJson(req)));
      if (pathname.startsWith('/api/')) return json(res, 404, { error: 'API endpoint not found.' });
      if (!['GET', 'HEAD'].includes(req.method)) return json(res, 405, { error: 'Method not allowed.' });
      const isDocument = pathname.startsWith('/docs/');
      const base = resolve(ROOT, isDocument ? 'docs' : 'public');
      const relative = isDocument ? pathname.slice('/docs/'.length) : (pathname === '/' ? 'index.html' : pathname.slice(1));
      const target = resolve(base, relative);
      if (!target.startsWith(base + sep)) throw new RequestError('File not found.', 404);
      const contentType = types[extname(target).toLowerCase()];
      if (!contentType) throw new RequestError('File not found.', 404);
      let content;
      try { content = await readFile(target); } catch { throw new RequestError('File not found.', 404); }
      res.writeHead(200, { ...headers, 'Content-Type': contentType, 'Content-Length': content.length, 'Cache-Control': 'no-cache' });
      res.end(req.method === 'HEAD' ? undefined : content);
    } catch (err) {
      if (!res.headersSent) json(res, err.status ?? (err instanceof URIError ? 400 : 500), { error: err.status ? err.message : 'The request could not be completed.' });
      else res.end();
    }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const port = Number(process.env.PORT ?? 4173);
  const host = process.env.HOST ?? '127.0.0.1';
  const server = createAppServer();
  server.listen(port, host, () => console.log(`AURA Twin is ready at http://${host}:${port}\nSynthetic data only. Press Ctrl+C to stop.`));
  server.on('error', err => { console.error(`Unable to start AURA Twin: ${err.message}`); process.exitCode = 1; });
}

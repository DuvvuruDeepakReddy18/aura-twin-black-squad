import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, extname, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { initializeModel, infer, validatePatient } from './lib/model.mjs';
import { createChallengeLab } from './lib/challenge.mjs';
import { createSessionCodec } from './lib/session-token.mjs';
import { publicAuthConfig } from './lib/auth-config.mjs';
import { createResearchService } from './lib/research-service.mjs';
import { verifyResearchBundle } from './lib/research-integrity.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const [model, patients, metrics] = await Promise.all(
  ['model', 'patients', 'metrics'].map(name => readFile(resolve(ROOT, `data/${name}.json`), 'utf8').then(JSON.parse)),
);
initializeModel(model);
const modelFileBytes = await readFile(resolve(ROOT, 'data/model.json'));
const patientById = new Map(patients.map(patient => [patient.id, patient]));
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.pdf': 'application/pdf', '.mp4': 'video/mp4', '.md': 'text/plain; charset=utf-8', '.json': 'application/json; charset=utf-8', '.woff': 'font/woff', '.woff2': 'font/woff2' };
const headers = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' https://*.supabase.co wss://*.supabase.co; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
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
  // Vercel supplies a parsed-body getter; the local Node server supplies a raw stream.
  try {
    if (req.body !== undefined) {
      const value = req.body;
      if (!value || Array.isArray(value) || typeof value !== 'object' || Buffer.isBuffer(value)) throw new RequestError('Request body must be a valid JSON object.');
      if (Buffer.byteLength(JSON.stringify(value)) > 2_000_000) throw new RequestError('Payload exceeds the 2 MB limit.', 413);
      return value;
    }
  } catch (err) { throw err instanceof RequestError ? err : new RequestError('Request body must be a valid JSON object.'); }
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
export function createAppHandler({sessionKey, allowExternalPatients = true} = {}) {
  const sessionCodec = sessionKey ? createSessionCodec(sessionKey) : null;
  const challengeLab = createChallengeLab({patients, model, modelFileBytes, sessionCodec});
  let researchPromise;
  const research = () => researchPromise ??= (async () => {
    try {
      const files = await Promise.all(['patients', 'model', 'metrics', 'provenance', 'manifest', 'truth', 'ablations']
        .map(name => readFile(resolve(ROOT, `data/research-${name}.json`))));
      const [researchPatients, researchModel, researchMetrics, provenance, manifest, truth, ablations] = files.map(file => JSON.parse(file));
      verifyResearchBundle({patients:files[0],model:files[1],metrics:files[2],truth:files[5],ablations:files[6]},manifest,researchMetrics);
      const {createResearchModel} = await import('./lib/research-model.mjs');
      const ablationRuntimes = Object.fromEntries(Object.entries(ablations.models ?? ablations)
        .filter(([, artifact]) => artifact?.featureSet === 'big_ideas_history_v1')
        .map(([family, artifact]) => [family, createResearchModel(artifact)]));
      return createResearchService({patients: researchPatients, truth, model: researchModel, modelBytes: files[1],
        metrics: researchMetrics, provenance, manifest, runtime: createResearchModel(researchModel), ablationRuntimes, sessionCodec});
    } catch (error) {
      researchPromise = undefined;
      if (error.code === 'ENOENT' || error.code === 'ERR_MODULE_NOT_FOUND') throw new RequestError('The frozen research artifacts are not yet available.', 503);
      throw error;
    }
  })();
  return async (req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      const pathname = decodeURIComponent(url.pathname);
      if (req.method === 'GET' && pathname === '/api/auth/config') return json(res, 200, publicAuthConfig());
      const researchAliases = {
        '/api/model/metrics': '/api/research/metrics', '/api/model/card': '/api/research/card',
        '/api/model/provenance': '/api/research/provenance', '/api/data/provenance': '/api/research/provenance',
        '/api/model/audit': '/api/research/manifest', '/api/robustness/run': '/api/research/challenge',
      };
      const route = researchAliases[pathname] ?? pathname;
      if (route.startsWith('/api/research/')) {
        const service = await research();
        const endpoint = route.slice('/api/research/'.length);
        if (req.method === 'GET') {
          if (endpoint === 'health') return json(res, 200, service.health());
          if (endpoint === 'patients') return json(res, 200, service.list());
          if (endpoint === 'metrics') return json(res, 200, service.metrics);
          if (endpoint === 'provenance') return json(res, 200, service.provenance);
          if (endpoint === 'manifest') return json(res, 200, service.manifest);
          if (endpoint === 'card') return json(res, 200, service.card());
          if (endpoint === 'runtime-audit') {
            let audit;
            try { audit = JSON.parse(await readFile(resolve(ROOT, 'data/research-runtime-audit.json'), 'utf8')); }
            catch (error) { if (error.code === 'ENOENT') throw new RequestError('The post-freeze runtime audit has not been generated.', 503); throw error; }
            if (audit.modelSHA256 !== service.modelSHA256) throw new RequestError('The runtime audit belongs to a different model artifact.', 409);
            return json(res, 200, audit);
          }
          if (endpoint === 'challenge/modes') return json(res, 200, service.modes());
          const match = /^patients\/([^/]+)(?:\/([^/]+))?$/.exec(endpoint);
          if (match) return json(res, 200, service.patientRoute(match[1], match[2], url.searchParams));
        }
        if (req.method === 'POST') {
          const body = await readJson(req);
          if (endpoint === 'predict') return json(res, 200, service.predict(body));
          if (endpoint === 'scenario') return json(res, 200, service.scenario(body));
          if (endpoint === 'ablation/predict') return json(res, 200, service.ablation(body));
          if (endpoint === 'challenge') return json(res, 200, service.freeze(body));
          if (endpoint === 'challenge/reveal') return json(res, 200, service.reveal(body));
          const match = /^patients\/([^/]+)\/(predict|scenario|replay\/evaluate)$/.exec(endpoint);
          if (match) {
            if (body.patientId && body.patientId !== match[1]) throw new RequestError('Route and body participant IDs differ.');
            const input = {...body, patientId: match[1]};
            return json(res, 200, match[2] === 'scenario' ? service.scenario(input) : match[2] === 'predict' ? service.predict(input) : service.freeze(input));
          }
        }
        throw new RequestError('Research endpoint not found.', 404);
      }
      if (req.method === 'GET' && pathname === '/api/health') return json(res, 200, { status: 'ok', name: 'AURA Twin', scope: 'legacy-synthetic-api', primaryHealth: '/api/research/health', synthetic: true, version: model.modelVersion.replace('aura-synthetic-', ''), modelVersion: model.modelVersion, challengeStorage: sessionCodec ? 'encrypted-browser-token' : 'memory' });
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
      if (req.method === 'POST' && pathname === '/api/predict') {
        const body = await readJson(req);
        if (!allowExternalPatients && body.patient !== undefined) throw new RequestError('The hosted demo accepts bundled synthetic records only. Use the local sandbox for your own synthetic data.', 403);
        return json(res, 200, makePrediction(body));
      }
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
  };
}

export function createAppServer(options) {
  return createServer(createAppHandler(options));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const port = Number(process.env.PORT ?? 4173);
  const host = process.env.HOST ?? '127.0.0.1';
  const server = createAppServer();
  server.listen(port, host, () => console.log(`AURA Twin is ready at http://${host}:${port}\nResearch replay and a separate synthetic sandbox. Press Ctrl+C to stop.`));
  server.on('error', err => { console.error(`Unable to start AURA Twin: ${err.message}`); process.exitCode = 1; });
}

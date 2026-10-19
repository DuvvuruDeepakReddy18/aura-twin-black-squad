/* AURA Twin — dependency-free clinical research workspace. */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const isNumber = value => typeof value === 'number' && Number.isFinite(value);
const num = (value, digits = 0) => isNumber(value) ? value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—';
const pct = (value, digits = 0) => isNumber(value) ? `${num(value * 100, digits)}%` : 'Unavailable';
function probabilityLabel(value, digits = 0) {
  if (!isNumber(value)) return 'Unavailable';
  const percent = value * 100;
  if (percent > 0 && percent < 0.1) return '<0.1%';
  if (percent < 100 && percent > 99.9) return '>99.9%';
  const precision = (percent > 0 && percent < 1) || (percent > 99 && percent < 100)
    ? Math.max(1, digits) : digits;
  return `${num(percent, precision)}%`;
}
const time = timestamp => new Date(timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit' });
const date = timestamp => new Date(timestamp).toLocaleDateString('en-GB', { timeZone: 'UTC', day: '2-digit', month: 'short', year: 'numeric' });
const paths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  record: '<path d="M7 4h10a2 2 0 0 1 2 2v14H5V6a2 2 0 0 1 2-2Z"/><path d="M9 3h6v4H9zM8 12h8M8 16h5"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  shield: '<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Z"/><path d="m8 12 3 3 5-6"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v4h16v-4"/>',
  activity: '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7h.01"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4M12 17h.01"/>',
  radar: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12 19 5"/><circle cx="12" cy="12" r="1"/>',
  sliders: '<path d="M4 7h7m4 0h5M4 17h3m4 0h9"/><circle cx="13" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  reset: '<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',
  play: '<path d="m9 5 10 7-10 7V5Z"/>',
  pause: '<path d="M8 5h2v14H8zM14 5h2v14h-2z"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  connect: '<path d="M4 12h16M12 4v16"/>',
  heart: '<path d="M20 5a5 5 0 0 0-8 1 5 5 0 0 0-8-1c-5 5 8 15 8 15S25 10 20 5Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  flask: '<path d="M9 3h6M10 3v6L4 19a1.4 1.4 0 0 0 1.2 2h13.6A1.4 1.4 0 0 0 20 19L14 9V3M7 15h10"/><path d="M10 18h.01M14 17h.01"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  alert: '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5M12 17h.01"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.info}</svg>`;
function hydrateIcons(root = document) { $$('[data-icon]', root).forEach(node => { node.innerHTML = icon(node.dataset.icon); }); }

const state = { patients: [], patient: null, prediction: null, metrics: null, metricsError: null, robustness: null, robustnessError: null, robustnessLoading: false, cursor: 0, tab: 'overview', scenario: { mealCarbs: 0, activityMinutes: 0 }, playing: false, timer: null, request: null, requestId: 0, timelineDebounce: null, notesDebounce: null, storageAvailable: true };
const challenge = { mode: 'baseline', frozen: null, revealed: null, busy: null, error: null, controller: null, generation: 0, context: null, stress: null, stressError: null, stressLoading: false };
const challengeModes = [
  { id: 'baseline', number: '01', label: 'Clean replay', tag: 'THE REFERENCE', icon: 'activity', description: 'Keep all original readings. Test the unmodified forecast.', expected: 'Establish the reference for this patient and cutoff. Reveal the recorded future, then compare the frozen forecast with last-value persistence. A clean stream can still produce an inaccurate forecast.' },
  { id: 'short_gap', number: '02', label: '10-minute CGM gap', tag: 'A RECOVERABLE GAP', icon: 'clock', description: 'Remove the last two glucose readings. Test short-gap handling.', expected: 'The last 10 minutes of CGM values are missing. The model may proceed with forward filling and a degraded quality label. Being able to produce a forecast does not establish that its estimate is accurate.' },
  { id: 'cgm_dropout', number: '03', label: '30-minute dropout', tag: 'THE ABSTENTION TEST', icon: 'shield', description: 'Remove the last six readings. Test whether the model refuses.', expected: 'The latest usable CGM is now 30 minutes old. The model’s freshness gate should withhold the forecast. An abstention has no numeric risk, forecast error or interval-coverage score.' },
  { id: 'cgm_bias', number: '04', label: 'Undetected sensor bias', tag: 'A DELIBERATE BLIND SPOT', icon: 'alert', description: 'Add 30 mg/dL to two hours of CGM. Plausible values can mislead.', expected: 'A +30 mg/dL offset in the last two hours can remain within plausible bounds. Current quality rules do not detect this bias. Reveal the original, unmodified future to inspect the resulting error; a passed data check is not proof of accuracy.' }
];
let toastTimer;
function toast(message) { clearTimeout(toastTimer); const node = $('#toast'); node.textContent = message; node.hidden = false; toastTimer = setTimeout(() => { node.hidden = true; }, 3800); }
function localGet(key, fallback = '') { try { return localStorage.getItem(`aura-twin:${key}`) ?? fallback; } catch { state.storageAvailable = false; return fallback; } }
function localSet(key, value) { try { localStorage.setItem(`aura-twin:${key}`, value); return true; } catch { state.storageAvailable = false; return false; } }
function displayError(message, retry = true) { $('#error-banner').innerHTML = `<span>${esc(message)}</span>${retry ? '<button id="retry-button">Try again</button>' : ''}`; $('#error-banner').hidden = false; $('#retry-button')?.addEventListener('click', () => state.patient ? loadPrediction() : initialize()); }
function clearError() { $('#error-banner').hidden = true; }
async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  let result;
  try { result = await response.json(); } catch { throw new Error('The server returned an unreadable response. Restart the local server and try again.'); }
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
  return result;
}

async function initialize() {
  clearError();
  const [patientResult, metricsResult] = await Promise.allSettled([request('/api/patients'), request('/api/metrics')]);
  if (metricsResult.status === 'fulfilled') { state.metrics = metricsResult.value; state.metricsError = null; } else { state.metricsError = metricsResult.reason.message; }
  if (patientResult.status === 'rejected') {
    displayError(`The patient workspace could not connect. ${patientResult.reason.message}`);
    $('#patient-list').innerHTML = '<div class="sidebar-loading">Patient data unavailable.<br>Use “Try again” to reconnect.</div>';
    $('#patient-header').innerHTML = '<div class="empty-state"><h2>Your workspace is offline</h2><p>Start the local AURA server, then reconnect to load the synthetic patients.</p></div>';
    $('#glucose-chart').innerHTML = '<div class="chart-loading">Waiting for the local data service.</div>';
    return;
  }
  state.patients = patientResult.value.patients || patientResult.value;
  if (!Array.isArray(state.patients) || !state.patients.length) { displayError('No synthetic patients were found in this workspace.'); return; }
  $('#patient-count').textContent = String(state.patients.length).padStart(2, '0');
  await selectPatient(state.patients[0].id);
  renderEvidence();
}

function renderPatientList() {
  const query = $('#patient-search').value.trim().toLowerCase();
  const visible = state.patients.filter(patient => `${patient.name} ${patient.id}`.toLowerCase().includes(query));
  $('#patient-list').innerHTML = visible.map(patient => `<button class="patient-item ${patient.id === state.patient?.id ? 'active' : ''}" data-patient-id="${esc(patient.id)}" ${patient.id === state.patient?.id ? 'aria-current="true"' : ''} aria-label="View ${esc(patient.name)}, ${esc(patient.id)}"><span class="patient-avatar">${esc(patient.initials || patient.name.split(' ').map(w => w[0]).join('').slice(0, 2))}</span><span><span class="patient-item-name">${esc(patient.name)}</span><span class="patient-item-meta">${esc(patient.id)} · ${esc(patient.age)} years</span></span>${patient.id === state.patient?.id ? '<span class="selected-dot"></span>' : ''}</button>`).join('') || '<div class="sidebar-loading">No matching patients.<br>Try a name or patient ID.</div>';
  $$('[data-patient-id]').forEach(button => button.addEventListener('click', () => selectPatient(button.dataset.patientId)));
}

async function selectPatient(id) {
  invalidateChallenge();
  stopPlayback();
  clearTimeout(state.timelineDebounce);
  clearTimeout(state.notesDebounce);
  if (state.patient) saveNotes(false);
  const next = state.patients.find(patient => patient.id === id);
  if (!next) return;
  state.request?.abort();
  state.requestId++;
  try {
    state.patient = next.series ? next : await request(`/api/patients/${encodeURIComponent(id)}`);
    state.prediction = null;
    state.cursor = Math.min(state.patient.defaultCursor ?? 287, state.patient.series.length - 1);
    state.scenario = { mealCarbs: 0, activityMinutes: 0 };
    resetScenarioControls();
    renderPatientList();
    renderPatientHeader();
    setupTimeline();
    $('#clinical-notes').value = localGet(`notes:${id}`);
    $('#notes-status').textContent = state.storageAvailable ? 'Private to this browser. Avoid personal information.' : 'Browser storage unavailable. Notes cannot be saved.';
    $('#sidebar').classList.remove('is-open');
    $('#menu-toggle').setAttribute('aria-expanded', 'false');
    await loadPrediction();
  } catch (error) { displayError(`This patient could not be loaded. ${error.message}`); }
}

function renderPatientHeader() {
  const patient = state.patient;
  const diagnosis = patient.ehr?.diagnoses?.[0] || 'No diagnosis recorded';
  const routine = patient.routineLabel || patient.routine?.title || patient.routine?.label || (typeof patient.routine === 'string' ? patient.routine : '');
  $('#patient-header').classList.toggle('has-routine', Boolean(routine));
  $('#patient-header').innerHTML = `<div class="patient-header-avatar">${esc(patient.initials)}</div><div><h2 class="patient-header-name">${esc(patient.name)}</h2><div class="patient-demographics"><span>${esc(patient.id)}</span><i class="separator-dot"></i><span>${esc(patient.age)} years</span><i class="separator-dot"></i><span>${esc(patient.sex)}</span></div></div><div class="patient-header-tags"><span class="neutral-tag">${esc(diagnosis)}</span><span class="neutral-tag green">Digital twin connected</span></div><div class="patient-header-status"><span><i class="live-dot"></i>Replay connected</span><small>5-minute wearable cadence</small></div>${routine ? `<div class="patient-routine-strip">${icon('clock')}<span>Simulated routine: <strong>${esc(routine)}</strong></span><small>Display context only · not a model input</small></div>` : ''}`;
}

function setupTimeline() {
  const slider = $('#timeline-slider');
  const dayStart = Math.floor(state.cursor / 288) * 288;
  slider.min = Math.max(287, dayStart);
  slider.max = Math.min(dayStart + 287, state.patient.series.length - 1);
  slider.value = state.cursor;
  slider.disabled = false;
  $('#play-button').disabled = false;
  renderTime();
}

function renderTime() {
  const row = state.patient.series[state.cursor];
  $('#replay-time').textContent = `${time(row.timestamp)} UTC`;
  $('#simulation-time').textContent = `${date(row.timestamp)} · ${time(row.timestamp)} UTC · Replay`;
  $('#timeline-slider').setAttribute('aria-valuetext', `${date(row.timestamp)}, ${time(row.timestamp)} UTC, simulated time`);
}

async function loadPrediction() {
  if (!state.patient) return;
  state.request?.abort();
  const controller = new AbortController();
  state.request = controller;
  const requestId = ++state.requestId;
  $('#glucose-chart').classList.add('updating');
  $('#export-button').disabled = true;
  $('#apply-scenario').disabled = true;
  try {
    const prediction = await request('/api/predict', { method: 'POST', body: JSON.stringify({ patientId: state.patient.id, cursor: state.cursor, scenario: state.scenario }), signal: controller.signal });
    if (requestId !== state.requestId) return;
    state.prediction = prediction;
    if (prediction.driverMethod === 'group_reference_sensitivity' && !state.robustness && !state.robustnessLoading && !state.robustnessError) loadRobustness();
    clearError();
    renderTime();
    renderMetrics();
    renderChart();
    renderRisk();
    renderFusion();
    renderScenarioResult();
    if (state.tab === 'record') renderRecord();
    if (state.tab === 'evidence') renderEvidence();
    if (state.tab === 'challenge') renderChallenge();
    $('#export-button').disabled = false;
    $('#apply-scenario').disabled = Boolean(prediction.abstained);
  } catch (error) {
    if (error.name === 'AbortError' || requestId !== state.requestId) return;
    stopPlayback();
    state.prediction = null;
    displayError(`The forecast is currently unavailable. ${error.message}`);
    $('#glucose-chart').innerHTML = '<div class="chart-loading">Forecast unavailable. Reconnect to continue the replay.</div>';
    $('#risk-content').innerHTML = '<div class="risk-placeholder">Forecast unavailable. No current risk estimate.</div>';
    $('#metric-row').innerHTML = '<div class="empty-state">No current prediction available.</div>';
    $('#fusion-content').innerHTML = '<p class="record-note">Live stream summary unavailable until the workspace reconnects.</p>';
    $('#quality-label').textContent = 'Data quality unavailable';
    $('#scenario-result').hidden = true;
    if (state.tab === 'record') renderRecord();
    $('#apply-scenario').disabled = true;
  } finally { if (requestId === state.requestId) $('#glucose-chart').classList.remove('updating'); }
}

function renderMetrics() {
  const prediction = state.prediction;
  const current = prediction.current;
  const forecast = prediction.forecast?.at(-1);
  const prior = state.patient.series[Math.max(0, state.cursor - 6)]?.glucose;
  const change = isNumber(current.glucose) && isNumber(prior) ? current.glucose - prior : null;
  const scenario = prediction.scenario?.active;
  const values = [
    ['Glucose now', num(current.glucose), 'mg/dL', isNumber(change) ? `${change >= 0 ? '↗' : '↘'} ${num(Math.abs(change))} mg/dL in 30 min` : 'No recent trend', change > 10],
    [scenario ? 'Scenario · +2 hours' : 'Forecast · +2 hours', num(forecast?.glucose), 'mg/dL', prediction.abstained ? 'Withheld · data quality' : `${num(forecast?.lower)}–${num(forecast?.upper)} interval`, forecast?.glucose >= 180],
    ['Sleep · last 24 hours', num(current.sleep, 1), 'hrs', 'Simulated sleep duration', false],
    ['Heart-rate variability', num(current.hrv), 'ms', 'Latest wearable sample', false]
  ];
  $('#metric-row').innerHTML = values.map(([label, value, unit, description, coral]) => `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value">${value}<small>${unit}</small></div><div class="metric-trend ${coral ? 'coral' : ''}">${esc(description)}</div></div>`).join('');
  $('#chart-note').textContent = prediction.abstained ? `Forecast withheld: ${(prediction.quality?.reasons || []).join(' ')}` : scenario ? 'Illustrative scenario curve. Baseline risk is unchanged; shifted intervals have no measured coverage.' : 'Only past observations enter the model. Shading: nominal 90% residual interval, not a guarantee.';
}

function renderChart() {
  const chart = $('#glucose-chart');
  const patient = state.patient;
  const prediction = state.prediction;
  const now = Date.parse(patient.series[state.cursor].timestamp);
  const observed = patient.series.slice(Math.max(0, state.cursor - 36), state.cursor + 1).filter(row => isNumber(row.glucose)).map(row => ({ ...row, minutes: (Date.parse(row.timestamp) - now) / 60000, type: 'Observed' }));
  const future = (prediction.forecast || []).map(point => ({ ...point, timestamp: new Date(now + point.minutes * 60000).toISOString(), type: prediction.scenario?.active ? 'Illustrative scenario' : 'Forecast' }));
  const width = Math.max(330, chart.clientWidth);
  const height = chart.clientHeight;
  const padding = { left: 42, right: 25, top: 23, bottom: 38 };
  const yMax = Math.max(240, Math.ceil(Math.max(...observed.map(row => row.glucose), ...future.map(row => row.upper), 180) / 40) * 40);
  const yMin = Math.min(60, Math.floor(Math.min(...observed.map(row => row.glucose), ...future.map(row => row.lower), 70) / 20) * 20);
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const x = minutes => padding.left + ((minutes + 180) / 300) * plotWidth;
  const y = glucose => padding.top + ((yMax - glucose) / (yMax - yMin)) * plotHeight;
  const path = points => points.map((point, index) => `${index ? 'L' : 'M'}${x(point.minutes).toFixed(2)},${y(point.glucose).toFixed(2)}`).join(' ');
  const currentPoint = observed.at(-1);
  const forecastPoints = currentPoint ? [{ minutes: 0, glucose: currentPoint.glucose, lower: currentPoint.glucose, upper: currentPoint.glucose }, ...future] : future;
  const upper = forecastPoints.map(point => `${x(point.minutes)},${y(point.upper)}`);
  const lower = [...forecastPoints].reverse().map(point => `${x(point.minutes)},${y(point.lower)}`);
  const yStep = yMax - yMin > 240 ? 60 : 40;
  const yTicks = [];
  for (let value = Math.ceil(yMin / yStep) * yStep; value <= yMax; value += yStep) yTicks.push(value);
  const labelMinutes = [-180, -120, -60, 0, 60, 120];
  const endpoint = future.at(-1);
  chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" tabindex="0" aria-labelledby="chart-title chart-description"><title id="chart-title">${esc(patient.name)} glucose trajectory</title><desc id="chart-description">Observed glucose for the previous three hours, and forecasts through two hours ahead. ${prediction.abstained ? 'Forecast withheld due to insufficient data.' : `Current glucose ${num(prediction.current.glucose)}; two-hour forecast ${num(endpoint?.glucose)} milligrams per deciliter.`} Use left and right arrow keys to inspect measurements. Times are UTC.</desc>
    <defs><linearGradient id="observed-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#73976e" stop-opacity=".12"/><stop offset="100%" stop-color="#73976e" stop-opacity="0"/></linearGradient></defs>
    <rect x="${x(0)}" y="${padding.top}" width="${x(120) - x(0)}" height="${plotHeight}" fill="#f6f9f1"/>
    ${yTicks.map(value => `<line x1="${padding.left}" y1="${y(value)}" x2="${width - padding.right}" y2="${y(value)}" stroke="#e9eee2" stroke-width=".8"/><text x="${padding.left - 10}" y="${y(value) + 3}" text-anchor="end" class="chart-axis">${value}</text>`).join('')}
    <line x1="${padding.left}" y1="${y(180)}" x2="${width - padding.right}" y2="${y(180)}" stroke="#dfbea5" stroke-width=".8" stroke-dasharray="4 4"/><text x="${padding.left + 5}" y="${y(180) - 6}" class="chart-threshold-label">180 · event threshold</text>
    ${currentPoint ? `<path d="${path(observed)} L${x(currentPoint.minutes)},${y(yMin)} L${x(observed[0].minutes)},${y(yMin)} Z" fill="url(#observed-fill)"/>` : ''}
    ${future.length ? `<polygon points="${[...upper, ...lower].join(' ')}" fill="#c9dfbb" opacity=".55"/>` : ''}
    <line x1="${x(0)}" y1="${padding.top - 4}" x2="${x(0)}" y2="${height - padding.bottom}" stroke="#c1d1b2" stroke-width="1" stroke-dasharray="3 4"/>
    <text x="${x(0)}" y="${padding.top - 11}" text-anchor="middle" class="chart-label" style="font-size:7px;letter-spacing:1px;fill:#7a9364">NOW</text>
    <text x="${x(65)}" y="${padding.top - 11}" text-anchor="middle" class="chart-label" style="font-size:7px;letter-spacing:1px">${prediction.scenario?.active ? 'SCENARIO' : 'FORECAST'}</text>
    <path d="${path(observed)}" fill="none" stroke="#597f54" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
    ${future.length ? `<path d="${path(forecastPoints)}" fill="none" stroke="#62945b" stroke-width="2" stroke-dasharray="5 5" stroke-linecap="round" stroke-linejoin="round"/>` : ''}
    ${currentPoint ? `<circle cx="${x(0)}" cy="${y(currentPoint.glucose)}" r="5" fill="#fff" stroke="#4f7d46" stroke-width="2"/><circle cx="${x(0)}" cy="${y(currentPoint.glucose)}" r="2" fill="#4f7d46"/>` : ''}
    ${endpoint ? `<circle cx="${x(120)}" cy="${y(endpoint.glucose)}" r="4" fill="#eef5e8" stroke="#72a05c" stroke-width="1.5"/>` : ''}
    ${labelMinutes.map(minute => `<text x="${x(minute)}" y="${height - 15}" text-anchor="middle" class="chart-axis">${time(now + minute * 60000)}</text>`).join('')}
    <line id="chart-crosshair" x1="0" x2="0" y1="${padding.top}" y2="${height - padding.bottom}" stroke="#99b182" stroke-width="1" opacity="0"/><circle id="chart-hover-dot" cx="0" cy="0" r="4" fill="#fff" stroke="#4d7e3c" stroke-width="2" opacity="0"/>
  </svg><div class="chart-tooltip" hidden></div>`;
  const points = [...observed, ...future];
  let active = Math.max(0, observed.length - 1);
  const show = index => {
    const point = points[index];
    if (!point) return;
    active = index;
    const tooltip = $('.chart-tooltip', chart);
    tooltip.innerHTML = `${esc(time(point.timestamp))} UTC · ${esc(point.type)}<strong>${num(point.glucose)} <span style="font-size:9px">mg/dL</span></strong>${point.lower !== undefined ? `<small>Interval ${num(point.lower)}–${num(point.upper)}</small>` : ''}`;
    tooltip.hidden = false;
    tooltip.style.left = `${Math.min(width - 68, Math.max(68, x(point.minutes)))}px`;
    tooltip.style.top = `${Math.max(73, y(point.glucose) - 11)}px`;
    $('#chart-crosshair').setAttribute('x1', x(point.minutes));
    $('#chart-crosshair').setAttribute('x2', x(point.minutes));
    $('#chart-crosshair').setAttribute('opacity', '.7');
    $('#chart-hover-dot').setAttribute('cx', x(point.minutes));
    $('#chart-hover-dot').setAttribute('cy', y(point.glucose));
    $('#chart-hover-dot').setAttribute('opacity', '1');
  };
  const hide = () => { $('.chart-tooltip', chart).hidden = true; $('#chart-crosshair')?.setAttribute('opacity', '0'); $('#chart-hover-dot')?.setAttribute('opacity', '0'); };
  $('svg', chart).addEventListener('pointermove', event => {
    const bounds = chart.getBoundingClientRect();
    const target = event.clientX - bounds.left;
    let index = 0;
    for (let i = 1; i < points.length; i++) if (Math.abs(x(points[i].minutes) - target) < Math.abs(x(points[index].minutes) - target)) index = i;
    show(index);
  });
  $('svg', chart).addEventListener('pointerleave', hide);
  $('svg', chart).addEventListener('focus', () => show(active));
  $('svg', chart).addEventListener('blur', hide);
  $('svg', chart).addEventListener('keydown', event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); show(Math.min(points.length - 1, Math.max(0, active + (event.key === 'ArrowRight' ? 1 : -1)))); } });
}

function renderRisk() {
  const prediction = state.prediction;
  const treeDrivers = prediction.driverMethod === 'group_reference_sensitivity';
  if (prediction.abstained || !isNumber(prediction.risk)) {
    $('#risk-title').textContent = 'More context needed.';
    $('#risk-content').innerHTML = `<div class="risk-main"><div class="risk-number" style="font-size:34px;letter-spacing:-1px">Unavailable</div></div><p class="risk-description">The model has withheld its forecast because the available stream does not meet its data-quality requirements.</p><div class="risk-divider"></div><div class="drivers-caption">DATA QUALITY CHECK</div><ul class="detail-list" style="margin-top:15px">${(prediction.quality?.reasons || ['Insufficient observations.']).map(reason => `<li style="color:#bfd0b2">${esc(reason)}</li>`).join('')}</ul><p class="risk-bottom">Missing or stale measurements never produce a zero-risk estimate.</p>`;
    return;
  }
  const triggered = prediction.alert?.triggered ?? prediction.risk >= .5;
  const threshold = prediction.alert?.threshold ?? .5;
  $('#risk-title').textContent = triggered ? 'A window to act.' : 'A moment of clarity.';
  const acknowledgement = localGet(`ack:${state.patient.id}:${state.cursor}`);
  const drivers = prediction.drivers?.slice(0, 4) || [];
  const max = Math.max(...drivers.map(driver => Math.abs(driver.contribution)), .01);
  $('#risk-content').innerHTML = `<div class="risk-main"><div class="risk-number">${esc(probabilityLabel(prediction.risk).slice(0, -1))}<span>%</span></div><span class="risk-level ${triggered ? '' : 'low'}"><i class="live-dot"></i>${triggered ? 'Review suggested' : 'Below threshold'}</span></div><p class="risk-description">Model probability of glucose ≥180 mg/dL<br>at exactly <strong>+2 hours</strong>.</p><div class="risk-range"><span style="width:${prediction.risk * 100}%"></span></div><div class="risk-range-label"><span>0%</span><span>REVIEW THRESHOLD ${pct(threshold, 2)}</span><span>100%</span></div><div class="risk-divider"></div><div class="drivers-caption">WHAT SHAPES THIS ESTIMATE<small>${treeDrivers ? 'Reference sensitivity' : 'Model associations'}</small></div><div class="drivers-list">${drivers.map((driver, index) => `<div class="driver"><div class="driver-label"><span><span class="driver-rank">0${index + 1}</span>${esc(driver.name)}</span><span class="driver-value" title="${esc(driver.source)} · ${esc(driver.value)}">${driver.contribution >= 0 ? '+' : '−'}${num(Math.abs(driver.contribution), 2)}${treeDrivers ? ' pp' : ''}</span></div><div class="driver-track"><span class="${driver.contribution < 0 ? 'negative' : ''}" style="width:${Math.max(5, Math.abs(driver.contribution) / max * 100)}%"></span></div></div>`).join('')}</div><button id="acknowledge-button" class="acknowledge-button">${icon(acknowledgement ? 'check' : 'record')}${acknowledgement ? 'Observation acknowledged' : 'Acknowledge observation'}</button>${acknowledgement ? '<p class="acknowledged-label">Saved locally for this replay moment · click to undo</p>' : ''}<p class="risk-bottom">${treeDrivers ? 'Values show risk change in percentage points when a feature group is replaced with training medians. Nonadditive; not causal.' : 'Signed values are additive log-odds associations, not causes.'} ${prediction.scenario?.active ? 'This is the unchanged baseline probability.' : 'Synthetic research estimate; not a clinical risk score.'}</p>`;
  $('#acknowledge-button').addEventListener('click', () => {
    const key = `ack:${state.patient.id}:${state.cursor}`;
    const current = localGet(key);
    if (localSet(key, current ? '' : new Date().toISOString())) { renderRisk(); toast(current ? 'Acknowledgement removed for this replay moment.' : 'Observation acknowledged for this replay moment.'); } else { toast('Browser storage is unavailable. Acknowledgement was not saved.'); }
  });
}

function renderFusion() {
  const ehr = state.patient.ehr;
  const current = state.prediction.current;
  const cell = (label, value, unit = '') => `<div class="source-item"><span>${esc(label)}</span><strong>${value} <small>${esc(unit)}</small></strong></div>`;
  $('#fusion-content').innerHTML = `<div class="fusion-source"><div class="fusion-source-top">${icon('record')}Historical health record<span class="source-tag">STATIC</span></div><div class="source-data">${cell('HbA1c', num(ehr.hba1c, 1), '%')}${cell('Body mass index', num(ehr.bmi, 1), 'kg/m²')}${cell('LDL cholesterol', num(ehr.ldl), 'mg/dL')}${cell('Diabetes history', num(ehr.diabetesYears, 1), 'years')}</div></div><div class="fusion-connector"><span>${icon('connect')}</span></div><div class="fusion-source"><div class="fusion-source-top">${icon('activity')}Wearable stream<span class="source-tag">DYNAMIC</span></div><div class="source-data">${cell('Heart rate', num(current.hr), 'bpm')}${cell('Steps · 24 hours', num(current.steps))}${cell('Sleep · 24 hours', num(current.sleep, 1), 'hrs')}${cell('CGM cadence', '5', 'min')}</div></div>`;
  const quality = state.prediction.quality;
  $('#quality-label').textContent = `${num(quality?.score)}% observed · ${quality?.status === 'good' ? 'Data checks passed' : quality?.status === 'degraded' ? 'Some values imputed' : 'Insufficient data'}`;
}

function renderScenarioResult() {
  const scenario = state.prediction.scenario;
  const result = $('#scenario-result');
  result.hidden = !scenario?.active;
  if (scenario?.active) {
    const delta = scenario.glucoseDelta;
    result.innerHTML = `ILLUSTRATIVE CHANGE AT +2 HOURS<strong>${delta >= 0 ? '+' : '−'}${num(Math.abs(delta), 1)} <span style="font-size:10px">mg/dL</span></strong><small>Baseline risk stays ${esc(probabilityLabel(state.prediction.risk))}. This arithmetic scenario is not a treatment effect.</small>`;
  }
  $('#apply-scenario').innerHTML = `Explore scenario <span aria-hidden="true">↗</span>`;
}

function resetScenarioControls() {
  $('#meal-slider').value = '0';
  $('#activity-slider').value = '0';
  $('#meal-value').textContent = '0 g';
  $('#activity-value').textContent = '0 min';
  $('#scenario-result').hidden = true;
}

function setTab(tab, focus = false) {
  if (!['overview', 'record', 'evidence', 'challenge'].includes(tab)) return;
  state.tab = tab;
  $$('[data-tab]').forEach(button => {
    if (button.matches('.nav-button, [role="tab"]')) {
      button.classList.toggle('active', button.dataset.tab === tab);
      if (button.matches('[role="tab"]')) { button.setAttribute('aria-selected', String(button.dataset.tab === tab)); button.tabIndex = button.dataset.tab === tab ? 0 : -1; }
      if (button.matches('.nav-button')) { if (button.dataset.tab === tab) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current'); }
    }
  });
  ['overview', 'record', 'evidence', 'challenge'].forEach(value => { $(`#${value}-view`).hidden = tab !== value; });
  $('#breadcrumb-view').textContent = { overview: 'Overview', record: 'Patient record', evidence: 'Model evidence', challenge: 'Challenge lab' }[tab];
  $('#sidebar').classList.remove('is-open');
  $('#menu-toggle').setAttribute('aria-expanded', 'false');
  if (tab !== 'overview') stopPlayback();
  if (tab === 'record') renderRecord();
  if (tab === 'evidence') renderEvidence();
  if (tab === 'challenge') renderChallenge();
  if (tab === 'overview' && state.prediction) requestAnimationFrame(renderChart);
  if (focus) $(`#tab-${tab}`).focus();
}

function renderRecord() {
  const patient = state.patient;
  if (!patient) { $('#record-view').innerHTML = '<div class="empty-state">Load a synthetic patient to explore their record.</div>'; return; }
  const ehr = patient.ehr;
  const row = (label, value, unit = '') => `<div class="record-field"><dt>${esc(label)}</dt><dd>${esc(value)}<small>${esc(unit)}</small></dd></div>`;
  const visible = patient.series.slice(Math.max(0, state.cursor - 11), state.cursor + 1).reverse();
  $('#record-view').innerHTML = `<div class="record-grid"><section class="card"><div class="eyebrow">HISTORICAL / STATIC</div><h2>Health record</h2><dl class="record-fields">${row('Age', patient.age, 'years')}${row('Recorded sex', patient.sex)}${row('HbA1c', num(ehr.hba1c, 1), '%')}${row('Body mass index', num(ehr.bmi, 1), 'kg/m²')}${row('LDL cholesterol', num(ehr.ldl), 'mg/dL')}${row('Diabetes history', num(ehr.diabetesYears, 1), 'years')}</dl></section><section class="card"><div class="eyebrow">PATIENT CONTEXT</div><h2>More than a measurement</h2><div class="eyebrow" style="font-size:8px">RECORDED DIAGNOSES</div><div class="record-list">${(ehr.diagnoses || []).map(value => `<span class="neutral-tag">${esc(value)}</span>`).join('') || '<p class="record-note">None provided</p>'}</div><div class="eyebrow" style="font-size:8px">MEDICATION HISTORY</div><p class="record-note" style="margin:9px 0 20px">${(ehr.medications || []).map(esc).join('<br>') || 'None provided'}</p><div class="eyebrow" style="font-size:8px">GENETIC MARKER</div><p class="record-note" style="margin-top:9px">${esc(ehr.geneticMarker)}<br>Descriptive context only; not used as a model feature.</p></section><section class="card record-full"><div class="eyebrow">DYNAMIC / FIVE-MINUTE OBSERVATIONS</div><h2>Wearable data at this moment</h2><p class="record-note">The 12 most recent observations available at ${time(patient.series[state.cursor].timestamp)} UTC on ${date(patient.series[state.cursor].timestamp)}. Future observations do not enter the prediction.</p><div class="table-scroll"><table class="stream-table"><thead><tr><th scope="col">Time · UTC</th><th scope="col">Glucose<br>mg/dL</th><th scope="col">Heart rate<br>bpm</th><th scope="col">HRV<br>ms</th><th scope="col">Steps<br>per interval</th><th scope="col">Sleep state</th></tr></thead><tbody>${visible.map(point => `<tr><td class="stream-time">${time(point.timestamp)}</td><td>${num(point.glucose, 1)}</td><td>${num(point.hr, 1)}</td><td>${num(point.hrv, 1)}</td><td>${num(point.steps)}</td><td>${point.sleep === 1 ? 'Asleep' : point.sleep === 0 ? 'Awake' : 'Missing'}</td></tr>`).join('')}</tbody></table></div></section></div><div class="evidence-disclaimer">${icon('shield')}<span>Fictional patient identity, health record and sensor measurements. The simulation has no link to a real individual. ${esc(patient.replayNote || 'This patient is a held-out synthetic demonstration identity.')}</span></div>`;
}

function renderEvidence() {
  const metrics = state.metrics;
  if (!metrics) {
    $('#evidence-view').innerHTML = `<div class="card empty-state"><h2>Evidence is currently unavailable</h2><p>${esc(state.metricsError || 'The evaluation file has not loaded.')}</p><button id="retry-metrics" class="button" style="margin-top:18px">Reload model evidence</button></div>`;
    $('#retry-metrics')?.addEventListener('click', async () => { try { state.metrics = await request('/api/metrics'); renderEvidence(); } catch (error) { toast(error.message); } });
    return;
  }
  const fused = metrics.models?.fused || {};
  const treeModel = state.prediction?.driverMethod === 'group_reference_sensitivity' || state.prediction?.modelKind === 'hist_gradient_boosting' || metrics.featureSet?.startsWith('clock_free_') || metrics.modelKind === 'hist_gradient_boosting';
  const treeRegression = state.prediction?.regressionKind === 'hist_gradient_boosting' || (state.prediction?.regressionKind === undefined && metrics.modelKind === 'hist_gradient_boosting');
  const treeClassification = state.prediction?.classificationKind === 'hist_gradient_boosting' || (state.prediction?.classificationKind === undefined && metrics.modelKind === 'hist_gradient_boosting');
  const algorithmRows = treeModel ? [
    `<li><strong>Forecast:</strong> ${treeRegression ? 'exported histogram-gradient-boosted trees use raw' : 'ridge regression uses standardized'} past-only features to predict glucose at 30, 60, 90 and 120 minutes.</li>`,
    `<li><strong>Event probability:</strong> ${treeClassification ? 'a boosted-tree classifier' : 'logistic regression'} calibrated on separate patient identities estimates glucose ≥180 mg/dL at exactly +120 minutes.</li>`,
    '<li><strong>Fusion:</strong> EHR context combines with recent CGM levels, slopes, variability, prior-day observations, HR/HRV, sleep and activity.</li>',
    '<li><strong>No wall-clock shortcut:</strong> the revised model receives no time-of-day or future meal information. Unannounced future meals remain an uncertainty.</li>',
    '<li><strong>Uncertainty:</strong> residuals from separate calibration patients form nominal 90% intervals. Coverage is marginal and may change with routines or patient populations.</li>',
    '<li><strong>Explanations:</strong> replacing one feature group with training medians measures a change in predicted risk. These sensitivities are nonadditive, not causal, and may use unrealistic feature combinations.</li>'
  ].join('') : [
    '<li><strong>Forecast:</strong> standardized features feed a ridge regression model for 30, 60, 90 and 120-minute glucose.</li>',
    '<li><strong>Event probability:</strong> logistic regression with validation-set calibration estimates glucose ≥180 mg/dL at exactly +120 minutes.</li>',
    '<li><strong>Fusion:</strong> EHR context, trailing CGM trends, HR/HRV, sleep, activity and explicit EHR × wearable interactions.</li>',
    '<li><strong>Uncertainty:</strong> validation residuals form nominal 90% intervals. Coverage is marginal, not a guarantee for one patient.</li>',
    '<li><strong>Explanations:</strong> signed feature-group contributions to calibrated log-odds. They are associations, not causal effects.</li>'
  ].join('');
  const policy = fused.alertPolicy || {};
  const cohort = metrics.cohort || {};
  const threshold = policy.threshold ?? metrics.probabilityThreshold;
  const improvement = isNumber(metrics.models?.sensorOnly?.mae) && isNumber(fused.mae) ? (metrics.models.sensorOnly.mae - fused.mae) / metrics.models.sensorOnly.mae : null;
  const evidenceMetric = (label, value, note) => `<div class="card evidence-metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
  const tableRow = (name, value) => `<tr><th scope="row">${name}</th><td>${value}</td></tr>`;
  $('#evidence-view').innerHTML = `<div class="evidence-intro"><div><div class="eyebrow">TRANSPARENCY IS PART OF THE PRODUCT</div><h2>Evidence, with its boundaries.</h2><p>A reproducible patient-level evaluation on synthetic data. These results demonstrate a working data-fusion prototype; they do not establish clinical performance.</p></div><span class="version-badge">${esc(state.prediction?.modelVersion || 'AURA fused model')}</span></div><div class="metrics-grid">${evidenceMetric('Two-hour forecast MAE', num(fused.mae, 2), 'mg/dL · held-out synthetic patients')}${evidenceMetric('Discrimination · AUROC', num(fused.auroc, 3), 'Synthetic event classification')}${evidenceMetric('Recall · review policy', pct(policy.testRecall ?? fused.recall, 1), `At a ${pct(threshold, 2)} probability threshold`)}${evidenceMetric('Interval coverage', pct(fused.intervalCoverage, 1), 'Observed test coverage · nominal 90%')}</div><div class="evidence-columns"><section class="card"><div class="eyebrow">DOES FUSION HELP?</div><h2 style="margin-top:7px">Four models, one test set</h2><table class="metrics-table"><thead><tr><th>Model</th><td>2h MAE · mg/dL</td></tr></thead><tbody>${tableRow('<strong>EHR + wearables</strong>', `<strong>${num(fused.mae, 2)}</strong>`)}${tableRow('Wearables only', num(metrics.models?.sensorOnly?.mae, 2))}${tableRow('Static EHR only', num(metrics.models?.staticOnly?.mae, 2))}${tableRow('Last-value persistence', num(metrics.models?.persistence?.mae, 2))}</tbody></table><p class="record-note" style="margin-top:18px">${pct(Math.abs(improvement), 1)} ${improvement >= 0 ? 'lower' : 'higher'} MAE with fusion than the wearable-only model on this simulator. Lower error here does not imply the same advantage in real patients.</p></section><section class="card"><div class="eyebrow">EVALUATION DESIGN</div><h2 style="margin-top:7px">People stay in one split</h2><table class="metrics-table"><tbody>${tableRow('Synthetic patients', num(cohort.patients))}${tableRow('Training / validation / test', `${num(cohort.trainPatients)} / ${num(cohort.validationPatients)} / ${num(cohort.testPatients)}`)}${tableRow('Days per patient', num(cohort.days))}${tableRow('Held-out test windows', num(cohort.windows?.test))}${tableRow('Positive event prevalence', pct(cohort.positiveRate?.test, 2))}${tableRow('Generator seed', esc(metrics.seed))}</tbody></table><p class="record-note" style="margin-top:15px">All windows from a patient remain in the same split. Features use only the prior 24 hours. Overlapping windows are correlated.</p></section><section class="card"><div class="eyebrow">THE ACTUAL ALGORITHM</div><h2 style="margin-top:7px">An inspectable twin</h2><ul class="detail-list">${algorithmRows}</ul></section><section class="card"><div class="eyebrow">OPERATING POINT & RELIABILITY</div><h2 style="margin-top:7px">Make the tradeoffs visible</h2><table class="metrics-table"><tbody>${tableRow('Review threshold', pct(threshold, 2))}${tableRow('Review-policy precision', pct(policy.testPrecision ?? fused.precision, 1))}${tableRow('Review-policy recall', pct(policy.testRecall ?? fused.recall, 1))}${tableRow('Average precision', num(fused.averagePrecision, 3))}${tableRow('Brier score', num(fused.brier, 4))}${tableRow('MAE 95% patient-bootstrap CI', Array.isArray(fused.maePatientBootstrap95CI) ? `${num(fused.maePatientBootstrap95CI[0], 2)}–${num(fused.maePatientBootstrap95CI[1], 2)}` : 'Not available')}</tbody></table><p class="record-note" style="margin-top:16px">${treeModel ? 'The review threshold is selected on separate calibration identities and frozen before the final evaluation.' : 'The review threshold is selected on validation patients and frozen before test evaluation.'} For a fixed model, lowering the review threshold typically increases both recall and false alerts. Forecasts are withheld when required history is missing or channels become stale.</p></section></div><div class="card" style="padding:25px;margin-top:20px"><div class="eyebrow">LIMITATIONS, NOT FINE PRINT</div><h2 style="margin:7px 0 20px">What this prototype cannot tell us</h2><ul class="detail-list">${(metrics.limitations || []).map(limitation => `<li>${esc(limitation)}</li>`).join('')}<li>The scenario sliders use illustrative arithmetic. They do not estimate treatment effects; the trained baseline probability remains unchanged.</li></ul></div><div class="evidence-disclaimer">${icon('info')}<span>Target: ${esc(metrics.target)}. This workspace is a research demonstration with synthetic data only. No external or prospective clinical validation has been performed.</span></div>${treeModel ? '<section id="robustness-evidence" class="card stress-audit" aria-label="Routine robustness evaluation"></section>' : ''}`;
  if (treeModel) { renderRobustnessEvidence(); if (!state.robustness && !state.robustnessLoading && !state.robustnessError) loadRobustness(); }
}

function challengeContext() { return state.patient ? `${state.patient.id}:${state.cursor}` : ''; }

function invalidateChallenge() {
  challenge.controller?.abort();
  challenge.generation++;
  challenge.frozen = null;
  challenge.revealed = null;
  challenge.busy = null;
  challenge.error = null;
  challenge.context = null;
}

function renderChallenge() {
  const view = $('#challenge-view');
  if (!state.patient) { view.innerHTML = '<div class="card empty-state"><h2>The lab needs a patient.</h2><p>Load a synthetic patient to begin a reproducible challenge.</p></div>'; return; }
  if (challenge.context && challenge.context !== challengeContext()) invalidateChallenge();
  const patient = state.patient;
  const cutoff = patient.series[state.cursor].timestamp;
  const mode = challengeModes.find(item => item.id === challenge.mode);
  const frozen = challenge.frozen;
  const prediction = frozen?.prediction;
  const revealed = challenge.revealed;
  const busy = challenge.busy;
  const unavailable = prediction?.abstained || (prediction && !isNumber(prediction.risk));
  const latestForecast = prediction?.forecast?.at(-1);
  const quality = prediction?.quality;
  const receipt = frozen?.receipt;
  const statusLabel = unavailable ? 'Forecast withheld' : quality?.status === 'degraded' ? 'Degraded · forecast produced' : 'Data checks passed';
  const timestampLabel = value => value ? `${date(value)} · ${time(value)} UTC` : 'Unavailable';
  const receiptField = (label, value, code = false) => `<div><dt>${label}</dt><dd${code ? ' class="receipt-hash"' : ''}>${esc(value)}</dd></div>`;
  const qualityReasons = quality?.reasons || [];
  view.innerHTML = `
    <section class="lab-hero" aria-labelledby="lab-title">
      <div class="lab-hero-copy"><div class="lab-eyebrow"><span class="lab-spark">${icon('flask')}</span> THE CHALLENGE LAB <span>FOR THE CURIOUS. AND THE SKEPTICAL.</span></div><h2 id="lab-title">Freeze the prediction.<br>Then reveal the future.</h2><p>Commit the inputs and output at one moment. Stress the sensor stream. <br>See where the model holds up — and where it does not.</p></div>
      <div class="lab-hero-aside"><div class="lab-sequence"><span class="lab-sequence-number">01</span><div>Choose a challenge<small>A clean stream, a gap or a hidden bias</small></div></div><div class="lab-sequence"><span class="lab-sequence-number">02</span><div>Freeze the estimate<small>Patient, cutoff, model and input receipt</small></div></div><div class="lab-sequence"><span class="lab-sequence-number">03</span><div>Reveal what followed<small>Original recorded future, never the perturbed one</small></div></div></div>
    </section>
    <details class="jury-guide"><summary><span>${icon('clock')}60-second jury walkthrough</span><span class="jury-guide-toggle">OPEN GUIDE +</span></summary><div class="jury-guide-steps"><p><strong>00–15s · Establish the reference.</strong> Choose Clean replay, freeze and reveal. Read the selected-window errors.</p><p><strong>15–30s · Test refusal.</strong> Choose 30-minute dropout and freeze again. Inspect the withheld forecast and freshness reason.</p><p><strong>30–45s · Expose a blind spot.</strong> Choose Undetected sensor bias. Freeze, then reveal. Passed quality checks do not mean accurate readings.</p><p><strong>45–60s · Inspect the evidence.</strong> Download the receipt and compare the routine-shift audit below. This is a synthetic test, not a clinical trial.</p></div></details>
    <fieldset class="lab-experiments"><legend>01 <span>Choose what the twin receives</span></legend><div class="experiment-grid">${challengeModes.map(item => `<label class="experiment-card ${item.id === challenge.mode ? 'selected' : ''} ${item.id === 'cgm_bias' ? 'experiment-bias' : ''}" for="experiment-${item.id}"><input id="experiment-${item.id}" type="radio" name="challenge-mode" value="${item.id}" ${item.id === challenge.mode ? 'checked' : ''}/><span class="experiment-top"><span class="experiment-icon">${icon(item.icon)}</span><span class="experiment-number">${item.number}</span></span><span class="experiment-tag">${item.tag}</span><strong>${item.label}</strong><span class="experiment-description">${item.description}</span><span class="experiment-selected">${item.id === challenge.mode ? `${icon('check')}Selected experiment` : 'Select experiment ↗'}</span></label>`).join('')}</div></fieldset>
    <div class="lab-cutoff-bar"><div class="lab-cutoff-label"><span class="eyebrow">AT THIS REPLAY MOMENT</span><strong>${esc(patient.name)} <small>${esc(patient.id)}</small></strong><span id="lab-cutoff-time">${timestampLabel(cutoff)}</span></div><div class="lab-cutoff-slider"><label for="challenge-cursor">Choose the cutoff <span>Past data only</span></label><input type="range" id="challenge-cursor" min="${$('#timeline-slider').min}" max="${$('#timeline-slider').max}" value="${state.cursor}" step="1" aria-label="Challenge replay cutoff" aria-valuetext="${esc(timestampLabel(cutoff))}"/><span>Changing patient or time clears the current experiment.</span></div><button id="freeze-prediction" class="button lab-freeze-button" ${busy ? 'disabled' : ''}>${icon('lock')}${busy === 'freeze' ? 'Freezing estimate…' : frozen ? 'Freeze again' : 'Freeze prediction'}<span>↗</span></button></div>
    ${challenge.error ? `<div class="error-banner lab-error" role="alert"><span>${esc(challenge.error)}</span><button id="lab-dismiss-error">Dismiss</button></div>` : ''}
    <div class="lab-workspace"><div class="lab-main">
      ${frozen ? `<section class="card lab-frozen-card" aria-labelledby="lab-results-title"><div class="lab-result-heading"><div><div class="eyebrow">02 / COMMITTED BEFORE REVEAL</div><h3 id="lab-results-title" tabindex="-1">A frozen point of view.</h3></div><span class="lab-frozen-badge">${icon('lock')}FROZEN</span></div><div class="lab-frozen-context"><span>${esc(frozen.modeLabel || mode.label)}</span><span>${esc(receipt.patientId)} · ${timestampLabel(receipt.cutoffTimestamp)}</span></div><div class="lab-frozen-metrics"><div><span>Input CGM at cutoff</span><strong>${num(prediction.current?.glucose)}<small>mg/dL</small></strong><p>${challenge.mode === 'cgm_bias' ? '+30 mg/dL bias applied' : quality?.status === 'degraded' ? 'May be forward-filled' : 'Latest usable reading'}</p></div><div><span>Frozen +2h forecast</span><strong>${unavailable ? 'Withheld' : num(latestForecast?.glucose)}${unavailable ? '' : '<small>mg/dL</small>'}</strong><p>${unavailable ? 'No numeric forecast' : `${num(latestForecast?.lower)}–${num(latestForecast?.upper)} nominal 90% interval`}</p></div><div><span>Frozen event probability</span><strong>${unavailable ? 'Unavailable' : esc(probabilityLabel(prediction.risk))}</strong><p>${unavailable ? 'Never represented as 0%' : 'Glucose ≥180 mg/dL at +2h'}</p></div></div><div class="lab-quality ${unavailable ? 'quality-withheld' : challenge.mode === 'cgm_bias' ? 'quality-blindspot' : ''}"><span class="lab-quality-icon">${icon(unavailable ? 'shield' : challenge.mode === 'cgm_bias' ? 'alert' : 'info')}</span><div><strong>${challenge.mode === 'cgm_bias' && !unavailable ? 'Bias undetected · data checks passed' : statusLabel}</strong><p>${unavailable ? esc(qualityReasons.join(' ') || 'Insufficient observations for a forecast.') : challenge.mode === 'cgm_bias' ? 'Plausible values pass the current checks. This blind spot can distort the forecast without a quality warning.' : `${num(quality?.score)}% observed data. ${quality?.status === 'degraded' ? 'Short gaps are imputed; compare the result rather than assuming recovery.' : 'Completeness and freshness are not guarantees of accuracy.'}`}</p></div></div><div class="lab-reveal-action"><div><strong>${revealed ? 'Recorded future revealed' : 'The future remains hidden'}</strong><p>${revealed ? unavailable ? 'The server recorded an abstention. There was no numerical estimate to score.' : 'The frozen estimate was compared with the original, unmodified record.' : unavailable ? 'The server stored this abstention. Reveal will confirm that there is no estimate to score.' : 'The server has stored this forecast. The next step compares it with later observations.'}</p></div><button id="reveal-future" class="button ${revealed ? 'button-secondary' : ''}" ${busy || revealed || !frozen.revealAvailable ? 'disabled' : ''}>${icon(revealed ? 'check' : 'eye')}${busy === 'reveal' ? 'Revealing…' : revealed ? 'Future revealed' : 'Reveal recorded future'}</button></div>${!frozen.revealAvailable ? '<p class="lab-inline-note">The record does not include enough future observations for this cutoff. Choose an earlier moment.</p>' : ''}</section>` : `<section class="card lab-locked-card"><div class="lab-lock-art" aria-hidden="true">${icon('lock')}</div><div class="eyebrow">02 / NOTHING COMMITTED YET</div><h3>The future can wait.</h3><p>Freeze an estimate using the selected patient’s available history.<br>The recorded future is only shown after you choose to reveal it.</p><span class="lab-empty-tag">${icon('shield')}No scenario-slider changes enter this experiment</span></section>`}
      ${revealed ? renderChallengeComparison(revealed) : ''}
    </div><aside class="lab-aside"><section class="card lab-field-notes"><div class="eyebrow">WHAT TO LOOK FOR</div><h3>${mode.label}</h3><p>${mode.expected}</p><div class="lab-input-note">${icon('layers')}<span>Health record stays fixed. Only the selected CGM perturbation changes. The comparison future stays original.</span></div>${frozen ? `<div class="lab-perturbation"><span>APPLIED TO THIS INPUT</span><p>${esc(frozen.perturbation?.description || '')}</p><strong>${num(frozen.perturbation?.changedPoints)} glucose readings changed</strong></div>` : ''}</section>
      <section class="card lab-receipt-card"><div class="lab-receipt-heading"><span class="eyebrow">REPRODUCIBILITY RECEIPT</span>${icon('record')}</div>${receipt ? `<p class="receipt-id">${esc(frozen.challengeId)}</p><dl class="lab-receipt-summary">${receiptField('Latest observation used', timestampLabel(receipt.latestUsedTimestamp))}${receiptField('Feature window', `${timestampLabel(receipt.featureWindow?.startTimestamp)} → ${timestampLabel(receipt.featureWindow?.endTimestamp)}`)}${receiptField('Model version', receipt.modelVersion)}</dl><details class="lab-receipt-details"><summary>Inspect full provenance <span>+</span></summary><dl>${receiptField('Model SHA-256', receipt.modelSHA256, true)}${receiptField('Input SHA-256', receipt.inputSHA256, true)}${receiptField('Hash format', receipt.hashFormat || 'SHA-256 canonical JSON')}${receiptField('History length', `${receipt.featureWindow?.historyMinutes ?? '—'} minutes`)}${receiptField('Created', receipt.createdAt)}${receiptField('Expires', receipt.expiresAt)}</dl></details><button id="download-receipt" class="button button-secondary">${icon('download')}Download receipt <small>JSON</small></button><p class="lab-receipt-footnote">Hashes aid reproducibility; they are not digital signatures. The server retains this frozen challenge for one hour.</p><div class="receipt-verify"><span>VERIFY THE RECEIPT OFFLINE</span><p>From the repository folder, using your downloaded file:</p><code>node scripts/verify_receipt.mjs &quot;path/to/receipt.json&quot;</code></div>` : `<p class="receipt-empty">Freezing creates a receipt with the input hash, model hash, feature window and cutoff.</p><div class="receipt-preview"><span>INPUT SHA-256</span><i></i><span>MODEL SHA-256</span><i></i><span>OBSERVATION CUTOFF</span><i></i></div><p class="lab-receipt-footnote">Provenance is inspectable. It is not a guarantee of clinical validity.</p>`}</section>
      <button id="reset-experiment" class="lab-reset-button">${icon('reset')}Reset experiment</button></aside></div>
    <section id="stress-audit" class="card stress-audit" aria-labelledby="stress-title"></section>
    <div class="lab-boundary-note">${icon('info')}<p>All experiments use synthetic data. The UI hides future observations until reveal; the dataset is available in the repository, so this is not a secure blind trial. One selected window is not a cohort benchmark. No automatic drift detector or correction is claimed.</p></div>`;
  $$('input[name="challenge-mode"]', view).forEach(input => input.addEventListener('change', () => { challenge.mode = input.value; invalidateChallenge(); renderChallenge(); $(`#experiment-${challenge.mode}`).focus(); }));
  $('#freeze-prediction').addEventListener('click', freezeChallenge);
  $('#reveal-future')?.addEventListener('click', revealChallenge);
  $('#download-receipt')?.addEventListener('click', downloadChallengeReceipt);
  $('#reset-experiment').addEventListener('click', () => { invalidateChallenge(); renderChallenge(); $('#freeze-prediction').focus(); toast('Experiment cleared. Patient, cutoff and selected challenge are unchanged.'); });
  $('#lab-dismiss-error')?.addEventListener('click', () => { challenge.error = null; renderChallenge(); });
  $('#challenge-cursor').addEventListener('input', event => { const timestamp = patient.series[Number(event.target.value)].timestamp; $('#lab-cutoff-time').textContent = timestampLabel(timestamp); event.target.setAttribute('aria-valuetext', timestampLabel(timestamp)); });
  $('#challenge-cursor').addEventListener('change', event => { stopPlayback(); invalidateChallenge(); state.cursor = Number(event.target.value); $('#timeline-slider').value = state.cursor; renderTime(); renderChallenge(); loadPrediction(); });
  renderStressAudit();
  if (!challenge.stress && !challenge.stressLoading && !challenge.stressError) loadStressAudit();
}

async function freezeChallenge() {
  if (!state.patient || challenge.busy) return;
  stopPlayback();
  invalidateChallenge();
  const context = challengeContext();
  const generation = challenge.generation;
  challenge.context = context;
  challenge.busy = 'freeze';
  challenge.controller = new AbortController();
  const cutoffTimestamp = state.patient.series[state.cursor].timestamp;
  const body = { patientId: state.patient.id, cursor: state.cursor, mode: challenge.mode };
  renderChallenge();
  try {
    const result = await request('/api/challenge', { method: 'POST', body: JSON.stringify(body), signal: challenge.controller.signal });
    if (generation !== challenge.generation || context !== challengeContext()) return;
    if (result.receipt?.patientId !== body.patientId || Date.parse(result.receipt?.cutoffTimestamp) !== Date.parse(cutoffTimestamp)) throw new Error('The returned receipt does not match this patient and cutoff. Reset and try again.');
    challenge.frozen = result;
    toast(result.prediction?.abstained ? 'Prediction frozen as an abstention. Inspect the data-quality reason.' : 'Prediction frozen. The recorded future has not been revealed.');
  } catch (error) { if (error.name !== 'AbortError' && generation === challenge.generation) challenge.error = `The prediction could not be frozen. ${error.message}`; }
  finally { if (generation === challenge.generation) { challenge.busy = null; renderChallenge(); $('#lab-results-title')?.focus({ preventScroll: true }); } }
}

async function revealChallenge() {
  if (!challenge.frozen || challenge.busy || challenge.context !== challengeContext()) return;
  const generation = challenge.generation;
  const challengeId = challenge.frozen.challengeId;
  challenge.busy = 'reveal';
  challenge.error = null;
  challenge.controller = new AbortController();
  renderChallenge();
  try {
    const result = await request('/api/challenge/reveal', { method: 'POST', body: JSON.stringify({ challengeId, challengeToken: challenge.frozen.challengeToken }), signal: challenge.controller.signal });
    if (generation !== challenge.generation || challenge.context !== challengeContext()) return;
    if (result.challengeId !== challengeId || result.receipt?.patientId !== state.patient.id || Date.parse(result.receipt?.cutoffTimestamp) !== Date.parse(challenge.frozen.receipt.cutoffTimestamp)) throw new Error('The revealed record does not match this frozen challenge. Reset the experiment.');
    challenge.revealed = result;
    toast(result.abstained ? 'No numerical comparison is available: the model withheld its forecast.' : 'Recorded future revealed. These results describe this selected window only.');
  } catch (error) { if (error.name !== 'AbortError' && generation === challenge.generation) challenge.error = `The recorded future could not be revealed. ${error.message}`; }
  finally { if (generation === challenge.generation) { challenge.busy = null; renderChallenge(); $('#lab-comparison-title')?.focus({ preventScroll: true }); } }
}

function renderChallengeComparison(result) {
  const comparisons = Array.isArray(result.comparisons) ? result.comparisons : [];
  if (result.abstained) return `<section class="card lab-comparison-card"><div class="lab-result-heading"><div><div class="eyebrow">03 / REVEAL RESULT</div><h3 id="lab-comparison-title" tabindex="-1">An abstention, not a zero.</h3></div>${icon('shield')}</div><div class="lab-abstention-result"><p>The model withheld its forecast for this input. There is no prediction to score against the future, so risk, forecast error and interval coverage remain unavailable.</p><p>Returning a number here would hide the failure to meet data-quality requirements. Try Clean replay or a shorter gap to inspect a numerical comparison.</p></div></section>`;
  if (!comparisons.length) return '<section class="card lab-comparison-card"><div class="lab-result-heading"><div><div class="eyebrow">03 / REVEAL RESULT</div><h3 id="lab-comparison-title" tabindex="-1">No recorded future available.</h3></div></div><div class="lab-abstention-result"><p>The record does not contain later observations for a numerical comparison at this cutoff. The frozen forecast remains available in its receipt. Choose an earlier replay moment to compare it with recorded outcomes.</p></div></section>';
  const summary = result.summary || {};
  const event = result.event;
  const hitCount = comparisons.filter(point => point.covered === true).length;
  const scoredIntervals = comparisons.filter(point => typeof point.covered === 'boolean').length;
  const statistic = (label, value, note) => `<div><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
  return `<section class="card lab-comparison-card"><div class="lab-result-heading"><div><div class="eyebrow">03 / THE ORIGINAL RECORDED FUTURE</div><h3 id="lab-comparison-title" tabindex="-1">How did the estimate hold up?</h3></div><span class="neutral-tag">SELECTED WINDOW ONLY</span></div><div class="lab-comparison-metrics">${statistic('Frozen model MAE', num(summary.mae, 2), 'mg/dL · available horizons')}${statistic('Persistence MAE', num(summary.persistenceMae, 2), 'mg/dL · last-value baseline')}${statistic('Inside the interval', `${hitCount} / ${scoredIntervals}`, 'observations · nominal 90% band')}</div><div class="lab-chart-legend"><span><i class="legend-dashed"></i>Frozen forecast</span><span><i class="legend-actual"></i>Recorded future</span><span><i class="legend-persistence"></i>Persistence</span></div><div class="challenge-chart">${challengeComparisonChart(comparisons)}</div><div class="table-scroll"><table class="lab-horizon-table"><caption class="sr-only">Frozen forecasts compared with the original unmodified future at each horizon</caption><thead><tr><th scope="col">Horizon</th><th scope="col">Forecast</th><th scope="col">Observed</th><th scope="col">Abs. error</th><th scope="col">90% interval</th><th scope="col">Interval hit</th><th scope="col">Persistence error</th></tr></thead><tbody>${comparisons.map(point => `<tr><th scope="row">+${num(point.minutes)} min</th><td>${num(point.predicted, 1)}</td><td class="observed-cell">${num(point.observed, 1)}</td><td>${num(point.absoluteError, 1)}</td><td>${num(point.lower, 1)}–${num(point.upper, 1)}</td><td><span class="interval-result ${point.covered === true ? 'interval-in' : 'interval-out'}">${point.covered === true ? 'Inside' : point.covered === false ? 'Outside' : 'Unavailable'}</span></td><td>${num(point.persistenceAbsoluteError, 1)}</td></tr>`).join('')}</tbody></table></div><p class="lab-table-note">All glucose values and errors are in mg/dL. Persistence repeats the last usable input reading. These ${num(summary.availableHorizons)} horizons are one correlated window, not independent test cases.</p>${event ? `<div class="lab-event-result"><div><span>FROZEN +2H EVENT PROBABILITY</span><strong>${esc(probabilityLabel(event.risk, 1))}</strong></div><span class="lab-event-arrow">→</span><div><span>ORIGINAL +2H OUTCOME</span><strong>${event.outcome === true ? 'Threshold met' : event.outcome === false ? 'Threshold not met' : 'Unavailable'}</strong><p>${num(event.observed, 1)} mg/dL observed · threshold ${num(event.thresholdMgDl)} mg/dL</p></div></div>` : '<p class="lab-inline-note">The +2-hour outcome is unavailable at this cutoff.</p>'}${result.limitations?.length ? `<details class="lab-result-limitations"><summary>How to interpret this comparison</summary><ul>${result.limitations.map(text => `<li>${esc(text)}</li>`).join('')}</ul></details>` : ''}</section>`;
}

function challengeComparisonChart(points) {
  const numeric = points.filter(point => isNumber(point.predicted) && isNumber(point.observed));
  if (!numeric.length) return '<p class="empty-state">No numeric comparison is available.</p>';
  const W = 720, H = 244, L = 46, R = 27, T = 22, B = 35;
  const values = numeric.flatMap(point => [point.predicted, point.observed, point.lower, point.upper, point.persistence]).filter(isNumber);
  const min = Math.floor((Math.min(...values) - 10) / 20) * 20;
  const max = Math.ceil((Math.max(...values) + 10) / 20) * 20;
  const y = value => T + (max - value) / (max - min) * (H - T - B);
  const x = minutes => L + (minutes - 30) / 90 * (W - L - R);
  const line = field => numeric.filter(point => isNumber(point[field])).map((point, index) => `${index ? 'L' : 'M'}${x(point.minutes)},${y(point[field])}`).join(' ');
  const band = [...numeric.map(point => `${x(point.minutes)},${y(point.upper)}`), ...[...numeric].reverse().map(point => `${x(point.minutes)},${y(point.lower)}`)].join(' ');
  const ticks = []; const step = max - min > 200 ? 60 : 40;
  for (let value = Math.ceil(min / step) * step; value <= max; value += step) ticks.push(value);
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Frozen forecast, recorded future and persistence across 30 to 120 minutes. Exact values are provided in the table below.">${ticks.map(value => `<line x1="${L}" x2="${W - R}" y1="${y(value)}" y2="${y(value)}" stroke="#e5eadf"/><text x="${L - 10}" y="${y(value) + 4}" class="chart-axis" text-anchor="end">${value}</text>`).join('')}<polygon points="${band}" fill="#e6eddd"/><path d="${line('persistence')}" fill="none" stroke="#9d9f8f" stroke-width="1.5" stroke-dasharray="3 5"/><path d="${line('predicted')}" fill="none" stroke="#5b8254" stroke-width="2" stroke-dasharray="6 5"/><path d="${line('observed')}" fill="none" stroke="#b66b4d" stroke-width="2.5"/>${numeric.map(point => `<circle cx="${x(point.minutes)}" cy="${y(point.predicted)}" r="3.5" fill="#fff" stroke="#5b8254" stroke-width="1.5"><title>Frozen +${point.minutes}min: ${num(point.predicted, 1)} mg/dL</title></circle><circle cx="${x(point.minutes)}" cy="${y(point.observed)}" r="4" fill="#fff" stroke="#b66b4d" stroke-width="2"><title>Observed +${point.minutes}min: ${num(point.observed, 1)} mg/dL</title></circle><text x="${x(point.minutes)}" y="${H - 11}" text-anchor="middle" class="chart-axis">+${point.minutes} min</text>`).join('')}<text x="${L}" y="12" class="chart-label">GLUCOSE · mg/dL</text></svg>`;
}

function downloadChallengeReceipt() {
  if (!challenge.frozen || challenge.context !== challengeContext()) return;
  const { challengeToken, ...frozenReceipt } = challenge.frozen;
  const receipt = { schemaVersion: 1, challenge: frozenReceipt, reveal: challenge.revealed || null };
  const url = URL.createObjectURL(new Blob([JSON.stringify(receipt, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = `AURA-challenge-${state.patient.id}-${challenge.mode}-${time(challenge.frozen.receipt.cutoffTimestamp).replace(':', '')}.json`;
  document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast(challenge.revealed ? 'Receipt download requested with frozen prediction and revealed comparison.' : 'Frozen receipt download requested. No future comparison has been revealed.');
}

async function loadStressAudit() {
  if (challenge.stressLoading) return;
  challenge.stressLoading = true; challenge.stressError = null; renderStressAudit();
  try { challenge.stress = await request('/api/stress'); }
  catch (error) { challenge.stressError = error.message; }
  finally { challenge.stressLoading = false; renderStressAudit(); }
}

function renderStressAudit() {
  const container = $('#stress-audit');
  if (!container) return;
  if (state.robustness) { container.innerHTML = routineRobustnessHTML(); return; }
  if (state.prediction?.driverMethod === 'group_reference_sensitivity') {
    container.innerHTML = robustnessPendingHTML();
    $('[data-retry-robustness]', container)?.addEventListener('click', loadRobustness);
    if (!state.robustnessLoading && !state.robustnessError) loadRobustness();
    return;
  }
  const stress = challenge.stress;
  container.innerHTML = `<div class="stress-heading"><div><div class="eyebrow">BEYOND A SINGLE WINDOW</div><h3 id="stress-title">When the routine changes, the model can break.</h3><p>A separate synthetic stress audit with the existing frozen model. No retraining, automatic drift detection or correction.</p></div><span class="stress-audit-badge">ROUTINE SHIFT AUDIT</span></div>${stress ? `<div class="table-scroll"><table class="stress-table"><thead><tr><th scope="col">Synthetic test condition</th><th scope="col">+2h MAE<br><small>mg/dL · lower is better</small></th><th scope="col">90% interval coverage<br><small>measured, not guaranteed</small></th><th scope="col">Event recall<br><small>frozen review threshold</small></th><th scope="col">Patients / windows</th></tr></thead><tbody>${(stress.cases || []).map((item, index) => `<tr class="${index ? 'stress-shift-row' : 'stress-reference-row'}"><th scope="row"><span class="stress-row-index">0${index + 1}</span>${esc(item.title)}</th><td>${num(item.mae, 2)}</td><td>${pct(item.intervalCoverage, 1)}</td><td>${pct(item.recall, 1)}</td><td>${num(item.patients)} / ${num(item.windows)}</td></tr>`).join('')}</tbody></table></div><div class="stress-interpretation">${icon('alert')}<p><strong>Clock dependence is a failure mode.</strong> A model that benefits from regular simulated meal times can lose accuracy and interval coverage when those routines shift. Nominal 90% bands do not guarantee 90% coverage under a changed data distribution.</p></div>${stress.limitations?.length ? `<details class="lab-result-limitations"><summary>Audit protocol and limits</summary><p>${esc(typeof stress.protocol === 'string' ? stress.protocol : JSON.stringify(stress.protocol))}</p><ul>${stress.limitations.map(text => `<li>${esc(text)}</li>`).join('')}</ul></details>` : ''}` : challenge.stressError ? `<div class="lab-stress-error"><p>The audit could not be loaded. ${esc(challenge.stressError)}</p><button id="retry-stress" class="button button-secondary">Reload audit</button></div>` : '<div class="chart-loading lab-stress-loading"><span class="loading-ring"></span>Loading the frozen-model stress audit…</div>'}`;
  $('#retry-stress')?.addEventListener('click', loadStressAudit);
}

function robustnessPendingHTML() {
  return state.robustnessError ? `<div class="stress-heading"><div><div class="eyebrow">ROUTINE ROBUSTNESS</div><h3>Measured evidence is unavailable.</h3><p>No performance claim is shown without the evaluation artifact. ${esc(state.robustnessError)}</p></div></div><button class="button button-secondary" data-retry-robustness>Reload robustness evidence</button>` : '<div class="chart-loading lab-stress-loading"><span class="loading-ring"></span>Loading the measured routine-robustness evaluation…</div>';
}

async function loadRobustness() {
  if (state.robustnessLoading) return;
  state.robustnessLoading = true;
  state.robustnessError = null;
  try {
    const result = await request('/api/robustness');
    if (!Array.isArray(result.cases) || !result.aggregate?.models?.fused) throw new Error('The robustness artifact has an unsupported format.');
    if (state.prediction?.modelVersion && result.modelVersion !== state.prediction.modelVersion) throw new Error('The evaluation version does not match the loaded model. Reload after the model update finishes.');
    state.robustness = result;
  } catch (error) { state.robustnessError = error.message; }
  finally {
    state.robustnessLoading = false;
    renderStressAudit();
    renderRobustnessEvidence();
  }
}

function renderRobustnessEvidence() {
  const container = $('#robustness-evidence');
  if (!container) return;
  container.innerHTML = state.robustness ? routineRobustnessHTML() : robustnessPendingHTML();
  $('[data-retry-robustness]', container)?.addEventListener('click', loadRobustness);
}

function routineRobustnessHTML() {
  const data = state.robustness;
  const aggregate = data.aggregate;
  const fused = aggregate.models.fused;
  const baselineKey = aggregate.models.legacyV2 ? 'legacyV2' : 'legacyV1';
  const baselineLabel = baselineKey === 'legacyV2' ? 'Frozen v2' : 'Original v1';
  const currentVersion = String(data.modelVersion || '').match(/(?:^|-)(\d+)\./)?.[1];
  const currentLabel = currentVersion ? `Current v${currentVersion}` : 'Current model';
  const differences = aggregate.pairedDifferences || {};
  const baselineDifference = differences[baselineKey] || {};
  const signed = value => isNumber(value) ? `${value > 0 ? '+' : ''}${num(value, 2)}` : '—';
  const ci = values => Array.isArray(values) ? `${signed(values[0])} to ${signed(values[1])}` : 'Not available';
  const metric = (label, value, note) => `<div><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
  const protocol = data.protocol || {};
  const hasHeldOutCombination = Boolean(protocol.heldOutCombination && data.cases.some(condition => condition.id === protocol.heldOutCombination.id));
  const routineBoundary = hasHeldOutCombination ? 'Primary scores below pool six familiar routine families. The held-out combination is reported separately in the table and excluded from those primary scores. It tests a new parameter combination within the same simulator, not new physiology or a clinical population.' : 'The routine families appeared in training; this evaluates new identities, not unseen routine families.';
  const counts = protocol.splits ? Object.fromEntries(Object.entries(protocol.splits).map(([name, ids]) => [name, Array.isArray(ids) ? ids.length : null])) : {};
  const selectedModel = (condition, name) => condition.models?.[name] || {};
  const variableCase = data.cases.find(condition => condition.id === 'variable_routine');
  const variableLimits = variableCase?.models?.fused;
  const regressions = data.cases.map(condition => {
    const current = confusionCounts(condition.models?.fused), previous = confusionCounts(condition.models?.[baselineKey]);
    if (!current || !previous || current.total !== previous.total) return '';
    const increases = [];
    if (current.fn > previous.fn) increases.push(`${num(current.fn - previous.fn)} more missed-positive windows`);
    if (current.fp > previous.fp) increases.push(`${num(current.fp - previous.fp)} more false-positive windows`);
    return increases.length ? `${esc(condition.title)}: ${increases.join(' and ')}.` : '';
  }).filter(Boolean);
  return `<div class="stress-heading robustness-heading"><div><div class="eyebrow">ROUTINE ROBUSTNESS / FROZEN MODEL</div><h3>Different days. Measured against the same record.</h3><p>The current model and its comparators share ${num(aggregate.patients)} fresh synthetic identities across ${num(data.cases.length)} predefined routines. ${routineBoundary}</p></div><span class="robustness-version">${esc(data.modelVersion)}<small>No absolute-clock inputs</small></span></div>
    <div class="robustness-summary">${metric(currentLabel + ' +2h MAE', num(fused.mae, 2), hasHeldOutCombination ? 'mg/dL · six familiar routine families' : 'mg/dL · all declared routines')}${metric('Change vs ' + baselineLabel, signed(baselineDifference.meanDifference), `mg/dL · current minus previous<br>95% paired CI ${ci(baselineDifference.patientBootstrap95CI)}`)}${metric('Fusion vs wearables only', signed(differences.sensorOnly?.meanDifference), `mg/dL · fused minus sensors<br>95% paired CI ${ci(differences.sensorOnly?.patientBootstrap95CI)}`)}${metric('Interval width', num(fused.intervalMeanWidth, 1), `mg/dL · ${pct(fused.intervalCoverage, 1)} pooled coverage<br>Nominal coverage: 90%`)}</div>
    <div class="robustness-key"><span>${icon('layers')}EHR + past physiology</span><span>${icon('clock')}No future meals or clock features</span><span>${icon('shield')}Frozen before final evaluation</span></div>
    ${alertComparisonHTML(fused, aggregate.models[baselineKey], currentLabel, baselineLabel, aggregate.pairedDecisionDifferences)}${regressions.length ? `<div class="robustness-regressions">${icon('alert')}<div><strong>Routine-level regressions remain.</strong><p>Compared with ${esc(baselineLabel)} at each model’s frozen review threshold: ${regressions.join(' ')}</p></div></div>` : ''}<div class="table-scroll"><table class="robustness-table"><caption class="sr-only">Fresh-identity synthetic evaluation by routine, comparing original and revised models with ablations and persistence</caption><thead><tr><th scope="col">Synthetic routine</th><th scope="col">${esc(baselineLabel)} MAE<br><small>mg/dL</small></th><th scope="col">${esc(currentLabel)} MAE<br><small>mg/dL</small></th><th scope="col">Wearables MAE<br><small>mg/dL</small></th><th scope="col">Persistence MAE<br><small>mg/dL</small></th><th scope="col">Current coverage<br><small>nominal 90%</small></th><th scope="col">Interval width<br><small>mg/dL</small></th><th scope="col">Event recall<br><small>fixed threshold</small></th><th scope="col">Event precision<br><small>false-alert tradeoff</small></th></tr></thead><tbody>${data.cases.map((condition, index) => `<tr class="${condition.id === protocol.heldOutCombination?.id ? 'robustness-heldout' : ''}"><th scope="row"><span class="stress-row-index">0${index + 1}</span>${esc(condition.title)}<small>${condition.id === protocol.heldOutCombination?.id ? 'Outside primary aggregate · ' : ''}${num(condition.patients)} identities · ${num(condition.windows)} windows</small></th><td>${num(selectedModel(condition, baselineKey).mae, 2)}</td><td class="revised-value">${num(selectedModel(condition, 'fused').mae, 2)}</td><td>${num(selectedModel(condition, 'sensorOnly').mae, 2)}</td><td>${num(selectedModel(condition, 'persistence').mae, 2)}</td><td>${pct(selectedModel(condition, 'fused').intervalCoverage, 1)}</td><td>${num(selectedModel(condition, 'fused').intervalMeanWidth, 1)}</td><td>${pct(selectedModel(condition, 'fused').recall, 1)}</td><td>${pct(selectedModel(condition, 'fused').precision, 1)}</td></tr>`).join('')}</tbody></table></div>
    ${routineAlertComparisonHTML(data.cases, baselineKey, currentLabel, baselineLabel, protocol.heldOutCombination?.id)}<div class="robustness-interpretation"><div>${icon('info')}<p><strong>Read both error and uncertainty.</strong> Negative paired MAE differences favor the revised model. Wider bands can improve coverage without improving the point forecast. Repeated windows and routine variants are correlated; confidence intervals resample patient identities.</p></div><div>${icon('alert')}<p><strong>Unknown future meals are still unknown.</strong> The model sees only past measurements. An unexpected meal, changed sleep or new activity may still produce a missed event.${variableLimits ? ` The variable-routine case has ${pct(variableLimits.recall, 2)} recall, ${pct(variableLimits.precision, 2)} precision and ${pct(variableLimits.intervalCoverage, 1)} interval coverage.` : ''} No clinical validation or automatic drift correction is claimed.</p></div></div>
    <details class="robustness-protocol"><summary>Inspect selection, calibration and final-evaluation boundaries <span>+</span></summary><div class="robustness-protocol-grid"><div><span>Identity splits</span><p>${num(counts.train)} training · ${num(counts.selection)} selection · ${num(counts.calibration)} calibration · ${num(counts.test)} final</p></div><div><span>Regressor selection</span><p>${esc(protocol.regressionSelection || 'See the exported protocol.')}</p></div><div><span>Classifier selection</span><p>${esc(protocol.classificationSelection || 'See the exported protocol.')}</p></div><div><span>Calibration</span><p>${esc(protocol.calibration || 'Separate calibration identities.')}</p></div><div><span>Freeze boundary</span><p>${esc(protocol.finalLock || 'Model frozen before final evaluation.')}</p></div><div><span>Final model SHA-256</span><code>${esc(data.modelSHA256)}</code></div></div><ul>${(data.limitations || []).map(text => `<li>${esc(text)}</li>`).join('')}</ul></details>`;
}

function confusionCounts(result) {
  const matrix = result?.alertPolicy?.testConfusionMatrix ?? result?.confusionMatrix;
  if (!Array.isArray(matrix) || matrix.length !== 2 || matrix.some(row => !Array.isArray(row) || row.length !== 2 || row.some(value => !Number.isInteger(value) || value < 0))) return null;
  const [[tn, fp], [fn, tp]] = matrix;
  return { tn, fp, fn, tp, total: tn + fp + fn + tp };
}

function routineAlertComparisonHTML(cases, baselineKey, currentLabel, previousLabel, heldOutId) {
  const rows = cases.map(condition => {
    const current = confusionCounts(condition.models?.fused), previous = confusionCounts(condition.models?.[baselineKey]);
    if (!current || !previous || current.total !== previous.total) return '';
    return `<tr class="${condition.id === heldOutId ? 'robustness-heldout' : ''}"><th scope="row">${esc(condition.title)}<small>${num(current.total)} overlapping windows${condition.id === heldOutId ? ' · outside primary aggregate' : ''}</small></th><td>${num(previous.fn)}</td><td>${num(current.fn)}</td><td>${num(previous.fp)}</td><td>${num(current.fp)}</td></tr>`;
  }).join('');
  if (!rows) return '';
  return `<details class="robustness-alert-details"><summary>Compare missed and false-positive windows for every routine <span>+</span></summary><p>Every row uses the same patients and times for both models, with each model’s own frozen global review threshold. Counts are correlated windows, not separate clinical events.</p><div class="table-scroll"><table class="robustness-table"><caption class="sr-only">Previous and current missed-positive and false-positive window counts for every routine</caption><thead><tr><th scope="col">Routine</th><th scope="col">${esc(previousLabel)}<br><small>Missed positive windows</small></th><th scope="col">${esc(currentLabel)}<br><small>Missed positive windows</small></th><th scope="col">${esc(previousLabel)}<br><small>False-positive windows</small></th><th scope="col">${esc(currentLabel)}<br><small>False-positive windows</small></th></tr></thead><tbody>${rows}</tbody></table></div></details>`;
}

function alertComparisonHTML(current, previous, currentLabel, previousLabel, pairedDecisions = {}) {
  const currentCounts = confusionCounts(current), previousCounts = confusionCounts(previous);
  if (!currentCounts || !previousCounts || currentCounts.total !== previousCounts.total || currentCounts.tp + currentCounts.fn !== previousCounts.tp + previousCounts.fn) return '';
  const threshold = result => result?.threshold ?? result?.alertPolicy?.threshold;
  const recall = result => result?.alertPolicy?.testRecall ?? result?.recall;
  const precision = result => result?.alertPolicy?.testPrecision ?? result?.precision;
  const countChange = (key, label) => {
    const delta = currentCounts[key] - previousCounts[key];
    const interval = pairedDecisions[key === 'fn' ? 'falseNegativeWindows' : 'falsePositiveWindows']?.patientBootstrap95CI;
    const intervalNote = Array.isArray(interval) && interval.length === 2 && interval.every(isNumber) ? `<p>95% paired patient-bootstrap CI: ${num(interval[0], 1)} to ${num(interval[1], 1)} windows (current minus previous).${interval[0] <= 0 && interval[1] >= 0 ? ' Includes zero; the direction of change is uncertain.' : ''}</p>` : '';
    return `<div class="alert-change"><span>${label}</span><div><small>${num(previousCounts[key])}</small><span aria-hidden="true">→</span><strong>${num(currentCounts[key])}</strong></div><p>${delta === 0 ? 'Unchanged count' : `${num(Math.abs(delta))} ${delta < 0 ? 'fewer' : 'more'} windows`} · ${esc(previousLabel)} to ${esc(currentLabel)}</p>${intervalNote}</div>`;
  };
  const row = (label, oldValue, newValue) => `<tr><th scope="row">${label}</th><td>${oldValue}</td><td>${newValue}</td></tr>`;
  return `<section class="alert-comparison" aria-label="Frozen model review-policy comparison"><div class="alert-comparison-heading"><div class="eyebrow">THE REVIEW-POLICY TRADEOFF</div><h3>Missed events. False alerts. Both matter.</h3><p>Compare each model at its own frozen operating threshold on the same ${num(currentCounts.total)} synthetic windows. A threshold change can change these counts independently of forecast accuracy.</p></div><div class="alert-change-grid">${countChange('fn', 'Missed events · false negatives')}${countChange('fp', 'False alerts · false positives')}</div><div class="table-scroll"><table class="alert-comparison-table"><caption class="sr-only">Confusion counts and frozen thresholds for the previous and current models</caption><thead><tr><th scope="col">Review policy</th><th scope="col">${esc(previousLabel)}</th><th scope="col">${esc(currentLabel)}</th></tr></thead><tbody>${row('Frozen probability threshold', pct(threshold(previous), 2), pct(threshold(current), 2))}${row('Events detected · true positives', num(previousCounts.tp), num(currentCounts.tp))}${row('Correct non-alerts · true negatives', num(previousCounts.tn), num(currentCounts.tn))}${row('Event recall', pct(recall(previous), 1), pct(recall(current), 1))}${row('Alert precision', pct(precision(previous), 1), pct(precision(current), 1))}${row('Brier score · lower is better', num(previous.brier, 4), num(current.brier, 4))}</tbody></table></div><p class="alert-comparison-note">Counts are overlapping replay windows, not unique clinical episodes or people. A false alert means the +120-minute glucose threshold was not met; it does not establish that an intervention was needed.</p></section>`;
}

function stopPlayback() {
  state.playing = false;
  clearTimeout(state.timer);
  $('#play-button').innerHTML = icon('play');
  $('#play-button').setAttribute('aria-label', 'Play simulated data stream');
}
async function playbackTick() {
  if (!state.playing) return;
  invalidateChallenge();
  const max = Number($('#timeline-slider').max);
  if (state.cursor >= max) { stopPlayback(); toast('Replay complete for this simulated day.'); return; }
  state.cursor += 1;
  $('#timeline-slider').value = state.cursor;
  renderTime();
  await loadPrediction();
  if (state.playing) state.timer = setTimeout(playbackTick, 1100);
}

function saveNotes(notify = true) {
  clearTimeout(state.notesDebounce);
  if (!state.patient) return;
  const content = $('#clinical-notes').value;
  if (localGet(`notes:${state.patient.id}`) === content && !notify) return;
  const saved = localSet(`notes:${state.patient.id}`, content);
  $('#notes-status').textContent = saved ? 'Saved on this device · available when you return.' : 'Browser storage unavailable. Copy your note before leaving.';
  if (notify) toast(saved ? 'Patient note saved on this device.' : 'Unable to save the note. Browser storage is unavailable.');
}

function exportSummary() {
  if (!state.patient || !state.prediction) return;
  saveNotes(false);
  const patient = state.patient, prediction = state.prediction;
  const treeDrivers = prediction.driverMethod === 'group_reference_sensitivity';
  const timestamp = patient.series[state.cursor].timestamp;
  const rows = prediction.forecast.map(point => `<tr><td>+${point.minutes} min</td><td>${num(point.glucose, 1)} mg/dL</td><td>${num(point.lower, 1)}–${num(point.upper, 1)} mg/dL</td></tr>`).join('');
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AURA Twin · ${esc(patient.name)} · Research summary</title><style>body{font:14px/1.7 'Segoe UI',sans-serif;max-width:800px;margin:50px auto;padding:0 30px;color:#1c3b2d}h1,h2{font-family:Georgia,serif;font-weight:400}h1{font-size:35px;line-height:1.3}h2{font-size:23px;margin-top:30px}small{color:#74876b}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:11px 8px;text-align:left;border-bottom:1px solid #dce6d4}th{color:#6a805c;font-weight:500}section{border-top:1px solid #dce6d4;margin-top:24px;padding-top:4px}.notice{padding:16px;background:#edf3e7;border:1px solid #dce7d2}.notes{white-space:pre-wrap}.footer{font-size:11px;color:#81936f;margin-top:30px}@media print{body{margin:20px auto}.notice{background:white}}</style></head><body><small>AURA / TWIN · BLACK SQUAD · AMRITA, CHENNAI</small><h1>Patient twin observation</h1><div class="notice"><strong>Synthetic data · Research prototype · Not for clinical use</strong><br>Fictional patient and observations. No diagnosis or treatment recommendation.</div><h2>${esc(patient.name)}</h2><p>${esc(patient.id)} · ${esc(patient.age)} years · ${esc(patient.sex)}<br>Replay time: ${date(timestamp)} · ${time(timestamp)} UTC<br>Model: ${esc(prediction.modelVersion)}</p><section><h2>Current observation</h2><p>Glucose ${num(prediction.current.glucose, 1)} mg/dL · Heart rate ${num(prediction.current.hr)} bpm · HRV ${num(prediction.current.hrv)} ms<br>Trailing 24 hours: ${num(prediction.current.sleep, 1)} hours sleep · ${num(prediction.current.steps)} steps</p><p><strong>Baseline model probability: ${esc(probabilityLabel(prediction.risk, 1))}</strong><br>Target: glucose ≥180 mg/dL at exactly +120 minutes.<br>${prediction.abstained ? `Forecast withheld: ${esc((prediction.quality?.reasons || []).join(' '))}` : `Review threshold: ${pct(prediction.alert?.threshold, 2)}. ${esc(prediction.alert?.label || '')}.`}</p></section><section><h2>${prediction.scenario?.active ? 'Illustrative scenario' : 'Glucose forecast'}</h2>${prediction.scenario?.active ? `<p class="notice">Additional carbohydrates ${state.scenario.mealCarbs} g; additional activity ${state.scenario.activityMinutes} minutes. Arithmetic sensitivity only, not a causal estimate. Trained baseline risk is unchanged. Shifted intervals have no measured coverage.</p>` : '<p>Nominal 90% residual intervals. They are not guaranteed for this patient.</p>'}<table><thead><tr><th>Horizon</th><th>Glucose</th><th>Interval</th></tr></thead><tbody>${rows || '<tr><td colspan="3">Forecast withheld due to insufficient data.</td></tr>'}</tbody></table></section><section><h2>Historical context</h2><p>HbA1c ${num(patient.ehr.hba1c, 1)}% · BMI ${num(patient.ehr.bmi, 1)} kg/m² · LDL ${num(patient.ehr.ldl)} mg/dL · Diabetes history ${num(patient.ehr.diabetesYears, 1)} years</p><p>${(patient.ehr.diagnoses || []).map(esc).join(', ')}</p></section><section><h2>${treeDrivers ? 'Reference sensitivity' : 'Model associations'}</h2><table><thead><tr><th>Feature group</th><th>Source</th><th>${treeDrivers ? 'Risk sensitivity · percentage points' : 'Log-odds contribution'}</th></tr></thead><tbody>${(prediction.drivers || []).map(driver => `<tr><td>${esc(driver.name)}</td><td>${esc(driver.source)}</td><td>${driver.contribution >= 0 ? '+' : ''}${num(driver.contribution, 3)}</td></tr>`).join('')}</tbody></table><p>${esc(prediction.driverExplanation || 'Associations relative to training feature means; not causal effects.')}</p></section><section><h2>Clinician observation</h2><p class="notes">${esc($('#clinical-notes').value || 'No note recorded.')}</p><p>${localGet(`ack:${patient.id}:${state.cursor}`) ? 'Observation acknowledged in this browser.' : 'Observation not acknowledged.'}</p></section><p class="footer">All results concern a designed synthetic generator. No external, prospective or clinical validation. Exported ${esc(new Date().toISOString())}. Open this HTML file in a browser to print or save as PDF.</p></body></html>`;
  const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `AURA-summary-${patient.id}-${time(timestamp).replace(':', '')}.html`;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('Summary downloaded. Open it to print or save as PDF.');
}

hydrateIcons();
$$('[data-tab]').forEach(button => button.addEventListener('click', () => setTab(button.dataset.tab)));
$$('[role="tab"]').forEach(button => button.addEventListener('keydown', event => {
  const tabs = ['overview', 'record', 'evidence', 'challenge'];
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); setTab(tabs[(tabs.indexOf(state.tab) + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length], true); }
  if (event.key === 'Home') { event.preventDefault(); setTab('overview', true); }
  if (event.key === 'End') { event.preventDefault(); setTab('challenge', true); }
}));
$('#patient-search').addEventListener('input', renderPatientList);
$('#menu-toggle').addEventListener('click', () => { const open = $('#sidebar').classList.toggle('is-open'); $('#menu-toggle').setAttribute('aria-expanded', String(open)); });
document.addEventListener('pointerdown', event => { if (window.innerWidth <= 700 && !event.target.closest('#sidebar, #menu-toggle')) { $('#sidebar').classList.remove('is-open'); $('#menu-toggle').setAttribute('aria-expanded', 'false'); } });
document.addEventListener('keydown', event => {
  if (event.key === '/' && !event.target.matches('input,textarea') && !$('#guide-dialog').open) { event.preventDefault(); if (window.innerWidth <= 700) { $('#sidebar').classList.add('is-open'); $('#menu-toggle').setAttribute('aria-expanded', 'true'); } $('#patient-search').focus(); }
  if (event.key === 'Escape') { $('#sidebar').classList.remove('is-open'); $('#menu-toggle').setAttribute('aria-expanded', 'false'); }
});
$('#guide-button').addEventListener('click', () => { stopPlayback(); $('#guide-dialog').showModal(); });
$('#close-guide').addEventListener('click', () => $('#guide-dialog').close());
$('#start-exploring').addEventListener('click', () => $('#guide-dialog').close());
$('#guide-dialog').addEventListener('click', event => { if (event.target === $('#guide-dialog')) { const bounds = event.target.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) event.target.close(); } });
$('#timeline-slider').addEventListener('input', () => {
  invalidateChallenge();
  stopPlayback();
  clearTimeout(state.timelineDebounce);
  state.request?.abort();
  state.requestId++;
  state.cursor = Number($('#timeline-slider').value);
  renderTime();
  $('#export-button').disabled = true;
  $('#glucose-chart').classList.add('updating');
  state.timelineDebounce = setTimeout(loadPrediction, 110);
});
$('#play-button').addEventListener('click', () => {
  if (state.playing) { stopPlayback(); return; }
  if (state.cursor >= Number($('#timeline-slider').max)) { state.cursor = Number($('#timeline-slider').min); $('#timeline-slider').value = state.cursor; }
  state.playing = true;
  $('#play-button').innerHTML = icon('pause');
  $('#play-button').setAttribute('aria-label', 'Pause simulated data stream');
  playbackTick();
});
$('#meal-slider').addEventListener('input', () => { $('#meal-value').textContent = `${$('#meal-slider').value} g`; });
$('#activity-slider').addEventListener('input', () => { $('#activity-value').textContent = `${$('#activity-slider').value} min`; });
$('#apply-scenario').addEventListener('click', async () => {
  stopPlayback();
  state.scenario = { mealCarbs: Number($('#meal-slider').value), activityMinutes: Number($('#activity-slider').value) };
  $('#apply-scenario').textContent = 'Calculating…';
  await loadPrediction();
  if (state.prediction) toast(state.prediction.scenario?.active ? 'Illustrative scenario applied. Baseline risk is unchanged.' : 'Baseline forecast restored.');
});
$('#reset-scenario').addEventListener('click', async () => {
  stopPlayback(); resetScenarioControls(); state.scenario = { mealCarbs: 0, activityMinutes: 0 };
  await loadPrediction();
  if (state.prediction) toast('Scenario reset to the baseline forecast.');
});
$('#clinical-notes').addEventListener('input', () => { $('#notes-status').textContent = 'Saving on this device…'; clearTimeout(state.notesDebounce); state.notesDebounce = setTimeout(() => saveNotes(false), 700); });
$('#save-notes').addEventListener('click', () => saveNotes(true));
$('#export-button').addEventListener('click', exportSummary);
window.addEventListener('beforeunload', () => { if (state.patient) saveNotes(false); });
let resizeTimer;
window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (state.prediction && state.tab === 'overview') renderChart(); }, 120); });
document.addEventListener('visibilitychange', () => { if (document.hidden) stopPlayback(); });
initialize();

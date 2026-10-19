/* AURA Twin — dependency-free clinical research workspace. */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const isNumber = value => typeof value === 'number' && Number.isFinite(value);
const num = (value, digits = 0) => isNumber(value) ? value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—';
const pct = (value, digits = 0) => isNumber(value) ? `${num(value * 100, digits)}%` : 'Unavailable';
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
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.info}</svg>`;
function hydrateIcons(root = document) { $$('[data-icon]', root).forEach(node => { node.innerHTML = icon(node.dataset.icon); }); }

const state = { patients: [], patient: null, prediction: null, metrics: null, metricsError: null, cursor: 0, tab: 'overview', scenario: { mealCarbs: 0, activityMinutes: 0 }, playing: false, timer: null, request: null, requestId: 0, timelineDebounce: null, notesDebounce: null, storageAvailable: true };
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
  $('#patient-header').innerHTML = `<div class="patient-header-avatar">${esc(patient.initials)}</div><div><h2 class="patient-header-name">${esc(patient.name)}</h2><div class="patient-demographics"><span>${esc(patient.id)}</span><i class="separator-dot"></i><span>${esc(patient.age)} years</span><i class="separator-dot"></i><span>${esc(patient.sex)}</span></div></div><div class="patient-header-tags"><span class="neutral-tag">Type 2 diabetes · simulated</span><span class="neutral-tag green">Digital twin connected</span></div><div class="patient-header-status"><span><i class="live-dot"></i>Replay connected</span><small>5-minute wearable cadence</small></div>`;
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
    clearError();
    renderTime();
    renderMetrics();
    renderChart();
    renderRisk();
    renderFusion();
    renderScenarioResult();
    if (state.tab === 'record') renderRecord();
    if (state.tab === 'evidence') renderEvidence();
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
  $('#risk-content').innerHTML = `<div class="risk-main"><div class="risk-number">${num(prediction.risk * 100)}<span>%</span></div><span class="risk-level ${triggered ? '' : 'low'}"><i class="live-dot"></i>${triggered ? 'Review suggested' : 'Below threshold'}</span></div><p class="risk-description">Model probability of glucose ≥180 mg/dL<br>at exactly <strong>+2 hours</strong>.</p><div class="risk-range"><span style="width:${prediction.risk * 100}%"></span></div><div class="risk-range-label"><span>0%</span><span>REVIEW THRESHOLD ${pct(threshold)}</span><span>100%</span></div><div class="risk-divider"></div><div class="drivers-caption">WHAT SHAPES THIS ESTIMATE<small>Model associations</small></div><div class="drivers-list">${drivers.map((driver, index) => `<div class="driver"><div class="driver-label"><span><span class="driver-rank">0${index + 1}</span>${esc(driver.name)}</span><span class="driver-value" title="${esc(driver.source)} · ${esc(driver.value)}">${driver.contribution >= 0 ? '+' : '−'}${num(Math.abs(driver.contribution), 2)}</span></div><div class="driver-track"><span class="${driver.contribution < 0 ? 'negative' : ''}" style="width:${Math.max(5, Math.abs(driver.contribution) / max * 100)}%"></span></div></div>`).join('')}</div><button id="acknowledge-button" class="acknowledge-button">${icon(acknowledgement ? 'check' : 'record')}${acknowledgement ? 'Observation acknowledged' : 'Acknowledge observation'}</button>${acknowledgement ? '<p class="acknowledged-label">Saved locally for this replay moment · click to undo</p>' : ''}<p class="risk-bottom">Signed values are additive log-odds associations, not causes. ${prediction.scenario?.active ? 'This is the unchanged baseline probability.' : 'Synthetic research estimate; not a clinical risk score.'}</p>`;
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
    result.innerHTML = `ILLUSTRATIVE CHANGE AT +2 HOURS<strong>${delta >= 0 ? '+' : '−'}${num(Math.abs(delta), 1)} <span style="font-size:10px">mg/dL</span></strong><small>Baseline risk stays ${pct(state.prediction.risk)}. This arithmetic scenario is not a treatment effect.</small>`;
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
  if (!['overview', 'record', 'evidence'].includes(tab)) return;
  state.tab = tab;
  $$('[data-tab]').forEach(button => {
    if (button.matches('.nav-button, [role="tab"]')) {
      button.classList.toggle('active', button.dataset.tab === tab);
      if (button.matches('[role="tab"]')) { button.setAttribute('aria-selected', String(button.dataset.tab === tab)); button.tabIndex = button.dataset.tab === tab ? 0 : -1; }
      if (button.matches('.nav-button')) { if (button.dataset.tab === tab) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current'); }
    }
  });
  ['overview', 'record', 'evidence'].forEach(value => { $(`#${value}-view`).hidden = tab !== value; });
  $('#breadcrumb-view').textContent = { overview: 'Overview', record: 'Patient record', evidence: 'Model evidence' }[tab];
  $('#sidebar').classList.remove('is-open');
  $('#menu-toggle').setAttribute('aria-expanded', 'false');
  if (tab !== 'overview') stopPlayback();
  if (tab === 'record') renderRecord();
  if (tab === 'evidence') renderEvidence();
  if (tab === 'overview' && state.prediction) requestAnimationFrame(renderChart);
  if (focus) $(`#tab-${tab}`).focus();
}

function renderRecord() {
  const patient = state.patient;
  if (!patient) { $('#record-view').innerHTML = '<div class="empty-state">Load a synthetic patient to explore their record.</div>'; return; }
  const ehr = patient.ehr;
  const row = (label, value, unit = '') => `<div class="record-field"><dt>${esc(label)}</dt><dd>${esc(value)}<small>${esc(unit)}</small></dd></div>`;
  const visible = patient.series.slice(Math.max(0, state.cursor - 11), state.cursor + 1).reverse();
  $('#record-view').innerHTML = `<div class="record-grid"><section class="card"><div class="eyebrow">HISTORICAL / STATIC</div><h2>Health record</h2><dl class="record-fields">${row('Age', patient.age, 'years')}${row('Recorded sex', patient.sex)}${row('HbA1c', num(ehr.hba1c, 1), '%')}${row('Body mass index', num(ehr.bmi, 1), 'kg/m²')}${row('LDL cholesterol', num(ehr.ldl), 'mg/dL')}${row('Diabetes history', num(ehr.diabetesYears, 1), 'years')}</dl></section><section class="card"><div class="eyebrow">PATIENT CONTEXT</div><h2>More than a measurement</h2><div class="eyebrow" style="font-size:8px">RECORDED DIAGNOSES</div><div class="record-list">${(ehr.diagnoses || []).map(value => `<span class="neutral-tag">${esc(value)}</span>`).join('') || '<p class="record-note">None provided</p>'}</div><div class="eyebrow" style="font-size:8px">MEDICATION HISTORY</div><p class="record-note" style="margin:9px 0 20px">${(ehr.medications || []).map(esc).join('<br>') || 'None provided'}</p><div class="eyebrow" style="font-size:8px">GENETIC MARKER</div><p class="record-note" style="margin-top:9px">${esc(ehr.geneticMarker)}<br>Descriptive context only; not used as a model feature.</p></section><section class="card record-full"><div class="eyebrow">DYNAMIC / FIVE-MINUTE OBSERVATIONS</div><h2>Wearable data at this moment</h2><p class="record-note">The 12 most recent observations available at ${time(patient.series[state.cursor].timestamp)} UTC on ${date(patient.series[state.cursor].timestamp)}. Future observations do not enter the prediction.</p><div class="table-scroll"><table class="stream-table"><thead><tr><th scope="col">Time · UTC</th><th scope="col">Glucose<br>mg/dL</th><th scope="col">Heart rate<br>bpm</th><th scope="col">HRV<br>ms</th><th scope="col">Steps<br>per interval</th><th scope="col">Sleep state</th></tr></thead><tbody>${visible.map(point => `<tr><td class="stream-time">${time(point.timestamp)}</td><td>${num(point.glucose, 1)}</td><td>${num(point.hr, 1)}</td><td>${num(point.hrv, 1)}</td><td>${num(point.steps)}</td><td>${point.sleep === 1 ? 'Asleep' : point.sleep === 0 ? 'Awake' : 'Missing'}</td></tr>`).join('')}</tbody></table></div></section></div><div class="evidence-disclaimer">${icon('shield')}<span>Fictional patient identity, health record and sensor measurements. The simulation has no link to a real individual. This patient is a curated example from the held-out synthetic test cohort.</span></div>`;
}

function renderEvidence() {
  const metrics = state.metrics;
  if (!metrics) {
    $('#evidence-view').innerHTML = `<div class="card empty-state"><h2>Evidence is currently unavailable</h2><p>${esc(state.metricsError || 'The evaluation file has not loaded.')}</p><button id="retry-metrics" class="button" style="margin-top:18px">Reload model evidence</button></div>`;
    $('#retry-metrics')?.addEventListener('click', async () => { try { state.metrics = await request('/api/metrics'); renderEvidence(); } catch (error) { toast(error.message); } });
    return;
  }
  const fused = metrics.models?.fused || {};
  const policy = fused.alertPolicy || {};
  const cohort = metrics.cohort || {};
  const threshold = policy.threshold ?? metrics.probabilityThreshold;
  const improvement = isNumber(metrics.models?.sensorOnly?.mae) && isNumber(fused.mae) ? (metrics.models.sensorOnly.mae - fused.mae) / metrics.models.sensorOnly.mae : null;
  const evidenceMetric = (label, value, note) => `<div class="card evidence-metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
  const tableRow = (name, value) => `<tr><th scope="row">${name}</th><td>${value}</td></tr>`;
  $('#evidence-view').innerHTML = `<div class="evidence-intro"><div><div class="eyebrow">TRANSPARENCY IS PART OF THE PRODUCT</div><h2>Evidence, with its boundaries.</h2><p>A reproducible patient-level evaluation on synthetic data. These results demonstrate a working data-fusion prototype; they do not establish clinical performance.</p></div><span class="version-badge">${esc(state.prediction?.modelVersion || 'AURA fused model')}</span></div><div class="metrics-grid">${evidenceMetric('Two-hour forecast MAE', num(fused.mae, 2), 'mg/dL · held-out synthetic patients')}${evidenceMetric('Discrimination · AUROC', num(fused.auroc, 3), 'Synthetic event classification')}${evidenceMetric('Recall · review policy', pct(policy.testRecall ?? fused.recall, 1), `At a ${pct(threshold)} probability threshold`)}${evidenceMetric('Interval coverage', pct(fused.intervalCoverage, 1), 'Observed test coverage · nominal 90%')}</div><div class="evidence-columns"><section class="card"><div class="eyebrow">DOES FUSION HELP?</div><h2 style="margin-top:7px">Four models, one test set</h2><table class="metrics-table"><thead><tr><th>Model</th><td>2h MAE · mg/dL</td></tr></thead><tbody>${tableRow('<strong>EHR + wearables</strong>', `<strong>${num(fused.mae, 2)}</strong>`)}${tableRow('Wearables only', num(metrics.models?.sensorOnly?.mae, 2))}${tableRow('Static EHR only', num(metrics.models?.staticOnly?.mae, 2))}${tableRow('Last-value persistence', num(metrics.models?.persistence?.mae, 2))}</tbody></table><p class="record-note" style="margin-top:18px">${pct(improvement, 1)} lower MAE with fusion than the wearable-only model on this simulator. Lower error here does not imply the same advantage in real patients.</p></section><section class="card"><div class="eyebrow">EVALUATION DESIGN</div><h2 style="margin-top:7px">People stay in one split</h2><table class="metrics-table"><tbody>${tableRow('Synthetic patients', num(cohort.patients))}${tableRow('Training / validation / test', `${num(cohort.trainPatients)} / ${num(cohort.validationPatients)} / ${num(cohort.testPatients)}`)}${tableRow('Days per patient', num(cohort.days))}${tableRow('Held-out test windows', num(cohort.windows?.test))}${tableRow('Positive event prevalence', pct(cohort.positiveRate?.test, 2))}${tableRow('Generator seed', esc(metrics.seed))}</tbody></table><p class="record-note" style="margin-top:15px">All windows from a patient remain in the same split. Features use only the prior 24 hours. Overlapping windows are correlated.</p></section><section class="card"><div class="eyebrow">THE ACTUAL ALGORITHM</div><h2 style="margin-top:7px">An inspectable twin</h2><ul class="detail-list"><li><strong>Forecast:</strong> standardized features feed a ridge regression model for 30, 60, 90 and 120-minute glucose.</li><li><strong>Event probability:</strong> logistic regression with validation-set calibration estimates glucose ≥180 mg/dL at exactly +120 minutes.</li><li><strong>Fusion:</strong> EHR context, trailing CGM trends, HR/HRV, sleep, activity and explicit EHR × wearable interactions.</li><li><strong>Uncertainty:</strong> validation residuals form nominal 90% intervals. Coverage is marginal, not a guarantee for one patient.</li><li><strong>Explanations:</strong> signed feature-group contributions to calibrated log-odds. They are associations, not causal effects.</li></ul></section><section class="card"><div class="eyebrow">OPERATING POINT & RELIABILITY</div><h2 style="margin-top:7px">Make the tradeoffs visible</h2><table class="metrics-table"><tbody>${tableRow('Review threshold', pct(threshold))}${tableRow('Review-policy precision', pct(policy.testPrecision ?? fused.precision, 1))}${tableRow('Review-policy recall', pct(policy.testRecall ?? fused.recall, 1))}${tableRow('Average precision', num(fused.averagePrecision, 3))}${tableRow('Brier score', num(fused.brier, 4))}${tableRow('MAE 95% patient-bootstrap CI', Array.isArray(fused.maePatientBootstrap95CI) ? `${num(fused.maePatientBootstrap95CI[0], 2)}–${num(fused.maePatientBootstrap95CI[1], 2)}` : 'Not available')}</tbody></table><p class="record-note" style="margin-top:16px">The review threshold is selected on validation patients and frozen before test evaluation. Higher recall means more false alerts. Forecasts are withheld when required history is missing or channels become stale.</p></section></div><div class="card" style="padding:25px;margin-top:20px"><div class="eyebrow">LIMITATIONS, NOT FINE PRINT</div><h2 style="margin:7px 0 20px">What this prototype cannot tell us</h2><ul class="detail-list">${(metrics.limitations || []).map(limitation => `<li>${esc(limitation)}</li>`).join('')}<li>The scenario sliders use illustrative arithmetic. They do not estimate treatment effects; the trained baseline probability remains unchanged.</li></ul></div><div class="evidence-disclaimer">${icon('info')}<span>Target: ${esc(metrics.target)}. This workspace is a research demonstration with synthetic data only. No external or prospective clinical validation has been performed.</span></div>`;
}

function stopPlayback() {
  state.playing = false;
  clearTimeout(state.timer);
  $('#play-button').innerHTML = icon('play');
  $('#play-button').setAttribute('aria-label', 'Play simulated data stream');
}
async function playbackTick() {
  if (!state.playing) return;
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
  const timestamp = patient.series[state.cursor].timestamp;
  const rows = prediction.forecast.map(point => `<tr><td>+${point.minutes} min</td><td>${num(point.glucose, 1)} mg/dL</td><td>${num(point.lower, 1)}–${num(point.upper, 1)} mg/dL</td></tr>`).join('');
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AURA Twin · ${esc(patient.name)} · Research summary</title><style>body{font:14px/1.7 'Segoe UI',sans-serif;max-width:800px;margin:50px auto;padding:0 30px;color:#1c3b2d}h1,h2{font-family:Georgia,serif;font-weight:400}h1{font-size:35px;line-height:1.3}h2{font-size:23px;margin-top:30px}small{color:#74876b}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:11px 8px;text-align:left;border-bottom:1px solid #dce6d4}th{color:#6a805c;font-weight:500}section{border-top:1px solid #dce6d4;margin-top:24px;padding-top:4px}.notice{padding:16px;background:#edf3e7;border:1px solid #dce7d2}.notes{white-space:pre-wrap}.footer{font-size:11px;color:#81936f;margin-top:30px}@media print{body{margin:20px auto}.notice{background:white}}</style></head><body><small>AURA / TWIN · BLACK SQUAD · AMRITA, CHENNAI</small><h1>Patient twin observation</h1><div class="notice"><strong>Synthetic data · Research prototype · Not for clinical use</strong><br>Fictional patient and observations. No diagnosis or treatment recommendation.</div><h2>${esc(patient.name)}</h2><p>${esc(patient.id)} · ${esc(patient.age)} years · ${esc(patient.sex)}<br>Replay time: ${date(timestamp)} · ${time(timestamp)} UTC<br>Model: ${esc(prediction.modelVersion)}</p><section><h2>Current observation</h2><p>Glucose ${num(prediction.current.glucose, 1)} mg/dL · Heart rate ${num(prediction.current.hr)} bpm · HRV ${num(prediction.current.hrv)} ms<br>Trailing 24 hours: ${num(prediction.current.sleep, 1)} hours sleep · ${num(prediction.current.steps)} steps</p><p><strong>Baseline model probability: ${pct(prediction.risk, 1)}</strong><br>Target: glucose ≥180 mg/dL at exactly +120 minutes.<br>${prediction.abstained ? `Forecast withheld: ${esc((prediction.quality?.reasons || []).join(' '))}` : `Review threshold: ${pct(prediction.alert?.threshold)}. ${esc(prediction.alert?.label || '')}.`}</p></section><section><h2>${prediction.scenario?.active ? 'Illustrative scenario' : 'Glucose forecast'}</h2>${prediction.scenario?.active ? `<p class="notice">Additional carbohydrates ${state.scenario.mealCarbs} g; additional activity ${state.scenario.activityMinutes} minutes. Arithmetic sensitivity only, not a causal estimate. Trained baseline risk is unchanged. Shifted intervals have no measured coverage.</p>` : '<p>Nominal 90% residual intervals. They are not guaranteed for this patient.</p>'}<table><thead><tr><th>Horizon</th><th>Glucose</th><th>Interval</th></tr></thead><tbody>${rows || '<tr><td colspan="3">Forecast withheld due to insufficient data.</td></tr>'}</tbody></table></section><section><h2>Historical context</h2><p>HbA1c ${num(patient.ehr.hba1c, 1)}% · BMI ${num(patient.ehr.bmi, 1)} kg/m² · LDL ${num(patient.ehr.ldl)} mg/dL · Diabetes history ${num(patient.ehr.diabetesYears, 1)} years</p><p>${(patient.ehr.diagnoses || []).map(esc).join(', ')}</p></section><section><h2>Model associations</h2><table><thead><tr><th>Feature group</th><th>Source</th><th>Log-odds contribution</th></tr></thead><tbody>${(prediction.drivers || []).map(driver => `<tr><td>${esc(driver.name)}</td><td>${esc(driver.source)}</td><td>${driver.contribution >= 0 ? '+' : ''}${num(driver.contribution, 3)}</td></tr>`).join('')}</tbody></table><p>Associations relative to training feature means; not causal effects.</p></section><section><h2>Clinician observation</h2><p class="notes">${esc($('#clinical-notes').value || 'No note recorded.')}</p><p>${localGet(`ack:${patient.id}:${state.cursor}`) ? 'Observation acknowledged in this browser.' : 'Observation not acknowledged.'}</p></section><p class="footer">All results concern a designed synthetic generator. No external, prospective or clinical validation. Exported ${esc(new Date().toISOString())}. Open this HTML file in a browser to print or save as PDF.</p></body></html>`;
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
  const tabs = ['overview', 'record', 'evidence'];
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); setTab(tabs[(tabs.indexOf(state.tab) + (event.key === 'ArrowRight' ? 1 : 2)) % 3], true); }
  if (event.key === 'Home') { event.preventDefault(); setTab('overview', true); }
  if (event.key === 'End') { event.preventDefault(); setTab('evidence', true); }
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

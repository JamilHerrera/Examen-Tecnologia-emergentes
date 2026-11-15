import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import sql from 'mssql';
import WebSocket from 'ws';
import { createApp } from '../src/app.js';
import { closePool } from '../src/db.js';
import { closeWebSocket, setupWebSocket } from '../src/services/ws.js';
import { setMailForTests } from '../src/services/mailer.js';
import { createAlert, deliverAlert, evaluateAlerts, getAlert, severityForDrop } from '../src/services/alerts.js';

let server;
let base;
let analystToken;
let adminToken;
let sa;
const created = [];

const stamp = () => `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
const baseAlert = (extra = {}) => ({
  type: 'sales_drop', severity: 'medium', indicator: 'Ventas netas mensuales (prueba)', entity: 'Total',
  observedValue: 80, thresholdValue: 85, referencePeriod: 'prueba', source: 'rule', simulated: true,
  dedupKey: `test:${stamp()}`, ...extra,
});

async function loginAs(username, password) {
  const res = await fetch(`${base}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }),
  });
  return (await res.json()).token;
}
const api = (path, token, init = {}) =>
  fetch(`${base}/api${path}`, { ...init, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } });

async function newAlert(extra) {
  const res = await createAlert(baseAlert(extra));
  if (res.created) created.push(res.alert.id);
  return res;
}

before(async () => {
  server = createApp().listen(0);
  setupWebSocket(server);
  base = `http://127.0.0.1:${server.address().port}`;
  analystToken = await loginAs('analyst', process.env.DEMO_ANALYST_PASSWORD);
  adminToken = await loginAs('admin', process.env.DEMO_ADMIN_PASSWORD);
  sa = await new sql.ConnectionPool({
    server: 'localhost', port: 1433, database: 'WideWorldImporters', user: 'sa', password: process.env.MSSQL_SA_PASSWORD,
    options: { encrypt: false, trustServerCertificate: true },
  }).connect();
});

after(async () => {
  if (created.length) {
    const ids = created.join(',');
    await sa.request().query(`DELETE FROM ops.alert_delivery WHERE AlertID IN (${ids}); DELETE FROM ops.alert WHERE AlertID IN (${ids});`);
  }
  setMailForTests({});
  closeWebSocket();
  server.close();
  await closePool();
  await sa.close();
});

test('condicion FALSA: con un umbral inalcanzable no se generan alertas candidatas', async () => {
  const r = await evaluateAlerts({ dryRun: true, salesDropThresholdPct: 99, forecastBelowPct: 1 });
  assert.equal(r.candidates.length, 0);
});

test('condicion VERDADERA: con umbral permisivo se generan candidatas con todos los campos minimos', async () => {
  const r = await evaluateAlerts({ dryRun: true, salesDropThresholdPct: -1000 });
  const a = r.candidates.find((c) => c.indicator === 'Ventas netas mensuales' && c.entity === 'Total');
  assert.ok(a, 'debe existir candidata mensual total');
  for (const k of ['type', 'severity', 'indicator', 'observedValue', 'thresholdValue', 'referencePeriod', 'source', 'dedupKey', 'explanation']) {
    assert.ok(a[k] !== undefined && a[k] !== null, `falta ${k}`);
  }
  assert.equal(a.source, 'rule');
  assert.ok(r.candidates.some((c) => c.indicator === 'Ventas netas semanales'));
});

test('dryRun no persiste nada', async () => {
  const before = (await sa.request().query('SELECT COUNT(*) n FROM ops.alert')).recordset[0].n;
  await evaluateAlerts({ dryRun: true, salesDropThresholdPct: -1000 });
  const after = (await sa.request().query('SELECT COUNT(*) n FROM ops.alert')).recordset[0].n;
  assert.equal(after, before);
});

test('el mismo evento no genera notificaciones duplicadas (DedupKey)', async () => {
  const key = `test:dedup:${stamp()}`;
  const first = await newAlert({ dedupKey: key });
  const second = await newAlert({ dedupKey: key });
  assert.equal(first.created, true);
  assert.equal(second.created, false);
  const n = (await sa.request().input('k', key).query('SELECT COUNT(*) n FROM ops.alert WHERE DedupKey = @k')).recordset[0].n;
  assert.equal(n, 1);
});

test('correo: reintenta tras fallas y registra cada intento hasta enviar', async () => {
  let calls = 0;
  setMailForTests({ enabled: true, send: async () => { calls += 1; if (calls < 3) throw new Error('SMTP caido'); } });
  const { alert } = await newAlert();
  const summary = await deliverAlert(alert, { retryDelayMs: 1 });
  assert.equal(summary.email, 'sent');
  const emailLog = (await getAlert(alert.id)).deliveries.filter((d) => d.channel === 'email');
  assert.deepEqual(emailLog.map((d) => d.status), ['failed', 'failed', 'sent']);
  assert.deepEqual(emailLog.map((d) => d.attempt), [1, 2, 3]);
});

test('correo: si todos los intentos fallan queda registrado como failed', async () => {
  setMailForTests({ enabled: true, send: async () => { throw new Error('rechazado'); } });
  const { alert } = await newAlert();
  const summary = await deliverAlert(alert, { retryDelayMs: 1 });
  assert.equal(summary.email, 'failed');
  const emailLog = (await getAlert(alert.id)).deliveries.filter((d) => d.channel === 'email');
  assert.equal(emailLog.length, 3);
  assert.ok(emailLog.every((d) => d.status === 'failed' && d.detail === 'rechazado'));
});

test('correo: sin SMTP configurado se registra como skipped (no falla el flujo)', async () => {
  setMailForTests({ enabled: false });
  const { alert } = await newAlert();
  const summary = await deliverAlert(alert);
  assert.equal(summary.email, 'skipped');
  assert.equal(summary.dashboard, 'sent');
});

test('WebSocket: cliente autenticado recibe la alerta; sin autenticar se rechaza', async () => {
  setMailForTests({ enabled: false });
  const url = base.replace('http', 'ws') + '/ws';

  const anon = new WebSocket(url);
  const anonClosed = new Promise((resolve) => anon.on('close', (code) => resolve(code)));
  anon.on('open', () => anon.send(JSON.stringify({ type: 'auth', token: 'falso' })));
  assert.equal(await anonClosed, 4401);

  const ws = new WebSocket(url);
  const ready = new Promise((resolve) => ws.on('message', (m) => { const d = JSON.parse(m); if (d.type === 'ready') resolve(); }));
  ws.on('open', () => ws.send(JSON.stringify({ type: 'auth', token: analystToken })));
  await ready;
  const received = new Promise((resolve) => ws.on('message', (m) => { const d = JSON.parse(m); if (d.type === 'alert') resolve(d.alert); }));
  const { alert } = await newAlert();
  const summary = await deliverAlert(alert);
  assert.equal(summary.websocket, 'sent');
  assert.equal((await received).id, alert.id);
  ws.close();
});

test('API: consultar detalle, cambiar estado y control de permisos', async () => {
  setMailForTests({ enabled: false });
  const { alert } = await newAlert();
  await deliverAlert(alert);
  const detail = await (await api(`/alerts/${alert.id}`, analystToken)).json();
  assert.equal(detail.status, 'new');
  assert.ok(detail.deliveries.length >= 3);
  const patched = await (await api(`/alerts/${alert.id}/status`, analystToken, { method: 'PATCH', body: JSON.stringify({ status: 'attended' }) })).json();
  assert.equal(patched.status, 'attended');
  assert.equal(patched.statusChangedBy, 'analyst');
  assert.equal((await api(`/alerts/${alert.id}/status`, analystToken, { method: 'PATCH', body: JSON.stringify({ status: 'borrar' }) })).status, 400);
  assert.equal((await api('/alerts/evaluate', analystToken, { method: 'POST', body: '{}' })).status, 403);
  assert.equal((await api('/alerts/999999999', analystToken)).status, 404);
  const list = await (await api('/alerts?status=attended&limit=5', analystToken)).json();
  assert.ok(list.some((a) => a.id === alert.id));
});

test('severidad escala con la magnitud de la caida', () => {
  assert.equal(severityForDrop(16), 'medium');
  assert.equal(severityForDrop(30), 'high');
  assert.equal(severityForDrop(45), 'critical');
});

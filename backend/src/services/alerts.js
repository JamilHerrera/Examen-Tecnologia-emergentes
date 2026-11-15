import { query, sql } from '../db.js';
import { config } from '../config.js';
import { chat, ollamaStatus } from '../assistant/ollama.js';
import { parsePeriod, shiftMonths } from '../assistant/periods.js';
import { TOOLS } from '../assistant/tools.js';
import { findUnverifiedNumbers } from '../assistant/verify.js';
import { getBreakdown, getFreshness, getKpis, iso } from './analytics.js';
import { loadForecast } from '../routes/ml.js';
import { emailConfigured, sendMail } from './mailer.js';
import { broadcast } from './ws.js';

const STATUSES = ['new', 'attended', 'dismissed', 'resolved'];
const sleepMs = (ms) => new Promise((r) => setTimeout(r, ms));

export function severityForDrop(dropPct) {
  if (dropPct >= 40) return 'critical';
  if (dropPct >= 25) return 'high';
  if (dropPct >= 15) return 'medium';
  return 'low';
}

const toDto = (r) => ({
  id: Number(r.AlertID), createdAt: r.CreatedAt, type: r.AlertType, severity: r.Severity,
  indicator: r.Indicator, entity: r.Entity, observedValue: r.ObservedValue == null ? null : Number(r.ObservedValue),
  thresholdValue: r.ThresholdValue == null ? null : Number(r.ThresholdValue), referencePeriod: r.ReferencePeriod,
  source: r.Source, modelVersion: r.ModelVersion, explanation: r.Explanation, recommendedAction: r.RecommendedAction,
  simulated: Boolean(r.IsSimulated), status: r.Status, statusChangedAt: r.StatusChangedAt, statusChangedBy: r.StatusChangedBy,
});

// ---------------------------------------------------------------------------
// Persistencia y entrega
// ---------------------------------------------------------------------------

async function logDelivery(alertId, channel, attempt, status, detail) {
  await query(
    'INSERT INTO ops.alert_delivery (AlertID, Channel, Attempt, Status, Detail) VALUES (@a, @c, @n, @s, @d)',
    { a: alertId, c: channel, n: attempt, s: status, d: detail?.slice(0, 500) ?? null },
  );
}

/** Crea la alerta si no existe otra con el mismo DedupKey (evita duplicados del mismo evento). */
export async function createAlert(a) {
  try {
    const rows = await query(
      `INSERT INTO ops.alert (AlertType, Severity, Indicator, Entity, ObservedValue, ThresholdValue, ReferencePeriod,
                              Source, ModelVersion, Explanation, RecommendedAction, IsSimulated, DedupKey)
       OUTPUT INSERTED.*
       VALUES (@type, @sev, @ind, @ent, @obs, @thr, @ref, @src, @mv, @exp, @act, @sim, @dedup)`,
      {
        type: a.type, sev: a.severity, ind: a.indicator, ent: a.entity ?? null,
        obs: { type: sql.Decimal(18, 2), value: a.observedValue ?? null },
        thr: { type: sql.Decimal(18, 2), value: a.thresholdValue ?? null },
        ref: a.referencePeriod ?? null, src: a.source, mv: a.modelVersion ?? null,
        exp: a.explanation ?? null, act: a.recommendedAction ?? null, sim: a.simulated ? 1 : 0, dedup: a.dedupKey,
      },
    );
    return { created: true, alert: toDto(rows[0]) };
  } catch (err) {
    if (err.number === 2601 || err.number === 2627) return { created: false, dedupKey: a.dedupKey };
    throw err;
  }
}

function emailBody(alert) {
  return [
    `Alerta #${alert.id} [${alert.severity.toUpperCase()}] ${alert.simulated ? '(SIMULADA) ' : ''}`,
    `Fecha: ${new Date(alert.createdAt).toISOString()}`,
    `Origen: ${alert.source === 'rule' ? 'regla de negocio' : alert.source === 'model' ? `modelo ML ${alert.modelVersion}` : 'IA generativa (texto generado)'}`,
    `Indicador: ${alert.indicator}${alert.entity ? ` · ${alert.entity}` : ''}`,
    `Valor observado: ${alert.observedValue} · Umbral/referencia: ${alert.thresholdValue}`,
    `Periodo de referencia: ${alert.referencePeriod}`,
    alert.explanation ? `Explicacion: ${alert.explanation}` : '',
    alert.recommendedAction ? `Accion recomendada: ${alert.recommendedAction}` : '',
  ].filter(Boolean).join('\n');
}

/** Entrega por dashboard (BD), WebSocket y correo con reintentos; cada intento queda registrado. */
export async function deliverAlert(alert, { retryDelayMs = 500 } = {}) {
  const summary = {};
  await logDelivery(alert.id, 'dashboard', 1, 'sent', 'Alerta disponible en el panel de alertas');
  summary.dashboard = 'sent';

  const clients = broadcast({ type: 'alert', alert });
  await logDelivery(alert.id, 'websocket', 1, clients ? 'sent' : 'skipped', `${clients} cliente(s) conectados`);
  summary.websocket = clients ? 'sent' : 'skipped';

  if (!emailConfigured()) {
    await logDelivery(alert.id, 'email', 1, 'skipped', 'SMTP no configurado');
    summary.email = 'skipped';
    return summary;
  }
  const subject = `[${alert.severity.toUpperCase()}] ${alert.indicator}${alert.simulated ? ' (simulada)' : ''}`;
  for (let attempt = 1; attempt <= config.alerts.emailRetries; attempt += 1) {
    try {
      await sendMail(subject, emailBody(alert));
      await logDelivery(alert.id, 'email', attempt, 'sent', 'Correo enviado');
      summary.email = 'sent';
      return summary;
    } catch (err) {
      await logDelivery(alert.id, 'email', attempt, 'failed', err.message);
      summary.email = 'failed';
      if (attempt < config.alerts.emailRetries) await sleepMs(retryDelayMs * 2 ** (attempt - 1));
    }
  }
  return summary;
}

export async function listAlerts({ status, limit = 50 } = {}) {
  const top = Math.min(Math.max(parseInt(limit, 10) || 50, 1), 200);
  if (status && !STATUSES.includes(status)) {
    const e = new Error('status invalido'); e.status = 400; throw e;
  }
  const rows = await query(
    `SELECT TOP (${top}) * FROM ops.alert ${status ? 'WHERE Status = @s' : ''} ORDER BY CreatedAt DESC, AlertID DESC`,
    status ? { s: status } : {},
  );
  return rows.map(toDto);
}

export async function getAlert(id) {
  const rows = await query('SELECT * FROM ops.alert WHERE AlertID = @id', { id: { type: sql.BigInt, value: id } });
  if (!rows.length) return null;
  const deliveries = await query(
    'SELECT Channel, Attempt, Status, Detail, AttemptedAt FROM ops.alert_delivery WHERE AlertID = @id ORDER BY DeliveryID',
    { id: { type: sql.BigInt, value: id } },
  );
  return { ...toDto(rows[0]), deliveries: deliveries.map((d) => ({ channel: d.Channel, attempt: d.Attempt, status: d.Status, detail: d.Detail, at: d.AttemptedAt })) };
}

export async function setAlertStatus(id, status, username) {
  if (!STATUSES.includes(status)) {
    const e = new Error(`status debe ser uno de: ${STATUSES.join(', ')}`); e.status = 400; throw e;
  }
  const rows = await query(
    `UPDATE ops.alert SET Status = @s, StatusChangedAt = SYSUTCDATETIME(), StatusChangedBy = @u
     OUTPUT INSERTED.* WHERE AlertID = @id`,
    { s: status, u: username, id: { type: sql.BigInt, value: id } },
  );
  return rows.length ? toDto(rows[0]) : null;
}

// ---------------------------------------------------------------------------
// Generacion de alertas
// ---------------------------------------------------------------------------

/** Regla de negocio: ventas del ultimo mes completo vs el mismo mes del ano anterior (total y por categoria). */
async function monthlySalesDropCandidates(fresh, threshold) {
  const period = parsePeriod('ultimo mes', { firstDate: fresh.firstOrderDate, lastDate: fresh.lastOrderDate });
  const ref = { from: shiftMonths(period.from, -12), to: shiftMonths(period.to, -12) };
  if (ref.from < fresh.firstOrderDate) return [];
  const month = period.from.slice(0, 7);
  const [cur, prev, curCat, prevCat] = await Promise.all([
    getKpis({ from: period.from, to: period.to }), getKpis({ from: ref.from, to: ref.to }),
    getBreakdown({ from: period.from, to: period.to }, 'category', 50), getBreakdown({ from: ref.from, to: ref.to }, 'category', 50),
  ]);
  const rows = [
    { entity: 'Total', cur: cur.kpis.netSales.value, prev: prev.kpis.netSales.value },
    ...curCat.map((c) => ({ entity: c.name, cur: c.netSales, prev: prevCat.find((p) => p.name === c.name)?.netSales ?? 0 })),
  ];
  return rows.filter((r) => r.prev > 0).flatMap((r) => {
    const drop = ((r.prev - r.cur) / r.prev) * 100;
    if (!(drop > threshold)) return [];
    return [{
      type: 'sales_drop', severity: severityForDrop(drop), indicator: 'Ventas netas mensuales', entity: r.entity,
      observedValue: Math.round(r.cur * 100) / 100, thresholdValue: Math.round(r.prev * (1 - threshold / 100) * 100) / 100,
      referencePeriod: `${month} vs ${ref.from.slice(0, 7)} (caida ${drop.toFixed(1)}%, umbral ${threshold}%)`,
      source: 'rule', dedupKey: `rule:sales_drop:month:${r.entity}:${month}`,
      explanation: `Las ventas netas de ${r.entity} en ${month} (${Math.round(r.cur).toLocaleString('en-GB')} GBP) cayeron ${drop.toFixed(1)}% frente a ${ref.from.slice(0, 7)} (${Math.round(r.prev).toLocaleString('en-GB')} GBP).`,
      recommendedAction: 'Revisar las categorias y regiones con mayor caida en el dashboard y validar la carga del DW.',
      parentPeriod: period,
    }];
  });
}

/** Regla de negocio semanal: ultima semana completa vs promedio de las 4 semanas previas. */
async function weeklySalesDropCandidates(fresh, threshold) {
  const rows = await query(
    `SELECT TOP 5 w.WeekStart, w.NetSales FROM bi.vw_weekly_sales w
     WHERE w.WeekStart >= @first AND DATEADD(DAY, 6, w.WeekStart) <= @last ORDER BY w.WeekStart DESC`,
    { first: { type: sql.Date, value: fresh.firstOrderDate }, last: { type: sql.Date, value: fresh.lastOrderDate } },
  );
  if (rows.length < 5) return [];
  const [latest, ...previous] = rows;
  const avg = previous.reduce((s, r) => s + Number(r.NetSales), 0) / previous.length;
  const drop = ((avg - Number(latest.NetSales)) / avg) * 100;
  if (!(drop > threshold)) return [];
  const week = iso(latest.WeekStart);
  return [{
    type: 'sales_drop', severity: severityForDrop(drop), indicator: 'Ventas netas semanales', entity: 'Total',
    observedValue: Number(latest.NetSales), thresholdValue: Math.round(avg * (1 - threshold / 100) * 100) / 100,
    referencePeriod: `semana ${week} vs promedio de las 4 semanas previas (caida ${drop.toFixed(1)}%, umbral ${threshold}%)`,
    source: 'rule', dedupKey: `rule:sales_drop:week:Total:${week}`,
    explanation: `Las ventas de la semana ${week} (${Math.round(Number(latest.NetSales)).toLocaleString('en-GB')} GBP) estan ${drop.toFixed(1)}% por debajo del promedio de las 4 semanas previas (${Math.round(avg).toLocaleString('en-GB')} GBP).`,
    recommendedAction: 'Verificar si la caida es estacional o por datos incompletos antes de actuar.',
  }];
}

/** Regla ML: prediccion de la proxima semana por debajo de un % del promedio reciente. */
async function forecastLowCandidates(fresh, belowPct) {
  const f = await loadForecast();
  if (!f.model || !f.predictions.length || f.history.length < 8) return [];
  const avg = f.history.slice(-8).reduce((s, h) => s + h.netSales, 0) / 8;
  const next = f.predictions[0];
  const threshold = (belowPct / 100) * avg;
  if (!(next.value < threshold)) return [];
  return [{
    type: 'forecast_low', severity: next.value < 0.7 * avg ? 'high' : 'medium', indicator: 'Prediccion de ventas semanales', entity: 'Total',
    observedValue: next.value, thresholdValue: Math.round(threshold * 100) / 100, referencePeriod: `semana ${next.period} (horizonte ${next.step}) vs ${belowPct}% del promedio de 8 semanas`,
    source: 'model', modelVersion: f.model.version, dedupKey: `model:forecast_low:${f.model.version}:${next.period}`,
    explanation: `PREDICCION: el modelo ${f.model.version} estima ${Math.round(next.value).toLocaleString('en-GB')} GBP para la semana ${next.period} (intervalo ${Math.round(next.lower).toLocaleString('en-GB')} a ${Math.round(next.upper).toLocaleString('en-GB')}), por debajo del ${belowPct}% del promedio de las ultimas 8 semanas (${Math.round(avg).toLocaleString('en-GB')} GBP).`,
    recommendedAction: 'Anticipar acciones comerciales; recordar que es una prediccion con incertidumbre.',
  }];
}

/** Disparador GenAI: resume la anomalia con Ollama. El texto se marca como generado y se valida contra hechos. */
export async function generateAiAlert(parent, { extraFacts = [] } = {}) {
  const status = await ollamaStatus();
  if (!status.available) return { created: false, reason: 'Ollama no disponible' };

  const fresh = await getFreshness();
  const period = parent.parentPeriod ?? parsePeriod('ultimo mes', { firstDate: fresh.firstOrderDate, lastDate: fresh.lastOrderDate });
  const real = await TOOLS.growth_by_dimension({ period, dimension: 'category' }).catch(() => ({ facts: [] }));
  const facts = [...extraFacts, parent.explanation, ...real.facts];
  const raw = await chat([
    { role: 'system', content: 'Eres analista de ventas. Con los HECHOS dados responde SOLO JSON {"explicacion":"max 2 frases","accion":"max 1 frase"}. No inventes cifras; si citas una, copiala de los HECHOS. Responde en espanol.' },
    { role: 'user', content: `HECHOS:\n${facts.map((f) => `- ${f}`).join('\n')}` },
  ], { json: true, maxTokens: 220 });
  let parsed;
  try { parsed = JSON.parse(raw); } catch { return { created: false, reason: 'respuesta del modelo no valida' }; }
  if (typeof parsed.explicacion !== 'string' || typeof parsed.accion !== 'string') return { created: false, reason: 'respuesta del modelo incompleta' };
  const unverified = findUnverifiedNumbers(`${parsed.explicacion} ${parsed.accion}`, facts);
  if (unverified.length) return { created: false, reason: `cifras no verificadas: ${unverified.join(', ')}` };

  return createAlert({
    type: 'ai_anomaly_summary', severity: parent.severity, indicator: parent.indicator, entity: parent.entity,
    observedValue: parent.observedValue, thresholdValue: parent.thresholdValue, referencePeriod: parent.referencePeriod,
    source: 'ai', simulated: parent.simulated,
    explanation: `[Texto generado por IA · ${status.model}] ${parsed.explicacion}`,
    recommendedAction: `[Generado por IA] ${parsed.accion}`,
    dedupKey: `ai:${parent.dedupKey}`,
  });
}

/**
 * Evalua reglas de negocio y ML. dryRun=true devuelve los candidatos sin guardar ni notificar.
 * Es idempotente: el mismo evento (DedupKey) nunca genera dos alertas.
 */
export async function evaluateAlerts({ dryRun = false, salesDropThresholdPct, forecastBelowPct, withAi = true } = {}) {
  const fresh = await getFreshness();
  const drop = salesDropThresholdPct ?? config.alerts.salesDropThresholdPct;
  const below = forecastBelowPct ?? config.alerts.forecastBelowPct;
  const candidates = [
    ...(await monthlySalesDropCandidates(fresh, drop)),
    ...(await weeklySalesDropCandidates(fresh, drop)),
    ...(await forecastLowCandidates(fresh, below)),
  ];
  if (dryRun) return { dryRun: true, evaluated: 3, candidates, created: [], duplicates: 0 };

  const created = [];
  let duplicates = 0;
  for (const c of candidates) {
    const res = await createAlert(c);
    if (!res.created) { duplicates += 1; continue; }
    created.push(res.alert);
    await deliverAlert(res.alert);
    if (withAi && ['high', 'critical'].includes(c.severity)) {
      const ai = await generateAiAlert(c).catch((err) => ({ created: false, reason: err.message }));
      if (ai.created) { created.push(ai.alert); await deliverAlert(ai.alert); }
    }
  }
  await query(
    `INSERT INTO ops.etl_run_log (Process, Status, FinishedAt, RowsProcessed, Message)
     VALUES ('alert_evaluation', 'success', SYSUTCDATETIME(), @n, @m)`,
    { n: created.length, m: `${candidates.length} candidatas, ${created.length} creadas, ${duplicates} duplicadas` },
  );
  return { dryRun: false, evaluated: 3, candidates, created, duplicates };
}

/** Evento simulado (identificado como tal) para demostrar el flujo completo sin esperar una caida real. */
export async function simulateAlert(kind, username) {
  const stamp = Date.now();
  const base = { simulated: true, dedupKey: `sim:${kind}:${stamp}` };
  const fresh = await getFreshness();
  if (kind === 'rule') {
    const a = {
      ...base, type: 'sales_drop', severity: 'high', indicator: 'Ventas netas mensuales', entity: 'Packaging Materials',
      observedValue: 780000, thresholdValue: 850000, referencePeriod: `SIMULACION: ${fresh.lastOrderDate.slice(0, 7)} vs mismo mes del ano anterior (caida 22%, umbral 15%)`,
      source: 'rule', explanation: 'EVENTO SIMULADO: las ventas de Packaging Materials caen 22% frente a la referencia.',
      recommendedAction: 'Solo demostracion: no requiere accion.',
    };
    const res = await createAlert(a);
    if (res.created) await deliverAlert(res.alert);
    return [res.alert];
  }
  if (kind === 'model') {
    const a = {
      ...base, type: 'forecast_low', severity: 'medium', indicator: 'Prediccion de ventas semanales', entity: 'Total',
      observedValue: 850000, thresholdValue: 980000, referencePeriod: 'SIMULACION: semana +1 vs 85% del promedio de 8 semanas',
      source: 'model', modelVersion: 'simulated', explanation: 'EVENTO SIMULADO: PREDICCION por debajo del umbral.',
      recommendedAction: 'Solo demostracion.',
    };
    const res = await createAlert(a);
    if (res.created) await deliverAlert(res.alert);
    return [res.alert];
  }
  if (kind === 'ai') {
    const parent = {
      ...base, type: 'sales_drop', severity: 'high', indicator: 'Ventas netas mensuales', entity: 'Packaging Materials',
      observedValue: 780000, thresholdValue: 850000, referencePeriod: 'SIMULACION: caida 22% vs referencia (umbral 15%)', source: 'rule',
      explanation: 'EVENTO SIMULADO: las ventas netas de Packaging Materials cayeron 22% frente a la referencia.',
      recommendedAction: 'Solo demostracion.', dedupKey: `sim:rule:${stamp}`,
    };
    const parentRes = await createAlert(parent);
    const out = [];
    if (parentRes.created) { await deliverAlert(parentRes.alert); out.push(parentRes.alert); }
    const ai = await generateAiAlert(parent, { extraFacts: ['La anomalia anterior es una SIMULACION para demostracion.'] });
    if (ai.created) { await deliverAlert(ai.alert); out.push(ai.alert); }
    else out.push({ aiSkipped: ai.reason });
    return out;
  }
  const e = new Error('kind debe ser rule, model o ai'); e.status = 400; throw e;
}

let timer;
export function startAlertScheduler() {
  const ms = config.alerts.evalIntervalMinutes * 60_000;
  const run = () => evaluateAlerts().catch((err) => console.error('[alerts] evaluacion fallida', err.message));
  setTimeout(run, 10_000).unref();
  timer = setInterval(run, ms);
  timer.unref();
}
export const stopAlertScheduler = () => clearInterval(timer);

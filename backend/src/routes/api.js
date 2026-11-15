import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { authenticate, login } from '../auth.js';
import { query } from '../db.js';
import {
  KPI_DEFINITIONS, ValidationError, addDays, getBreakdown, getDetail, getDimensionValues,
  getFreshness, getKpis, getOrder, getTrend, parseFilters,
} from '../services/analytics.js';
import { snapshotMetrics } from '../metrics.js';
import { requireRole } from '../auth.js';

export const router = Router();

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Demasiados intentos de inicio de sesion. Intenta mas tarde.' },
});

let freshnessCache = { at: 0, value: null };
async function cachedFreshness() {
  if (Date.now() - freshnessCache.at > 60_000) {
    freshnessCache = { at: Date.now(), value: await getFreshness() };
  }
  return freshnessCache.value;
}

/** Filtros validados; si no se indica rango se usan los ultimos 12 meses de datos disponibles. */
async function resolveFilters(q) {
  const filters = parseFilters(q);
  if (!filters.from || !filters.to) {
    const fresh = await cachedFreshness();
    filters.to = filters.to ?? fresh.lastOrderDate;
    filters.from = filters.from ?? addDays(filters.to, -364);
    if (filters.from > filters.to) throw new ValidationError('from no puede ser mayor que to');
  }
  return filters;
}

const wrap = (fn) => (req, res, next) => fn(req, res).catch(next);

router.post('/auth/login', loginLimiter, wrap(async (req, res) => {
  const result = await login(req.body?.username, req.body?.password);
  if (!result) return res.status(401).json({ error: 'Credenciales invalidas' });
  res.json(result);
}));

router.get('/health', wrap(async (_req, res) => {
  await query('SELECT 1 AS ok');
  res.json({ status: 'ok', time: new Date().toISOString() });
}));

router.use(authenticate);

router.get('/meta', wrap(async (_req, res) => {
  const [freshness, dimensions] = await Promise.all([cachedFreshness(), getDimensionValues()]);
  res.json({ freshness, dimensions, defaultRange: { from: addDays(freshness.lastOrderDate, -364), to: freshness.lastOrderDate } });
}));

router.get('/kpis/definitions', (_req, res) => res.json(KPI_DEFINITIONS));

router.get('/kpis', wrap(async (req, res) => {
  res.json(await getKpis(await resolveFilters(req.query)));
}));

router.get('/trends', wrap(async (req, res) => {
  const filters = await resolveFilters(req.query);
  const granularity = req.query.granularity ?? 'month';
  res.json({ granularity, series: await getTrend(filters, granularity) });
}));

router.get('/breakdown', wrap(async (req, res) => {
  const filters = await resolveFilters(req.query);
  res.json({ by: req.query.by ?? 'category', rows: await getBreakdown(filters, req.query.by, req.query.limit) });
}));

router.get('/detail', wrap(async (req, res) => {
  const filters = await resolveFilters(req.query);
  res.json(await getDetail(filters, req.query));
}));

router.get('/orders/:orderId', wrap(async (req, res) => {
  const id = Number.parseInt(req.params.orderId, 10);
  if (!Number.isInteger(id) || id <= 0) throw new ValidationError('orderId invalido');
  const order = await getOrder(id);
  if (!order) return res.status(404).json({ error: 'Pedido no encontrado' });
  res.json(order);
}));

router.get('/ops/etl-status', wrap(async (_req, res) => {
  const [runs, checks, freshness] = await Promise.all([
    query(`SELECT TOP 10 RunID, Process, Status, StartedAt, FinishedAt, RowsProcessed, Message
           FROM ops.etl_run_log ORDER BY RunID DESC`),
    query(`SELECT r.CheckName, r.SourceValue, r.DwValue, r.Difference, r.Passed, r.CheckedAt
           FROM ops.reconciliation_result r
           WHERE r.RunID = (SELECT MAX(RunID) FROM ops.reconciliation_result) ORDER BY r.ResultID`),
    cachedFreshness(),
  ]);
  const lastSuccess = runs.find((r) => r.Status === 'success');
  res.json({ freshness, lastSuccessfulRun: lastSuccess ?? null, runs, reconciliation: checks });
}));

router.get('/ops/metrics', requireRole('admin'), (_req, res) => res.json(snapshotMetrics()));

import { Router } from 'express';
import { requireRole } from '../auth.js';
import { evaluateAlerts, getAlert, listAlerts, setAlertStatus, simulateAlert } from '../services/alerts.js';

export const alertsRouter = Router();
const wrap = (fn) => (req, res, next) => fn(req, res).catch(next);

alertsRouter.get('/', wrap(async (req, res) => {
  res.json(await listAlerts({ status: req.query.status, limit: req.query.limit }));
}));

alertsRouter.get('/:id', wrap(async (req, res) => {
  const id = Number.parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: 'id invalido' });
  const alert = await getAlert(id);
  if (!alert) return res.status(404).json({ error: 'Alerta no encontrada' });
  res.json(alert);
}));

alertsRouter.patch('/:id/status', requireRole('analyst'), wrap(async (req, res) => {
  const id = Number.parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: 'id invalido' });
  const alert = await setAlertStatus(id, req.body?.status, req.user.username);
  if (!alert) return res.status(404).json({ error: 'Alerta no encontrada' });
  res.json(alert);
}));

alertsRouter.post('/evaluate', requireRole('admin'), wrap(async (req, res) => {
  res.json(await evaluateAlerts({ dryRun: Boolean(req.body?.dryRun) }));
}));

alertsRouter.post('/simulate', requireRole('admin'), wrap(async (req, res) => {
  res.json({ simulated: true, alerts: await simulateAlert(req.body?.kind, req.user.username) });
}));

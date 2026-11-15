import { useEffect, useState } from 'react';
import { api, fmt, useApi } from '../api.js';
import { Card, Status } from '../components/Common.jsx';

const SOURCE = {
  rule: ['Regla de negocio', 'ok'],
  model: ['Modelo ML (prediccion)', 'pred'],
  ai: ['Texto generado por IA', 'ai'],
};
const STATUS_LABEL = { new: 'Nueva', attended: 'Atendida', dismissed: 'Descartada', resolved: 'Resuelta' };

function AlertItem({ a, canEdit, onChange }) {
  const [open, setOpen] = useState(false);
  const detail = useApi(open ? `/alerts/${a.id}` : null, [open, a.status]);
  const [src, srcClass] = SOURCE[a.source];

  async function setStatus(status) {
    const updated = await api(`/alerts/${a.id}/status`, { method: 'PATCH', body: { status } });
    onChange(updated);
  }

  return (
    <article className={`alert ${a.severity} ${a.status}`}>
      <div className="msg-badges">
        <span className={`badge ${a.severity === 'low' || a.severity === 'medium' ? 'ai' : 'bad'}`}>{a.severity.toUpperCase()}</span>
        <span className={`badge ${srcClass}`}>{src}</span>
        {a.simulated && <span className="badge">SIMULACION</span>}
        <span className="badge">{STATUS_LABEL[a.status]}</span>
        <span className="muted">#{a.id} · {fmt.datetime(a.createdAt)}</span>
      </div>
      <strong>{a.indicator}{a.entity ? ` · ${a.entity}` : ''}</strong>
      <p className="muted">
        Observado: {fmt.money(a.observedValue)} · Umbral/referencia: {fmt.money(a.thresholdValue)} · {a.referencePeriod}
        {a.modelVersion ? ` · modelo ${a.modelVersion}` : ''}
      </p>
      {a.explanation && <p>{a.explanation}</p>}
      {a.recommendedAction && <p><em>Accion recomendada:</em> {a.recommendedAction}</p>}
      <div className="alert-actions">
        {canEdit && a.status === 'new' && <button onClick={() => setStatus('attended')}>Marcar atendida</button>}
        {canEdit && ['new', 'attended'].includes(a.status) && <button onClick={() => setStatus('resolved')}>Resolver</button>}
        {canEdit && ['new', 'attended'].includes(a.status) && <button onClick={() => setStatus('dismissed')}>Descartar</button>}
        <button className="link" onClick={() => setOpen(!open)}>{open ? 'Ocultar entrega' : 'Ver entrega'}</button>
      </div>
      {open && (
        <Status loading={detail.loading} error={detail.error} height={60}>
          {detail.data && (
            <table>
              <thead><tr><th>Canal</th><th>Intento</th><th>Estado</th><th>Detalle</th><th>Hora</th></tr></thead>
              <tbody>
                {detail.data.deliveries.map((d, i) => (
                  <tr key={i}><td>{d.channel}</td><td>{d.attempt}</td><td>{d.status}</td><td>{d.detail}</td><td>{fmt.datetime(d.at)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </Status>
      )}
    </article>
  );
}

export default function Alerts({ user, liveAlert }) {
  const [status, setStatus] = useState('');
  const { loading, error, data, reload } = useApi(`/alerts?limit=50${status ? `&status=${status}` : ''}`);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => { if (data) setItems(data); }, [data]);
  // Una alerta recibida por WebSocket aparece sin recargar.
  useEffect(() => {
    if (liveAlert && (!status || status === liveAlert.status)) {
      setItems((prev) => (prev.some((a) => a.id === liveAlert.id) ? prev : [liveAlert, ...prev]));
    }
  }, [liveAlert, status]);

  const canEdit = user.role !== 'viewer';
  const isAdmin = user.role === 'admin';

  async function run(label, fn) {
    setBusy(label); setNotice('');
    try { setNotice(await fn()); reload(); } catch (e) { setNotice(`Error: ${e.message}`); } finally { setBusy(''); }
  }
  const evaluate = () => run('evaluate', async () => {
    const r = await api('/alerts/evaluate', { method: 'POST', body: {} });
    return `Evaluacion completada: ${r.candidates.length} candidata(s), ${r.created.length} creada(s), ${r.duplicates} duplicada(s).`;
  });
  const simulate = (kind) => run(kind, async () => {
    const r = await api('/alerts/simulate', { method: 'POST', body: { kind } });
    const skipped = r.alerts.find((x) => x.aiSkipped);
    return `Simulacion '${kind}' ejecutada${skipped ? ` (resumen IA omitido: ${skipped.aiSkipped})` : ''}.`;
  });

  return (
    <Card title="Alertas" subtitle="Reglas de negocio, modelo predictivo e IA generativa · se actualizan en vivo por WebSocket"
          actions={
            <select aria-label="Filtrar por estado" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Todos los estados</option>
              {Object.entries(STATUS_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          }>
      {isAdmin && (
        <div className="alert-actions">
          <button disabled={!!busy} onClick={evaluate}>{busy === 'evaluate' ? 'Evaluando…' : 'Evaluar reglas ahora'}</button>
          <button disabled={!!busy} onClick={() => simulate('rule')}>Simular regla</button>
          <button disabled={!!busy} onClick={() => simulate('model')}>Simular modelo</button>
          <button disabled={!!busy} onClick={() => simulate('ai')}>{busy === 'ai' ? 'Generando resumen IA…' : 'Simular anomalia + resumen IA'}</button>
        </div>
      )}
      {notice && <p className="muted" role="status">{notice}</p>}
      <Status loading={loading && !items.length} error={error} onRetry={reload} empty={!loading && items.length === 0} height={120}>
        <div className="alert-list">
          {items.map((a) => (
            <AlertItem key={a.id} a={a} canEdit={canEdit}
                       onChange={(u) => setItems((prev) => prev.map((x) => (x.id === u.id ? u : x)))} />
          ))}
        </div>
      </Status>
    </Card>
  );
}

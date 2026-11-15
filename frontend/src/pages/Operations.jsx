import { fmt, useApi } from '../api.js';
import { Card, Status } from '../components/Common.jsx';

export default function Operations({ user }) {
  const etl = useApi('/ops/etl-status');
  const kpiDefs = useApi('/kpis/definitions');
  const metrics = useApi(user.role === 'admin' ? '/ops/metrics' : null);

  return (
    <>
      <Card title="Estado del ETL / Data Warehouse" subtitle="Ejecuciones recientes y reconciliacion origen vs DW">
        <Status loading={etl.loading} error={etl.error} onRetry={etl.reload} height={160}>
          {etl.data && (
            <>
              <div className="kpis">
                <div className="kpi"><span className="kpi-label">Ultima carga del DW</span><strong>{fmt.datetime(etl.data.freshness.lastLoadedAt)}</strong></div>
                <div className="kpi"><span className="kpi-label">Ultima ejecucion exitosa</span><strong>{fmt.datetime(etl.data.lastSuccessfulRun?.FinishedAt)}</strong></div>
                <div className="kpi"><span className="kpi-label">Filas en FactSales</span><strong>{fmt.int(etl.data.freshness.factRows)}</strong></div>
                <div className="kpi"><span className="kpi-label">Datos hasta</span><strong>{etl.data.freshness.lastOrderDate}</strong></div>
              </div>
              <h3>Reconciliacion (ultima ejecucion)</h3>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Comprobacion</th><th>Origen</th><th>DW</th><th>Resultado</th></tr></thead>
                  <tbody>
                    {etl.data.reconciliation.map((c) => (
                      <tr key={c.CheckName}>
                        <td>{c.CheckName}</td><td className="num">{fmt.int(c.SourceValue)}</td><td className="num">{fmt.int(c.DwValue)}</td>
                        <td><span className={`badge ${c.Passed ? 'ok' : 'bad'}`}>{c.Passed ? 'OK' : 'Diferencia'}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <h3>Ejecuciones</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>#</th><th>Proceso</th><th>Estado</th><th>Fin</th><th>Leidas</th>
                      <th>Insertadas</th><th>Actualizadas</th><th>Rechazadas</th><th>Eliminadas</th>
                      <th>Duracion (s)</th><th>Detalle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {etl.data.runs.map((r) => (
                      <tr key={r.RunID}>
                        <td>{r.RunID}</td><td>{r.Process}</td>
                        <td><span className={`badge ${r.Status === 'success' ? 'ok' : r.Status === 'warning' ? 'warn' : 'bad'}`}>{r.Status}</span></td>
                        <td>{fmt.datetime(r.FinishedAt)}</td>
                        <td className="num">{fmt.int(r.RowsRead ?? r.RowsProcessed)}</td>
                        <td className="num">{fmt.int(r.RowsInserted)}</td>
                        <td className="num">{fmt.int(r.RowsUpdated)}</td>
                        <td className="num">{fmt.int(r.RowsRejected)}</td>
                        <td className="num">{fmt.int(r.RowsDeleted)}</td>
                        <td className="num">{r.DurationSeconds == null ? '-' : Number(r.DurationSeconds).toFixed(1)}</td>
                        <td>{r.Message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Status>
      </Card>

      <Card title="Definicion de KPIs">
        <Status loading={kpiDefs.loading} error={kpiDefs.error} onRetry={kpiDefs.reload}>
          {kpiDefs.data && (
            <div className="table-wrap">
              <table>
                <thead><tr><th>KPI</th><th>Proposito</th><th>Formula</th><th>Unidad</th><th>Fuente</th><th>Responsable</th></tr></thead>
                <tbody>
                  {kpiDefs.data.map((k) => (
                    <tr key={k.id}><td>{k.name}</td><td>{k.purpose}</td><td>{k.formula}</td><td>{k.unit}</td><td>{k.source}</td><td>{k.owner}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Status>
      </Card>

      {user.role === 'admin' && (
        <Card title="Tiempos de respuesta de la API" subtitle="Medidos desde el ultimo reinicio del backend">
          <Status loading={metrics.loading} error={metrics.error} onRetry={metrics.reload}>
            {metrics.data && (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Ruta</th><th>Llamadas</th><th>Prom. (ms)</th><th>p50</th><th>p95</th></tr></thead>
                  <tbody>
                    {metrics.data.map((m) => (
                      <tr key={m.route}><td>{m.route}</td><td className="num">{m.count}</td><td className="num">{m.avgMs}</td><td className="num">{m.p50Ms}</td><td className="num">{m.p95Ms}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Status>
        </Card>
      )}
    </>
  );
}

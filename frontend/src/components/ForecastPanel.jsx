import { Area, Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fmt, useApi } from '../api.js';
import { Card, Status } from './Common.jsx';

const pctOrDash = (v) => (v == null ? '—' : `${v.toFixed(1)}%`);

export default function ForecastPanel() {
  const { loading, error, data, reload } = useApi('/ml/forecast');
  const unavailable = data && !data.model;

  const chart = data?.model
    ? [
        ...data.history.map((h) => ({ name: h.period.slice(5), actual: h.netSales })),
        ...data.predictions.map((p) => ({
          name: p.period.slice(5), predicted: p.value, baseline: p.baseline, band: [p.lower, p.upper],
        })),
      ]
    : [];
  const test = data?.model?.metrics?.test;

  return (
    <Card title="Prediccion de ventas semanales" className="forecast"
          subtitle="PREDICCION generada por un modelo de machine learning; no es un dato historico"
          actions={data?.model && <span className="badge pred">Prediccion · modelo {data.model.version}</span>}>
      <Status loading={loading} error={error} onRetry={reload} empty={unavailable} height={200}>
        {data?.model && (
          <>
            <div className="chart" role="img" aria-label="Historial y prediccion de ventas semanales">
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" minTickGap={14} />
                  <YAxis tickFormatter={fmt.compact} width={56} />
                  <Tooltip formatter={(v) => (Array.isArray(v) ? `${fmt.money(v[0])} – ${fmt.money(v[1])}` : fmt.money(v))} />
                  <Legend />
                  <Bar dataKey="actual" name="Historico (dato)" fill="#2563eb" />
                  <Area dataKey="band" name="Intervalo de prediccion" fill="#ddd6fe" stroke="none" />
                  <Line dataKey="predicted" name="Prediccion (modelo)" stroke="#7c3aed" strokeWidth={2} dot />
                  <Line dataKey="baseline" name="Linea base (semana comparable)" stroke="#9ca3af" strokeDasharray="5 4" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Metrica (conjunto de prueba)</th><th>Modelo</th><th>Linea base</th></tr></thead>
                <tbody>
                  <tr><td>MAE</td><td className="num">{fmt.money(test.model.mae)}</td><td className="num">{fmt.money(test.baseline.mae)}</td></tr>
                  <tr><td>RMSE</td><td className="num">{fmt.money(test.model.rmse)}</td><td className="num">{fmt.money(test.baseline.rmse)}</td></tr>
                  <tr><td>MAPE</td><td className="num">{pctOrDash(test.model.mape)}</td><td className="num">{pctOrDash(test.baseline.mape)}</td></tr>
                </tbody>
              </table>
            </div>
            <p className="muted">
              {data.model.algorithm} · entrenado {fmt.datetime(data.model.trainedAt)} · entrenamiento {data.model.trainPeriod} ·
              prueba {data.model.testPeriod}. {data.model.limitations}
            </p>
          </>
        )}
      </Status>
    </Card>
  );
}

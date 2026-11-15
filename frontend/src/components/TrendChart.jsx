import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fmt } from '../api.js';

const label = (period, granularity) =>
  granularity === 'quarter'
    ? `${period.slice(0, 4)}-T${Math.floor((Number(period.slice(5, 7)) - 1) / 3) + 1}`
    : granularity === 'week' ? period.slice(5) : period.slice(0, 7);

/** `forecast` (opcional) = predicciones del modelo, dibujadas aparte y rotuladas como prediccion. */
export default function TrendChart({ series, granularity, forecast = [] }) {
  const data = [
    ...series.map((p) => ({ name: label(p.period, granularity), actual: p.netSales, previous: p.previousYearSales })),
    ...forecast.map((p) => ({ name: label(p.period, granularity), predicted: p.value })),
  ];
  return (
    <div className="chart" role="img" aria-label="Tendencia de ventas netas">
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" minTickGap={16} />
          <YAxis tickFormatter={fmt.compact} width={56} />
          <Tooltip formatter={(v) => fmt.money(v)} />
          <Legend />
          <Bar dataKey="actual" name="Ventas netas (dato historico)" fill="#2563eb" />
          <Line dataKey="previous" name="Mismo periodo ano anterior" stroke="#f59e0b" strokeWidth={2} dot={false} connectNulls />
          {forecast.length > 0 && <Bar dataKey="predicted" name="Prediccion (modelo ML)" fill="#a78bfa" />}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

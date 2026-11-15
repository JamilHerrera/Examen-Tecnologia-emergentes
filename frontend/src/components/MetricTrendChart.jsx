import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { fmt } from '../api.js';

export default function MetricTrendChart({
  series, measures, type = 'line', valueFormat = fmt.money, ariaLabel,
}) {
  const data = series.map((row) => ({ ...row, label: row.period.slice(0, 7) }));
  const Chart = type === 'bar' ? BarChart : LineChart;
  return (
    <div className="chart" role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height={300}>
        <Chart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" minTickGap={16} />
          <YAxis tickFormatter={fmt.compact} width={64} />
          <Tooltip formatter={(value) => valueFormat(value)} />
          <Legend />
          {measures.map((measure) => (
            type === 'bar'
              ? <Bar key={measure.key} dataKey={measure.key} name={measure.name} fill={measure.color} />
              : <Line key={measure.key} dataKey={measure.key} name={measure.name}
                  stroke={measure.color} strokeWidth={2} dot={false} connectNulls />
          ))}
        </Chart>
      </ResponsiveContainer>
    </div>
  );
}

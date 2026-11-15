import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fmt } from '../api.js';

/** Barras horizontales; si `onSelect` existe, hacer clic en una barra aplica drill-down. */
export default function BreakdownChart({ rows, onSelect, activeName }) {
  const height = Math.max(220, rows.length * 34);
  return (
    <div className="chart" role="img" aria-label="Ventas netas por dimension">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={fmt.compact} />
          <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v, _n, p) => [`${fmt.money(v)} (${p.payload.sharePct.toFixed(1)}%)`, 'Ventas netas']} />
          <Bar dataKey="netSales" cursor={onSelect ? 'pointer' : 'default'}
               onClick={(d) => onSelect?.(d.name)}>
            {rows.map((r) => <Cell key={r.name} fill={r.name === activeName ? '#1d4ed8' : '#60a5fa'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

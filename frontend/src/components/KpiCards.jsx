import { fmt } from '../api.js';

const CARDS = [
  ['netSales', 'Ventas netas', fmt.money, 'GBP antes de impuestos'],
  ['orders', 'Pedidos', fmt.int, 'pedidos distintos'],
  ['avgTicket', 'Ticket promedio', fmt.money2, 'ventas / pedidos'],
  ['units', 'Unidades vendidas', fmt.int, 'unidades'],
  ['activeCustomers', 'Clientes activos', fmt.int, 'con compras en el periodo'],
  ['growth', 'Crecimiento de ventas', fmt.pct, 'vs. periodo anterior'],
];

export default function KpiCards({ data }) {
  const prev = data.previousPeriod;
  return (
    <div className="kpis">
      {CARDS.map(([id, label, format, hint]) => {
        const k = data.kpis[id];
        const delta = id === 'growth' ? null : k.deltaPct;
        const trendClass = (id === 'growth' ? k.value : delta) >= 0 ? 'up' : 'down';
        return (
          <div className="kpi" key={id}>
            <span className="kpi-label">{label}</span>
            <strong className={id === 'growth' && k.value != null ? trendClass : ''}>{format(k.value)}</strong>
            <span className="muted">{hint}</span>
            {delta != null && (
              <span className={`delta ${trendClass}`} title={`Periodo anterior: ${prev.from} a ${prev.to}`}>
                {fmt.pct(delta)} vs. anterior
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

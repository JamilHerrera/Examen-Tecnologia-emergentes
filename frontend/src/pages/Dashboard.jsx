import { useMemo, useState } from 'react';
import { fmt, toQuery, useApi } from '../api.js';
import { Card, Status } from '../components/Common.jsx';
import Filters from '../components/Filters.jsx';
import KpiCards from '../components/KpiCards.jsx';
import TrendChart from '../components/TrendChart.jsx';
import BreakdownChart from '../components/BreakdownChart.jsx';
import DetailTable from '../components/DetailTable.jsx';
import OrderModal from '../components/OrderModal.jsx';
import ForecastPanel from '../components/ForecastPanel.jsx';

const BREAKDOWNS = [
  ['category', 'Categoria de producto'],
  ['region', 'Region'],
  ['customerCategory', 'Categoria de cliente'],
  ['state', 'Estado / provincia'],
  ['customer', 'Cliente'],
];
const DRILLABLE = new Set(['category', 'region', 'customerCategory']);

export default function Dashboard({ meta }) {
  const defaults = useMemo(() => ({
    from: meta.defaultRange.from, to: meta.defaultRange.to,
    category: '', region: '', customerCategory: '', product: '',
  }), [meta]);
  const [filters, setFilters] = useState(defaults);
  const [granularity, setGranularity] = useState('month');
  const [by, setBy] = useState('category');
  const [orderId, setOrderId] = useState(null);

  const qs = toQuery(filters);
  const kpis = useApi(`/kpis?${qs}`);
  const trend = useApi(`/trends?${qs}&granularity=${granularity}`);
  const breakdown = useApi(`/breakdown?${qs}&by=${by}&limit=12`);
  const products = useApi(`/breakdown?${qs}&by=product&limit=10`);

  const drill = (name) => {
    const patch = { [by]: filters[by] === name ? '' : name };
    setFilters({ ...filters, ...patch });
  };

  return (
    <>
      <Filters meta={meta} filters={filters} onChange={setFilters} onReset={() => setFilters(defaults)} />

      <Status loading={kpis.loading} error={kpis.error} onRetry={kpis.reload} empty={kpis.data && !kpis.data.hasData} height={140}>
        {kpis.data && <KpiCards data={kpis.data} />}
      </Status>

      <div className="grid two">
        <Card title="Tendencia de ventas netas" subtitle="Comparada con el mismo periodo del ano anterior"
              className="span-2"
              actions={
                <select aria-label="Granularidad" value={granularity} onChange={(e) => setGranularity(e.target.value)}>
                  <option value="month">Mensual</option><option value="quarter">Trimestral</option><option value="week">Semanal</option>
                </select>
              }>
          <Status loading={trend.loading} error={trend.error} onRetry={trend.reload} empty={trend.data && trend.data.series.length === 0} height={300}>
            {trend.data && <TrendChart series={trend.data.series} granularity={granularity} />}
          </Status>
        </Card>

        <Card title="Ventas por dimension" subtitle={DRILLABLE.has(by) ? 'Haz clic en una barra para filtrar (drill-down)' : undefined}
              actions={
                <select aria-label="Dimension" value={by} onChange={(e) => setBy(e.target.value)}>
                  {BREAKDOWNS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select>
              }>
          <Status loading={breakdown.loading} error={breakdown.error} onRetry={breakdown.reload} empty={breakdown.data && breakdown.data.rows.length === 0} height={220}>
            {breakdown.data && <BreakdownChart rows={breakdown.data.rows} activeName={filters[by]} onSelect={DRILLABLE.has(by) ? drill : undefined} />}
          </Status>
        </Card>

        <Card title="Top 10 productos" subtitle="Haz clic para filtrar por producto">
          <Status loading={products.loading} error={products.error} onRetry={products.reload} empty={products.data && products.data.rows.length === 0} height={220}>
            {products.data && <BreakdownChart rows={products.data.rows} activeName={filters.product}
              onSelect={(name) => setFilters({ ...filters, product: filters.product === name ? '' : name })} />}
          </Status>
        </Card>
      </div>

      <ForecastPanel />

      <Card title="Detalle de ventas" subtitle={`Lineas de pedido del periodo ${filters.from} a ${filters.to}. Haz clic en un pedido para ver su detalle.`}>
        <DetailTable filters={filters} onOpenOrder={setOrderId} />
      </Card>

      <p className="muted footnote">
        Datos historicos del Data Warehouse · pedidos hasta {meta.freshness.lastOrderDate} ·
        ultima carga {fmt.datetime(meta.freshness.lastLoadedAt)}
      </p>
      {orderId && <OrderModal orderId={orderId} onClose={() => setOrderId(null)} />}
    </>
  );
}

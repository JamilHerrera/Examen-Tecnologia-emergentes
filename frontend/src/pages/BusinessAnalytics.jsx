import { useState } from 'react';
import { fmt, toQuery, useApi } from '../api.js';
import { Card, Status } from '../components/Common.jsx';
import MetricTrendChart from '../components/MetricTrendChart.jsx';

const SECTIONS = [
  ['purchases', 'Compras'],
  ['profitability', 'Rentabilidad'],
  ['inventory', 'Inventario'],
];

function MetricCards({ items }) {
  return (
    <div className="kpis">
      {items.map(([label, value, note]) => (
        <div className="kpi" key={label}>
          <span className="kpi-label">{label}</span>
          <strong>{value}</strong>
          <span className="muted">{note}</span>
        </div>
      ))}
    </div>
  );
}

function RankingTable({ title, rows, columns, emptyText }) {
  return (
    <Card title={title}>
      {rows.length === 0 ? <p className="muted">{emptyText}</p> : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.name}>
                  {columns.map(([key, _label, format]) => (
                    <td className={format ? 'num' : ''} key={key}>
                      {format ? format(row[key]) : row[key] ?? '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function Purchases({ result }) {
  const { summary } = result.data;
  return (
    <Status loading={result.loading} error={result.error} onRetry={result.reload}
      empty={result.data && summary.lines === 0} height={180}>
      {result.data && (
        <>
          <MetricCards items={[
            ['Compras netas', fmt.money2(summary.purchaseAmount), 'Facturas de proveedor, antes de impuestos'],
            ['Unidades recibidas', fmt.int(summary.receivedQuantity), 'Unidades base de los articulos'],
            ['Ordenes de compra', fmt.int(summary.purchaseOrders), 'Con lineas recibidas y facturadas'],
            ['Proveedores', fmt.int(summary.suppliers), 'En el periodo seleccionado'],
          ]} />
          <div className="grid two">
            <Card title="Compras netas por mes" subtitle="GBP antes de impuestos">
              <MetricTrendChart series={result.data.series}
                measures={[{ key: 'purchaseAmount', name: 'Compras netas', color: '#2563eb' }]}
                ariaLabel="Compras netas mensuales" />
            </Card>
            <RankingTable title="Compras por proveedor" rows={result.data.suppliers}
              columns={[
                ['name', 'Proveedor'],
                ['purchaseOrders', 'Ordenes'],
                ['receivedQuantity', 'Unidades', fmt.int],
                ['purchaseAmount', 'Importe', fmt.money2],
              ]} emptyText="No hay proveedores para el periodo." />
            <RankingTable title="Compras por producto" rows={result.data.products}
              columns={[
                ['name', 'Producto'],
                ['receivedQuantity', 'Unidades', fmt.int],
                ['purchaseAmount', 'Importe', fmt.money2],
              ]} emptyText="No hay productos para el periodo." />
          </div>
        </>
      )}
    </Status>
  );
}

function Profitability({ result }) {
  const { summary } = result.data;
  return (
    <Status loading={result.loading} error={result.error} onRetry={result.reload}
      empty={result.data && summary.lines === 0} height={180}>
      {result.data && (
        <>
          <MetricCards items={[
            ['Ventas facturadas', fmt.money2(summary.netSales), 'Importe antes de impuestos'],
            ['Utilidad', fmt.money2(summary.profit), 'Suma de LineProfit del origen'],
            ['Margen', fmt.pct(summary.marginPct), 'Utilidad / ventas facturadas'],
            ['Facturas', fmt.int(summary.invoices), 'En el periodo seleccionado'],
          ]} />
          <div className="grid two">
            <Card title="Ventas y utilidad por mes" subtitle="Fuente: lineas de factura de venta">
              <MetricTrendChart series={result.data.series}
                measures={[
                  { key: 'netSales', name: 'Ventas facturadas', color: '#2563eb' },
                  { key: 'profit', name: 'Utilidad', color: '#15803d' },
                ]}
                ariaLabel="Ventas facturadas y utilidad mensual" />
            </Card>
            <RankingTable title="Rentabilidad por categoria" rows={result.data.categories}
              columns={[
                ['name', 'Categoria'],
                ['netSales', 'Ventas', fmt.money2],
                ['profit', 'Utilidad', fmt.money2],
                ['marginPct', 'Margen', fmt.pct],
              ]} emptyText="No hay categorias para el periodo." />
            <RankingTable title="Utilidad por producto" rows={result.data.products}
              columns={[
                ['name', 'Producto'],
                ['invoices', 'Facturas'],
                ['netSales', 'Ventas', fmt.money2],
                ['profit', 'Utilidad', fmt.money2],
              ]} emptyText="No hay productos para el periodo." />
          </div>
        </>
      )}
    </Status>
  );
}

function Inventory({ result }) {
  const { movements, snapshot } = result.data;
  return (
    <Status loading={result.loading} error={result.error} onRetry={result.reload}
      empty={result.data && movements.transactions === 0 && snapshot.items === 0} height={180}>
      {result.data && (
        <>
          <MetricCards items={[
            ['Existencias en snapshot', fmt.int(snapshot.unitsOnHand), `${fmt.int(snapshot.items)} articulos`],
            ['Articulos bajo minimo', fmt.int(snapshot.belowReorder), `Snapshot ${snapshot.date ?? 'no disponible'}`],
            ['Entradas', fmt.int(movements.receipts), 'Movimientos positivos del periodo'],
            ['Salidas', fmt.int(movements.issues), 'Movimientos negativos del periodo'],
          ]} />
          <div className="grid two">
            <Card title="Movimientos de inventario por mes" subtitle="Unidades recibidas y emitidas; ajustes segun el origen">
              <MetricTrendChart type="bar" valueFormat={fmt.int} series={movements.series}
                measures={[
                  { key: 'receipts', name: 'Entradas', color: '#15803d' },
                  { key: 'issues', name: 'Salidas', color: '#b91c1c' },
                  { key: 'adjustments', name: 'Ajustes', color: '#f59e0b' },
                ]}
                ariaLabel="Movimientos de inventario mensuales" />
            </Card>
            <RankingTable title="Existencias bajo el punto de reorden" rows={snapshot.lowStock}
              columns={[
                ['name', 'Producto'],
                ['category', 'Categoria'],
                ['quantityOnHand', 'Disponible', fmt.int],
                ['reorderLevel', 'Reorden', fmt.int],
                ['status', 'Estado'],
              ]} emptyText="No hay articulos por debajo del punto de reorden." />
          </div>
          <p className="muted">
            Los movimientos muestran flujos historicos. Las existencias son solo el snapshot del {snapshot.date};
            no se reconstruyen saldos historicos porque el origen no los reconcilia para todos los articulos.
          </p>
        </>
      )}
    </Status>
  );
}

export default function BusinessAnalytics({ meta }) {
  const [section, setSection] = useState('purchases');
  const [period, setPeriod] = useState(() => ({
    from: meta.defaultRange.from,
    to: meta.defaultRange.to,
  }));
  const query = toQuery(period);
  const purchases = useApi(`/business/purchases?${query}`);
  const profitability = useApi(`/business/profitability?${query}`);
  const inventory = useApi(`/business/inventory?${query}`);

  return (
    <>
      <div className="filters">
        <label>Desde
          <input type="date" value={period.from} onChange={(event) => setPeriod({ ...period, from: event.target.value })} />
        </label>
        <label>Hasta
          <input type="date" value={period.to} onChange={(event) => setPeriod({ ...period, to: event.target.value })} />
        </label>
      </div>
      <nav className="subtabs" aria-label="Analitica comercial">
        {SECTIONS.map(([id, label]) => (
          <button key={id} className={section === id ? 'tab active' : 'tab'} onClick={() => setSection(id)}>
            {label}
          </button>
        ))}
      </nav>
      {section === 'purchases' && <Purchases result={purchases} />}
      {section === 'profitability' && <Profitability result={profitability} />}
      {section === 'inventory' && <Inventory result={inventory} />}
      <p className="muted footnote">Importes en GBP; ventas por factura, compras por factura de proveedor e inventario por movimientos y snapshot.</p>
    </>
  );
}

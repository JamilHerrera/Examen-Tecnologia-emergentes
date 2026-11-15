import { useState } from 'react';
import { fmt, toQuery, useApi } from '../api.js';
import { Status } from './Common.jsx';

const COLUMNS = [
  ['date', 'Fecha', 'orderDate'],
  ['customer', 'Cliente', 'customer'],
  ['product', 'Producto', 'product'],
  ['quantity', 'Cant.', 'quantity'],
  ['netSales', 'Venta neta', 'netSales'],
];

export default function DetailTable({ filters, onOpenOrder }) {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState('date');
  const [dir, setDir] = useState('desc');
  const qs = toQuery({ ...filters, page, pageSize: 15, sort, dir });
  const { loading, error, data, reload } = useApi(`/detail?${qs}`);

  function toggle(col) {
    if (col === sort) setDir(dir === 'asc' ? 'desc' : 'asc');
    else { setSort(col); setDir('desc'); }
    setPage(1);
  }

  return (
    <Status loading={loading} error={error} onRetry={reload} empty={data && data.total === 0} height={200}>
      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {COLUMNS.map(([key, label]) => (
                    <th key={key} onClick={() => toggle(key)} className="sortable" aria-sort={sort === key ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                      {label}{sort === key ? (dir === 'asc' ? ' ▲' : ' ▼') : ''}
                    </th>
                  ))}
                  <th>Pedido</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={`${r.orderId}-${r.orderLineId}`}>
                    <td>{r.orderDate}</td><td>{r.customer}</td><td>{r.product}</td>
                    <td className="num">{fmt.int(r.quantity)}</td><td className="num">{fmt.money2(r.netSales)}</td>
                    <td><button className="link" onClick={() => onOpenOrder(r.orderId)}>#{r.orderId}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
            <span>Pagina {data.page} de {fmt.int(data.totalPages)} · {fmt.int(data.total)} lineas</span>
            <button disabled={page >= data.totalPages} onClick={() => setPage(page + 1)}>Siguiente</button>
          </div>
        </>
      )}
    </Status>
  );
}

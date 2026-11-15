import { fmt, useApi } from '../api.js';
import { Status } from './Common.jsx';

export default function OrderModal({ orderId, onClose }) {
  const { loading, error, data, reload } = useApi(`/orders/${orderId}`);
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal card" role="dialog" aria-modal="true" aria-label={`Pedido ${orderId}`} onClick={(e) => e.stopPropagation()}>
        <header className="card-head">
          <h2>Pedido #{orderId}</h2>
          <button onClick={onClose} aria-label="Cerrar">×</button>
        </header>
        <Status loading={loading} error={error} onRetry={reload}>
          {data && (
            <>
              <p className="muted">{data.customer} · {data.city} ({data.region}) · {data.orderDate}</p>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Categoria</th><th>Producto</th><th>Cant.</th><th>Precio</th><th>Venta neta</th></tr></thead>
                  <tbody>
                    {data.lines.map((l) => (
                      <tr key={l.orderLineId}>
                        <td>{l.category}</td><td>{l.product}</td><td className="num">{fmt.int(l.quantity)}</td>
                        <td className="num">{fmt.money2(l.unitPrice)}</td><td className="num">{fmt.money2(l.netSales)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot><tr><td colSpan="4">Total del pedido</td><td className="num">{fmt.money2(data.total)}</td></tr></tfoot>
                </table>
              </div>
            </>
          )}
        </Status>
      </div>
    </div>
  );
}

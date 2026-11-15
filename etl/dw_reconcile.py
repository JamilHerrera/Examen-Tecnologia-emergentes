"""
Reconciliacion origen -> staging -> Data Warehouse -> capa BI.
Registra la ejecucion en ops.etl_run_log y cada comprobacion en ops.reconciliation_result.

Uso:  python etl/dw_reconcile.py
"""
import sys

sys.path.insert(0, ".")
from etl.config import SQL_SERVER_CONFIG
from etl.extract import DatabaseConnector

# (nombre, SQL origen, SQL DW, nota)
CHECKS = [
    ("Lineas de pedido: origen vs FactSales",
     "SELECT COUNT_BIG(*) FROM Sales.OrderLines",
     "SELECT COUNT_BIG(*) FROM dw.FactSales",
     "Grano = linea de pedido; sin rechazos esperados"),
    ("Lineas de pedido: staging_clean vs FactSales",
     "SELECT COUNT_BIG(*) FROM staging_clean.Sales_OrderLines_clean",
     "SELECT COUNT_BIG(*) FROM dw.FactSales",
     "Staging no descarta filas"),
    ("Ventas netas (cantidad x precio): origen vs FactSales",
     "SELECT SUM(CAST(Quantity AS DECIMAL(24,2)) * UnitPrice) FROM Sales.OrderLines",
     "SELECT SUM(CAST(LineTotal AS DECIMAL(24,2))) FROM dw.FactSales",
     "Ventas netas antes de impuestos"),
    ("Unidades vendidas: origen vs FactSales",
     "SELECT SUM(CAST(Quantity AS DECIMAL(24,2))) FROM Sales.OrderLines",
     "SELECT SUM(CAST(Quantity AS DECIMAL(24,2))) FROM dw.FactSales",
     None),
    ("Pedidos distintos: origen vs FactSales",
     "SELECT COUNT(DISTINCT OrderID) FROM Sales.OrderLines",
     "SELECT COUNT(DISTINCT OrderID) FROM dw.FactSales",
     None),
    ("Clientes: origen vs DimCustomer",
     "SELECT COUNT(*) FROM Sales.Customers",
     "SELECT COUNT(*) FROM dw.DimCustomer WHERE IsCurrent = 1",
     "Solo version vigente (SCD tipo 2)"),
    ("Productos: origen vs DimProduct",
     "SELECT COUNT(*) FROM Warehouse.StockItems",
     "SELECT COUNT(*) FROM dw.DimProduct",
     None),
    ("Ventas netas: FactSales vs vista bi.vw_sales_detail (sin duplicacion por joins)",
     "SELECT SUM(CAST(LineTotal AS DECIMAL(24,2))) FROM dw.FactSales",
     "SELECT SUM(CAST(NetSales AS DECIMAL(24,2))) FROM bi.vw_sales_detail",
     "Verifica que los joins a dimensiones no multiplican importes"),
    ("Hechos huerfanos (FK a dimensiones) = 0",
     "SELECT 0",
     """SELECT COUNT(*) FROM dw.FactSales f
        WHERE NOT EXISTS (SELECT 1 FROM dw.DimDate d WHERE d.DateKey = f.DateKey)
           OR NOT EXISTS (SELECT 1 FROM dw.DimCustomer c WHERE c.CustomerKey = f.CustomerKey)
           OR NOT EXISTS (SELECT 1 FROM dw.DimProduct p WHERE p.ProductKey = f.ProductKey)
           OR NOT EXISTS (SELECT 1 FROM dw.DimGeography g WHERE g.GeographyKey = f.GeographyKey)""",
     None),
    ("Hechos sin geografia real = 0",
     "SELECT 0",
     "SELECT COUNT(*) FROM dw.FactSales WHERE GeographyKey = 1",
     "GeographyKey=1 es el miembro 'Unknown'"),
]


def main():
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cn = conn.connection
    cur = cn.cursor()
    cur.execute(
        "INSERT INTO ops.etl_run_log (Process, Status) OUTPUT INSERTED.RunID "
        "VALUES ('dw_reconciliation', 'running')"
    )
    run_id = cur.fetchone()[0]
    cn.commit()

    failures = 0
    print(f"{'COMPROBACION':<78} {'ORIGEN':>18} {'DW':>18}  OK")
    for name, src_sql, dw_sql, note in CHECKS:
        cur.execute(src_sql)
        src = cur.fetchone()[0] or 0
        cur.execute(dw_sql)
        dw = cur.fetchone()[0] or 0
        passed = int(src) == int(dw) if float(src).is_integer() and float(dw).is_integer() else abs(float(src) - float(dw)) < 0.005
        failures += 0 if passed else 1
        print(f"{name[:78]:<78} {float(src):>18,.2f} {float(dw):>18,.2f}  {'SI' if passed else 'NO'}")
        cur.execute(
            "INSERT INTO ops.reconciliation_result (RunID, CheckName, SourceValue, DwValue, Passed, Note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            run_id, name, src, dw, 1 if passed else 0, note,
        )

    cur.execute("SELECT COUNT_BIG(*) FROM dw.FactSales")
    rows = cur.fetchone()[0]
    cur.execute(
        "UPDATE ops.etl_run_log SET Status = ?, FinishedAt = SYSUTCDATETIME(), RowsProcessed = ?, Message = ? "
        "WHERE RunID = ?",
        "success" if failures == 0 else "warning", rows,
        f"{len(CHECKS) - failures}/{len(CHECKS)} comprobaciones superadas", run_id,
    )
    cn.commit()
    conn.disconnect()
    print(f"\nResultado: {len(CHECKS) - failures}/{len(CHECKS)} comprobaciones superadas (RunID {run_id})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

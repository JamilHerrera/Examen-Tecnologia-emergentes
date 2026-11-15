"""Load purchasing, invoice profitability, and inventory facts into the DW."""

import sys

sys.path.insert(0, ".")
from etl.config import SQL_SERVER_CONFIG
from etl.extract import DatabaseConnector
from etl.ops_log import finish_run, start_run

SUPPLIER_UPDATE_SQL = """
UPDATE dimension
SET SupplierName = source.SupplierName,
    SupplierCategory = source.SupplierCategory
FROM dw.DimSupplier dimension
JOIN (
    SELECT supplier.SupplierID, supplier.SupplierName,
           category.SupplierCategoryName AS SupplierCategory
    FROM Purchasing.Suppliers supplier
    LEFT JOIN Purchasing.SupplierCategories category
        ON category.SupplierCategoryID = supplier.SupplierCategoryID
) source ON source.SupplierID = dimension.SupplierID
WHERE dimension.SupplierName <> source.SupplierName
   OR ISNULL(dimension.SupplierCategory, N'') <> ISNULL(source.SupplierCategory, N'');
"""

SUPPLIER_INSERT_SQL = """
INSERT INTO dw.DimSupplier (SupplierID, SupplierName, SupplierCategory)
SELECT supplier.SupplierID, supplier.SupplierName, category.SupplierCategoryName
FROM Purchasing.Suppliers supplier
LEFT JOIN Purchasing.SupplierCategories category
    ON category.SupplierCategoryID = supplier.SupplierCategoryID
WHERE NOT EXISTS (
    SELECT 1 FROM dw.DimSupplier dimension
    WHERE dimension.SupplierID = supplier.SupplierID
);
"""

PURCHASE_INVOICE_CTE = """
WITH SupplierInvoices AS (
    SELECT txn.SupplierTransactionID, txn.SupplierID,
           txn.PurchaseOrderID, txn.TransactionDate,
           txn.AmountExcludingTax
    FROM Purchasing.SupplierTransactions txn
    JOIN Application.TransactionTypes type
        ON type.TransactionTypeID = txn.TransactionTypeID
    WHERE type.TransactionTypeName = N'Supplier Invoice'
)
"""

PRECHECKS = [
    (
        "supplier invoice without purchase order",
        """
        SELECT COUNT_BIG(*)
        FROM Purchasing.SupplierTransactions txn
        JOIN Application.TransactionTypes type
            ON type.TransactionTypeID = txn.TransactionTypeID
        WHERE type.TransactionTypeName = N'Supplier Invoice'
          AND txn.PurchaseOrderID IS NULL
        """,
        "Supplier invoices must reference a purchase order before product-level allocation.",
    ),
    (
        "purchase orders with multiple supplier invoices",
        """
        SELECT COUNT_BIG(*) FROM (
            SELECT txn.PurchaseOrderID
            FROM Purchasing.SupplierTransactions txn
            JOIN Application.TransactionTypes type
                ON type.TransactionTypeID = txn.TransactionTypeID
            WHERE type.TransactionTypeName = N'Supplier Invoice'
            GROUP BY txn.PurchaseOrderID
            HAVING COUNT_BIG(*) <> 1
        ) duplicates
        """,
        "Each purchase order must have one supplier invoice to allocate its amount to lines.",
    ),
    (
        "purchase invoice amounts not reconciled to received lines",
        PURCHASE_INVOICE_CTE
        + """
        SELECT COUNT_BIG(*)
        FROM SupplierInvoices invoice
        LEFT JOIN (
            SELECT PurchaseOrderID,
                   SUM(CAST(ExpectedUnitPricePerOuter * ReceivedOuters AS DECIMAL(19,2))) AS LineAmount
            FROM Purchasing.PurchaseOrderLines
            GROUP BY PurchaseOrderID
        ) lines ON lines.PurchaseOrderID = invoice.PurchaseOrderID
        WHERE lines.PurchaseOrderID IS NULL
           OR ABS(lines.LineAmount - invoice.AmountExcludingTax) > 0.01
        """,
        "Purchase-order line allocations must equal the supplier invoice amount before tax.",
    ),
    (
        "received purchase lines without supplier invoice",
        """
        SELECT COUNT_BIG(*)
        FROM Purchasing.PurchaseOrderLines line
        WHERE line.ReceivedOuters > 0
          AND NOT EXISTS (
              SELECT 1
              FROM Purchasing.SupplierTransactions txn
              JOIN Application.TransactionTypes type
                  ON type.TransactionTypeID = txn.TransactionTypeID
              WHERE type.TransactionTypeName = N'Supplier Invoice'
                AND txn.PurchaseOrderID = line.PurchaseOrderID
          )
        """,
        "Received purchase lines must have a supplier invoice for spend reporting.",
    ),
    (
        "unresolved invoice-line dimension keys",
        """
        SELECT COUNT_BIG(*)
        FROM Sales.InvoiceLines line
        JOIN Sales.Invoices invoice ON invoice.InvoiceID = line.InvoiceID
        LEFT JOIN dw.DimDate date ON date.Date = invoice.InvoiceDate
        LEFT JOIN dw.DimProduct product ON product.StockItemID = line.StockItemID
        LEFT JOIN dw.DimCustomer customer
            ON customer.CustomerID = invoice.CustomerID
           AND CONVERT(DATETIME2(7), invoice.InvoiceDate) >= customer.ValidFrom
           AND CONVERT(DATETIME2(7), invoice.InvoiceDate) < customer.ValidTo
        WHERE date.DateKey IS NULL OR product.ProductKey IS NULL OR customer.CustomerKey IS NULL
        """,
        "Every invoice line must resolve to date, product, and as-of customer dimensions.",
    ),
    (
        "unresolved purchasing dimension keys",
        PURCHASE_INVOICE_CTE
        + """
        SELECT COUNT_BIG(*)
        FROM Purchasing.PurchaseOrderLines line
        JOIN SupplierInvoices invoice ON invoice.PurchaseOrderID = line.PurchaseOrderID
        LEFT JOIN dw.DimDate date ON date.Date = invoice.TransactionDate
        LEFT JOIN dw.DimProduct product ON product.StockItemID = line.StockItemID
        LEFT JOIN dw.DimSupplier supplier ON supplier.SupplierID = invoice.SupplierID
        WHERE line.ReceivedOuters > 0
          AND (date.DateKey IS NULL OR product.ProductKey IS NULL OR supplier.SupplierKey IS NULL)
        """,
        "Every received purchase line must resolve to date, product, and supplier dimensions.",
    ),
    (
        "unresolved inventory movement keys or types",
        """
        SELECT COUNT_BIG(*)
        FROM Warehouse.StockItemTransactions txn
        LEFT JOIN dw.DimDate date ON date.Date = CAST(txn.TransactionOccurredWhen AS DATE)
        LEFT JOIN dw.DimProduct product ON product.StockItemID = txn.StockItemID
        LEFT JOIN Application.TransactionTypes type
            ON type.TransactionTypeID = txn.TransactionTypeID
        WHERE date.DateKey IS NULL OR product.ProductKey IS NULL OR type.TransactionTypeName IS NULL
        """,
        "Every inventory movement must resolve to date, product, and transaction type.",
    ),
    (
        "unresolved inventory snapshot keys",
        """
        SELECT COUNT_BIG(*)
        FROM Warehouse.StockItemHoldings holding
        LEFT JOIN dw.DimDate date ON date.Date = CAST(holding.LastEditedWhen AS DATE)
        LEFT JOIN dw.DimProduct product ON product.StockItemID = holding.StockItemID
        WHERE date.DateKey IS NULL OR product.ProductKey IS NULL
        """,
        "Every current inventory row must resolve to its snapshot date and product.",
    ),
]

LOAD_STATEMENTS = [
    (
        "invoice profitability",
        """
        INSERT INTO dw.FactInvoiceProfit (
            InvoiceLineID, InvoiceID, DateKey, CustomerKey, ProductKey,
            Quantity, NetSales, TaxAmount, LineProfit, IsCreditNote
        )
        SELECT line.InvoiceLineID, invoice.InvoiceID, date.DateKey,
               customer.CustomerKey, product.ProductKey, line.Quantity,
               line.ExtendedPrice, line.TaxAmount, line.LineProfit, invoice.IsCreditNote
        FROM Sales.InvoiceLines line
        JOIN Sales.Invoices invoice ON invoice.InvoiceID = line.InvoiceID
        JOIN dw.DimDate date ON date.Date = invoice.InvoiceDate
        JOIN dw.DimProduct product ON product.StockItemID = line.StockItemID
        JOIN dw.DimCustomer customer
            ON customer.CustomerID = invoice.CustomerID
           AND CONVERT(DATETIME2(7), invoice.InvoiceDate) >= customer.ValidFrom
           AND CONVERT(DATETIME2(7), invoice.InvoiceDate) < customer.ValidTo;
        """,
    ),
    (
        "purchase lines",
        PURCHASE_INVOICE_CTE
        + """
        INSERT INTO dw.FactPurchaseLine (
            PurchaseOrderLineID, PurchaseOrderID, SupplierTransactionID,
            DateKey, SupplierKey, ProductKey, OrderedOuters, ReceivedOuters,
            ReceivedQuantity, UnitCostPerOuter, PurchaseAmountExclTax, IsOrderFinalized
        )
        SELECT line.PurchaseOrderLineID, line.PurchaseOrderID, invoice.SupplierTransactionID,
               date.DateKey, supplier.SupplierKey, product.ProductKey,
               line.OrderedOuters, line.ReceivedOuters,
               CAST(line.ReceivedOuters AS DECIMAL(18,3))
                   * CAST(item.QuantityPerOuter AS DECIMAL(18,3)),
               line.ExpectedUnitPricePerOuter,
               CAST(line.ExpectedUnitPricePerOuter * line.ReceivedOuters AS DECIMAL(19,2)),
               purchase.IsOrderFinalized
        FROM Purchasing.PurchaseOrderLines line
        JOIN Purchasing.PurchaseOrders purchase
            ON purchase.PurchaseOrderID = line.PurchaseOrderID
        JOIN SupplierInvoices invoice
            ON invoice.PurchaseOrderID = line.PurchaseOrderID
           AND invoice.SupplierID = purchase.SupplierID
        JOIN dw.DimDate date ON date.Date = invoice.TransactionDate
        JOIN dw.DimSupplier supplier ON supplier.SupplierID = invoice.SupplierID
        JOIN dw.DimProduct product ON product.StockItemID = line.StockItemID
        JOIN Warehouse.StockItems item ON item.StockItemID = line.StockItemID
        WHERE line.ReceivedOuters > 0;
        """,
    ),
    (
        "inventory movements",
        """
        INSERT INTO dw.FactStockMovement (
            StockItemTransactionID, DateKey, ProductKey, TransactionTypeID,
            TransactionTypeName, TransactionOccurredWhen, Quantity,
            CustomerID, InvoiceID, SupplierID, PurchaseOrderID
        )
        SELECT txn.StockItemTransactionID, date.DateKey, product.ProductKey,
               txn.TransactionTypeID, type.TransactionTypeName,
               txn.TransactionOccurredWhen, txn.Quantity,
               txn.CustomerID, txn.InvoiceID,
               txn.SupplierID, txn.PurchaseOrderID
        FROM Warehouse.StockItemTransactions txn
        JOIN dw.DimDate date
            ON date.Date = CAST(txn.TransactionOccurredWhen AS DATE)
        JOIN dw.DimProduct product ON product.StockItemID = txn.StockItemID
        JOIN Application.TransactionTypes type
            ON type.TransactionTypeID = txn.TransactionTypeID;
        """,
    ),
    (
        "inventory snapshot",
        """
        INSERT INTO dw.FactInventorySnapshot (
            SnapshotDateKey, ProductKey, StockItemID, QuantityOnHand,
            LastStocktakeQuantity, LastCostPrice, ReorderLevel,
            TargetStockLevel, LastEditedWhen
        )
        SELECT date.DateKey, product.ProductKey, holding.StockItemID,
               holding.QuantityOnHand, holding.LastStocktakeQuantity,
               holding.LastCostPrice, holding.ReorderLevel,
               holding.TargetStockLevel, holding.LastEditedWhen
        FROM Warehouse.StockItemHoldings holding
        JOIN dw.DimDate date ON date.Date = CAST(holding.LastEditedWhen AS DATE)
        JOIN dw.DimProduct product ON product.StockItemID = holding.StockItemID;
        """,
    ),
]


def _assert_no_rows(cursor, query, message):
    cursor.execute(query)
    count = cursor.fetchone()[0]
    if count:
        raise RuntimeError(f"{message} ({count} fila(s))")


def _load_supplier_dimension(cursor):
    cursor.execute(SUPPLIER_UPDATE_SQL)
    cursor.execute(SUPPLIER_INSERT_SQL)


def _load_facts(cursor, connection):
    cursor.execute("DELETE FROM dw.FactInventorySnapshot")
    cursor.execute("DELETE FROM dw.FactStockMovement")
    cursor.execute("DELETE FROM dw.FactPurchaseLine")
    cursor.execute("DELETE FROM dw.FactInvoiceProfit")

    for label, statement in LOAD_STATEMENTS:
        cursor.execute(statement)
        print(f"  {label}: {cursor.rowcount:,} filas")

    connection.commit()


def load_business_analytics():
    run_id = start_run("dw_business_analytics")
    connector = DatabaseConnector(SQL_SERVER_CONFIG)
    try:
        if not connector.connect():
            raise RuntimeError("No se pudo conectar a WideWorldImporters para cargar las nuevas métricas.")

        cursor = connector.connection.cursor()
        cursor.execute("""
        IF OBJECT_ID('dw.FactInvoiceProfit', 'U') IS NULL
           OR OBJECT_ID('dw.FactPurchaseLine', 'U') IS NULL
           OR OBJECT_ID('dw.FactStockMovement', 'U') IS NULL
           OR OBJECT_ID('dw.FactInventorySnapshot', 'U') IS NULL
           OR OBJECT_ID('dw.DimSupplier', 'U') IS NULL
            THROW 51000, 'Ejecute database/apply_dw_layer.py antes de esta carga.', 1;
        """)

        _load_supplier_dimension(cursor)
        for label, statement, message in PRECHECKS:
            _assert_no_rows(cursor, statement, message)
            print(f"  Verificado: {label}")

        _load_facts(cursor, connector.connection)
        cursor.execute("""
        SELECT
            (SELECT COUNT_BIG(*) FROM dw.FactInvoiceProfit)
          + (SELECT COUNT_BIG(*) FROM dw.FactPurchaseLine)
          + (SELECT COUNT_BIG(*) FROM dw.FactStockMovement)
          + (SELECT COUNT_BIG(*) FROM dw.FactInventorySnapshot)
        """)
        rows = cursor.fetchone()[0]
        finish_run(run_id, "success", rows, "Hechos de compras, rentabilidad e inventario cargados.")
        print(f"Carga analítica completada: {rows:,} filas")
        return rows
    except Exception as exc:
        if connector.connection:
            connector.connection.rollback()
        finish_run(run_id, "failed", message=str(exc))
        raise
    finally:
        if connector.connection:
            connector.disconnect()


if __name__ == "__main__":
    load_business_analytics()

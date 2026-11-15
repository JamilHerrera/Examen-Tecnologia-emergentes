-- FASE 5 - Capa analitica (schema bi) consumida por el backend y por ML.
-- El backend NO consulta dw.* directamente: solo vistas aprobadas en bi.
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'bi') EXEC('CREATE SCHEMA bi');
GO

CREATE OR ALTER VIEW bi.vw_sales_detail AS
SELECT
    f.SalesFactKey,
    f.OrderID,
    f.OrderLineID,
    d.[Date]            AS OrderDate,
    d.[Year]            AS [Year],
    d.[Quarter]         AS [Quarter],
    d.[Month]           AS [Month],
    d.MonthName         AS MonthName,
    c.CustomerKey,
    c.CustomerID,
    c.CustomerName,
    c.CustomerCategory,
    c.BuyingGroup,
    g.City,
    g.StateProvince,
    g.Region,
    p.ProductKey,
    p.StockItemID,
    p.ProductName,
    p.Category,
    p.Brand,
    f.Quantity,
    f.UnitPrice,
    f.TaxRate,
    f.LineTotal         AS NetSales
FROM dw.FactSales f
JOIN dw.DimDate      d ON d.DateKey      = f.DateKey
JOIN dw.DimCustomer  c ON c.CustomerKey  = f.CustomerKey
JOIN dw.DimProduct   p ON p.ProductKey   = f.ProductKey
JOIN dw.DimGeography g ON g.GeographyKey = f.GeographyKey
WHERE f.IsDeleted = 0;
GO

-- Ventas semanales (lunes a domingo) para el modelo predictivo.
CREATE OR ALTER VIEW bi.vw_weekly_sales AS
SELECT
    DATEADD(DAY, -((DATEPART(WEEKDAY, d.[Date]) + @@DATEFIRST - 2) % 7), d.[Date]) AS WeekStart,
    SUM(f.LineTotal)            AS NetSales,
    SUM(f.Quantity)             AS Units,
    COUNT(DISTINCT f.OrderID)   AS Orders,
    COUNT(DISTINCT f.CustomerKey) AS ActiveCustomers
FROM dw.FactSales f
JOIN dw.DimDate d ON d.DateKey = f.DateKey
WHERE f.IsDeleted = 0
GROUP BY DATEADD(DAY, -((DATEPART(WEEKDAY, d.[Date]) + @@DATEFIRST - 2) % 7), d.[Date]);
GO

-- Fecha de ultima actualizacion de los datos.
CREATE OR ALTER VIEW bi.vw_data_freshness AS
SELECT
    MAX(f.LoadedDate)  AS LastLoadedAt,
    MAX(d.[Date])      AS LastOrderDate,
    MIN(d.[Date])      AS FirstOrderDate,
    COUNT_BIG(*)       AS FactRows
FROM dw.FactSales f
JOIN dw.DimDate d ON d.DateKey = f.DateKey;
GO

-- Rentabilidad real por linea de factura (no se mezcla con el grano de pedido).
CREATE OR ALTER VIEW bi.vw_invoice_profit_detail AS
SELECT
    f.InvoiceProfitFactKey,
    f.InvoiceID,
    f.InvoiceLineID,
    d.[Date] AS InvoiceDate,
    d.[Year],
    d.[Quarter],
    d.[Month],
    d.MonthName,
    c.CustomerKey,
    c.CustomerID,
    c.CustomerName,
    c.CustomerCategory,
    g.Region,
    p.ProductKey,
    p.StockItemID,
    p.ProductName,
    p.Category,
    f.Quantity,
    f.NetSales,
    f.TaxAmount,
    f.LineProfit,
    CAST(100.0 * f.LineProfit / NULLIF(f.NetSales, 0) AS DECIMAL(9,2)) AS ProfitMarginPct,
    f.IsCreditNote
FROM dw.FactInvoiceProfit f
JOIN dw.DimDate d ON d.DateKey = f.DateKey
JOIN dw.DimCustomer c ON c.CustomerKey = f.CustomerKey
LEFT JOIN dw.DimGeography g ON g.GeographyKey = c.GeographyKey
JOIN dw.DimProduct p ON p.ProductKey = f.ProductKey;
GO

-- Gasto por linea recibida; la suma se reconcilia con la factura de proveedor sin impuestos.
CREATE OR ALTER VIEW bi.vw_purchase_detail AS
SELECT
    f.PurchaseLineFactKey,
    f.PurchaseOrderLineID,
    f.PurchaseOrderID,
    f.SupplierTransactionID,
    d.[Date] AS PurchaseDate,
    d.[Year],
    d.[Quarter],
    d.[Month],
    d.MonthName,
    s.SupplierKey,
    s.SupplierID,
    s.SupplierName,
    s.SupplierCategory,
    p.ProductKey,
    p.StockItemID,
    p.ProductName,
    p.Category,
    f.OrderedOuters,
    f.ReceivedOuters,
    f.ReceivedQuantity,
    f.UnitCostPerOuter,
    f.PurchaseAmountExclTax,
    f.IsOrderFinalized
FROM dw.FactPurchaseLine f
JOIN dw.DimDate d ON d.DateKey = f.DateKey
JOIN dw.DimSupplier s ON s.SupplierKey = f.SupplierKey
JOIN dw.DimProduct p ON p.ProductKey = f.ProductKey;
GO

-- Movimientos firmados: entradas positivas, salidas negativas y ajustes segun el origen.
CREATE OR ALTER VIEW bi.vw_inventory_movement_detail AS
SELECT
    f.StockItemTransactionID,
    f.TransactionOccurredWhen,
    d.[Date] AS TransactionDate,
    d.[Year],
    d.[Quarter],
    d.[Month],
    d.MonthName,
    f.TransactionTypeID,
    f.TransactionTypeName,
    CASE
        WHEN f.Quantity > 0 THEN N'Entrada'
        WHEN f.Quantity < 0 THEN N'Salida'
        ELSE N'Sin cambio'
    END AS MovementDirection,
    p.ProductKey,
    p.StockItemID,
    p.ProductName,
    p.Category,
    f.Quantity,
    f.CustomerID,
    f.InvoiceID,
    f.SupplierID,
    f.PurchaseOrderID
FROM dw.FactStockMovement f
JOIN dw.DimDate d ON d.DateKey = f.DateKey
JOIN dw.DimProduct p ON p.ProductKey = f.ProductKey;
GO

-- Solo expone el ultimo snapshot; no implica que existan saldos historicos.
CREATE OR ALTER VIEW bi.vw_inventory_snapshot AS
SELECT
    d.[Date] AS SnapshotDate,
    p.ProductKey,
    p.StockItemID,
    p.ProductName,
    p.Category,
    f.QuantityOnHand,
    f.LastStocktakeQuantity,
    f.LastCostPrice,
    f.ReorderLevel,
    f.TargetStockLevel,
    CASE
        WHEN f.QuantityOnHand = 0 THEN N'Agotado'
        WHEN f.QuantityOnHand < f.ReorderLevel THEN N'Bajo de minimo'
        WHEN f.QuantityOnHand > f.TargetStockLevel THEN N'Sobre objetivo'
        ELSE N'Adecuado'
    END AS StockStatus
FROM dw.FactInventorySnapshot f
JOIN dw.DimDate d ON d.DateKey = f.SnapshotDateKey
JOIN dw.DimProduct p ON p.ProductKey = f.ProductKey
WHERE f.SnapshotDateKey = (
    SELECT MAX(SnapshotDateKey) FROM dw.FactInventorySnapshot
);
GO

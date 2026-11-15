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

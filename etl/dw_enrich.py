"""
FASE 4.5: Enriquecimiento del Data Warehouse
Las dimensiones cargadas en 4.2 venian casi vacias (nombres genericos, sin categoria,
sin geografia). Este script las completa desde las tablas fuente de WideWorldImporters,
corrige la semantica de FactSales.Discount (en realidad era la tasa de impuesto) y
asigna GeographyKey real a cada hecho. Es idempotente.
"""
import sys

sys.path.insert(0, ".")
from etl.config import SQL_SERVER_CONFIG
from etl.extract import DatabaseConnector

STEPS = [
    (
        "Nuevas columnas en dimensiones",
        """
        IF COL_LENGTH('dw.DimCustomer','CustomerCategory') IS NULL ALTER TABLE dw.DimCustomer ADD CustomerCategory NVARCHAR(100) NULL;
        IF COL_LENGTH('dw.DimCustomer','BuyingGroup') IS NULL ALTER TABLE dw.DimCustomer ADD BuyingGroup NVARCHAR(100) NULL;
        IF COL_LENGTH('dw.DimCustomer','GeographyKey') IS NULL ALTER TABLE dw.DimCustomer ADD GeographyKey INT NULL;
        IF COL_LENGTH('dw.DimProduct','Color') IS NULL ALTER TABLE dw.DimProduct ADD Color NVARCHAR(50) NULL;
        IF COL_LENGTH('dw.DimProduct','Size') IS NULL ALTER TABLE dw.DimProduct ADD Size NVARCHAR(50) NULL;
        IF COL_LENGTH('dw.DimGeography','CityID') IS NULL ALTER TABLE dw.DimGeography ADD CityID INT NULL;
        """,
    ),
    (
        "FactSales.Discount -> TaxRate (la columna guardaba TaxRate/100)",
        """
        IF COL_LENGTH('dw.FactSales','Discount') IS NOT NULL AND COL_LENGTH('dw.FactSales','TaxRate') IS NULL
            EXEC sp_rename 'dw.FactSales.Discount', 'TaxRate', 'COLUMN';
        """,
    ),
    (
        "DimGeography desde Application.Cities/StateProvinces/Countries",
        """
        INSERT INTO dw.DimGeography (CityID, City, StateProvince, Country, Region)
        SELECT DISTINCT ci.CityID, ci.CityName, sp.StateProvinceName, co.CountryName, sp.SalesTerritory
        FROM Sales.Customers c
        JOIN Application.Cities ci ON ci.CityID = c.DeliveryCityID
        JOIN Application.StateProvinces sp ON sp.StateProvinceID = ci.StateProvinceID
        JOIN Application.Countries co ON co.CountryID = sp.CountryID
        WHERE NOT EXISTS (SELECT 1 FROM dw.DimGeography g WHERE g.CityID = ci.CityID);
        """,
    ),
    (
        "DimCustomer con nombre, contacto, categoria, grupo y ciudad reales",
        """
        UPDATE d SET
            d.CustomerName = c.CustomerName,
            d.PrimaryContactPerson = p.FullName,
            d.CustomerCategory = cc.CustomerCategoryName,
            d.BuyingGroup = bg.BuyingGroupName,
            d.City = g.City,
            d.StateProvince = g.StateProvince,
            d.Country = g.Country,
            d.PostalCode = c.DeliveryPostalCode,
            d.GeographyKey = g.GeographyKey
        FROM dw.DimCustomer d
        JOIN Sales.Customers c ON c.CustomerID = d.CustomerID
        LEFT JOIN Application.People p ON p.PersonID = c.PrimaryContactPersonID
        LEFT JOIN Sales.CustomerCategories cc ON cc.CustomerCategoryID = c.CustomerCategoryID
        LEFT JOIN Sales.BuyingGroups bg ON bg.BuyingGroupID = c.BuyingGroupID
        LEFT JOIN dw.DimGeography g ON g.CityID = c.DeliveryCityID
        WHERE d.IsCurrent = 1;
        """,
    ),
    (
        "DimProduct con categoria (grupo principal), marca, color y tamano",
        """
        UPDATE d SET
            d.ProductName = s.StockItemName,
            d.Brand = s.Brand,
            d.Size = s.Size,
            d.Color = col.ColorName,
            d.UnitPrice = s.UnitPrice,
            d.RecommendedRetailPrice = s.RecommendedRetailPrice,
            d.Category = COALESCE(grp.StockGroupName, 'Sin categoria')
        FROM dw.DimProduct d
        JOIN Warehouse.StockItems s ON s.StockItemID = d.StockItemID
        LEFT JOIN Warehouse.Colors col ON col.ColorID = s.ColorID
        OUTER APPLY (
            SELECT TOP 1 g.StockGroupName
            FROM Warehouse.StockItemStockGroups sg
            JOIN Warehouse.StockGroups g ON g.StockGroupID = sg.StockGroupID
            WHERE sg.StockItemID = s.StockItemID
            ORDER BY sg.StockGroupID
        ) grp;
        """,
    ),
    (
        "FactSales.GeographyKey desde la geografia del cliente",
        """
        UPDATE f SET f.GeographyKey = c.GeographyKey
        FROM dw.FactSales f
        JOIN dw.DimCustomer c ON c.CustomerKey = f.CustomerKey
        WHERE c.GeographyKey IS NOT NULL AND f.GeographyKey <> c.GeographyKey;
        """,
    ),
]


def run():
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cur = conn.connection.cursor()
    for name, sql in STEPS:
        cur.execute(sql)
        affected = cur.rowcount
        conn.connection.commit()
        print(f"  OK  {name} (filas afectadas: {affected})")

    checks = {
        "Clientes sin nombre real": "SELECT COUNT(*) FROM dw.DimCustomer WHERE CustomerName LIKE 'Customer[_]%'",
        "Clientes sin ciudad": "SELECT COUNT(*) FROM dw.DimCustomer WHERE GeographyKey IS NULL",
        "Productos sin categoria": "SELECT COUNT(*) FROM dw.DimProduct WHERE Category IS NULL",
        "Hechos con geografia desconocida": "SELECT COUNT(*) FROM dw.FactSales WHERE GeographyKey = 1",
        "Categorias distintas": "SELECT COUNT(DISTINCT Category) FROM dw.DimProduct",
        "Regiones distintas": "SELECT COUNT(DISTINCT Region) FROM dw.DimGeography",
    }
    print("\nVerificacion:")
    for label, sql in checks.items():
        cur.execute(sql)
        print(f"  {label}: {cur.fetchone()[0]}")
    conn.disconnect()


if __name__ == "__main__":
    run()

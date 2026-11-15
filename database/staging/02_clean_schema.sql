-- ============================================================================
-- STAGING_CLEAN SCHEMA
-- Capa de datos limpios, validados y estandarizados
-- Listos para cargar al Data Warehouse
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging_clean')
    EXEC sp_executesql N'CREATE SCHEMA staging_clean'
GO

-- =============================================================================
-- SALES SCHEMA TABLES (CLEAN)
-- =============================================================================

-- Sales.Orders (limpia)
IF OBJECT_ID('staging_clean.Sales_Orders', 'U') IS NOT NULL
    DROP TABLE staging_clean.Sales_Orders
GO

CREATE TABLE staging_clean.Sales_Orders (
    OrderID INT NOT NULL,
    CustomerID INT NOT NULL,
    SalespersonPersonID INT NOT NULL,
    PickedByPersonID INT NULL,
    ContactPersonID INT NOT NULL,
    OrderDate DATE NOT NULL,
    ExpectedDeliveryDate DATE NOT NULL,
    CustomerPurchaseOrderNumber NVARCHAR(20) NULL,
    IsUndersupplyBackordered BIT NOT NULL,
    PickingCompletedWhen DATE NULL,
    LastEditedWhen DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Sales_Orders_OrderID ON staging_clean.Sales_Orders(OrderID)
GO

-- Sales.OrderLines (limpia)
IF OBJECT_ID('staging_clean.Sales_OrderLines', 'U') IS NOT NULL
    DROP TABLE staging_clean.Sales_OrderLines
GO

CREATE TABLE staging_clean.Sales_OrderLines (
    OrderLineID INT NOT NULL,
    OrderID INT NOT NULL,
    StockItemID INT NOT NULL,
    Description NVARCHAR(MAX) NOT NULL,
    Quantity FLOAT NOT NULL,
    UnitPrice FLOAT NOT NULL,
    TaxRate FLOAT NOT NULL,
    LineTotal FLOAT NOT NULL,
    PickedQuantity FLOAT NOT NULL,
    LastEditedWhen DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Sales_OrderLines_OrderLineID ON staging_clean.Sales_OrderLines(OrderLineID)
GO

-- =============================================================================
-- CUSTOMERS SCHEMA TABLES (CLEAN)
-- =============================================================================

-- Sales.Customers (limpia)
IF OBJECT_ID('staging_clean.Sales_Customers', 'U') IS NOT NULL
    DROP TABLE staging_clean.Sales_Customers
GO

CREATE TABLE staging_clean.Sales_Customers (
    CustomerID INT NOT NULL,
    CustomerName NVARCHAR(100) NOT NULL,
    CustomerCategoryID INT NOT NULL,
    PrimaryContactPersonID INT NOT NULL,
    PhoneNumber NVARCHAR(20) NULL,
    FaxNumber NVARCHAR(20) NULL,
    WebsiteURL NVARCHAR(256) NULL,
    CreditLimit FLOAT NULL,
    AccountOpenedDate DATE NOT NULL,
    StandardDiscountPercentage FLOAT NOT NULL,
    IsStatementSent BIT NOT NULL,
    IsOnCreditHold BIT NOT NULL,
    ValidFrom DATE NOT NULL,
    ValidTo DATE NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Sales_Customers_CustomerID ON staging_clean.Sales_Customers(CustomerID)
GO

-- Sales.CustomerCategories (limpia)
IF OBJECT_ID('staging_clean.Sales_CustomerCategories', 'U') IS NOT NULL
    DROP TABLE staging_clean.Sales_CustomerCategories
GO

CREATE TABLE staging_clean.Sales_CustomerCategories (
    CustomerCategoryID INT NOT NULL,
    CustomerCategoryName NVARCHAR(50) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Sales_CustomerCategories_ID ON staging_clean.Sales_CustomerCategories(CustomerCategoryID)
GO

-- =============================================================================
-- WAREHOUSE SCHEMA TABLES (CLEAN)
-- =============================================================================

-- Warehouse.Products (limpia)
IF OBJECT_ID('staging_clean.Warehouse_Products', 'U') IS NOT NULL
    DROP TABLE staging_clean.Warehouse_Products
GO

CREATE TABLE staging_clean.Warehouse_Products (
    ProductID INT NOT NULL,
    ProductName NVARCHAR(100) NOT NULL,
    SupplierID INT NOT NULL,
    UnitPrice FLOAT NOT NULL,
    RecommendedRetailPrice FLOAT NULL,
    TaxRate FLOAT NOT NULL,
    Brand NVARCHAR(50) NULL,
    ValidFrom DATE NOT NULL,
    ValidTo DATE NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Warehouse_Products_ProductID ON staging_clean.Warehouse_Products(ProductID)
GO

-- Warehouse.ProductCategories (limpia)
IF OBJECT_ID('staging_clean.Warehouse_ProductCategories', 'U') IS NOT NULL
    DROP TABLE staging_clean.Warehouse_ProductCategories
GO

CREATE TABLE staging_clean.Warehouse_ProductCategories (
    ProductCategoryID INT NOT NULL,
    ProductCategoryName NVARCHAR(50) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Warehouse_ProductCategories_ID ON staging_clean.Warehouse_ProductCategories(ProductCategoryID)
GO

-- =============================================================================
-- APPLICATION SCHEMA TABLES (CLEAN - GEOGRAPHY)
-- =============================================================================

-- Application.People (limpia)
IF OBJECT_ID('staging_clean.Application_People', 'U') IS NOT NULL
    DROP TABLE staging_clean.Application_People
GO

CREATE TABLE staging_clean.Application_People (
    PersonID INT NOT NULL,
    FullName NVARCHAR(50) NOT NULL,
    PreferredName NVARCHAR(50) NOT NULL,
    EmailAddress NVARCHAR(256) NULL,
    PhoneNumber NVARCHAR(20) NULL,
    CreatedWhen DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Application_People_PersonID ON staging_clean.Application_People(PersonID)
GO

-- Application.Cities (limpia)
IF OBJECT_ID('staging_clean.Application_Cities', 'U') IS NOT NULL
    DROP TABLE staging_clean.Application_Cities
GO

CREATE TABLE staging_clean.Application_Cities (
    CityID INT NOT NULL,
    CityName NVARCHAR(50) NOT NULL,
    StateProvinceID INT NOT NULL,
    LatestRecordedPopulation BIGINT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Application_Cities_CityID ON staging_clean.Application_Cities(CityID)
GO

-- Application.StateProvinces (limpia)
IF OBJECT_ID('staging_clean.Application_StateProvinces', 'U') IS NOT NULL
    DROP TABLE staging_clean.Application_StateProvinces
GO

CREATE TABLE staging_clean.Application_StateProvinces (
    StateProvinceID INT NOT NULL,
    StateProvinceName NVARCHAR(50) NOT NULL,
    CountryID INT NOT NULL,
    SalesTerritory NVARCHAR(50) NOT NULL,
    LatestRecordedPopulation BIGINT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Application_StateProvinces_ID ON staging_clean.Application_StateProvinces(StateProvinceID)
GO

-- Application.Countries (limpia)
IF OBJECT_ID('staging_clean.Application_Countries', 'U') IS NOT NULL
    DROP TABLE staging_clean.Application_Countries
GO

CREATE TABLE staging_clean.Application_Countries (
    CountryID INT NOT NULL,
    CountryName NVARCHAR(60) NOT NULL,
    FormalName NVARCHAR(60) NOT NULL,
    IsoAlpha3Code NVARCHAR(3) NULL,
    Continent NVARCHAR(30) NOT NULL,
    Region NVARCHAR(30) NOT NULL,
    Subregion NVARCHAR(30) NOT NULL,
    LatestRecordedPopulation BIGINT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE(),
    QualityFlag NVARCHAR(50) DEFAULT 'VALID'
)
GO

CREATE CLUSTERED INDEX CIX_Clean_Application_Countries_ID ON staging_clean.Application_Countries(CountryID)
GO

-- =============================================================================
-- QUALITY AND AUDIT TABLES
-- =============================================================================

-- Data Quality Metrics
IF OBJECT_ID('staging_clean.DataQualityMetrics', 'U') IS NOT NULL
    DROP TABLE staging_clean.DataQualityMetrics
GO

CREATE TABLE staging_clean.DataQualityMetrics (
    MetricID BIGINT PRIMARY KEY IDENTITY(1,1),
    TableName NVARCHAR(100) NOT NULL,
    MetricDate DATETIME2(7) DEFAULT GETUTCDATE(),
    TotalRows INT NOT NULL,
    ValidRows INT NOT NULL,
    DuplicateRows INT NOT NULL,
    NullRows INT NOT NULL,
    InvalidRows INT NOT NULL,
    CompletenessScore FLOAT,
    UniquenessScore FLOAT,
    ValidityScore FLOAT,
    ConsistencyScore FLOAT,
    OverallScore FLOAT
)
GO

CREATE INDEX IX_DQM_Table ON staging_clean.DataQualityMetrics(TableName, MetricDate DESC)
GO

-- Data Lineage
IF OBJECT_ID('staging_clean.DataLineage', 'U') IS NOT NULL
    DROP TABLE staging_clean.DataLineage
GO

CREATE TABLE staging_clean.DataLineage (
    LineageID BIGINT PRIMARY KEY IDENTITY(1,1),
    SourceTable NVARCHAR(100) NOT NULL,
    TargetTable NVARCHAR(100) NOT NULL,
    TransformationType NVARCHAR(50),
    SourceRowCount INT,
    TargetRowCount INT,
    DataLoss INT,
    TransformationDate DATETIME2(7) DEFAULT GETUTCDATE(),
    Notes NVARCHAR(MAX)
)
GO

CREATE INDEX IX_Lineage_Source ON staging_clean.DataLineage(SourceTable, TransformationDate DESC)
GO

PRINT '✓ staging_clean schema created successfully'

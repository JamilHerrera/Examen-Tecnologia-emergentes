-- ============================================================================
-- STAGING_RAW SCHEMA
-- Capa de datos crudos extraídos de WideWorldImporters
-- Sin transformaciones, réplica exacta de la fuente
-- ============================================================================

-- Crear esquema staging_raw
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging_raw')
    EXEC sp_executesql N'CREATE SCHEMA staging_raw'
GO

-- =============================================================================
-- SALES SCHEMA TABLES
-- =============================================================================

-- Sales.Orders (cabecera de órdenes)
IF OBJECT_ID('staging_raw.Sales_Orders', 'U') IS NOT NULL
    DROP TABLE staging_raw.Sales_Orders
GO

CREATE TABLE staging_raw.Sales_Orders (
    OrderID INT NOT NULL,
    CustomerID INT NOT NULL,
    SalespersonPersonID INT NOT NULL,
    PickedByPersonID INT NULL,
    ContactPersonID INT NOT NULL,
    BackorderOrderID INT NULL,
    OrderDate DATETIME2(7) NOT NULL,
    ExpectedDeliveryDate DATETIME2(7) NOT NULL,
    CustomerPurchaseOrderNumber NVARCHAR(20) NULL,
    IsUndersupplyBackordered BIT NOT NULL,
    Comments NVARCHAR(MAX) NULL,
    DeliveryInstructions NVARCHAR(MAX) NULL,
    InternalComments NVARCHAR(MAX) NULL,
    PickingCompletedWhen DATETIME2(7) NULL,
    LastEditedBy INT NOT NULL,
    LastEditedWhen DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Sales_Orders_OrderID ON staging_raw.Sales_Orders(OrderID)
GO

-- Sales.OrderLines (detalles de órdenes)
IF OBJECT_ID('staging_raw.Sales_OrderLines', 'U') IS NOT NULL
    DROP TABLE staging_raw.Sales_OrderLines
GO

CREATE TABLE staging_raw.Sales_OrderLines (
    OrderLineID INT NOT NULL,
    OrderID INT NOT NULL,
    StockItemID INT NOT NULL,
    Description NVARCHAR(MAX) NOT NULL,
    PackageTypeID INT NOT NULL,
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(18, 2) NOT NULL,
    TaxRate DECIMAL(18, 3) NOT NULL,
    PickedQuantity INT NOT NULL,
    LastEditedBy INT NOT NULL,
    LastEditedWhen DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Sales_OrderLines_OrderLineID ON staging_raw.Sales_OrderLines(OrderLineID)
GO

-- =============================================================================
-- CUSTOMERS SCHEMA TABLES
-- =============================================================================

-- Sales.Customers (maestro de clientes)
IF OBJECT_ID('staging_raw.Sales_Customers', 'U') IS NOT NULL
    DROP TABLE staging_raw.Sales_Customers
GO

CREATE TABLE staging_raw.Sales_Customers (
    CustomerID INT NOT NULL,
    CustomerName NVARCHAR(100) NOT NULL,
    BillToCustomerID INT NOT NULL,
    CustomerCategoryID INT NOT NULL,
    BuyingGroupID INT NULL,
    PrimaryContactPersonID INT NOT NULL,
    AlternateContactPersonID INT NULL,
    DeliveryAddressLine1 NVARCHAR(60) NOT NULL,
    DeliveryAddressLine2 NVARCHAR(60) NULL,
    DeliveryCity NVARCHAR(50) NOT NULL,
    DeliveryPostalCode NVARCHAR(10) NOT NULL,
    DeliveryStateProvinceID INT NOT NULL,
    DeliveryCountryID INT NOT NULL,
    PostalAddressLine1 NVARCHAR(60) NOT NULL,
    PostalAddressLine2 NVARCHAR(60) NULL,
    PostalCity NVARCHAR(50) NOT NULL,
    PostalPostalCode NVARCHAR(10) NOT NULL,
    PostalStateProvinceID INT NOT NULL,
    PostalCountryID INT NOT NULL,
    PhoneNumber NVARCHAR(20) NOT NULL,
    FaxNumber NVARCHAR(20) NOT NULL,
    WebsiteURL NVARCHAR(256) NOT NULL,
    DeliveryMethod NVARCHAR(10) NULL,
    CreditLimit DECIMAL(18, 2) NULL,
    AccountOpenedDate DATE NOT NULL,
    StandardDiscountPercentage DECIMAL(18, 3) NOT NULL,
    IsStatementSent BIT NOT NULL,
    IsOnCreditHold BIT NOT NULL,
    PaymentDays INT NOT NULL,
    PhoneNumberTypeID INT NULL,
    FaxNumberTypeID INT NULL,
    DeliveryRun NVARCHAR(5) NULL,
    RunPosition NVARCHAR(5) NULL,
    WebsiteURLTypeID INT NULL,
    LastEditedBy INT NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Sales_Customers_CustomerID ON staging_raw.Sales_Customers(CustomerID)
GO

-- Sales.CustomerCategories (categorías de clientes)
IF OBJECT_ID('staging_raw.Sales_CustomerCategories', 'U') IS NOT NULL
    DROP TABLE staging_raw.Sales_CustomerCategories
GO

CREATE TABLE staging_raw.Sales_CustomerCategories (
    CustomerCategoryID INT NOT NULL,
    CustomerCategoryName NVARCHAR(50) NOT NULL,
    LastEditedBy INT NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Sales_CustomerCategories_ID ON staging_raw.Sales_CustomerCategories(CustomerCategoryID)
GO

-- =============================================================================
-- WAREHOUSE SCHEMA TABLES
-- =============================================================================

-- Warehouse.Products (maestro de productos)
IF OBJECT_ID('staging_raw.Warehouse_Products', 'U') IS NOT NULL
    DROP TABLE staging_raw.Warehouse_Products
GO

CREATE TABLE staging_raw.Warehouse_Products (
    ProductID INT NOT NULL,
    ProductName NVARCHAR(100) NOT NULL,
    SupplierID INT NOT NULL,
    ColorID INT NULL,
    UnitPackageID INT NOT NULL,
    OuterPackageID INT NOT NULL,
    Brand NVARCHAR(50) NULL,
    Size NVARCHAR(20) NULL,
    LeadTimeDays INT NOT NULL,
    QuantityPerOuter INT NOT NULL,
    IsChillerStock BIT NOT NULL,
    Barcode NVARCHAR(50) NULL,
    TaxRate DECIMAL(18, 3) NOT NULL,
    UnitPrice DECIMAL(18, 2) NOT NULL,
    RecommendedRetailPrice DECIMAL(18, 2) NULL,
    TypicalWeightPerUnit DECIMAL(18, 3) NULL,
    LastEditedBy INT NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Warehouse_Products_ProductID ON staging_raw.Warehouse_Products(ProductID)
GO

-- Warehouse.ProductCategories (categorías de productos)
IF OBJECT_ID('staging_raw.Warehouse_ProductCategories', 'U') IS NOT NULL
    DROP TABLE staging_raw.Warehouse_ProductCategories
GO

CREATE TABLE staging_raw.Warehouse_ProductCategories (
    ProductCategoryID INT NOT NULL,
    ProductCategoryName NVARCHAR(50) NOT NULL,
    LastEditedBy INT NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Warehouse_ProductCategories_ID ON staging_raw.Warehouse_ProductCategories(ProductCategoryID)
GO

-- =============================================================================
-- APPLICATION SCHEMA TABLES (GEOGRAPHY)
-- =============================================================================

-- Application.People (personas)
IF OBJECT_ID('staging_raw.Application_People', 'U') IS NOT NULL
    DROP TABLE staging_raw.Application_People
GO

CREATE TABLE staging_raw.Application_People (
    PersonID INT NOT NULL,
    FullName NVARCHAR(50) NOT NULL,
    PreferredName NVARCHAR(50) NOT NULL,
    SearchName NVARCHAR(101) NOT NULL,
    IsPermittedToLogon BIT NOT NULL,
    LogonName NVARCHAR(256) NULL,
    IsExternalLogonProvider BIT NOT NULL,
    EmailAddress NVARCHAR(256) NULL,
    PhoneNumber NVARCHAR(20) NULL,
    FaxNumber NVARCHAR(20) NULL,
    CreatedBy INT NOT NULL,
    CreatedWhen DATETIME2(7) NOT NULL,
    LastEditedBy INT NOT NULL,
    LastEditedWhen DATETIME2(7) NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Application_People_PersonID ON staging_raw.Application_People(PersonID)
GO

-- Application.Cities (ciudades)
IF OBJECT_ID('staging_raw.Application_Cities', 'U') IS NOT NULL
    DROP TABLE staging_raw.Application_Cities
GO

CREATE TABLE staging_raw.Application_Cities (
    CityID INT NOT NULL,
    CityName NVARCHAR(50) NOT NULL,
    StateProvinceID INT NOT NULL,
    Location GEOGRAPHY NULL,
    LatestRecordedPopulation BIGINT NULL,
    LastEditedBy INT NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Application_Cities_CityID ON staging_raw.Application_Cities(CityID)
GO

-- Application.StateProvinces (estados/provincias)
IF OBJECT_ID('staging_raw.Application_StateProvinces', 'U') IS NOT NULL
    DROP TABLE staging_raw.Application_StateProvinces
GO

CREATE TABLE staging_raw.Application_StateProvinces (
    StateProvinceID INT NOT NULL,
    StateProvinceName NVARCHAR(50) NOT NULL,
    CountryID INT NOT NULL,
    SalesTerritory NVARCHAR(50) NOT NULL,
    LatestRecordedPopulation BIGINT NULL,
    LastEditedBy INT NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Application_StateProvinces_ID ON staging_raw.Application_StateProvinces(StateProvinceID)
GO

-- Application.Countries (países)
IF OBJECT_ID('staging_raw.Application_Countries', 'U') IS NOT NULL
    DROP TABLE staging_raw.Application_Countries
GO

CREATE TABLE staging_raw.Application_Countries (
    CountryID INT NOT NULL,
    CountryName NVARCHAR(60) NOT NULL,
    FormalName NVARCHAR(60) NOT NULL,
    IsoAlpha3Code NVARCHAR(3) NULL,
    IsoNumericCode INT NULL,
    CountryType NVARCHAR(20) NOT NULL,
    LatestRecordedPopulation BIGINT NULL,
    Continent NVARCHAR(30) NOT NULL,
    Region NVARCHAR(30) NOT NULL,
    Subregion NVARCHAR(30) NOT NULL,
    LastEditedBy INT NOT NULL,
    ValidFrom DATETIME2(7) NOT NULL,
    ValidTo DATETIME2(7) NOT NULL,
    LoadedDate DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

CREATE CLUSTERED INDEX CIX_Application_Countries_ID ON staging_raw.Application_Countries(CountryID)
GO

-- =============================================================================
-- AUDIT TABLES
-- =============================================================================

-- ETL Audit Log
IF OBJECT_ID('dbo.etl_audit_log', 'U') IS NOT NULL
    DROP TABLE dbo.etl_audit_log
GO

CREATE TABLE dbo.etl_audit_log (
    AuditID BIGINT PRIMARY KEY IDENTITY(1,1),
    ETLDate DATETIME2(7) DEFAULT GETUTCDATE(),
    Phase NVARCHAR(50) NOT NULL,
    TableName NVARCHAR(100) NOT NULL,
    RowCount INT NOT NULL,
    Status NVARCHAR(20) NOT NULL,
    ErrorMessage NVARCHAR(MAX) NULL,
    Duration_Seconds FLOAT NOT NULL,
    LoadedBy NVARCHAR(256) DEFAULT SYSTEM_USER
)
GO

CREATE INDEX IX_etl_audit_log_ETLDate ON dbo.etl_audit_log(ETLDate DESC)
GO

PRINT '✓ staging_raw schema created successfully'

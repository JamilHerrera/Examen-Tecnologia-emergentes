-- DW facts for purchasing, invoice profitability, and inventory activity.
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dw')
    EXEC('CREATE SCHEMA dw');
GO

IF OBJECT_ID('dw.DimSupplier', 'U') IS NULL
CREATE TABLE dw.DimSupplier (
    SupplierKey       INT IDENTITY(1,1) PRIMARY KEY,
    SupplierID        INT NOT NULL UNIQUE,
    SupplierName      NVARCHAR(100) NOT NULL,
    SupplierCategory  NVARCHAR(100) NULL
);
GO

IF OBJECT_ID('dw.FactInvoiceProfit', 'U') IS NULL
CREATE TABLE dw.FactInvoiceProfit (
    InvoiceProfitFactKey BIGINT IDENTITY(1,1) PRIMARY KEY,
    InvoiceLineID        INT NOT NULL UNIQUE,
    InvoiceID            INT NOT NULL,
    DateKey              INT NOT NULL,
    CustomerKey          INT NOT NULL,
    ProductKey           INT NOT NULL,
    Quantity             INT NOT NULL,
    NetSales             DECIMAL(19,2) NOT NULL,
    TaxAmount            DECIMAL(19,2) NOT NULL,
    LineProfit           DECIMAL(19,2) NOT NULL,
    IsCreditNote         BIT NOT NULL,
    LoadedAt             DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_FactInvoiceProfit_Date
        FOREIGN KEY (DateKey) REFERENCES dw.DimDate(DateKey),
    CONSTRAINT FK_FactInvoiceProfit_Customer
        FOREIGN KEY (CustomerKey) REFERENCES dw.DimCustomer(CustomerKey),
    CONSTRAINT FK_FactInvoiceProfit_Product
        FOREIGN KEY (ProductKey) REFERENCES dw.DimProduct(ProductKey)
);
GO

IF OBJECT_ID('dw.FactPurchaseLine', 'U') IS NULL
CREATE TABLE dw.FactPurchaseLine (
    PurchaseLineFactKey    BIGINT IDENTITY(1,1) PRIMARY KEY,
    PurchaseOrderLineID    INT NOT NULL UNIQUE,
    PurchaseOrderID        INT NOT NULL,
    SupplierTransactionID  INT NOT NULL,
    DateKey                INT NOT NULL,
    SupplierKey            INT NOT NULL,
    ProductKey             INT NOT NULL,
    OrderedOuters          INT NOT NULL,
    ReceivedOuters         INT NOT NULL,
    ReceivedQuantity       DECIMAL(18,3) NOT NULL,
    UnitCostPerOuter       DECIMAL(18,4) NOT NULL,
    PurchaseAmountExclTax  DECIMAL(19,2) NOT NULL,
    IsOrderFinalized       BIT NOT NULL,
    LoadedAt               DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_FactPurchaseLine_Date
        FOREIGN KEY (DateKey) REFERENCES dw.DimDate(DateKey),
    CONSTRAINT FK_FactPurchaseLine_Supplier
        FOREIGN KEY (SupplierKey) REFERENCES dw.DimSupplier(SupplierKey),
    CONSTRAINT FK_FactPurchaseLine_Product
        FOREIGN KEY (ProductKey) REFERENCES dw.DimProduct(ProductKey)
);
GO

IF OBJECT_ID('dw.FactStockMovement', 'U') IS NULL
CREATE TABLE dw.FactStockMovement (
    StockItemTransactionID  INT NOT NULL PRIMARY KEY,
    DateKey                 INT NOT NULL,
    ProductKey              INT NOT NULL,
    TransactionTypeID       INT NOT NULL,
    TransactionTypeName     NVARCHAR(100) NOT NULL,
    TransactionOccurredWhen DATETIME2(7) NOT NULL,
    Quantity                DECIMAL(18,3) NOT NULL,
    CustomerID              INT NULL,
    InvoiceID               INT NULL,
    SupplierID              INT NULL,
    PurchaseOrderID         INT NULL,
    LoadedAt                DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_FactStockMovement_Date
        FOREIGN KEY (DateKey) REFERENCES dw.DimDate(DateKey),
    CONSTRAINT FK_FactStockMovement_Product
        FOREIGN KEY (ProductKey) REFERENCES dw.DimProduct(ProductKey)
);
GO

IF OBJECT_ID('dw.FactInventorySnapshot', 'U') IS NULL
CREATE TABLE dw.FactInventorySnapshot (
    InventorySnapshotKey  BIGINT IDENTITY(1,1) PRIMARY KEY,
    SnapshotDateKey       INT NOT NULL,
    ProductKey            INT NOT NULL,
    StockItemID           INT NOT NULL,
    QuantityOnHand        INT NOT NULL,
    LastStocktakeQuantity INT NOT NULL,
    LastCostPrice         DECIMAL(18,2) NOT NULL,
    ReorderLevel          INT NOT NULL,
    TargetStockLevel      INT NOT NULL,
    LastEditedWhen        DATETIME2(7) NOT NULL,
    LoadedAt              DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UX_FactInventorySnapshot_Date_Product
        UNIQUE (SnapshotDateKey, ProductKey),
    CONSTRAINT FK_FactInventorySnapshot_Date
        FOREIGN KEY (SnapshotDateKey) REFERENCES dw.DimDate(DateKey),
    CONSTRAINT FK_FactInventorySnapshot_Product
        FOREIGN KEY (ProductKey) REFERENCES dw.DimProduct(ProductKey)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dw.FactInvoiceProfit') AND name = 'IX_FactInvoiceProfit_Date')
    CREATE INDEX IX_FactInvoiceProfit_Date ON dw.FactInvoiceProfit(DateKey);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dw.FactInvoiceProfit') AND name = 'IX_FactInvoiceProfit_Product')
    CREATE INDEX IX_FactInvoiceProfit_Product ON dw.FactInvoiceProfit(ProductKey);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dw.FactPurchaseLine') AND name = 'IX_FactPurchaseLine_Date')
    CREATE INDEX IX_FactPurchaseLine_Date ON dw.FactPurchaseLine(DateKey);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dw.FactPurchaseLine') AND name = 'IX_FactPurchaseLine_Supplier')
    CREATE INDEX IX_FactPurchaseLine_Supplier ON dw.FactPurchaseLine(SupplierKey);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dw.FactStockMovement') AND name = 'IX_FactStockMovement_Date')
    CREATE INDEX IX_FactStockMovement_Date ON dw.FactStockMovement(DateKey);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dw.FactStockMovement') AND name = 'IX_FactStockMovement_Product')
    CREATE INDEX IX_FactStockMovement_Product ON dw.FactStockMovement(ProductKey);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dw.FactInventorySnapshot') AND name = 'IX_FactInventorySnapshot_Product')
    CREATE INDEX IX_FactInventorySnapshot_Product ON dw.FactInventorySnapshot(ProductKey);
GO

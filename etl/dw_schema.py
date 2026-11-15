"""
Phase 4.1: Create Data Warehouse Schema
Creates DW tables: DimDate, DimCustomer, DimProduct, DimGeography, FactSales
"""
import sys
sys.path.insert(0, '.')
from etl.extract import DatabaseConnector
from etl.config import SQL_SERVER_CONFIG
import logging

logger = logging.getLogger(__name__)

def create_dw_schema():
    """Create DW schema and all dimensional tables"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()
    
    try:
        # Create DW schema - must use GO batch separator in ODBC
        print("📊 Creating DW Schema...")
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dw')
        BEGIN
            EXEC sp_executesql N'CREATE SCHEMA dw'
        END
        """)
        conn.connection.commit()
        print("✓ Schema 'dw' created\n")
        
        # Drop tables in correct order (dependencies first)
        print("🔄 Dropping existing tables...")
        for table in ['FactSales', 'DimCustomer', 'DimProduct', 'DimGeography', 'DimDate']:
            try:
                cursor.execute(f"IF OBJECT_ID('dw.{table}', 'U') IS NOT NULL DROP TABLE dw.{table};")
                conn.connection.commit()
                print(f"  ✓ Dropped {table}")
            except:
                pass
        print()
        
        # Create DimDate
        print("📅 Creating DimDate table...")
        cursor.execute("""
        CREATE TABLE dw.DimDate (
            DateKey INT PRIMARY KEY,
            Date DATE NOT NULL UNIQUE,
            Year INT NOT NULL,
            Month INT NOT NULL,
            MonthName NVARCHAR(20) NOT NULL,
            Quarter INT NOT NULL,
            DayOfWeek INT NOT NULL,
            DayOfWeekName NVARCHAR(10) NOT NULL,
            IsWeekend BIT NOT NULL DEFAULT 0,
            IsHoliday BIT DEFAULT 0,
            Week INT,
            DayOfYear INT
        );
        """)
        conn.connection.commit()
        print("✓ DimDate table created")
        
        # Create DimCustomer (SCD Type 2)
        print("📌 Creating DimCustomer table...")
        cursor.execute("""
        CREATE TABLE dw.DimCustomer (
            CustomerKey INT PRIMARY KEY IDENTITY(1,1),
            CustomerID INT NOT NULL,
            CustomerName NVARCHAR(255),
            PrimaryContactPerson NVARCHAR(255),
            City NVARCHAR(100),
            StateProvince NVARCHAR(100),
            Country NVARCHAR(100),
            PostalCode NVARCHAR(20),
            ValidFrom DATETIME2(7) NOT NULL,
            ValidTo DATETIME2(7) NOT NULL
                CONSTRAINT DF_DimCustomer_ValidTo DEFAULT ('9999-12-31T23:59:59.9999999'),
            IsCurrent BIT NOT NULL DEFAULT 1,
            CustomerCategory NVARCHAR(100),
            BuyingGroup NVARCHAR(100),
            GeographyKey INT
        );
        """)
        conn.connection.commit()
        print("✓ DimCustomer table created")
        
        # Create DimProduct (SCD Type 1)
        print("🏷️  Creating DimProduct table...")
        cursor.execute("""
        CREATE TABLE dw.DimProduct (
            ProductKey INT PRIMARY KEY IDENTITY(1,1),
            StockItemID INT NOT NULL UNIQUE,
            ProductName NVARCHAR(255),
            Category NVARCHAR(100),
            Brand NVARCHAR(100),
            UnitPrice DECIMAL(18,2),
            RecommendedRetailPrice DECIMAL(18,2),
            IsDeleted BIT DEFAULT 0
        );
        """)
        conn.connection.commit()
        print("✓ DimProduct table created")
        
        # Create DimGeography
        print("🌍 Creating DimGeography table...")
        cursor.execute("""
        CREATE TABLE dw.DimGeography (
            GeographyKey INT PRIMARY KEY IDENTITY(1,1),
            City NVARCHAR(100) NOT NULL,
            StateProvince NVARCHAR(100),
            Country NVARCHAR(100) NOT NULL,
            Region NVARCHAR(100),
            PostalCode NVARCHAR(20),
            CityID INT
        );
        """)
        conn.connection.commit()
        print("✓ DimGeography table created")
        
        # Create FactSales
        print("💰 Creating FactSales table...")
        cursor.execute("""
        CREATE TABLE dw.FactSales (
            SalesFactKey BIGINT PRIMARY KEY IDENTITY(1,1),
            
            -- Foreign Keys to Dimensions
            DateKey INT NOT NULL,
            CustomerKey INT NOT NULL,
            ProductKey INT NOT NULL,
            GeographyKey INT NOT NULL,
            
            -- Natural Keys (traceability)
            OrderID INT NOT NULL,
            OrderLineID INT NOT NULL,
            InvoiceID INT NULL,
            
            -- Measures (additive)
            Quantity INT NOT NULL,
            UnitPrice DECIMAL(18,2) NOT NULL,
            TaxRate DECIMAL(5,2) DEFAULT 0,
            LineTotal DECIMAL(18,2) NOT NULL,
            
            -- Contextual Attributes
            OrderStatus NVARCHAR(50),
            InvoiceStatus NVARCHAR(50),
            
            -- Audit
            LoadedDate DATETIME DEFAULT GETDATE(),
            SourceLastModified DATETIME,
            IsDeleted BIT DEFAULT 0,
            
            FOREIGN KEY (DateKey) REFERENCES dw.DimDate(DateKey),
            FOREIGN KEY (CustomerKey) REFERENCES dw.DimCustomer(CustomerKey),
            FOREIGN KEY (ProductKey) REFERENCES dw.DimProduct(ProductKey),
            FOREIGN KEY (GeographyKey) REFERENCES dw.DimGeography(GeographyKey)
        );
        """)
        conn.connection.commit()
        print("✓ FactSales table created")
        
        # Create Indexes (skip clustered - PK already creates it)
        print("\n🔑 Creating Indexes...")
        
        cursor.execute("""
        CREATE NONCLUSTERED INDEX IDX_FactSales_DateKey 
            ON dw.FactSales(DateKey);
        """)
        conn.connection.commit()
        print("✓ Index on DateKey created")
        
        cursor.execute("""
        CREATE NONCLUSTERED INDEX IDX_FactSales_CustomerKey 
            ON dw.FactSales(CustomerKey);
        """)
        conn.connection.commit()
        print("✓ Index on CustomerKey created")
        
        cursor.execute("""
        CREATE NONCLUSTERED INDEX IDX_FactSales_ProductKey 
            ON dw.FactSales(ProductKey);
        """)
        conn.connection.commit()
        print("✓ Index on ProductKey created")
        
        cursor.execute("""
        CREATE NONCLUSTERED INDEX IDX_FactSales_GeographyKey 
            ON dw.FactSales(GeographyKey);
        """)
        conn.connection.commit()
        print("✓ Index on GeographyKey created")
        
        cursor.execute("""
        CREATE NONCLUSTERED INDEX IDX_DimCustomer_Current 
            ON dw.DimCustomer(IsCurrent, CustomerID);
        """)
        conn.connection.commit()
        print("✓ Index on DimCustomer(IsCurrent) created")

        cursor.execute("""
        CREATE UNIQUE NONCLUSTERED INDEX UX_DimCustomer_CustomerID_ValidFrom
            ON dw.DimCustomer(CustomerID, ValidFrom);
        """)
        conn.connection.commit()
        print("✓ Unique index on DimCustomer version periods created")

        cursor.execute("""
        CREATE UNIQUE NONCLUSTERED INDEX UX_DimCustomer_Current
            ON dw.DimCustomer(CustomerID)
            WHERE IsCurrent = 1;
        """)
        conn.connection.commit()
        print("✓ Unique filtered index on current DimCustomer rows created")

        cursor.execute("""
        CREATE UNIQUE NONCLUSTERED INDEX UX_DimGeography_CityID
            ON dw.DimGeography(CityID)
            WHERE CityID IS NOT NULL;
        """)
        conn.connection.commit()
        print("✓ Unique filtered index on DimGeography city IDs created")
        
        cursor.execute("""
        CREATE NONCLUSTERED INDEX IDX_DimDate_Date 
            ON dw.DimDate(Date);
        """)
        conn.connection.commit()
        print("✓ Index on DimDate(Date) created")
        
        # Verify structure
        print("\n✅ Verifying DW Schema Structure...")
        cursor.execute("""
        SELECT 
            TABLE_NAME,
            (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
             WHERE TABLE_SCHEMA = 'dw' AND TABLE_NAME = t.TABLE_NAME) as column_count
        FROM INFORMATION_SCHEMA.TABLES t
        WHERE TABLE_SCHEMA = 'dw'
        ORDER BY TABLE_NAME
        """)
        
        tables = cursor.fetchall()
        print("\n📊 DW Tables Structure:")
        print("-" * 60)
        for table_name, col_count in tables:
            print(f"  {table_name:30} | Columns: {col_count:>3}")
        
        print("\n" + "=" * 60)
        print("✅ FASE 4.1 COMPLETADA - DW Schema Created Successfully")
        print("=" * 60)
        
        conn.disconnect()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        conn.disconnect()
        raise

if __name__ == "__main__":
    create_dw_schema()

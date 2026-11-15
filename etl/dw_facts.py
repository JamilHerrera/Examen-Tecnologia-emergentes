"""
FASE 4.3: Populate FactSales Table
Loads ~605K rows of sales facts from staging_clean tables into dw.FactSales
Joins with dimension tables to resolve surrogate keys
"""

import os
import pyodbc
from datetime import datetime
from typing import List, Tuple
import logging
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": os.getenv("MSSQL_SERVER", "localhost,1433"),
    "database": os.getenv("MSSQL_DATABASE", "WideWorldImporters"),
    "user": os.getenv("MSSQL_SA_USER", "sa"),
    "password": os.environ["MSSQL_SA_PASSWORD"],
    "encrypt": "no",
    "trust_certificate": "yes",
}

logger = logging.getLogger(__name__)


class DatabaseConnector:
    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        self.connection = pyodbc.connect(
            f"Driver={self.config['driver']};"
            f"Server={self.config['server']};"
            f"Database={self.config['database']};"
            f"UID={self.config['user']};"
            f"PWD={self.config['password']};"
            f"Encrypt={self.config['encrypt']};"
            f"TrustServerCertificate={self.config['trust_certificate']}"
        )

    def disconnect(self):
        if self.connection:
            self.connection.close()


def populate_factsales():
    """
    Load FactSales from staging_clean.Sales_Orders_clean and Sales_OrderLines_clean
    
    Process:
    1. Join Sales_Orders_clean with Sales_OrderLines_clean
    2. Resolve surrogate keys from dimension tables
    3. Calculate LineAmount = Quantity Ã— UnitPrice Ã— (1 - TaxRate/100)
    4. Insert facts into dw.FactSales
    """
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()

    print("\nðŸ“Š POPULATING FactSales...")
    print("-" * 80)

    try:
        # Step 1: Get count of expected rows
        cursor.execute("""
            SELECT COUNT(*)
            FROM staging_clean.Sales_OrderLines_clean sol
        """)
        expected_rows = cursor.fetchone()[0]
        print(f"  Expected rows from OrderLines: {expected_rows:,}")

        # Step 2: Insert facts with JOIN to dimensions for surrogate keys
        # Note: All columns in staging_clean are NVARCHAR, must convert carefully
        insert_query = """
        INSERT INTO dw.FactSales 
        (DateKey, CustomerKey, ProductKey, GeographyKey, OrderID, OrderLineID, 
         Quantity, UnitPrice, TaxRate, LineTotal, OrderStatus, LoadedDate)
        SELECT
            COALESCE(dd.DateKey, -1) AS DateKey,
            COALESCE(dc.CustomerKey, -1) AS CustomerKey,
            COALESCE(dp.ProductKey, -1) AS ProductKey,
            1 AS GeographyKey,
            CAST(sol.OrderID AS INT) AS OrderID,
            CAST(ROUND(CAST(sol.OrderLineID AS FLOAT), 0) AS INT) AS OrderLineID,
            CAST(ROUND(CAST(sol.Quantity AS FLOAT), 0) AS INT) AS Quantity,
            CAST(COALESCE(sol.UnitPrice, '0') AS DECIMAL(10, 2)) AS UnitPrice,
            CAST(COALESCE(sol.TaxRate, '0') AS DECIMAL(5, 2)) / 100.0 AS TaxRate,
            CAST(
                CAST(ROUND(CAST(sol.Quantity AS FLOAT), 0) AS DECIMAL(10, 2)) 
                * CAST(COALESCE(sol.UnitPrice, '0') AS DECIMAL(10, 2))
                AS DECIMAL(15, 2)
            ) AS LineTotal,
            'Completed' AS OrderStatus,
            GETDATE() AS LoadedDate
        FROM staging_clean.Sales_OrderLines_clean sol
        INNER JOIN staging_clean.Sales_Orders_clean so ON sol.OrderID = so.OrderID
        LEFT JOIN dw.DimCustomer dc
            ON dc.CustomerID = TRY_CONVERT(INT, so.CustomerID)
           AND CONVERT(DATETIME2(7), TRY_CONVERT(DATE, so.OrderDate)) >= dc.ValidFrom
           AND CONVERT(DATETIME2(7), TRY_CONVERT(DATE, so.OrderDate)) < dc.ValidTo
        LEFT JOIN dw.DimProduct dp ON CAST(ROUND(CAST(sol.StockItemID AS FLOAT), 0) AS VARCHAR) = CAST(dp.StockItemID AS VARCHAR)
        LEFT JOIN dw.DimDate dd ON CAST(SUBSTRING(so.OrderDate, 1, 10) AS DATE) = dd.Date
        """

        cursor.execute(insert_query)
        conn.connection.commit()
        
        # Step 3: Verify insert
        cursor.execute("SELECT COUNT(*) FROM dw.FactSales")
        inserted_rows = cursor.fetchone()[0]
        print(f"  âœ“ Inserted {inserted_rows:,}/{expected_rows:,} facts")

        # Step 4: Get statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT OrderID) AS UniqueOrders,
                COUNT(DISTINCT ProductKey) AS UniqueProducts,
                COUNT(DISTINCT CustomerKey) AS UniqueCustomers,
                SUM(LineTotal) AS TotalSalesAmount,
                AVG(LineTotal) AS AvgLineAmount,
                MIN(LineTotal) AS MinLineAmount,
                MAX(LineTotal) AS MaxLineAmount
            FROM dw.FactSales
        """)
        
        result = cursor.fetchone()
        print(f"\n  ðŸ“ˆ FactSales Statistics:")
        print(f"     Unique Orders:      {result[0]:,}")
        print(f"     Unique Products:    {result[1]:,}")
        print(f"     Unique Customers:   {result[2]:,}")
        print(f"     Total Sales Amount: ${result[3]:,.2f}")
        print(f"     Avg Line Amount:    ${result[4]:,.2f}")
        print(f"     Min Line Amount:    ${result[5]:,.2f}")
        print(f"     Max Line Amount:    ${result[6]:,.2f}")

        # Step 5: Check for -1 keys (unmapped dimension references)
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN CustomerKey = -1 THEN 1 ELSE 0 END) AS MissingCustomers,
                SUM(CASE WHEN ProductKey = -1 THEN 1 ELSE 0 END) AS MissingProducts,
                SUM(CASE WHEN DateKey = -1 THEN 1 ELSE 0 END) AS MissingDates
            FROM dw.FactSales
        """)
        
        result = cursor.fetchone()
        print(f"\n  âš ï¸  Data Quality Check:")
        print(f"     Missing Customers:  {result[0]:,}")
        print(f"     Missing Products:   {result[1]:,}")
        print(f"     Missing Dates:      {result[2]:,}")

        print(f"\n  âœ… FactSales populated: {inserted_rows:,} rows")
        conn.disconnect()
        return inserted_rows

    except Exception as e:
        print(f"\n  âŒ Error inserting facts: {str(e)}")
        conn.disconnect()
        raise


def verify_factsales():
    """Verify FactSales data integrity and completeness"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()

    print("\nâœ… VERIFYING FactSales...")
    print("-" * 80)

    try:
        # Get row counts
        cursor.execute("SELECT COUNT(*) FROM dw.FactSales")
        fact_rows = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM staging_clean.Sales_OrderLines_clean")
        staging_rows = cursor.fetchone()[0]

        print(f"  FactSales rows:           {fact_rows:,}")
        print(f"  Staging OrderLines rows:  {staging_rows:,}")
        print(f"  Match:                    {'âœ“ YES' if fact_rows == staging_rows else 'âœ— NO'}")

        # Check for NULL values in critical columns
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN CustomerKey IS NULL THEN 1 ELSE 0 END) AS NullCustomerKey,
                SUM(CASE WHEN ProductKey IS NULL THEN 1 ELSE 0 END) AS NullProductKey,
                SUM(CASE WHEN DateKey IS NULL THEN 1 ELSE 0 END) AS NullDateKey,
                SUM(CASE WHEN LineTotal IS NULL THEN 1 ELSE 0 END) AS NullLineTotal
            FROM dw.FactSales
        """)
        
        result = cursor.fetchone()
        print(f"\n  Null checks:")
        print(f"    NULL CustomerKey:  {result[0]}")
        print(f"    NULL ProductKey:   {result[1]}")
        print(f"    NULL DateKey:      {result[2]}")
        print(f"    NULL LineAmount:   {result[3]}")

        # Sample data
        cursor.execute("""
            SELECT TOP 5
                fs.SalesFactKey,
                fs.OrderID,
                fs.OrderLineID,
                fs.CustomerKey,
                fs.ProductKey,
                fs.DateKey,
                fs.Quantity,
                fs.UnitPrice,
                fs.TaxRate,
                fs.LineTotal
            FROM dw.FactSales fs
        """)
        
        print(f"\n  Sample rows:")
        print(f"    FactKey | OrderID | LineID | CustKey | ProdKey | DateKey | Qty | Price | TaxRate | LineTotal")
        for row in cursor.fetchall():
            print(f"    {row[0]:7} | {row[1]:7} | {row[2]:6} | {row[3]:7} | {row[4]:7} | {row[5]:7} | {row[6]:3} | {row[7]:5} | {row[8]:8} | {row[9]:9.2f}")

        conn.disconnect()

    except Exception as e:
        print(f"\n  âŒ Error verifying facts: {str(e)}")
        conn.disconnect()
        raise


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ðŸš€ FASE 4.3: POPULATE FACTSALES")
    print("=" * 80)

    try:
        populate_factsales()
        verify_factsales()

        print("\n" + "=" * 80)
        print("âœ… FASE 4.3 COMPLETADA - FactSales Populated")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\nâŒ Error in Phase 4.3: {str(e)}")
        raise


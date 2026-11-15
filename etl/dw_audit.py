"""
FASE 4.4: Data Warehouse Audit & Validation
Comprehensive quality checks and reconciliation of the data warehouse
"""

import pyodbc
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
SQL_SERVER_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": "localhost,1433",
    "database": "WideWorldImporters",
    "user": "sa",
    "password": "P@ssw0rd123",
    "encrypt": "no",
    "trust_certificate": "yes",
}


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


def reconcile_row_counts() -> Dict[str, int]:
    """Compare row counts between staging and DW"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()

    print("\n📊 ROW COUNT RECONCILIATION")
    print("-" * 80)

    reconciliation = {}

    # Check staging tables
    cursor.execute("SELECT COUNT(*) FROM staging_clean.Sales_Orders_clean")
    staging_orders = cursor.fetchone()[0]
    reconciliation['staging_orders'] = staging_orders

    cursor.execute("SELECT COUNT(*) FROM staging_clean.Sales_OrderLines_clean")
    staging_lines = cursor.fetchone()[0]
    reconciliation['staging_lines'] = staging_lines

    # Check DW tables
    cursor.execute("SELECT COUNT(*) FROM dw.FactSales")
    dw_facts = cursor.fetchone()[0]
    reconciliation['dw_facts'] = dw_facts

    cursor.execute("SELECT COUNT(*) FROM dw.DimCustomer")
    dw_customers = cursor.fetchone()[0]
    reconciliation['dw_customers'] = dw_customers

    cursor.execute("SELECT COUNT(*) FROM dw.DimProduct")
    dw_products = cursor.fetchone()[0]
    reconciliation['dw_products'] = dw_products

    cursor.execute("SELECT COUNT(*) FROM dw.DimDate")
    dw_dates = cursor.fetchone()[0]
    reconciliation['dw_dates'] = dw_dates

    # Display results
    print(f"  Staging Orders:       {staging_orders:,}")
    print(f"  Staging Order Lines:  {staging_lines:,}")
    print(f"  DW FactSales:         {dw_facts:,}")
    print(f"  DW DimCustomer:       {dw_customers:,}")
    print(f"  DW DimProduct:        {dw_products:,}")
    print(f"  DW DimDate:           {dw_dates:,}")

    # Validate reconciliation
    print(f"\n  ✓ FactSales vs OrderLines: {('MATCH ✓' if dw_facts == staging_lines else 'MISMATCH ✗')}")

    conn.disconnect()
    return reconciliation


def validate_foreign_keys() -> Dict[str, int]:
    """Check for orphaned records (FK violations)"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()

    print("\n🔗 FOREIGN KEY INTEGRITY CHECK")
    print("-" * 80)

    issues = {}

    # Check for missing CustomerKey
    cursor.execute("""
        SELECT COUNT(*) 
        FROM dw.FactSales 
        WHERE CustomerKey NOT IN (SELECT CustomerKey FROM dw.DimCustomer)
          AND CustomerKey != -1
    """)
    orphan_customers = cursor.fetchone()[0]
    issues['orphan_customers'] = orphan_customers
    print(f"  Orphaned CustomerKeys:  {orphan_customers} {'✓' if orphan_customers == 0 else '✗'}")

    # Check for missing ProductKey
    cursor.execute("""
        SELECT COUNT(*) 
        FROM dw.FactSales 
        WHERE ProductKey NOT IN (SELECT ProductKey FROM dw.DimProduct)
          AND ProductKey != -1
    """)
    orphan_products = cursor.fetchone()[0]
    issues['orphan_products'] = orphan_products
    print(f"  Orphaned ProductKeys:   {orphan_products} {'✓' if orphan_products == 0 else '✗'}")

    # Check for missing DateKey
    cursor.execute("""
        SELECT COUNT(*) 
        FROM dw.FactSales 
        WHERE DateKey NOT IN (SELECT DateKey FROM dw.DimDate)
          AND DateKey != -1
    """)
    orphan_dates = cursor.fetchone()[0]
    issues['orphan_dates'] = orphan_dates
    print(f"  Orphaned DateKeys:      {orphan_dates} {'✓' if orphan_dates == 0 else '✗'}")

    # Check for missing GeographyKey
    cursor.execute("""
        SELECT COUNT(*) 
        FROM dw.FactSales 
        WHERE GeographyKey NOT IN (SELECT GeographyKey FROM dw.DimGeography)
          AND GeographyKey != -1
    """)
    orphan_geography = cursor.fetchone()[0]
    issues['orphan_geography'] = orphan_geography
    print(f"  Orphaned GeographyKeys: {orphan_geography} {'✓' if orphan_geography == 0 else '✗'}")

    conn.disconnect()
    return issues


def validate_data_quality() -> Dict[str, any]:
    """Check for data quality issues"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()

    print("\n✅ DATA QUALITY VALIDATION")
    print("-" * 80)

    issues = {}

    # Check for NULL values in critical columns
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN Quantity IS NULL OR Quantity <= 0 THEN 1 ELSE 0 END) AS InvalidQuantity,
            SUM(CASE WHEN UnitPrice IS NULL OR UnitPrice < 0 THEN 1 ELSE 0 END) AS InvalidPrice,
            SUM(CASE WHEN LineTotal IS NULL OR LineTotal < 0 THEN 1 ELSE 0 END) AS InvalidTotal,
            SUM(CASE WHEN OrderID IS NULL THEN 1 ELSE 0 END) AS NullOrderID
        FROM dw.FactSales
    """)
    result = cursor.fetchone()
    issues['invalid_quantity'] = result[0] or 0
    issues['invalid_price'] = result[1] or 0
    issues['invalid_total'] = result[2] or 0
    issues['null_order_id'] = result[3] or 0

    print(f"  Invalid Quantities:     {issues['invalid_quantity']} {'✓' if issues['invalid_quantity'] == 0 else '✗'}")
    print(f"  Invalid Unit Prices:    {issues['invalid_price']} {'✓' if issues['invalid_price'] == 0 else '✗'}")
    print(f"  Invalid Line Totals:    {issues['invalid_total']} {'✓' if issues['invalid_total'] == 0 else '✗'}")
    print(f"  Null Order IDs:         {issues['null_order_id']} {'✓' if issues['null_order_id'] == 0 else '✗'}")

    # Check dimension data quality
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM dw.DimCustomer WHERE CustomerID IS NULL) AS NullCustomerID,
            (SELECT COUNT(*) FROM dw.DimProduct WHERE StockItemID IS NULL) AS NullStockItemID,
            (SELECT COUNT(*) FROM dw.DimDate WHERE Date IS NULL) AS NullDate
    """)
    result = cursor.fetchone()
    print(f"\n  Dimension Quality:")
    print(f"    NULL CustomerIDs:     {result[0]} {'✓' if result[0] == 0 else '✗'}")
    print(f"    NULL StockItemIDs:    {result[1]} {'✓' if result[1] == 0 else '✗'}")
    print(f"    NULL Dates:           {result[2]} {'✓' if result[2] == 0 else '✗'}")

    conn.disconnect()
    return issues


def validate_schema() -> Dict[str, bool]:
    """Verify schema completeness"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()

    print("\n🏗️  SCHEMA VALIDATION")
    print("-" * 80)

    validation = {}

    # Check tables exist
    tables = ['DimDate', 'DimCustomer', 'DimProduct', 'DimGeography', 'FactSales']
    print("  Tables:")
    for table in tables:
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dw' AND TABLE_NAME = '{table}'
        """)
        exists = cursor.fetchone()[0] == 1
        validation[f'table_{table}'] = exists
        print(f"    {table:20} {'✓' if exists else '✗'}")

    # Check indexes exist
    cursor.execute("""
        SELECT COUNT(*) 
        FROM sys.indexes 
        WHERE object_id IN (
            SELECT OBJECT_ID FROM sys.objects 
            WHERE schema_id = SCHEMA_ID('dw')
        )
    """)
    index_count = cursor.fetchone()[0]
    validation['indexes'] = index_count > 0
    print(f"\n  Indexes: {index_count} found {'✓' if index_count > 0 else '✗'}")

    # Check primary keys
    pk_count = 0
    for table in tables:
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = 'dw' AND TABLE_NAME = '{table}' 
              AND CONSTRAINT_NAME LIKE 'PK%'
        """)
        if cursor.fetchone()[0] > 0:
            pk_count += 1

    validation['primary_keys'] = pk_count == len(tables)
    print(f"  Primary Keys: {pk_count}/{len(tables)} tables {'✓' if pk_count == len(tables) else '✗'}")

    conn.disconnect()
    return validation


def get_summary_statistics() -> Dict[str, any]:
    """Get summary statistics about the DW"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()

    print("\n📈 DATA WAREHOUSE SUMMARY")
    print("-" * 80)

    stats = {}

    # Date range
    cursor.execute("""
        SELECT MIN(Date) AS MinDate, MAX(Date) AS MaxDate, COUNT(*) AS DateCount
        FROM dw.DimDate
    """)
    min_date, max_date, date_count = cursor.fetchone()
    stats['date_range'] = f"{min_date} to {max_date}"
    print(f"  Date Range:             {min_date} to {max_date}")
    print(f"  Total Dates:            {date_count:,}")

    # Sales summary
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT OrderID) AS UniqOrders,
            COUNT(DISTINCT CustomerKey) AS UniqCustomers,
            COUNT(DISTINCT ProductKey) AS UniqProducts,
            SUM(LineTotal) AS TotalSales,
            AVG(LineTotal) AS AvgLineTotal,
            MIN(LineTotal) AS MinLineTotal,
            MAX(LineTotal) AS MaxLineTotal
        FROM dw.FactSales
    """)
    (uniq_orders, uniq_customers, uniq_products, 
     total_sales, avg_line, min_line, max_line) = cursor.fetchone()
    
    print(f"\n  Sales Metrics:")
    print(f"    Unique Orders:        {uniq_orders:,}")
    print(f"    Unique Customers:     {uniq_customers:,}")
    print(f"    Unique Products:      {uniq_products:,}")
    print(f"    Total Sales:          ${total_sales:,.2f}")
    print(f"    Avg Line Total:       ${avg_line:,.2f}")
    print(f"    Min/Max Line Total:   ${min_line:,.2f} / ${max_line:,.2f}")

    stats['total_sales'] = total_sales
    stats['unique_orders'] = uniq_orders
    stats['unique_customers'] = uniq_customers
    stats['unique_products'] = uniq_products

    conn.disconnect()
    return stats


def generate_audit_report():
    """Generate comprehensive audit report"""
    print("\n" + "=" * 80)
    print("🚀 FASE 4.4: DATA WAREHOUSE AUDIT & VALIDATION")
    print("=" * 80)

    try:
        # Run all validations
        reconciliation = reconcile_row_counts()
        fk_issues = validate_foreign_keys()
        quality_issues = validate_data_quality()
        schema_validation = validate_schema()
        summary_stats = get_summary_statistics()

        # Generate final report
        print("\n" + "=" * 80)
        print("📋 AUDIT REPORT SUMMARY")
        print("=" * 80)

        total_issues = sum([
            fk_issues.get('orphan_customers', 0),
            fk_issues.get('orphan_products', 0),
            fk_issues.get('orphan_dates', 0),
            fk_issues.get('orphan_geography', 0),
            quality_issues.get('invalid_quantity', 0),
            quality_issues.get('invalid_price', 0),
            quality_issues.get('invalid_total', 0),
        ])

        if total_issues == 0:
            print("\n  ✅ ALL VALIDATION CHECKS PASSED!")
            print("  Data Warehouse is ready for analytics and reporting.")
        else:
            print(f"\n  ⚠️  FOUND {total_issues} ISSUE(S):")
            if fk_issues.get('orphan_customers', 0) > 0:
                print(f"     - {fk_issues['orphan_customers']} orphaned customer references")
            if fk_issues.get('orphan_products', 0) > 0:
                print(f"     - {fk_issues['orphan_products']} orphaned product references")
            if quality_issues.get('invalid_quantity', 0) > 0:
                print(f"     - {quality_issues['invalid_quantity']} invalid quantities")

        print("\n  📊 Final Statistics:")
        print(f"     Total Fact Rows:      {reconciliation['dw_facts']:,}")
        print(f"     Total Sales Value:    ${summary_stats['total_sales']:,.2f}")
        print(f"     Unique Orders:        {summary_stats['unique_orders']:,}")
        print(f"     Unique Customers:     {summary_stats['unique_customers']:,}")
        print(f"     Unique Products:      {summary_stats['unique_products']:,}")
        print(f"     Date Range:           {summary_stats['date_range']}")

        print("\n" + "=" * 80)
        print("✅ FASE 4.4 COMPLETADA - Data Warehouse Audit & Validation")
        print("=" * 80 + "\n")

        return {
            'total_issues': total_issues,
            'reconciliation': reconciliation,
            'fk_issues': fk_issues,
            'quality_issues': quality_issues,
            'schema_valid': schema_validation,
            'summary_stats': summary_stats
        }

    except Exception as e:
        print(f"\n❌ Error in Phase 4.4: {str(e)}")
        raise


if __name__ == "__main__":
    report = generate_audit_report()

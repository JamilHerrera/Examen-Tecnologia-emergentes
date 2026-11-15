"""
Phase 4.2: Populate Dimensions
Loads data into DimDate, DimCustomer, DimProduct, DimGeography
"""
import sys
sys.path.insert(0, '.')
from etl.extract import DatabaseConnector
from etl.config import SQL_SERVER_CONFIG
from datetime import datetime, timedelta
import pandas as pd

def populate_dimdate():
    """Populate DimDate with all dates from min to max OrderDate"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()
    
    print("\n📅 POPULATING DimDate...")
    print("-" * 80)
    
    try:
        # Get date range from staging_clean
        cursor.execute("""
        SELECT 
            MIN(CAST(OrderDate AS DATE)) as min_date,
            MAX(CAST(OrderDate AS DATE)) as max_date
        FROM staging_clean.Sales_Orders_clean
        WHERE OrderDate IS NOT NULL
        """)
        result = cursor.fetchone()
        min_date = result[0]
        max_date = result[1]
        
        print(f"  Date range: {min_date} to {max_date}")
        
        # Generate date range
        dates = pd.date_range(start=min_date, end=max_date, freq='D')
        
        # Prepare batch insert
        batch = []
        for date in dates:
            date_key = int(date.strftime('%Y%m%d'))
            month_name = date.strftime('%B')
            day_name = date.strftime('%A')
            is_weekend = 1 if date.weekday() >= 5 else 0
            
            batch.append((
                date_key,
                date.date(),
                date.year,
                date.month,
                month_name,
                (date.month - 1) // 3 + 1,  # Quarter
                date.weekday(),
                day_name,
                is_weekend,
                0,  # IsHoliday
                date.isocalendar()[1],  # Week number
                date.timetuple().tm_yday  # Day of year
            ))
        
        # Insert in chunks
        chunk_size = 5000
        total_inserted = 0
        
        for i in range(0, len(batch), chunk_size):
            chunk = batch[i:i+chunk_size]
            cursor.executemany("""
            INSERT INTO dw.DimDate (DateKey, Date, Year, Month, MonthName, Quarter, 
                                    DayOfWeek, DayOfWeekName, IsWeekend, IsHoliday, Week, DayOfYear)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, chunk)
            conn.connection.commit()
            total_inserted += len(chunk)
            print(f"  ✓ Inserted {total_inserted}/{len(batch)} dates")
        
        print(f"  ✅ DimDate populated: {total_inserted} rows")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise
    finally:
        conn.disconnect()

def populate_dimcustomer():
    """Populate DimCustomer from staging_clean Sales_Orders"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()
    
    print("\n👤 POPULATING DimCustomer...")
    print("-" * 80)
    
    try:
        # Extract unique customers from Orders (assuming customer data is denormalized there)
        cursor.execute("""
        SELECT DISTINCT
            CAST(CustomerID AS INT) as CustomerID,
            NULL as CustomerName,
            NULL as PrimaryContact,
            NULL as City,
            NULL as StateProvince,
            NULL as Country,
            NULL as PostalCode,
            CAST(MIN(OrderDate) AS DATE) as ValidFrom
        FROM staging_clean.Sales_Orders_clean
        GROUP BY CustomerID
        ORDER BY CustomerID
        """)
        
        rows = cursor.fetchall()
        print(f"  Found {len(rows)} unique customers")
        
        batch = []
        for row in rows:
            customer_id, cust_name, contact, city, state, country, postal, valid_from = row
            batch.append((
                customer_id,
                f"Customer_{customer_id}",  # Placeholder name
                contact,
                city,
                state,
                country,
                postal,
                valid_from or datetime(2020, 1, 1).date(),
                '9999-12-31'
            ))
        
        # Insert in chunks
        chunk_size = 5000
        total_inserted = 0
        
        for i in range(0, len(batch), chunk_size):
            chunk = batch[i:i+chunk_size]
            cursor.executemany("""
            INSERT INTO dw.DimCustomer (CustomerID, CustomerName, PrimaryContactPerson, 
                                        City, StateProvince, Country, PostalCode, 
                                        ValidFrom, ValidTo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, chunk)
            conn.connection.commit()
            total_inserted += len(chunk)
            print(f"  ✓ Inserted {total_inserted}/{len(batch)} customers")
        
        print(f"  ✅ DimCustomer populated: {total_inserted} rows")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise
    finally:
        conn.disconnect()

def populate_dimproduct():
    """Populate DimProduct from Warehouse.StockItems_clean"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()
    
    print("\n🏷️  POPULATING DimProduct...")
    print("-" * 80)
    
    try:
        # Get products from staging_clean
        cursor.execute("""
        SELECT 
            CAST(StockItemID AS INT),
            StockItemName,
            NULL as Category,
            NULL as Brand,
            NULL as UnitPrice,
            NULL as RetailPrice
        FROM staging_clean.Warehouse_StockItems_clean
        ORDER BY StockItemID
        """)
        
        rows = cursor.fetchall()
        print(f"  Found {len(rows)} products")
        
        batch = []
        for row in rows:
            stock_id, name, cat, brand, price, retail = row
            batch.append((
                stock_id,
                name,
                cat,
                brand,
                price,
                retail
            ))
        
        # Insert in chunks
        chunk_size = 5000
        total_inserted = 0
        
        for i in range(0, len(batch), chunk_size):
            chunk = batch[i:i+chunk_size]
            cursor.executemany("""
            INSERT INTO dw.DimProduct (StockItemID, ProductName, Category, Brand, 
                                       UnitPrice, RecommendedRetailPrice)
            VALUES (?, ?, ?, ?, ?, ?)
            """, chunk)
            conn.connection.commit()
            total_inserted += len(chunk)
            print(f"  ✓ Inserted {total_inserted}/{len(batch)} products")
        
        print(f"  ✅ DimProduct populated: {total_inserted} rows")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise
    finally:
        conn.disconnect()

def populate_dimgeography():
    """Populate DimGeography from Sales data"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()
    
    print("\n🌍 POPULATING DimGeography...")
    print("-" * 80)
    
    try:
        # For now, create a simple default geography (since source doesn't have geographic data denormalized)
        # In real world, this would join to customer/location tables
        cursor.execute("""
        SELECT DISTINCT
            'Unknown' as City,
            NULL as StateProvince,
            'Unknown' as Country,
            NULL as Region,
            NULL as PostalCode
        """)
        
        rows = cursor.fetchall()
        
        batch = [(
            'Unknown',  # City
            None,       # StateProvince
            'Unknown',  # Country
            None,       # Region
            None        # PostalCode
        )]
        
        cursor.executemany("""
        INSERT INTO dw.DimGeography (City, StateProvince, Country, Region, PostalCode)
        VALUES (?, ?, ?, ?, ?)
        """, batch)
        conn.connection.commit()
        
        print(f"  ✓ Inserted 1 default geography")
        print(f"  ✅ DimGeography populated: 1 row (placeholder)")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise
    finally:
        conn.disconnect()

def verify_dimensions():
    """Verify dimension populations"""
    conn = DatabaseConnector(SQL_SERVER_CONFIG)
    conn.connect()
    cursor = conn.connection.cursor()
    
    print("\n✅ VERIFYING DIMENSIONS...")
    print("-" * 80)
    
    tables = ['DimDate', 'DimCustomer', 'DimProduct', 'DimGeography']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM dw.{table}")
        count = cursor.fetchone()[0]
        print(f"  {table:30} | Rows: {count:>8}")
    
    conn.disconnect()

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 FASE 4.2: POPULATE DIMENSIONS")
    print("=" * 80)
    
    try:
        # Clean up existing data
        conn = DatabaseConnector(SQL_SERVER_CONFIG)
        conn.connect()
        cursor = conn.connection.cursor()
        
        print("\n🧹 Cleaning existing dimension data...")
        for table in ['FactSales', 'DimCustomer', 'DimProduct', 'DimGeography', 'DimDate']:
            try:
                cursor.execute(f"DELETE FROM dw.{table}")
                conn.connection.commit()
                print(f"  ✓ Cleaned {table}")
            except:
                pass
        
        conn.disconnect()
        
        populate_dimdate()
        populate_dimcustomer()
        populate_dimproduct()
        populate_dimgeography()
        verify_dimensions()
        
        print("\n" + "=" * 80)
        print("✅ FASE 4.2 COMPLETADA - All Dimensions Populated")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error in Phase 4.2: {str(e)}")
        raise

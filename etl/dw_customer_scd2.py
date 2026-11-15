"""Load customer system-version history into dw.DimCustomer (SCD type 2)."""

import sys

sys.path.insert(0, ".")
from etl.config import SQL_SERVER_CONFIG
from etl.extract import DatabaseConnector


SCHEMA_MIGRATION_SQL = """
IF OBJECT_ID('dw.DimCustomer', 'U') IS NULL
    THROW 51000, 'dw.DimCustomer must exist before loading customer history.', 1;
IF OBJECT_ID('dw.DimGeography', 'U') IS NULL
    THROW 51000, 'dw.DimGeography must exist before loading customer history.', 1;

IF COL_LENGTH('dw.DimCustomer', 'CustomerCategory') IS NULL
    ALTER TABLE dw.DimCustomer ADD CustomerCategory NVARCHAR(100) NULL;
IF COL_LENGTH('dw.DimCustomer', 'BuyingGroup') IS NULL
    ALTER TABLE dw.DimCustomer ADD BuyingGroup NVARCHAR(100) NULL;
IF COL_LENGTH('dw.DimCustomer', 'GeographyKey') IS NULL
    ALTER TABLE dw.DimCustomer ADD GeographyKey INT NULL;
IF COL_LENGTH('dw.DimGeography', 'CityID') IS NULL
    ALTER TABLE dw.DimGeography ADD CityID INT NULL;

UPDATE dw.DimCustomer
SET ValidTo = '9999-12-31T23:59:59.9999999'
WHERE ValidTo IS NULL AND IsCurrent = 1;
IF EXISTS (SELECT 1 FROM dw.DimCustomer WHERE ValidTo IS NULL)
    THROW 51000, 'dw.DimCustomer contains a historical row without ValidTo.', 1;

IF EXISTS (SELECT 1 FROM dw.DimCustomer WHERE IsCurrent IS NULL)
    THROW 51000, 'dw.DimCustomer contains a row without an IsCurrent value.', 1;
"""

CUSTOMER_SOURCE_SQL = """
IF OBJECT_ID('tempdb..#CustomerSource') IS NOT NULL DROP TABLE #CustomerSource;
SELECT
    source.CustomerID,
    source.CustomerName,
    source.CustomerCategoryID,
    source.BuyingGroupID,
    source.PrimaryContactPersonID,
    source.DeliveryCityID,
    source.DeliveryPostalCode,
    source.ValidFrom,
    source.ValidTo,
    source.IsCurrent
INTO #CustomerSource
FROM (
    SELECT CustomerID, CustomerName, CustomerCategoryID, BuyingGroupID,
           PrimaryContactPersonID, DeliveryCityID, DeliveryPostalCode,
           ValidFrom, ValidTo, CONVERT(BIT, 1) AS IsCurrent
    FROM Sales.Customers
    UNION ALL
    SELECT CustomerID, CustomerName, CustomerCategoryID, BuyingGroupID,
           PrimaryContactPersonID, DeliveryCityID, DeliveryPostalCode,
           ValidFrom, ValidTo, CONVERT(BIT, 0) AS IsCurrent
    FROM Sales.Customers_Archive
) AS source;
"""

GEOGRAPHY_SQL = """
INSERT INTO dw.DimGeography (CityID, City, StateProvince, Country, Region)
SELECT DISTINCT
    ci.CityID,
    ci.CityName,
    sp.StateProvinceName,
    co.CountryName,
    sp.SalesTerritory
FROM #CustomerSource source
JOIN Application.Cities ci ON ci.CityID = source.DeliveryCityID
JOIN Application.StateProvinces sp ON sp.StateProvinceID = ci.StateProvinceID
JOIN Application.Countries co ON co.CountryID = sp.CountryID
WHERE source.ValidFrom < source.ValidTo
  AND NOT EXISTS (
    SELECT 1 FROM dw.DimGeography g WHERE g.CityID = ci.CityID
);
"""

CUSTOMER_VERSIONS_SQL = """
IF OBJECT_ID('tempdb..#CustomerVersions') IS NOT NULL DROP TABLE #CustomerVersions;
SELECT
    source.CustomerID,
    source.CustomerName,
    people.FullName AS PrimaryContactPerson,
    cities.CityName AS City,
    provinces.StateProvinceName AS StateProvince,
    countries.CountryName AS Country,
    source.DeliveryPostalCode AS PostalCode,
    source.ValidFrom,
    source.ValidTo,
    source.IsCurrent,
    categories.CustomerCategoryName AS CustomerCategory,
    groups.BuyingGroupName AS BuyingGroup,
    COALESCE(geography.GeographyKey, 1) AS GeographyKey
INTO #CustomerVersions
FROM #CustomerSource source
LEFT JOIN Application.People people
    ON people.PersonID = source.PrimaryContactPersonID
LEFT JOIN Sales.CustomerCategories categories
    ON categories.CustomerCategoryID = source.CustomerCategoryID
LEFT JOIN Sales.BuyingGroups groups
    ON groups.BuyingGroupID = source.BuyingGroupID
LEFT JOIN Application.Cities cities
    ON cities.CityID = source.DeliveryCityID
LEFT JOIN dw.DimGeography geography
    ON geography.CityID = source.DeliveryCityID
LEFT JOIN Application.StateProvinces provinces
    ON provinces.StateProvinceID = cities.StateProvinceID
LEFT JOIN Application.Countries countries
    ON countries.CountryID = provinces.CountryID
WHERE source.ValidFrom < source.ValidTo;
"""

CURRENT_CUSTOMER_SQL = """
UPDATE dimension
SET CustomerName = source.CustomerName,
    PrimaryContactPerson = source.PrimaryContactPerson,
    City = source.City,
    StateProvince = source.StateProvince,
    Country = source.Country,
    PostalCode = source.PostalCode,
    ValidFrom = source.ValidFrom,
    ValidTo = source.ValidTo,
    IsCurrent = 1,
    CustomerCategory = source.CustomerCategory,
    BuyingGroup = source.BuyingGroup,
    GeographyKey = source.GeographyKey
FROM dw.DimCustomer dimension
JOIN #CustomerVersions source
    ON source.CustomerID = dimension.CustomerID AND source.IsCurrent = 1
WHERE dimension.IsCurrent = 1;

INSERT INTO dw.DimCustomer (
    CustomerID, CustomerName, PrimaryContactPerson, City, StateProvince, Country,
    PostalCode, ValidFrom, ValidTo, IsCurrent, CustomerCategory, BuyingGroup, GeographyKey
)
SELECT
    source.CustomerID, source.CustomerName, source.PrimaryContactPerson,
    source.City, source.StateProvince, source.Country, source.PostalCode,
    source.ValidFrom, source.ValidTo, 1, source.CustomerCategory,
    source.BuyingGroup, source.GeographyKey
FROM #CustomerVersions source
WHERE source.IsCurrent = 1
  AND NOT EXISTS (
      SELECT 1 FROM dw.DimCustomer dimension
      WHERE dimension.CustomerID = source.CustomerID AND dimension.IsCurrent = 1
  );
"""

HISTORICAL_CUSTOMER_SQL = """
UPDATE dimension
SET CustomerName = source.CustomerName,
    PrimaryContactPerson = source.PrimaryContactPerson,
    City = source.City,
    StateProvince = source.StateProvince,
    Country = source.Country,
    PostalCode = source.PostalCode,
    ValidTo = source.ValidTo,
    IsCurrent = 0,
    CustomerCategory = source.CustomerCategory,
    BuyingGroup = source.BuyingGroup,
    GeographyKey = source.GeographyKey
FROM dw.DimCustomer dimension
JOIN #CustomerVersions source
    ON source.CustomerID = dimension.CustomerID
   AND source.ValidFrom = dimension.ValidFrom
   AND source.IsCurrent = 0
WHERE dimension.IsCurrent = 0;

INSERT INTO dw.DimCustomer (
    CustomerID, CustomerName, PrimaryContactPerson, City, StateProvince, Country,
    PostalCode, ValidFrom, ValidTo, IsCurrent, CustomerCategory, BuyingGroup, GeographyKey
)
SELECT
    source.CustomerID, source.CustomerName, source.PrimaryContactPerson,
    source.City, source.StateProvince, source.Country, source.PostalCode,
    source.ValidFrom, source.ValidTo, 0, source.CustomerCategory,
    source.BuyingGroup, source.GeographyKey
FROM #CustomerVersions source
WHERE source.IsCurrent = 0
  AND NOT EXISTS (
      SELECT 1 FROM dw.DimCustomer dimension
      WHERE dimension.CustomerID = source.CustomerID
        AND dimension.ValidFrom = source.ValidFrom
        AND dimension.IsCurrent = 0
  );
"""


def _assert_no_rows(cursor, query, error_message):
    cursor.execute(query)
    violations = cursor.fetchone()[0]
    if violations:
        raise RuntimeError(f"{error_message}: {violations}")


def _migrate_schema(cursor):
    cursor.execute(SCHEMA_MIGRATION_SQL)
    cursor.execute("""
    SELECT c.name, t.name, c.is_nullable
    FROM sys.columns c
    JOIN sys.types t ON t.user_type_id = c.user_type_id
    WHERE c.object_id = OBJECT_ID('dw.DimCustomer')
      AND c.name IN ('ValidFrom', 'ValidTo')
    """)
    column_types = {
        row[0]: (row[1], row[2])
        for row in cursor.fetchall()
    }

    cursor.execute("""
    SELECT dc.name, dc.definition
    FROM sys.default_constraints dc
    JOIN sys.columns c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID('dw.DimCustomer') AND c.name = 'ValidTo'
    """)
    default_constraint = cursor.fetchone()
    if column_types["ValidTo"][0] in ("date", "datetime") and default_constraint:
        constraint_name = default_constraint[0].replace("]", "]]")
        cursor.execute(f"ALTER TABLE dw.DimCustomer DROP CONSTRAINT [{constraint_name}]")
        default_constraint = None

    if column_types["ValidFrom"][0] in ("date", "datetime"):
        cursor.execute("ALTER TABLE dw.DimCustomer ALTER COLUMN ValidFrom DATETIME2(7) NOT NULL")
    if column_types["ValidTo"][0] in ("date", "datetime"):
        cursor.execute("ALTER TABLE dw.DimCustomer ALTER COLUMN ValidTo DATETIME2(7) NOT NULL")

    expected_default = "9999-12-31T23:59:59.9999999"
    if default_constraint:
        normalized_definition = (
            default_constraint[1]
            .replace("(", "")
            .replace(")", "")
            .replace("'", "")
            .replace(" ", "")
        )
        if expected_default in normalized_definition:
            return
        constraint_name = default_constraint[0].replace("]", "]]")
        cursor.execute(f"ALTER TABLE dw.DimCustomer DROP CONSTRAINT [{constraint_name}]")

    cursor.execute("""
    ALTER TABLE dw.DimCustomer
        ADD CONSTRAINT DF_DimCustomer_ValidTo
        DEFAULT ('9999-12-31T23:59:59.9999999') FOR ValidTo
    """)


def _create_customer_indexes(cursor):
    cursor.execute("""
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dw.DimCustomer')
          AND name = 'UX_DimCustomer_CustomerID_ValidFrom'
    )
        CREATE UNIQUE NONCLUSTERED INDEX UX_DimCustomer_CustomerID_ValidFrom
            ON dw.DimCustomer(CustomerID, ValidFrom);
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dw.DimCustomer')
          AND name = 'UX_DimCustomer_Current'
    )
        CREATE UNIQUE NONCLUSTERED INDEX UX_DimCustomer_Current
            ON dw.DimCustomer(CustomerID)
            WHERE IsCurrent = 1;
    """)


def _create_geography_index(cursor):
    cursor.execute("""
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dw.DimGeography')
          AND name = 'UX_DimGeography_CityID'
    )
        CREATE UNIQUE NONCLUSTERED INDEX UX_DimGeography_CityID
            ON dw.DimGeography(CityID)
            WHERE CityID IS NOT NULL;
    """)


def _reassign_fact_customers(cursor):
    # OrderDate is date-only, so facts resolve at the start of that calendar day.
    temporal_match = """
        ON dimension.CustomerID = TRY_CONVERT(INT, orders.CustomerID)
       AND CONVERT(DATETIME2(7), TRY_CONVERT(DATE, orders.OrderDate)) >= dimension.ValidFrom
       AND CONVERT(DATETIME2(7), TRY_CONVERT(DATE, orders.OrderDate)) < dimension.ValidTo
    """
    _assert_no_rows(
        cursor,
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT facts.SalesFactKey
            FROM dw.FactSales facts
            LEFT JOIN staging_clean.Sales_Orders_clean orders
                ON TRY_CONVERT(INT, orders.OrderID) = facts.OrderID
            LEFT JOIN dw.DimCustomer dimension {temporal_match}
            GROUP BY facts.SalesFactKey
            HAVING COUNT(dimension.CustomerKey) <> 1
        ) AS unresolved
        """,
        "FactSales rows without exactly one customer version",
    )

    cursor.execute(f"""
    ;WITH resolved AS (
        SELECT facts.SalesFactKey, MIN(dimension.CustomerKey) AS CustomerKey
        FROM dw.FactSales facts
        JOIN staging_clean.Sales_Orders_clean orders
            ON TRY_CONVERT(INT, orders.OrderID) = facts.OrderID
        JOIN dw.DimCustomer dimension {temporal_match}
        GROUP BY facts.SalesFactKey
        HAVING COUNT(dimension.CustomerKey) = 1
    )
    UPDATE facts
    SET CustomerKey = resolved.CustomerKey
    FROM dw.FactSales facts
    JOIN resolved ON resolved.SalesFactKey = facts.SalesFactKey;
    """)
    reassigned_facts = cursor.rowcount

    cursor.execute("""
    UPDATE facts
    SET GeographyKey = customers.GeographyKey
    FROM dw.FactSales facts
    JOIN dw.DimCustomer customers ON customers.CustomerKey = facts.CustomerKey
    WHERE customers.GeographyKey IS NOT NULL
      AND facts.GeographyKey <> customers.GeographyKey;
    """)
    updated_geographies = cursor.rowcount

    _assert_no_rows(
        cursor,
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT facts.SalesFactKey, facts.CustomerKey
            FROM dw.FactSales facts
            LEFT JOIN staging_clean.Sales_Orders_clean orders
                ON TRY_CONVERT(INT, orders.OrderID) = facts.OrderID
            LEFT JOIN dw.DimCustomer dimension {temporal_match}
            GROUP BY facts.SalesFactKey, facts.CustomerKey
            HAVING COUNT(dimension.CustomerKey) <> 1
                OR MIN(dimension.CustomerKey) <> facts.CustomerKey
        ) AS mismatched
        """,
        "FactSales customer keys do not match their effective customer versions",
    )

    return reassigned_facts, updated_geographies


def run():
    connector = DatabaseConnector(SQL_SERVER_CONFIG)
    if not connector.connect():
        raise ConnectionError("Could not connect to SQL Server.")

    try:
        cursor = connector.connection.cursor()
        _migrate_schema(cursor)
        cursor.execute(CUSTOMER_SOURCE_SQL)
        cursor.execute("""
        SELECT COUNT(*)
        FROM #CustomerSource
        WHERE IsCurrent = 0 AND ValidFrom = ValidTo
        """)
        skipped_zero_duration_versions = cursor.fetchone()[0]
        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM #CustomerSource
            WHERE ValidFrom > ValidTo OR (IsCurrent = 1 AND ValidFrom = ValidTo)
            """,
            "Source customer history contains a reversed or empty current period",
        )
        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM (
                SELECT CustomerID, ValidFrom
                FROM #CustomerSource
                WHERE ValidFrom < ValidTo
                GROUP BY CustomerID, ValidFrom
                HAVING COUNT(*) > 1
            ) AS duplicate_periods
            """,
            "Source customer history contains duplicate version start times",
        )
        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM (
                SELECT ValidFrom,
                       LAG(ValidTo) OVER (
                           PARTITION BY CustomerID ORDER BY ValidFrom
                       ) AS PreviousValidTo
                FROM #CustomerSource
                WHERE ValidFrom < ValidTo
            ) AS periods
            WHERE PreviousValidTo > ValidFrom
            """,
            "Source customer history contains overlapping periods",
        )
        cursor.execute(GEOGRAPHY_SQL)
        _create_geography_index(cursor)
        cursor.execute(CUSTOMER_VERSIONS_SQL)

        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM (
                SELECT CustomerID
                FROM dw.DimCustomer
                WHERE IsCurrent = 1
                GROUP BY CustomerID
                HAVING COUNT(*) > 1
            ) AS duplicate_current
            """,
            "DimCustomer already has duplicate current versions",
        )

        cursor.execute(CURRENT_CUSTOMER_SQL)
        current_rows_updated = cursor.rowcount
        cursor.execute(HISTORICAL_CUSTOMER_SQL)
        historical_rows_updated = cursor.rowcount

        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM #CustomerVersions source
            WHERE NOT EXISTS (
                SELECT 1 FROM dw.DimCustomer dimension
                WHERE dimension.CustomerID = source.CustomerID
                  AND dimension.ValidFrom = source.ValidFrom
                  AND dimension.ValidTo = source.ValidTo
                  AND dimension.IsCurrent = source.IsCurrent
            )
            """,
            "Customer versions missing after load",
        )
        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM dw.DimCustomer dimension
            WHERE NOT EXISTS (
                SELECT 1 FROM #CustomerVersions source
                WHERE source.CustomerID = dimension.CustomerID
                  AND source.ValidFrom = dimension.ValidFrom
                  AND source.ValidTo = dimension.ValidTo
                  AND source.IsCurrent = dimension.IsCurrent
            )
            """,
            "DimCustomer contains versions absent from source history",
        )
        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM (
                SELECT CustomerID, ValidFrom,
                       LAG(ValidTo) OVER (
                           PARTITION BY CustomerID ORDER BY ValidFrom
                       ) AS PreviousValidTo
                FROM dw.DimCustomer
            ) AS periods
            WHERE PreviousValidTo > ValidFrom
            """,
            "DimCustomer contains overlapping version periods",
        )
        _assert_no_rows(
            cursor,
            """
            SELECT COUNT(*)
            FROM dw.DimCustomer customers
            LEFT JOIN dw.DimGeography geography
                ON geography.GeographyKey = customers.GeographyKey
            WHERE geography.GeographyKey IS NULL
            """,
            "DimCustomer contains an unmapped geography",
        )

        _create_customer_indexes(cursor)
        reassigned_facts, updated_geographies = _reassign_fact_customers(cursor)

        cursor.execute("""
        SELECT
            COUNT(*) AS TotalVersions,
            SUM(CASE WHEN IsCurrent = 1 THEN 1 ELSE 0 END) AS CurrentVersions,
            SUM(CASE WHEN IsCurrent = 0 THEN 1 ELSE 0 END) AS HistoricalVersions
        FROM dw.DimCustomer
        """)
        total_versions, current_versions, historical_versions = cursor.fetchone()
        connector.connection.commit()

        print(
            "DimCustomer SCD2 loaded: "
            f"{total_versions} total, {current_versions} current, "
            f"{historical_versions} historical."
        )
        print(f"Zero-duration source history rows skipped: {skipped_zero_duration_versions}.")
        print(
            f"Current versions updated: {current_rows_updated}; "
            f"historical versions updated: {historical_rows_updated}."
        )
        print(
            f"FactSales customer keys resolved: {reassigned_facts}; "
            f"geography keys updated: {updated_geographies}."
        )
    except Exception:
        connector.connection.rollback()
        raise
    finally:
        connector.disconnect()


if __name__ == "__main__":
    run()

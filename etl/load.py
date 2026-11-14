"""
ETL Load Module
Loads cleaned data into staging layers and dimensional warehouse
"""
import pyodbc
import pandas as pd
from typing import Dict, Any, List
import logging
from etl.config import SQL_SERVER_CONFIG, STAGING_RAW_SCHEMA, STAGING_CLEAN_SCHEMA

logger = logging.getLogger(__name__)


class StaginLoader:
    """Handles loading data to staging layers"""

    def __init__(self, connector):
        self.connector = connector

    def create_staging_schemas(self) -> bool:
        """Create staging schemas if they don't exist"""
        schemas = [STAGING_RAW_SCHEMA, STAGING_CLEAN_SCHEMA]
        for schema in schemas:
            sql = f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') CREATE SCHEMA {schema}"
            if self.connector.execute_script(sql):
                logger.info(f"✓ Schema {schema} ready")
            else:
                logger.error(f"✗ Failed to create schema {schema}")
                return False
        return True

    def load_to_staging_raw(self, extracted: Dict[str, pd.DataFrame]) -> bool:
        """Load extracted data to staging_raw (exact copy)"""
        logger.info(f"\n=== LOADING TO STAGING RAW ===")

        cursor = self.connector.connection.cursor()
        for table_name, df in extracted.items():
            try:
                # Create table in staging_raw
                schema, table = table_name.split(".")
                staging_table = f"{STAGING_RAW_SCHEMA}.{schema}_{table}"

                # Drop if exists
                drop_sql = f"DROP TABLE IF EXISTS {staging_table}"
                cursor.execute(drop_sql)

                # Create table from DataFrame
                # Build CREATE TABLE statement
                create_sql = self._generate_create_table_sql(staging_table, df)
                cursor.execute(create_sql)

                # Insert data
                insert_sql = self._generate_insert_sql(staging_table, df)
                cursor.execute(insert_sql, [tuple(row) for row in df.itertuples(index=False)])

                self.connector.connection.commit()
                logger.info(f"✓ Loaded {len(df)} rows to {staging_table}")

            except Exception as e:
                self.connector.connection.rollback()
                logger.error(f"✗ Error loading {table_name}: {e}")
                return False
            finally:
                cursor.close()

        return True

    def load_to_staging_clean(self, cleaned: Dict[str, pd.DataFrame]) -> bool:
        """Load cleaned data to staging_clean"""
        logger.info(f"\n=== LOADING TO STAGING CLEAN ===")

        cursor = self.connector.connection.cursor()
        for table_name, df in cleaned.items():
            try:
                schema, table = table_name.split(".")
                staging_table = f"{STAGING_CLEAN_SCHEMA}.{schema}_{table}"

                # Drop if exists
                drop_sql = f"DROP TABLE IF EXISTS {staging_table}"
                cursor.execute(drop_sql)

                # Create table from DataFrame
                create_sql = self._generate_create_table_sql(staging_table, df)
                cursor.execute(create_sql)

                # Insert data
                insert_sql = self._generate_insert_sql(staging_table, df)
                cursor.execute(insert_sql, [tuple(row) for row in df.itertuples(index=False)])

                self.connector.connection.commit()
                logger.info(f"✓ Loaded {len(df)} rows to {staging_table}")

            except Exception as e:
                self.connector.connection.rollback()
                logger.error(f"✗ Error loading {table_name}: {e}")
                return False
            finally:
                cursor.close()

        return True

    @staticmethod
    def _generate_create_table_sql(table_name: str, df: pd.DataFrame) -> str:
        """Generate CREATE TABLE statement from DataFrame"""
        columns = []
        for col, dtype in zip(df.columns, df.dtypes):
            if dtype == "object":
                sql_type = "VARCHAR(MAX)"
            elif dtype == "int64":
                sql_type = "BIGINT"
            elif dtype == "float64":
                sql_type = "FLOAT"
            elif dtype == "bool":
                sql_type = "BIT"
            elif "datetime" in str(dtype):
                sql_type = "DATETIME2"
            else:
                sql_type = "VARCHAR(MAX)"

            columns.append(f"[{col}] {sql_type}")

        create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
        return create_sql

    @staticmethod
    def _generate_insert_sql(table_name: str, df: pd.DataFrame) -> str:
        """Generate INSERT statement"""
        columns = [f"[{col}]" for col in df.columns]
        placeholders = ", ".join(["?" for _ in df.columns])
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        return insert_sql


class AuditLogger:
    """Logs ETL audit trail"""

    def __init__(self, connector):
        self.connector = connector

    def create_audit_table(self) -> bool:
        """Create ETL audit log table"""
        sql = """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'etl_audit_log')
        CREATE TABLE [dbo].[etl_audit_log] (
            [AuditID] BIGINT PRIMARY KEY IDENTITY(1,1),
            [ETLDate] DATETIME2 DEFAULT GETDATE(),
            [Phase] VARCHAR(100),
            [TableName] VARCHAR(200),
            [RowCount] BIGINT,
            [Status] VARCHAR(50),
            [ErrorMessage] VARCHAR(MAX),
            [Duration_Seconds] INT
        )
        """
        return self.connector.execute_script(sql)

    def log_load(self, phase: str, table_name: str, row_count: int, status: str, duration: int, error: str = None):
        """Log ETL operation"""
        cursor = self.connector.connection.cursor()
        try:
            sql = """
            INSERT INTO [dbo].[etl_audit_log] 
            ([Phase], [TableName], [RowCount], [Status], [ErrorMessage], [Duration_Seconds])
            VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (phase, table_name, row_count, status, error, duration))
            self.connector.connection.commit()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")
        finally:
            cursor.close()


def load_phase(extracted: Dict[str, pd.DataFrame], cleaned: Dict[str, pd.DataFrame], connector) -> bool:
    """Main load phase"""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3.3: LOAD - Writing to Staging Layers")
    logger.info("=" * 60)

    loader = StaginLoader(connector)
    audit = AuditLogger(connector)

    # Create schemas
    if not loader.create_staging_schemas():
        logger.error("Failed to create staging schemas")
        return False

    # Create audit table
    audit.create_audit_table()

    # Load to staging_raw
    if not loader.load_to_staging_raw(extracted):
        logger.error("Failed to load to staging_raw")
        return False

    # Load to staging_clean
    if not loader.load_to_staging_clean(cleaned):
        logger.error("Failed to load to staging_clean")
        return False

    logger.info(f"\n✓ Load phase complete")
    return True


if __name__ == "__main__":
    print("Load module loaded. Use in conjunction with extract.py and transform.py")

"""
ETL Extract Module
Connects to WideWorldImporters and extracts data into staging_raw layer
"""
import pyodbc
import pandas as pd
from typing import List, Dict, Any
import logging
from etl.config import (
    SQL_SERVER_CONFIG,
    SOURCE_DATABASE,
    SOURCE_TABLES,
    STAGING_RAW_SCHEMA,
    BATCH_SIZE,
    MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class DatabaseConnector:
    """Manages connections to SQL Server"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None

    def connect(self) -> bool:
        """Establish connection to SQL Server"""
        try:
            connection_string = (
                f"DRIVER={self.config['driver']};"
                f"SERVER={self.config['server']};"
                f"DATABASE={self.config['database']};"
                f"UID={self.config['user']};"
                f"PWD={self.config['password']};"
                f"Encrypt={self.config['encrypt']};"
                f"TrustServerCertificate={self.config['trust_certificate']};"
            )
            self.connection = pyodbc.connect(connection_string)
            logger.info(f"✓ Connected to {self.config['server']}")
            return True
        except pyodbc.Error as e:
            logger.error(f"✗ Connection failed: {e}")
            return False

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SELECT query and return DataFrame"""
        if not self.connection:
            logger.warning("No active connection. Attempting to reconnect...")
            self.connect()

        try:
            df = pd.read_sql(query, self.connection)
            logger.info(f"✓ Query executed: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"✗ Query failed: {e}")
            raise

    def execute_script(self, script: str) -> bool:
        """Execute DDL/DML script"""
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        try:
            cursor.execute(script)
            self.connection.commit()
            logger.info("✓ Script executed successfully")
            return True
        except Exception as e:
            self.connection.rollback()
            logger.error(f"✗ Script failed: {e}")
            return False
        finally:
            cursor.close()

    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
            logger.info("✓ Connection closed")


class DataExtractor:
    """Extracts data from WideWorldImporters"""

    def __init__(self, connector: DatabaseConnector):
        self.connector = connector
        self.extracted_tables: Dict[str, pd.DataFrame] = {}

    def extract_table(self, table_name: str, schema: str = "dbo") -> pd.DataFrame:
        """Extract single table with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                query = f"SELECT * FROM [{schema}].[{table_name}]"
                df = self.connector.execute_query(query)
                self.extracted_tables[table_name] = df
                logger.info(
                    f"✓ Extracted [{schema}].[{table_name}]: {len(df)} rows, {len(df.columns)} columns"
                )
                return df
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"✗ Failed to extract {table_name} after {MAX_RETRIES} attempts")
                    raise

    def extract_all_sources(self) -> Dict[str, pd.DataFrame]:
        """Extract all source tables"""
        extracted = {}
        for full_table_name in SOURCE_TABLES:
            schema, table = full_table_name.split(".")
            try:
                df = self.extract_table(table, schema)
                extracted[full_table_name] = df
            except Exception as e:
                logger.error(f"Skipping {full_table_name}: {e}")

        logger.info(f"\n=== EXTRACTION SUMMARY ===")
        logger.info(f"Successfully extracted: {len(extracted)}/{len(SOURCE_TABLES)} tables")
        for table_name, df in extracted.items():
            logger.info(f"  - {table_name}: {len(df)} rows")

        return extracted

    def validate_extraction(self, extracted: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate extracted data quality"""
        validation_report = {}

        for table_name, df in extracted.items():
            report = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "memory_mb": df.memory_usage(deep=True).sum() / 1024 ** 2,
                "null_count": df.isnull().sum().to_dict(),
                "duplicates": df.duplicated().sum(),
            }
            validation_report[table_name] = report
            logger.info(
                f"  {table_name}: {report['row_count']} rows, "
                f"{report['duplicates']} duplicates, "
                f"{report['memory_mb']:.2f} MB"
            )

        return validation_report


def extract_phase(config: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Main extraction phase"""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3.1: EXTRACT - Loading from WideWorldImporters")
    logger.info("=" * 60)

    connector = DatabaseConnector(config)
    if not connector.connect():
        raise ConnectionError("Failed to connect to database")

    extractor = DataExtractor(connector)
    extracted_data = extractor.extract_all_sources()

    # Validate extraction
    validation = extractor.validate_extraction(extracted_data)
    logger.info(f"\n✓ Extraction complete: {len(extracted_data)} tables extracted")

    connector.close()
    return extracted_data


if __name__ == "__main__":
    extract_phase(SQL_SERVER_CONFIG)

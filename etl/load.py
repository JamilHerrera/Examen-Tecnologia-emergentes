"""
ETL Load Module
Loads cleaned data into staging layers
Phase 3.3 Implementation
"""

import pandas as pd
from typing import Dict
import time
import logging
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class StagingLoader:
    """Handles loading data to staging layers"""
    
    def __init__(self, connector):
        self.connector = connector
        self.load_stats = {}
    
    def create_staging_schemas(self) -> bool:
        """Create staging schemas if they don't exist"""
        logger.info("  Creando schemas de staging...")
        
        schemas = ["staging_raw", "staging_clean"]
        cursor = self.connector.connection.cursor()
        
        try:
            for schema in schemas:
                try:
                    # Check if schema exists
                    check_sql = f"SELECT name FROM sys.schemas WHERE name = '{schema}'"
                    cursor.execute(check_sql)
                    result = cursor.fetchone()
                    
                    if not result:
                        # Schema doesn't exist, create it
                        create_sql = f"CREATE SCHEMA [{schema}]"
                        cursor.execute(create_sql)
                        self.connector.connection.commit()
                        logger.info(f"    ✓ Schema '{schema}' creado")
                    else:
                        logger.info(f"    ✓ Schema '{schema}' ya existe")
                        
                except Exception as e:
                    logger.error(f"    ✗ Error creando schema {schema}: {str(e)}")
                    self.connector.connection.rollback()
                    return False
            
            return True
        finally:
            cursor.close()

    def _insert_rows(self, cursor, table_name, layer, target_table, df, start_time):
        col_names = ', '.join([f"[{col}]" for col in df.columns])
        rows_inserted = 0
        failed_rows = 0
        error_examples = []

        for idx, row in df.iterrows():
            try:
                placeholders = ', '.join(['?' for _ in row])
                insert_sql = f"INSERT INTO {target_table} ({col_names}) VALUES ({placeholders})"
                row_values = tuple(None if pd.isna(value) else value for value in row)
                cursor.execute(insert_sql, row_values)
            except Exception as exc:
                failed_rows += 1
                if len(error_examples) < 5:
                    error_examples.append(f"row {idx}: {exc}")
                continue

            rows_inserted += 1
            if rows_inserted % 5000 == 0:
                self.connector.connection.commit()

        self.connector.connection.commit()
        elapsed = time.time() - start_time
        stats_key = f"{table_name}_clean" if layer == "staging_clean" else table_name
        self.load_stats[stats_key] = {
            "expected_rows": len(df),
            "rows": rows_inserted,
            "failed_rows": failed_rows,
            "success": failed_rows == 0,
            "target": target_table,
            "time": elapsed,
            "layer": layer,
        }

        if failed_rows:
            logger.error(
                "    ✗ %s: %s/%s filas fallidas en %s; ejemplos: %s",
                table_name,
                failed_rows,
                len(df),
                target_table,
                "; ".join(error_examples),
            )
            return False

        logger.info(
            "    ✓ %s: %s/%s filas → %s (%.2fs)",
            table_name,
            rows_inserted,
            len(df),
            target_table,
            elapsed,
        )
        return True
    
    def load_to_staging_raw(self, extracted: Dict[str, pd.DataFrame]) -> bool:
        """Load extracted data to staging_raw (exact copy)"""
        logger.info("\n  Cargando datos a staging_raw...")
        
        cursor = self.connector.connection.cursor()
        
        try:
            for table_name, df in extracted.items():
                try:
                    start_time = time.time()
                    
                    # Clean column names
                    df_copy = df.copy()
                    df_copy.columns = [col.replace(' ', '_').replace('.', '_') for col in df_copy.columns]
                    
                    # Add LoadedAt timestamp
                    df_copy['LoadedAt'] = pd.Timestamp.now()
                    
                    # Target table name
                    target_table = f"[staging_raw].[{table_name}_raw]"
                    
                    # Drop if exists
                    drop_sql = f"DROP TABLE IF EXISTS {target_table}"
                    cursor.execute(drop_sql)
                    self.connector.connection.commit()
                    
                    # Generate CREATE TABLE statement
                    columns_sql = []
                    for col in df_copy.columns:
                        col_name = f"[{col}]"
                        col_type = "NVARCHAR(MAX)"
                        columns_sql.append(f"{col_name} {col_type} NULL")
                    
                    create_sql = f"CREATE TABLE {target_table} ({', '.join(columns_sql)})"
                    cursor.execute(create_sql)
                    self.connector.connection.commit()
                    
                    if not self._insert_rows(
                        cursor, table_name, "staging_raw", target_table, df_copy, start_time
                    ):
                        return False
                    
                except Exception as e:
                    self.connector.connection.rollback()
                    logger.error(f"    ✗ Error loading {table_name} to staging_raw: {str(e)}")
                    return False
            
            return True
            
        finally:
            cursor.close()
    
    def load_to_staging_clean(self, cleaned: Dict[str, pd.DataFrame]) -> bool:
        """Load cleaned data to staging_clean"""
        logger.info("\n  Cargando datos a staging_clean...")
        
        cursor = self.connector.connection.cursor()
        
        try:
            for table_name, df in cleaned.items():
                try:
                    start_time = time.time()
                    
                    # Clean column names
                    df_copy = df.copy()
                    df_copy.columns = [col.replace(' ', '_').replace('.', '_') for col in df_copy.columns]
                    
                    # Add metadata columns
                    df_copy['QualityFlag'] = 'VALID'
                    df_copy['LoadedAt'] = pd.Timestamp.now()
                    
                    # Target table name
                    target_table = f"[staging_clean].[{table_name}_clean]"
                    
                    # Drop if exists
                    drop_sql = f"DROP TABLE IF EXISTS {target_table}"
                    cursor.execute(drop_sql)
                    self.connector.connection.commit()
                    
                    # Generate CREATE TABLE statement
                    columns_sql = []
                    for col in df_copy.columns:
                        col_name = f"[{col}]"
                        if col == 'QualityFlag':
                            col_type = "VARCHAR(50)"
                        else:
                            col_type = "NVARCHAR(MAX)"
                        columns_sql.append(f"{col_name} {col_type} NULL")
                    
                    create_sql = f"CREATE TABLE {target_table} ({', '.join(columns_sql)})"
                    cursor.execute(create_sql)
                    self.connector.connection.commit()
                    
                    if not self._insert_rows(
                        cursor, table_name, "staging_clean", target_table, df_copy, start_time
                    ):
                        return False
                    
                except Exception as e:
                    self.connector.connection.rollback()
                    logger.error(f"    ✗ Error loading {table_name} to staging_clean: {str(e)}")
                    return False
            
            return True
            
        finally:
            cursor.close()


def load_phase(
    extracted: Dict[str, pd.DataFrame],
    cleaned: Dict[str, pd.DataFrame],
    connector,
    mode="full",
    run_id=None,
    metadata=None,
    rejected_rows=None,
    profiles=None,
    stats_out=None,
) -> bool:
    """
    Execute FASE 3.3: LOAD
    Loads extracted and cleaned data to staging layers
    
    Args:
        extracted: Dictionary of extracted DataFrames
        cleaned: Dictionary of cleaned DataFrames
        connector: DatabaseConnector instance
        mode: Requested full or incremental load mode
        run_id: Operational execution identifier
        metadata: Per-table extraction and watermark metadata
        rejected_rows: Rows rejected by transformation rules
        profiles: Raw and clean profiles keyed by source table
        stats_out: Optional dictionary populated with committed per-layer counts
    
    Returns:
        True if successful, False otherwise
    """
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 FASE 3.3: CARGA A STAGING")
    logger.info("=" * 80)
    
    start_time = time.time()

    try:
        from etl.reliable_load import load_reliably

        succeeded, stats = load_reliably(
            extracted,
            cleaned,
            connector,
            mode,
            run_id,
            metadata or {},
            rejected_rows or [],
            profiles or {},
        )
        if not succeeded:
            return False

        if stats_out is not None:
            stats_out.update(stats)

        elapsed = time.time() - start_time
        logger.info("\n" + "-" * 80)
        logger.info(f"✅ CARGA COMPLETADA en {elapsed:.2f}s")
        logger.info(f"   ✓ Tablas cargadas a staging_raw: {len(extracted)}")
        logger.info(f"   ✓ Tablas cargadas a staging_clean: {len(cleaned)}")
        logger.info(
            "   ✓ Filas leidas: %s | insertadas: %s | actualizadas: %s | rechazadas: %s | eliminadas: %s",
            sum(item.get("row_count", 0) for item in (metadata or {}).values()),
            sum(item["inserted"] for item in stats.values()),
            sum(item["updated"] for item in stats.values()),
            len(rejected_rows or []),
            sum(item["deleted"] for item in stats.values()),
        )
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en Fase 3.3: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Load module loaded. Use in conjunction with extract.py and transform.py")


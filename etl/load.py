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
                    
                    # Prepare insert data row by row
                    col_names = ', '.join([f"[{col}]" for col in df_copy.columns])
                    insert_template = f"INSERT INTO {target_table} ({col_names}) VALUES (?, ?, "
                    
                    rows_inserted = 0
                    for idx, row in df_copy.iterrows():
                        try:
                            # Create placeholders for the row
                            placeholders = ', '.join(['?' for _ in row])
                            insert_sql = f"INSERT INTO {target_table} ({col_names}) VALUES ({placeholders})"
                            
                            # Convert row to list and handle None values
                            row_values = tuple(None if pd.isna(v) else v for v in row)
                            
                            cursor.execute(insert_sql, row_values)
                            rows_inserted += 1
                            
                            # Commit every 5000 rows
                            if rows_inserted % 5000 == 0:
                                self.connector.connection.commit()
                        except Exception as e:
                            logger.warning(f"    ⚠ Error in row {idx}: {str(e)}")
                            continue
                    
                    self.connector.connection.commit()
                    
                    elapsed = time.time() - start_time
                    self.load_stats[table_name] = {
                        "rows": rows_inserted,
                        "target": target_table,
                        "time": elapsed,
                        "layer": "staging_raw"
                    }
                    
                    logger.info(f"    ✓ {table_name}: {rows_inserted:,}/{len(df):,} filas → {target_table} ({elapsed:.2f}s)")
                    
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
                    
                    # Prepare insert data row by row
                    col_names = ', '.join([f"[{col}]" for col in df_copy.columns])
                    
                    rows_inserted = 0
                    for idx, row in df_copy.iterrows():
                        try:
                            # Create placeholders for the row
                            placeholders = ', '.join(['?' for _ in row])
                            insert_sql = f"INSERT INTO {target_table} ({col_names}) VALUES ({placeholders})"
                            
                            # Convert row to list and handle None values
                            row_values = tuple(None if pd.isna(v) else v for v in row)
                            
                            cursor.execute(insert_sql, row_values)
                            rows_inserted += 1
                            
                            # Commit every 5000 rows
                            if rows_inserted % 5000 == 0:
                                self.connector.connection.commit()
                        except Exception as e:
                            logger.warning(f"    ⚠ Error in row {idx}: {str(e)}")
                            continue
                    
                    self.connector.connection.commit()
                    
                    elapsed = time.time() - start_time
                    self.load_stats[f"{table_name}_clean"] = {
                        "rows": rows_inserted,
                        "target": target_table,
                        "time": elapsed,
                        "layer": "staging_clean"
                    }
                    
                    logger.info(f"    ✓ {table_name}: {rows_inserted:,}/{len(df):,} filas → {target_table} ({elapsed:.2f}s)")
                    
                except Exception as e:
                    self.connector.connection.rollback()
                    logger.error(f"    ✗ Error loading {table_name} to staging_clean: {str(e)}")
                    return False
            
            return True
            
        finally:
            cursor.close()


def load_phase(extracted: Dict[str, pd.DataFrame], cleaned: Dict[str, pd.DataFrame], connector) -> bool:
    """
    Execute FASE 3.3: LOAD
    Loads extracted and cleaned data to staging layers
    
    Args:
        extracted: Dictionary of extracted DataFrames
        cleaned: Dictionary of cleaned DataFrames
        connector: DatabaseConnector instance
    
    Returns:
        True if successful, False otherwise
    """
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 FASE 3.3: CARGA A STAGING")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    loader = StagingLoader(connector)
    
    try:
        # Create staging schemas
        if not loader.create_staging_schemas():
            logger.error("❌ Falló crear schemas de staging")
            return False
        
        # Load to staging_raw
        if not loader.load_to_staging_raw(extracted):
            logger.error("❌ Falló cargar a staging_raw")
            return False
        
        # Load to staging_clean
        if not loader.load_to_staging_clean(cleaned):
            logger.error("❌ Falló cargar a staging_clean")
            return False
        
        elapsed = time.time() - start_time
        
        # Summary
        logger.info("\n" + "-" * 80)
        logger.info(f"✅ CARGA COMPLETADA en {elapsed:.2f}s")
        logger.info(f"   ✓ Tablas cargadas a staging_raw: {len(extracted)}")
        logger.info(f"   ✓ Tablas cargadas a staging_clean: {len(cleaned)}")
        logger.info(f"   ✓ Filas totales: {sum(len(df) for df in extracted.values()):,}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en Fase 3.3: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Load module loaded. Use in conjunction with extract.py and transform.py")


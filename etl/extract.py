"""
FASE 3.1: EXTRACT
Extract data from WideWorldImporters source database into staging_raw layer
"""

import pyodbc
import pandas as pd
from typing import Dict, List, Optional, Tuple
import time
from datetime import datetime, timedelta
from etl.config import SQL_SERVER_CONFIG, SOURCE_DATABASE, SOURCE_TABLES, logger
from etl.config import SOURCE_TABLE_METADATA, ETL_OVERLAP_SECONDS
from etl.reliability import read_watermark


class DatabaseConnector:
    """Manages database connections to SQL Server"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.connection = None
        self.cursor = None
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            conn_str = (
                f"DRIVER={{{self.config['driver']}}};"
                f"SERVER={self.config['server']};"
                f"DATABASE={self.config['database']};"
                f"UID={self.config['user']};"
                f"PWD={self.config['password']};"
            )
            self.connection = pyodbc.connect(conn_str, timeout=30)
            self.cursor = self.connection.cursor()
            logger.info(f"✓ Connected to {self.config['server']} | Database: {self.config['database']}")
            return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("✓ Disconnected from database")
        except Exception as e:
            logger.error(f"✗ Disconnect failed: {str(e)}")
    
    def execute_query(self, query: str, params=None) -> Optional[pd.DataFrame]:
        """Execute SELECT query and return DataFrame"""
        try:
            df = pd.read_sql(query, self.connection, params=params)
            return df
        except Exception as e:
            logger.error(f"✗ Query execution failed: {str(e)}")
            raise
    
    def get_row_count(self, table: str) -> int:
        """Get row count for a table"""
        try:
            query = f"SELECT COUNT(*) as cnt FROM [{table.split('.')[0]}].[{table.split('.')[1]}]"
            result = self.execute_query(query)
            return int(result['cnt'].iloc[0]) if result is not None and len(result) > 0 else 0
        except Exception as e:
            logger.error(f"✗ Row count failed for {table}: {str(e)}")
            raise


class DataExtractor:
    """Extracts data from WideWorldImporters source tables"""
    
    def __init__(self, connector: DatabaseConnector):
        self.connector = connector
        self.extracted_data: Dict[str, pd.DataFrame] = {}
        self.extraction_metadata: Dict[str, Dict] = {}
        self.extraction_errors: List[Dict] = []
    
    def extract_table(self, source_table: str, target_name: str, mode="full") -> Optional[pd.DataFrame]:
        """
        Extract single table from source
        
        Args:
            source_table: Source table name (e.g., "Sales.Orders")
            target_name: Target table name for staging (e.g., "Sales_Orders")
        
        Returns:
            DataFrame with extracted data, or None on error
        """
        try:
            start_time = time.time()
            logger.info(f"  Extracting [{source_table}]...")
            
            schema, table = source_table.split(".")
            source_meta = SOURCE_TABLE_METADATA[source_table]
            cursor = self.connector.connection.cursor()
            cursor.execute(
                "SELECT name FROM sys.columns WHERE object_id = OBJECT_ID(?)",
                source_table,
            )
            source_columns = {row[0] for row in cursor.fetchall()}
            watermark_column = source_meta["watermark"]
            if source_meta["key"] not in source_columns or watermark_column not in source_columns:
                raise RuntimeError(
                    f"{source_table} no contiene la clave {source_meta['key']} "
                    f"o la columna de watermark {watermark_column}."
                )

            effective_mode = mode
            previous_column = None
            previous_watermark = None
            overlap_seconds = ETL_OVERLAP_SECONDS
            if mode == "incremental":
                previous_column, previous_watermark, overlap_seconds = read_watermark(
                    cursor, source_table
                )
                if previous_watermark is None:
                    effective_mode = "full"
                    logger.info("  Sin watermark para %s; se ejecuta carga inicial completa.", source_table)
            watermark_start = (
                previous_watermark - timedelta(seconds=overlap_seconds)
                if effective_mode == "incremental"
                else None
            )

            query = (
                f"SELECT * FROM [{schema}].[{table}]"
                + (f" WHERE [{watermark_column}] >= ?" if watermark_start is not None else "")
            )
            df = self.connector.execute_query(
                query,
                [watermark_start] if watermark_start is not None else None,
            )
            
            if df is None:
                logger.warning(f"  ⚠ Query returned None for {source_table}")
                self.extraction_errors.append({
                    "table": source_table,
                    "error": "Query returned None",
                    "timestamp": datetime.now()
                })
                return None
            
            if len(df) == 0 and effective_mode != "incremental":
                logger.warning(f"  ⚠ No data extracted from {source_table}")
                self.extraction_errors.append({
                    "table": source_table,
                    "error": "Empty result set",
                    "timestamp": datetime.now()
                })
                return None
            
            elapsed = time.time() - start_time
            row_count = len(df)
            col_count = len(df.columns)
            
            # Store extracted data
            self.extracted_data[target_name] = df
            
            watermark_end = None
            if watermark_column in df.columns and not df.empty:
                watermark_end = pd.to_datetime(df[watermark_column], errors="coerce").max()
                if pd.isna(watermark_end):
                    watermark_end = None
                elif hasattr(watermark_end, "to_pydatetime"):
                    watermark_end = watermark_end.to_pydatetime()
            if previous_watermark is not None and (
                watermark_end is None or watermark_end < previous_watermark
            ):
                watermark_end = previous_watermark

            # Store metadata
            self.extraction_metadata[target_name] = {
                "source_table": source_table,
                "target_name": target_name,
                "key_column": source_meta["key"],
                "watermark_column": watermark_column,
                "watermark_start": watermark_start,
                "watermark_end": watermark_end,
                "overlap_seconds": overlap_seconds,
                "mode": effective_mode,
                "row_count": row_count,
                "column_count": col_count,
                "columns": list(df.columns),
                "extraction_time": elapsed,
                "extraction_timestamp": datetime.now()
            }
            
            logger.info(f"  ✓ {source_table}: {row_count:,} rows | {col_count} cols | {elapsed:.2f}s")
            return df
            
        except Exception as e:
            logger.error(f"  ✗ Extraction failed for {source_table}: {str(e)}")
            self.extraction_errors.append({
                "table": source_table,
                "error": str(e),
                "timestamp": datetime.now()
            })
            return None
    
    def extract_all_sources(self, mode="full") -> Dict[str, pd.DataFrame]:
        """Extract all source tables"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 INICIANDO FASE 3.1: EXTRACCIÓN")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        logger.info(f"\nExtrayendo {len(SOURCE_TABLES)} tablas de {SOURCE_DATABASE}...")
        logger.info("-" * 80)
        
        for table_mapping in SOURCE_TABLES:
            source = table_mapping
            target = table_mapping.replace(".", "_")
            self.extract_table(source, target, mode)
        
        elapsed = time.time() - start_time
        
        logger.info("-" * 80)
        logger.info(f"✅ EXTRACCIÓN COMPLETADA en {elapsed:.1f}s")
        logger.info(f"   ✓ Tablas extraídas: {len(self.extracted_data)}/{len(SOURCE_TABLES)}")
        logger.info(f"   ✓ Filas totales: {sum(len(df) for df in self.extracted_data.values()):,}")
        logger.info(f"   ⚠ Errores: {len(self.extraction_errors)}")
        logger.info("=" * 80)
        
        return self.extracted_data
    
    def validate_extraction(self) -> bool:
        """Validate extracted data"""
        logger.info("\n🔍 Validando extracción...")
        logger.info("-" * 80)
        
        all_valid = (
            len(self.extraction_metadata) == len(SOURCE_TABLES)
            and not self.extraction_errors
        )
        
        for target_name in sorted(self.extraction_metadata.keys()):
            meta = self.extraction_metadata[target_name]
            df = self.extracted_data.get(target_name)
            
            if df is None or (df.empty and meta["mode"] != "incremental"):
                logger.warning(f"  ⚠ {meta['source_table']}: Empty or None")
                all_valid = False
            elif df.empty:
                logger.info(f"  ✓ {meta['source_table']}: sin cambios desde el watermark")
            else:
                # Check for nulls
                null_counts = df.isnull().sum()
                total_cells = len(df) * len(df.columns)
                null_cells = null_counts.sum()
                null_percentage = (null_cells / total_cells * 100) if total_cells > 0 else 0
                
                logger.info(f"  ✓ {meta['source_table']:30s} | {len(df):>8,} rows | Nulls: {null_percentage:>5.2f}%")
        
        logger.info("-" * 80)
        logger.info(f"✅ Validación completada - Tablas válidas: {len(self.extracted_data)}")
        
        return all_valid
    
    def get_extraction_report(self) -> str:
        """Generate extraction summary report"""
        report = "\n" + "=" * 80
        report += "\n📋 EXTRACTION REPORT\n"
        report += "=" * 80 + "\n"
        
        total_rows = 0
        total_time = 0
        
        for target_name in sorted(self.extraction_metadata.keys()):
            meta = self.extraction_metadata[target_name]
            report += f"\n{meta['source_table']:35s}\n"
            report += f"  Rows:      {meta['row_count']:>15,}\n"
            report += f"  Columns:   {meta['column_count']:>15}\n"
            report += f"  Time:      {meta['extraction_time']:>15.2f}s\n"
            
            total_rows += meta['row_count']
            total_time += meta['extraction_time']
        
        report += "\n" + "-" * 80 + "\n"
        report += f"Total Rows Extracted: {total_rows:,}\n"
        report += f"Total Extraction Time: {total_time:.2f}s\n"
        average_time = total_time / len(self.extraction_metadata) if self.extraction_metadata else 0
        report += f"Average Time/Table: {average_time:.2f}s\n"
        report += "=" * 80 + "\n"
        
        if self.extraction_errors:
            report += f"\n⚠ EXTRACTION ERRORS ({len(self.extraction_errors)}):\n"
            report += "-" * 80 + "\n"
            for error in self.extraction_errors:
                report += f"  • {error['table']}: {error['error']}\n"
            report += "=" * 80 + "\n"
        
        return report


# ============================================================================
# EXTRACTION ORCHESTRATION FUNCTION
# ============================================================================

def extract_phase(mode="incremental") -> Tuple[Dict[str, pd.DataFrame], Dict[str, Dict]]:
    """
    Execute FASE 3.1: EXTRACT
    Orchestrates extraction of all source tables from WideWorldImporters
    
    Returns:
        Tuple containing extracted DataFrames and per-table extraction metadata.
    """
    connector = DatabaseConnector(SQL_SERVER_CONFIG)
    
    if not connector.connect():
        raise RuntimeError("No se pudo conectar a la base de datos de origen.")
    
    extractor = DataExtractor(connector)
    try:
        extracted_data = extractor.extract_all_sources(mode)
        is_valid = extractor.validate_extraction()
        print(extractor.get_extraction_report())
    finally:
        connector.disconnect()
    
    if not is_valid:
        errors = "; ".join(
            f"{item['table']}: {item['error']}" for item in extractor.extraction_errors
        )
        raise RuntimeError(
            "La extracción está incompleta o no es válida."
            + (f" Detalles: {errors}" if errors else "")
        )
    
    logger.info("✅ FASE 3.1 COMPLETADA - Datos listos para transformación")
    
    return extracted_data, extractor.extraction_metadata


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    extracted_data = extract_phase()

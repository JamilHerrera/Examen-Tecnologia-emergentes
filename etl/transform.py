"""
ETL Transform Module
Implements data cleaning, validation, and transformations for Phase 3.2
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class DataCleaner:
    """Handles data quality and transformations"""
    
    def clean_sales_orders(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean Sales.Orders table"""
        df = df.copy()
        logger.info(f"  Cleaning Sales.Orders: {len(df)} rows input")
        
        # Convert date columns
        date_columns = ["OrderDate", "PickingCompletedWhen", "LastEditedWhen"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        # Remove rows with null OrderDate (critical field)
        rows_before = len(df)
        df = df.dropna(subset=["OrderDate"])
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with null OrderDate")
        
        # Convert numeric columns
        numeric_cols = [col for col in df.columns if col.endswith("ID") or "Amount" in col or "Price" in col]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        logger.info(f"  ✓ Cleaned Sales.Orders: {len(df)} rows output")
        return df
    
    def clean_sales_order_lines(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean Sales.OrderLines table"""
        df = df.copy()
        logger.info(f"  Cleaning Sales.OrderLines: {len(df)} rows input")
        
        # Convert numeric columns (OrderLines has Quantity, UnitPrice, TaxRate - no LineTotal)
        numeric_cols = ["Quantity", "UnitPrice", "TaxRate"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Remove rows with null critical fields
        rows_before = len(df)
        df = df.dropna(subset=["Quantity", "UnitPrice"])
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with null quantities/prices")
        
        # Remove negative quantities
        rows_before = len(df)
        df = df[df["Quantity"] > 0] if "Quantity" in df.columns else df
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with negative quantities")
        
        # Convert dates
        if "LastEditedWhen" in df.columns:
            df["LastEditedWhen"] = pd.to_datetime(df["LastEditedWhen"], errors="coerce")
        if "PickingCompletedWhen" in df.columns:
            df["PickingCompletedWhen"] = pd.to_datetime(df["PickingCompletedWhen"], errors="coerce")
        
        logger.info(f"  ✓ Cleaned Sales.OrderLines: {len(df)} rows output")
        return df
    
    def clean_sales_invoices(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean Sales.Invoices table"""
        df = df.copy()
        logger.info(f"  Cleaning Sales.Invoices: {len(df)} rows input")
        
        # Convert dates
        date_columns = ["InvoiceDate", "ConfirmedDeliveryTime", "LastEditedWhen"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        # Remove rows with null InvoiceDate
        rows_before = len(df)
        df = df.dropna(subset=["InvoiceDate"])
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with null InvoiceDate")
        
        # Convert numeric columns
        for col in df.select_dtypes(include=["object"]).columns:
            if col not in ["Comments"]:  # Skip text fields
                try:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                except:
                    pass
        
        logger.info(f"  ✓ Cleaned Sales.Invoices: {len(df)} rows output")
        return df
    
    def clean_sales_invoice_lines(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean Sales.InvoiceLines table"""
        df = df.copy()
        logger.info(f"  Cleaning Sales.InvoiceLines: {len(df)} rows input")
        
        # Convert numeric columns (InvoiceLines has Quantity, UnitPrice, TaxRate, TaxAmount, LineProfit, ExtendedPrice - no LineTotal)
        numeric_cols = ["Quantity", "UnitPrice", "TaxRate", "TaxAmount", "LineProfit", "ExtendedPrice"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Remove rows with null critical fields
        rows_before = len(df)
        df = df.dropna(subset=["Quantity", "ExtendedPrice"])
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with null quantities/extended prices")
        
        # Remove negative quantities
        rows_before = len(df)
        df = df[df["Quantity"] > 0] if "Quantity" in df.columns else df
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with negative quantities")
        
        # Convert dates
        if "LastEditedWhen" in df.columns:
            df["LastEditedWhen"] = pd.to_datetime(df["LastEditedWhen"], errors="coerce")
        
        logger.info(f"  ✓ Cleaned Sales.InvoiceLines: {len(df)} rows output")
        return df
    
    def clean_categorical_data(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Clean categorical/reference tables"""
        df = df.copy()
        logger.info(f"  Cleaning {table_name}: {len(df)} rows input")
        
        # Strip whitespace from text columns (only string types)
        for col in df.select_dtypes(include=["object"]).columns:
            try:
                if df[col].dtype == "object":
                    df[col] = df[col].astype(str).str.strip()
            except:
                pass
        
        # Remove duplicates based on ID (if exists)
        id_cols = [col for col in df.columns if col.endswith("ID")]
        if id_cols:
            rows_before = len(df)
            df = df.drop_duplicates(subset=[id_cols[0]])
            removed = rows_before - len(df)
            if removed > 0:
                logger.info(f"    - Removed {removed} duplicate rows")
        
        logger.info(f"  ✓ Cleaned {table_name}: {len(df)} rows output")
        return df
    
    def clean_all(self, extracted: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Apply cleaning to all extracted tables"""
        logger.info("\n" + "=" * 80)
        logger.info("🧹 INICIANDO LIMPIEZA DE DATOS")
        logger.info("=" * 80)
        
        cleaned = {}
        
        for table_name, df in extracted.items():
            try:
                if "Orders" in table_name and "Invoice" not in table_name:
                    cleaned[table_name] = self.clean_sales_orders(df)
                elif "OrderLines" in table_name:
                    cleaned[table_name] = self.clean_sales_order_lines(df)
                elif "Invoices" in table_name and "Lines" not in table_name:
                    cleaned[table_name] = self.clean_sales_invoices(df)
                elif "InvoiceLines" in table_name:
                    cleaned[table_name] = self.clean_sales_invoice_lines(df)
                else:
                    # Generic cleaning for reference/categorical tables
                    cleaned[table_name] = self.clean_categorical_data(df, table_name)
            except Exception as e:
                logger.error(f"  ✗ Error cleaning {table_name}: {str(e)}")
                cleaned[table_name] = df
        
        return cleaned


class DataValidator:
    """Validates data quality"""
    
    @staticmethod
    def validate_table(df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Validate single table"""
        validation = {
            "table_name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "null_count": df.isnull().sum().sum(),
            "null_percentage": (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100) if len(df) > 0 else 0,
            "duplicates": df.duplicated().sum(),
            "columns_with_nulls": (df.isnull().sum()[df.isnull().sum() > 0]).to_dict(),
        }
        
        return validation
    
    def validate_all(self, cleaned: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate all cleaned tables"""
        logger.info("\n" + "=" * 80)
        logger.info("🔍 VALIDACIÓN DE CALIDAD DE DATOS")
        logger.info("=" * 80)
        
        validation_report = {}
        
        for table_name, df in cleaned.items():
            report = self.validate_table(df, table_name)
            validation_report[table_name] = report
            
            logger.info(f"\n  {table_name}:")
            logger.info(f"    • Filas: {report['row_count']:,}")
            logger.info(f"    • Columnas: {report['column_count']}")
            logger.info(f"    • Duplicados: {report['duplicates']}")
            logger.info(f"    • Nulos totales: {report['null_count']:,} ({report['null_percentage']:.2f}%)")
            
            if report['columns_with_nulls']:
                logger.info(f"    • Columnas con valores nulos:")
                for col, null_count in sorted(report['columns_with_nulls'].items(), key=lambda x: x[1], reverse=True):
                    null_pct = (null_count / len(df) * 100) if len(df) > 0 else 0
                    logger.info(f"      - {col}: {null_count:,} ({null_pct:.2f}%)")
        
        return validation_report


def transform_phase(extracted: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """
    Execute FASE 3.2: TRANSFORM
    Cleans and validates extracted data
    
    Args:
        extracted: Dictionary of extracted DataFrames
    
    Returns:
        Tuple of (cleaned_data, validation_report)
    """
    logger.info("\n" + "=" * 80)
    logger.info("📊 FASE 3.2: TRANSFORMACIÓN")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # Clean data
    cleaner = DataCleaner()
    cleaned_data = cleaner.clean_all(extracted)
    
    # Validate data
    validator = DataValidator()
    validation_report = validator.validate_all(cleaned_data)
    
    elapsed = time.time() - start_time
    
    logger.info("\n" + "-" * 80)
    logger.info(f"✅ TRANSFORMACIÓN COMPLETADA en {elapsed:.2f}s")
    logger.info(f"   ✓ Tablas procesadas: {len(cleaned_data)}")
    logger.info(f"   ✓ Filas totales: {sum(len(df) for df in cleaned_data.values()):,}")
    logger.info("=" * 80)
    
    return cleaned_data, validation_report


if __name__ == "__main__":
    print("Transform module loaded. Use in conjunction with extract.py")

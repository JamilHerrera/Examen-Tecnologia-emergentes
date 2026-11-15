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

    def __init__(self):
        self.rejected_rows = []

    def _record_rejects(self, df, mask, table_name, rule_name, detail):
        rejected = df.loc[mask]
        if rejected.empty:
            return
        key_columns = [column for column in df.columns if column.endswith("ID")]
        key_column = key_columns[0] if key_columns else None
        for _, row in rejected.iterrows():
            self.rejected_rows.append({
                "source_table": table_name,
                "rule_name": rule_name,
                "business_key": None if key_column is None or pd.isna(row[key_column]) else str(row[key_column]),
                "row_data": row.to_dict(),
                "detail": detail,
            })
    
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
        invalid_order_date = df["OrderDate"].isna()
        self._record_rejects(
            df, invalid_order_date, "Sales.Orders", "required_order_date",
            "OrderDate is null or could not be parsed.",
        )
        rows_before = len(df)
        df = df.loc[~invalid_order_date]
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
        invalid_values = df[["Quantity", "UnitPrice"]].isna().any(axis=1)
        self._record_rejects(
            df, invalid_values, "Sales.OrderLines", "required_quantity_and_price",
            "Quantity or UnitPrice is null or could not be parsed.",
        )
        rows_before = len(df)
        df = df.loc[~invalid_values]
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with null quantities/prices")
        
        # Remove non-positive quantities
        invalid_quantity = df["Quantity"] <= 0
        self._record_rejects(
            df, invalid_quantity, "Sales.OrderLines", "positive_quantity",
            "Quantity must be greater than zero.",
        )
        rows_before = len(df)
        df = df.loc[~invalid_quantity]
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
        invalid_invoice_date = df["InvoiceDate"].isna()
        self._record_rejects(
            df, invalid_invoice_date, "Sales.Invoices", "required_invoice_date",
            "InvoiceDate is null or could not be parsed.",
        )
        rows_before = len(df)
        df = df.loc[~invalid_invoice_date]
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
        invalid_values = df[["Quantity", "ExtendedPrice"]].isna().any(axis=1)
        self._record_rejects(
            df, invalid_values, "Sales.InvoiceLines", "required_quantity_and_extended_price",
            "Quantity or ExtendedPrice is null or could not be parsed.",
        )
        rows_before = len(df)
        df = df.loc[~invalid_values]
        removed = rows_before - len(df)
        if removed > 0:
            logger.info(f"    - Removed {removed} rows with null quantities/extended prices")
        
        # Remove non-positive quantities
        invalid_quantity = df["Quantity"] <= 0
        self._record_rejects(
            df, invalid_quantity, "Sales.InvoiceLines", "positive_quantity",
            "Quantity must be greater than zero.",
        )
        rows_before = len(df)
        df = df.loc[~invalid_quantity]
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
            duplicate_mask = df.duplicated(subset=[id_cols[0]], keep="first")
            self._record_rejects(
                df, duplicate_mask, table_name.replace("_", ".", 1), "duplicate_business_key",
                f"Duplicate {id_cols[0]}; the first occurrence was retained.",
            )
            rows_before = len(df)
            df = df.loc[~duplicate_mask]
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
                raise
        
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


def transform_phase(extracted: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any], list]:
    """
    Execute FASE 3.2: TRANSFORM
    Cleans and validates extracted data
    
    Args:
        extracted: Dictionary of extracted DataFrames
    
    Returns:
        Tuple of cleaned data, validation report, and rejected-row details.
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
    
    return cleaned_data, validation_report, cleaner.rejected_rows


if __name__ == "__main__":
    print("Transform module loaded. Use in conjunction with extract.py")

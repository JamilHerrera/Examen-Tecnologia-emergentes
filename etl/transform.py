"""
ETL Transform Module
Implements data cleaning, validation, and transformations
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataCleaner:
    """Handles data quality and transformations"""

    @staticmethod
    def clean_sales_orders(df: pd.DataFrame) -> pd.DataFrame:
        """Clean Sales.Orders table"""
        df = df.copy()
        logger.info(f"Cleaning Sales.Orders: {len(df)} rows input")

        # Convert dates
        date_columns = ["OrderDate", "PickingCompletedWhen", "LastEditedWhen"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Remove rows with null OrderDate
        df = df.dropna(subset=["OrderDate"])

        # Convert amount columns to float
        amount_columns = [col for col in df.columns if "Amount" in col]
        for col in amount_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        logger.info(f"✓ Cleaned Sales.Orders: {len(df)} rows output")
        return df

    @staticmethod
    def clean_sales_order_lines(df: pd.DataFrame) -> pd.DataFrame:
        """Clean Sales.OrderLines table"""
        df = df.copy()
        logger.info(f"Cleaning Sales.OrderLines: {len(df)} rows input")

        # Convert numeric columns
        numeric_cols = ["Quantity", "UnitPrice", "LineTotal", "UnitPriceDiscountPct"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Remove rows with null Quantity or LineTotal
        df = df.dropna(subset=["Quantity", "LineTotal"])

        # Remove negative quantities (invalid)
        df = df[df["Quantity"] > 0]

        # Convert LastEditedWhen
        if "LastEditedWhen" in df.columns:
            df["LastEditedWhen"] = pd.to_datetime(df["LastEditedWhen"], errors="coerce")

        logger.info(f"✓ Cleaned Sales.OrderLines: {len(df)} rows output")
        return df

    @staticmethod
    def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
        """Clean Sales.Customers table"""
        df = df.copy()
        logger.info(f"Cleaning Sales.Customers: {len(df)} rows input")

        # Remove duplicates
        df = df.drop_duplicates(subset=["CustomerID"])

        # Clean phone and email
        if "PhoneNumber" in df.columns:
            df["PhoneNumber"] = df["PhoneNumber"].str.strip()
        if "FaxNumber" in df.columns:
            df["FaxNumber"] = df["FaxNumber"].str.strip()

        # Convert dates
        if "ValidFrom" in df.columns:
            df["ValidFrom"] = pd.to_datetime(df["ValidFrom"], errors="coerce")
        if "ValidTo" in df.columns:
            df["ValidTo"] = pd.to_datetime(df["ValidTo"], errors="coerce")

        logger.info(f"✓ Cleaned Sales.Customers: {len(df)} rows output")
        return df

    @staticmethod
    def clean_products(df: pd.DataFrame) -> pd.DataFrame:
        """Clean Warehouse.Products table"""
        df = df.copy()
        logger.info(f"Cleaning Warehouse.Products: {len(df)} rows input")

        # Remove duplicates
        df = df.drop_duplicates(subset=["ProductID"])

        # Convert numeric columns
        numeric_cols = ["UnitPrice", "RecommendedRetailPrice", "TypicalWeightPerUnit"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Remove negative prices
        if "UnitPrice" in df.columns:
            df = df[df["UnitPrice"] >= 0]

        logger.info(f"✓ Cleaned Warehouse.Products: {len(df)} rows output")
        return df

    @staticmethod
    def clean_geography(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Clean geography-related tables (Cities, StateProvinces, Countries)"""
        df = df.copy()
        logger.info(f"Cleaning {table_name}: {len(df)} rows input")

        # Remove duplicates based on ID column
        id_cols = [col for col in df.columns if "ID" in col and col.endswith("ID")]
        if id_cols:
            df = df.drop_duplicates(subset=[id_cols[0]])

        # Strip whitespace from text columns
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].str.strip()

        logger.info(f"✓ Cleaned {table_name}: {len(df)} rows output")
        return df

    def clean_all(self, extracted: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Apply cleaning to all extracted tables"""
        cleaned = {}

        for table_name, df in extracted.items():
            try:
                if "Sales.Orders" in table_name:
                    cleaned[table_name] = self.clean_sales_orders(df)
                elif "Sales.OrderLines" in table_name:
                    cleaned[table_name] = self.clean_sales_order_lines(df)
                elif "Sales.Customers" in table_name:
                    cleaned[table_name] = self.clean_customers(df)
                elif "Warehouse.Products" in table_name:
                    cleaned[table_name] = self.clean_products(df)
                elif any(x in table_name for x in ["Cities", "StateProvinces", "Countries"]):
                    cleaned[table_name] = self.clean_geography(df, table_name)
                else:
                    # Generic cleaning for other tables
                    cleaned[table_name] = df.copy()
                    logger.info(f"✓ Minimal cleaning for {table_name}")
            except Exception as e:
                logger.error(f"Error cleaning {table_name}: {e}")
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
            "null_percentages": (df.isnull().sum() / len(df) * 100).to_dict(),
            "duplicates": df.duplicated().sum(),
            "numeric_anomalies": {},
        }

        # Check for numeric anomalies
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            outliers = ((df[col] - mean).abs() > 3 * std).sum()
            if outliers > 0:
                validation["numeric_anomalies"][col] = outliers

        return validation

    def validate_all(self, cleaned: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate all cleaned tables"""
        logger.info("\n=== DATA QUALITY VALIDATION ===")
        validation_report = {}

        for table_name, df in cleaned.items():
            report = self.validate_table(df, table_name)
            validation_report[table_name] = report

            logger.info(f"\n{table_name}:")
            logger.info(f"  Rows: {report['row_count']}")
            logger.info(f"  Duplicates: {report['duplicates']}")
            logger.info(f"  Null % by column: {report['null_percentages']}")
            if report['numeric_anomalies']:
                logger.info(f"  Outliers: {report['numeric_anomalies']}")

        return validation_report


def transform_phase(extracted: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """Main transformation phase"""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3.2: TRANSFORM - Cleaning and Validating Data")
    logger.info("=" * 60)

    cleaner = DataCleaner()
    cleaned_data = cleaner.clean_all(extracted)

    validator = DataValidator()
    validation_report = validator.validate_all(cleaned_data)

    logger.info(f"\n✓ Transformation complete")
    return cleaned_data, validation_report


if __name__ == "__main__":
    print("Transform module loaded. Use in conjunction with extract.py")

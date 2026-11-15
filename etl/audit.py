"""
ETL Audit Module
Reconciliation and data quality validation between layers
"""
import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Reconciliation:
    """Validates data consistency across layers"""

    def __init__(self, connector):
        self.connector = connector

    def reconcile_sources(self, extracted: Dict[str, pd.DataFrame], cleaned: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Compare extracted vs cleaned for data loss"""
        logger.info("\n=== RECONCILIATION: EXTRACTED vs CLEANED ===")

        reconciliation_report = {}

        for table_name in extracted.keys():
            if table_name in cleaned:
                extracted_rows = len(extracted[table_name])
                cleaned_rows = len(cleaned[table_name])
                loss_pct = ((extracted_rows - cleaned_rows) / extracted_rows * 100) if extracted_rows > 0 else 0

                reconciliation_report[table_name] = {
                    "extracted_rows": extracted_rows,
                    "cleaned_rows": cleaned_rows,
                    "rows_lost": extracted_rows - cleaned_rows,
                    "loss_percentage": round(loss_pct, 2),
                    "status": "OK" if loss_pct < 5 else "WARNING",
                }

                status = reconciliation_report[table_name]["status"]
                logger.info(
                    f"{status}: {table_name}"
                    f" | Extracted: {extracted_rows} → Cleaned: {cleaned_rows}"
                    f" | Loss: {loss_pct:.2f}%"
                )

        return reconciliation_report

    def reconcile_staging_to_database(self, table_name: str) -> Dict[str, Any]:
        """Query database to validate staging layer row counts"""
        try:
            schema, table = table_name.split(".")
            staging_raw = f"{schema}_{table}_raw"
            staging_clean = f"{schema}_{table}_clean"

            # Count rows in staging layers
            query_raw = f"SELECT COUNT(*) as cnt FROM [staging_raw].[{staging_raw}]"
            query_clean = f"SELECT COUNT(*) as cnt FROM [staging_clean].[{staging_clean}]"

            raw_count = self.connector.execute_query(query_raw)["cnt"].values[0]
            clean_count = self.connector.execute_query(query_clean)["cnt"].values[0]

            reconciliation = {
                "table_name": table_name,
                "staging_raw_rows": raw_count,
                "staging_clean_rows": clean_count,
                "rows_lost_in_staging": raw_count - clean_count,
                "loss_percentage": round(((raw_count - clean_count) / raw_count * 100), 2) if raw_count > 0 else 0,
            }

            logger.info(
                f"  {table_name}: Raw={raw_count}, Clean={clean_count}, "
                f"Loss={reconciliation['loss_percentage']}%"
            )

            return reconciliation
        except Exception as e:
            logger.error(f"Failed to reconcile {table_name}: {e}")
            return {"error": str(e)}


class DataQualityMetrics:
    """Calculates data quality scores"""

    @staticmethod
    def calculate_quality_score(df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Calculate data quality score for table"""
        metrics = {
            "table_name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "completeness_score": 0,
            "uniqueness_score": 0,
            "validity_score": 0,
            "consistency_score": None,
            "overall_quality_score": 0,
        }

        # Completeness: % of non-null cells
        total_cells = len(df) * len(df.columns)
        non_null_cells = df.count().sum()
        metrics["completeness_score"] = (non_null_cells / total_cells * 100) if total_cells > 0 else 0

        # Uniqueness: 1 - (duplicates / total rows)
        duplicates = df.duplicated().sum()
        metrics["uniqueness_score"] = ((len(df) - duplicates) / len(df) * 100) if len(df) > 0 else 0

        # Validity: simplified check (no negative IDs, valid dates)
        valid_rows = len(df)
        id_cols = [col for col in df.columns if "ID" in col or "id" in col]
        for col in id_cols:
            if df[col].dtype in ["int64", "float64"]:
                valid_rows -= (df[col] < 0).sum()
        metrics["validity_score"] = (valid_rows / len(df) * 100) if len(df) > 0 else 0

        measured_scores = [
            metrics["completeness_score"],
            metrics["uniqueness_score"],
            metrics["validity_score"],
        ]
        metrics["overall_quality_score"] = sum(measured_scores) / len(measured_scores)

        return metrics

    @staticmethod
    def quality_report(cleaned: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Generate quality report for all tables"""
        logger.info("\n=== DATA QUALITY REPORT ===")

        report = {}
        overall_scores = []

        for table_name, df in cleaned.items():
            metrics = DataQualityMetrics.calculate_quality_score(df, table_name)
            report[table_name] = metrics
            overall_scores.append(metrics["overall_quality_score"])

            logger.info(
                f"{table_name}:"
                f" | Completeness: {metrics['completeness_score']:.1f}%"
                f" | Uniqueness: {metrics['uniqueness_score']:.1f}%"
                f" | Validity: {metrics['validity_score']:.1f}%"
                " | Consistency: not measured"
                f" | Overall (3 measured metrics): {metrics['overall_quality_score']:.1f}%"
            )

        avg_quality = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        logger.info(f"\n✓ Platform Average Quality Score: {avg_quality:.1f}%")

        return report


def audit_phase(extracted: Dict[str, pd.DataFrame], cleaned: Dict[str, pd.DataFrame], connector) -> Dict[str, Any]:
    """Main audit phase"""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3.4: AUDIT - Reconciliation & Quality Checks")
    logger.info("=" * 60)

    reconciliation = Reconciliation(connector)
    quality_metrics = DataQualityMetrics()

    # Reconcile extracted vs cleaned
    reconciliation_report = reconciliation.reconcile_sources(extracted, cleaned)

    staging_report = {}
    staging_errors = []
    for target_name in extracted:
        source_name = target_name.replace("_", ".", 1)
        result = reconciliation.reconcile_staging_to_database(source_name)
        staging_report[source_name] = result
        if "error" in result:
            staging_errors.append({"table": source_name, "error": result["error"]})

    # Generate quality report
    quality_report = quality_metrics.quality_report(cleaned)

    logger.info(f"\n✓ Audit phase complete")

    return {
        "reconciliation": reconciliation_report,
        "staging": staging_report,
        "staging_errors": staging_errors,
        "quality": quality_report,
    }


if __name__ == "__main__":
    print("Audit module loaded. Use in conjunction with ETL pipeline")

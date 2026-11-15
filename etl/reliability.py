"""Helpers for incremental ETL watermarks and reproducible data profiles."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from etl.config import ETL_OVERLAP_SECONDS

PIPELINE_NAME = "etl_staging_pipeline"


def _as_datetime(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def read_watermark(cursor, source_object):
    row = cursor.execute(
        "SELECT WatermarkColumn, WatermarkValue, OverlapSeconds "
        "FROM ops.etl_watermark WHERE PipelineName = ? AND SourceObject = ?",
        PIPELINE_NAME,
        source_object,
    ).fetchone()
    if not row:
        return None, None, ETL_OVERLAP_SECONDS
    return row[0], row[1], int(row[2])


def save_watermarks(connection, extraction_metadata, commit=True):
    cursor = connection.cursor()
    try:
        for metadata in extraction_metadata.values():
            column = metadata.get("watermark_column")
            value = _as_datetime(metadata.get("watermark_end"))
            if not column or value is None:
                continue
            cursor.execute(
                """
                UPDATE ops.etl_watermark
                SET WatermarkValue = CASE WHEN WatermarkValue < ? THEN ? ELSE WatermarkValue END,
                    WatermarkColumn = ?, OverlapSeconds = ?, UpdatedAt = SYSUTCDATETIME()
                WHERE PipelineName = ? AND SourceObject = ?;
                IF @@ROWCOUNT = 0
                    INSERT INTO ops.etl_watermark
                        (PipelineName, SourceObject, WatermarkColumn, WatermarkValue, OverlapSeconds)
                    VALUES (?, ?, ?, ?, ?);
                """,
                value,
                value,
                column,
                metadata.get("overlap_seconds", ETL_OVERLAP_SECONDS),
                PIPELINE_NAME,
                metadata["source_table"],
                PIPELINE_NAME,
                metadata["source_table"],
                column,
                value,
                metadata.get("overlap_seconds", ETL_OVERLAP_SECONDS),
            )
        if commit:
            connection.commit()
    finally:
        cursor.close()


def _json_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def profile_dataframe(frame, top_values=5):
    """Return column-level null, distinct, range, and frequent-value statistics."""
    row_count = len(frame)
    columns = {}
    for name in frame.columns:
        series = frame[name]
        profile = {
            "null_count": int(series.isna().sum()),
            "null_pct": round(float(series.isna().mean() * 100), 4) if row_count else 0.0,
            "distinct_count": int(series.nunique(dropna=True)),
        }
        non_null = series.dropna()
        if not non_null.empty and (
            pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_datetime64_any_dtype(series)
        ):
            profile["min"] = _json_value(non_null.min())
            profile["max"] = _json_value(non_null.max())
        if not non_null.empty and (
            pd.api.types.is_object_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
        ):
            has_binary_values = any(
                isinstance(value, (bytes, bytearray, memoryview))
                for value in non_null
            )
            if not has_binary_values:
                counts = non_null.astype(str).value_counts().head(top_values)
                profile["top_values"] = [
                    {"value": str(value), "count": int(count)}
                    for value, count in counts.items()
                ]
        columns[str(name)] = profile
    return {"row_count": row_count, "column_count": len(frame.columns), "columns": columns}


def write_profile_report(run_id, profiles):
    directory = Path("logs") / "profiling"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"etl_run_{run_id or 'untracked'}.json"
    path.write_text(json.dumps(profiles, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path

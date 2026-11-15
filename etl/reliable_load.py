"""Atomic full and incremental staging loads with audit and quarantine records."""

import json
import logging
import re
import time
import uuid
from datetime import date, datetime, timezone

import pandas as pd
import pyodbc

from etl.reliability import save_watermarks

logger = logging.getLogger(__name__)
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def _quote(name):
    if not IDENTIFIER.fullmatch(name):
        raise ValueError(f"Identificador SQL no permitido: {name}")
    return f"[{name}]"


def _value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


def _text_value(value):
    value = _value(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _row_json(row):
    def normalize(value):
        value = _value(value)
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    return json.dumps(row, ensure_ascii=False, default=normalize)


class ReliableStagingLoader:
    def __init__(self, connector, mode, run_id, metadata, rejected_rows, profiles):
        if mode not in {"full", "incremental"}:
            raise ValueError("mode debe ser full o incremental")
        self.connector = connector
        self.mode = mode
        self.run_id = run_id
        self.metadata = metadata
        self.rejected_rows = rejected_rows
        self.profiles = profiles
        self.stats = {}

    def _create_schema(self, cursor, schema):
        cursor.execute(
            f"IF SCHEMA_ID(N'{schema}') IS NULL EXEC(N'CREATE SCHEMA [{schema}]')"
        )

    def _stage_frame(self, frame, layer):
        result = frame.copy()
        result.columns = [str(column).replace(" ", "_").replace(".", "_") for column in result.columns]
        if layer == "staging_raw":
            result["LoadedAt"] = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            result["QualityFlag"] = "VALID"
            result["LoadedAt"] = datetime.now(timezone.utc).replace(tzinfo=None)
        return result

    def _create_table(self, cursor, schema, table, frame, key_column):
        definitions = []
        for column in frame.columns:
            name = _quote(column)
            if column == key_column:
                definitions.append(f"{name} NVARCHAR(450) NOT NULL")
            elif column in {"QualityFlag"}:
                definitions.append(f"{name} NVARCHAR(50) NULL")
            elif column in {"LoadedAt"}:
                definitions.append(f"{name} DATETIME2(7) NULL")
            else:
                definitions.append(f"{name} NVARCHAR(MAX) NULL")
        cursor.execute(
            f"CREATE TABLE [{schema}].[{table}] ({', '.join(definitions)})"
        )

    def _insert_frame(self, cursor, schema, table, frame):
        if frame.empty:
            return 0
        columns = list(frame.columns)
        names = ", ".join(_quote(column) for column in columns)
        params = ", ".join("?" for _ in columns)
        statement = f"INSERT INTO [{schema}].[{table}] ({names}) VALUES ({params})"
        for offset in range(0, len(frame), 1000):
            batch_frame = frame.iloc[offset:offset + 1000]
            batch = []
            max_lengths = [1] * len(columns)
            for row in batch_frame.itertuples(index=False, name=None):
                values = []
                for index, (column, value) in enumerate(zip(columns, row)):
                    if column == "LoadedAt":
                        normalized = _value(value)
                    else:
                        normalized = _text_value(value)
                        if normalized is not None:
                            max_lengths[index] = max(max_lengths[index], len(normalized))
                    values.append(normalized)
                batch.append(tuple(values))
            cursor.setinputsizes([
                (pyodbc.SQL_TYPE_TIMESTAMP, 27, 7)
                if column == "LoadedAt"
                else (pyodbc.SQL_WLONGVARCHAR, max_lengths[index], 0)
                for index, column in enumerate(columns)
            ])
            cursor.fast_executemany = True
            cursor.executemany(statement, batch)
        return len(frame)

    def _create_key_index(self, cursor, schema, table, key_column, suffix):
        if not key_column:
            return
        index_name = _quote(f"UX_{table}_{suffix}")
        cursor.execute(
            f"CREATE UNIQUE INDEX {index_name} ON [{schema}].[{table}] "
            f"({_quote(key_column)})"
        )

    def _replace_table(self, cursor, schema, target, frame, key_column, temp_suffix):
        temp = f"_etl_{target[:80]}_{temp_suffix}"
        self._create_table(cursor, schema, temp, frame, key_column)
        inserted = self._insert_frame(cursor, schema, temp, frame)
        cursor.execute(f"DROP TABLE IF EXISTS [{schema}].[{target}]")
        cursor.execute(
            f"EXEC sys.sp_rename N'{schema}.{temp}', N'{target}', N'OBJECT'"
        )
        self._create_key_index(cursor, schema, target, key_column, "key")
        return inserted

    def _merge_table(self, cursor, schema, target, frame, key_column, temp_suffix):
        if frame.empty:
            return {"inserted": 0, "updated": 0}
        temp = f"_etl_{target[:80]}_{temp_suffix}"
        self._create_table(cursor, schema, temp, frame, key_column)
        self._insert_frame(cursor, schema, temp, frame)
        columns = list(frame.columns)
        updates = [column for column in columns if column != key_column]
        join = f"target.{_quote(key_column)} = source.{_quote(key_column)}"
        updated = 0
        if updates:
            assignments = ", ".join(
                f"target.{_quote(column)} = source.{_quote(column)}"
                for column in updates
            )
            cursor.execute(
                f"UPDATE target SET {assignments} "
                f"FROM [{schema}].[{target}] AS target "
                f"JOIN [{schema}].[{temp}] AS source ON {join}"
            )
            updated = max(int(cursor.rowcount), 0)
        names = ", ".join(_quote(column) for column in columns)
        source_names = ", ".join(f"source.{_quote(column)}" for column in columns)
        cursor.execute(
            f"INSERT INTO [{schema}].[{target}] ({names}) "
            f"SELECT {source_names} FROM [{schema}].[{temp}] AS source "
            f"WHERE NOT EXISTS (SELECT 1 FROM [{schema}].[{target}] AS target "
            f"WITH (UPDLOCK, HOLDLOCK) WHERE {join})"
        )
        inserted = max(int(cursor.rowcount), 0)
        cursor.execute(f"DROP TABLE [{schema}].[{temp}]")
        return {"inserted": inserted, "updated": updated}

    def _delete_missing_source_rows(self, cursor, schema, target, source, key_column):
        source_schema, source_table = source.split(".", 1)
        cursor.execute(
            f"DELETE target FROM [{schema}].[{target}] AS target "
            f"WHERE NOT EXISTS (SELECT 1 FROM [{source_schema}].[{source_table}] AS source "
            f"WHERE CONVERT(NVARCHAR(450), source.{_quote(key_column)}) = "
            f"target.{_quote(key_column)})"
        )
        return max(int(cursor.rowcount), 0)

    def _remove_rejected_clean_rows(self, cursor, clean_table, key_column, rejects):
        if not rejects:
            return 0
        statement = (
            f"DELETE FROM [staging_clean].[{clean_table}] "
            f"WHERE {_quote(key_column)} = ?"
        )
        removed = 0
        for rejected in rejects:
            if rejected.get("business_key") is None:
                continue
            cursor.execute(statement, rejected["business_key"])
            removed += max(int(cursor.rowcount), 0)
        return removed

    def _persist_rejects(self, cursor):
        if not self.rejected_rows:
            return
        rows = [
            (
                self.run_id,
                item["source_table"],
                item["rule_name"],
                item.get("business_key"),
                _row_json(item["row_data"]),
                item.get("detail", "")[:2000],
            )
            for item in self.rejected_rows
        ]
        max_lengths = [
            max((len(row[index]) for row in rows if row[index] is not None), default=1)
            for index in range(1, 6)
        ]
        cursor.setinputsizes(
            [(pyodbc.SQL_BIGINT, 19, 0)]
            + [
                (pyodbc.SQL_WLONGVARCHAR, length, 0)
                for length in max_lengths
            ]
        )
        cursor.fast_executemany = True
        cursor.executemany(
            """
            INSERT INTO ops.etl_reject
                (RunID, SourceObject, RuleName, BusinessKey, RowData, Detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _clear_run_records(self, connection):
        if self.run_id is None:
            return
        cursor = connection.cursor()
        try:
            for table in ("etl_reject", "etl_profile", "etl_table_run"):
                cursor.execute(f"DELETE FROM ops.{table} WHERE RunID = ?", self.run_id)
        finally:
            cursor.close()

    def _persist_profiles(self, cursor):
        for source, layers in self.profiles.items():
            for layer, profile in layers.items():
                cursor.execute(
                    """
                    INSERT INTO ops.etl_profile (RunID, SourceObject, Layer, ProfileJson)
                    VALUES (?, ?, ?, ?)
                    """,
                    self.run_id,
                    source,
                    layer,
                    json.dumps(profile, ensure_ascii=False, default=str),
                )

    def _persist_table_runs(self, cursor):
        for (source, layer), stats in self.stats.items():
            meta = self.metadata[source.replace(".", "_")]
            cursor.execute(
                """
                INSERT INTO ops.etl_table_run (
                    RunID, Mode, SourceObject, TargetObject, WatermarkColumn,
                    WatermarkStart, WatermarkEnd, RowsRead, RowsInserted,
                    RowsUpdated, RowsRejected, RowsDeleted, DurationSeconds,
                    Status, ErrorDetail, FinishedAt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                self.run_id,
                meta.get("mode", self.mode),
                source,
                f"{layer}.{stats['target']}",
                meta.get("watermark_column"),
                meta.get("watermark_start"),
                meta.get("watermark_end"),
                meta.get("row_count", 0),
                stats["inserted"],
                stats["updated"],
                stats["rejected"],
                stats["deleted"],
                stats["duration"],
                "warning" if stats["rejected"] else "success",
                None,
            )

    def load(self, extracted, cleaned):
        connection = self.connector.connection
        cursor = connection.cursor()
        suffix = uuid.uuid4().hex[:12]
        try:
            cursor.execute("SET XACT_ABORT ON")
            self._create_schema(cursor, "staging_raw")
            self._create_schema(cursor, "staging_clean")
            for source, extracted_frame in extracted.items():
                meta = self.metadata.get(source)
                if meta is None:
                    if self.mode == "full":
                        raise RuntimeError(f"Falta metadato de clave para {source}.")
                    continue
                key_column = meta["key_column"].replace(" ", "_").replace(".", "_")
                raw_table = f"{source}_raw"
                clean_table = f"{source}_clean"
                rejected = [
                    item for item in self.rejected_rows
                    if item["source_table"] == meta["source_table"]
                ]
                for layer, frame, target in (
                    ("staging_raw", extracted_frame, raw_table),
                    ("staging_clean", cleaned.get(source, extracted_frame), clean_table),
                ):
                    started = time.monotonic()
                    batch = self._stage_frame(frame, layer)
                    mode = meta.get("mode", self.mode)
                    if mode == "full":
                        inserted = self._replace_table(
                            cursor, layer, target, batch, key_column, suffix
                        )
                        updated = deleted = 0
                    elif batch.empty:
                        inserted = updated = 0
                        deleted = self._delete_missing_source_rows(
                            cursor, layer, target, meta["source_table"], key_column
                        )
                    else:
                        result = self._merge_table(
                            cursor, layer, target, batch, key_column, suffix
                        )
                        inserted, updated = result["inserted"], result["updated"]
                        deleted = self._delete_missing_source_rows(
                            cursor, layer, target, meta["source_table"], key_column
                        )
                    rejected_count = len(rejected) if layer == "staging_clean" else 0
                    if layer == "staging_clean" and mode == "incremental":
                        deleted += self._remove_rejected_clean_rows(
                            cursor, target, key_column, rejected
                        )
                    self.stats[(meta["source_table"], layer)] = {
                        "target": target,
                        "inserted": inserted,
                        "updated": updated,
                        "rejected": rejected_count,
                        "deleted": deleted,
                        "duration": round(time.monotonic() - started, 3),
                    }
            self._clear_run_records(connection)
            for persist in (
                self._persist_rejects,
                self._persist_profiles,
                self._persist_table_runs,
            ):
                persist_cursor = connection.cursor()
                try:
                    persist(persist_cursor)
                finally:
                    persist_cursor.close()
            save_watermarks(connection, self.metadata, commit=False)
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


def load_reliably(
    extracted, cleaned, connector, mode, run_id, metadata, rejected_rows, profiles
):
    loader = ReliableStagingLoader(
        connector, mode, run_id, metadata, rejected_rows, profiles
    )
    try:
        success = loader.load(extracted, cleaned)
        logger.info(
            "Carga staging %s: %s tablas, %s filas leidas, %s rechazadas.",
            mode,
            len(extracted),
            sum(item.get("row_count", 0) for item in metadata.values()),
            len(rejected_rows),
        )
        return success, loader.stats
    except Exception:
        logger.exception("Fallo en carga atomica de staging; se revirtieron los cambios.")
        return False, loader.stats

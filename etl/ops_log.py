"""Registro de ejecuciones ETL en ops.etl_run_log (monitoreo operativo)."""
import logging

import pyodbc

from etl.config import SQL_SERVER_CONFIG

logger = logging.getLogger(__name__)


def _connect():
    c = SQL_SERVER_CONFIG
    return pyodbc.connect(
        f"Driver={{{c['driver']}}};Server={c['server']};Database={c['database']};"
        f"UID={c['user']};PWD={c['password']};Encrypt={c['encrypt']};"
        f"TrustServerCertificate={c['trust_certificate']}",
        autocommit=True,
    )


def start_run(process: str):
    """Abre una ejecucion 'running'. Si ops no existe (capa no aplicada) no interrumpe el ETL."""
    try:
        with _connect() as conn:
            row = conn.cursor().execute(
                "INSERT INTO ops.etl_run_log (Process, Status) OUTPUT INSERTED.RunID VALUES (?, 'running')", process
            ).fetchone()
            return row[0]
    except pyodbc.Error as exc:
        logger.warning("No se pudo registrar la ejecucion en ops.etl_run_log: %s", exc)
        return None


def finish_run(
    run_id,
    status: str,
    rows=None,
    message: str = "",
    rows_read=None,
    rows_inserted=None,
    rows_updated=None,
    rows_rejected=None,
    rows_deleted=None,
    watermark_start=None,
    watermark_end=None,
    duration_seconds=None,
):
    if run_id is None:
        return
    try:
        with _connect() as conn:
            conn.cursor().execute(
                """
                UPDATE ops.etl_run_log
                SET Status = ?, FinishedAt = SYSUTCDATETIME(), RowsProcessed = ?, Message = ?,
                    RowsRead = ?, RowsInserted = ?, RowsUpdated = ?, RowsRejected = ?,
                    RowsDeleted = ?, WatermarkStart = ?, WatermarkEnd = ?, DurationSeconds = ?
                WHERE RunID = ?
                """,
                status, rows, message[:1000], rows_read, rows_inserted, rows_updated,
                rows_rejected, rows_deleted, watermark_start, watermark_end,
                duration_seconds, run_id,
            )
    except pyodbc.Error as exc:
        logger.warning("No se pudo cerrar la ejecucion %s: %s", run_id, exc)

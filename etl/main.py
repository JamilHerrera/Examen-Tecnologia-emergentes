"""Orchestrate the incremental staging ETL pipeline."""

import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, "/app" if "/app" in sys.argv[0] else ".")

from etl.audit import audit_phase
from etl.config import MAX_RETRIES, RETRY_DELAY, SQL_SERVER_CONFIG, logger
from etl.extract import DatabaseConnector, extract_phase
from etl.load import load_phase
from etl.ops_log import finish_run, start_run
from etl.reliability import profile_dataframe, write_profile_report
from etl.transform import transform_phase


def _watermark_bounds(metadata, field):
    values = [item[field] for item in metadata.values() if item.get(field) is not None]
    return (min(values), max(values)) if values else (None, None)


def _run_etl_pipeline(mode, run_id, max_retries, retry_delay):
    start_time = time.monotonic()
    logger.info("\n%s", "=" * 70)
    logger.info("INICIANDO PIPELINE ETL - PLATAFORMA DE INGENIERÍA DE DATOS")
    logger.info("Modo: %s | RunID: %s", mode, run_id)
    logger.info("Timestamp: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("%s", "=" * 70)

    extract_started = time.monotonic()
    extracted_data, extraction_metadata = extract_phase(mode)
    logger.info("Extracción completada en %.1fs", time.monotonic() - extract_started)

    transform_started = time.monotonic()
    cleaned_data, validation_report, rejected_rows = transform_phase(extracted_data)
    logger.info("Validación generada para %s tablas.", len(validation_report))
    logger.info("Transformación completada en %.1fs", time.monotonic() - transform_started)

    profiles = {}
    for target, metadata in extraction_metadata.items():
        source = metadata["source_table"]
        profiles[source] = {
            "staging_raw": profile_dataframe(extracted_data[target]),
            "staging_clean": profile_dataframe(cleaned_data[target]),
        }

    load_succeeded = False
    load_stats = {}
    for attempt in range(max_retries + 1):
        connector = DatabaseConnector(SQL_SERVER_CONFIG)
        try:
            if not connector.connect():
                raise RuntimeError("No se pudo conectar a SQL Server para cargar staging.")
            load_started = time.monotonic()
            load_succeeded = load_phase(
                extracted_data,
                cleaned_data,
                connector,
                mode=mode,
                run_id=run_id,
                metadata=extraction_metadata,
                rejected_rows=rejected_rows,
                profiles=profiles,
                stats_out=load_stats,
            )
            if not load_succeeded:
                raise RuntimeError("Falló la carga atómica a staging.")
            logger.info("Carga atomica, watermarks y auditoria completados en %.1fs",
                        time.monotonic() - load_started)
            break
        except Exception:
            logger.exception("Intento de carga %s/%s fallido.", attempt + 1, max_retries + 1)
            if attempt == max_retries:
                raise
            time.sleep(retry_delay)
        finally:
            connector.disconnect()

    if not load_succeeded:
        raise RuntimeError("La carga a staging no se completó.")

    profile_path = write_profile_report(run_id, profiles)
    logger.info("Perfil de ejecución guardado en %s", profile_path)

    audit_started = time.monotonic()
    connector = DatabaseConnector(SQL_SERVER_CONFIG)
    try:
        if not connector.connect():
            raise RuntimeError("No se pudo conectar a SQL Server para auditar staging.")
        audit_results = audit_phase(extracted_data, cleaned_data, connector)
    finally:
        connector.disconnect()
    logger.info("Auditoría completada en %.1fs", time.monotonic() - audit_started)

    elapsed = time.monotonic() - start_time
    logger.info("Pipeline finalizado en %.1fs | rechazos: %s", elapsed, len(rejected_rows))
    return {
        "rows_read": sum(item["row_count"] for item in extraction_metadata.values()),
        "rows_inserted": sum(item["inserted"] for item in load_stats.values()),
        "rows_updated": sum(item["updated"] for item in load_stats.values()),
        "rows_rejected": len(rejected_rows),
        "rows_deleted": sum(item["deleted"] for item in load_stats.values()),
        "load_stats": load_stats,
        "profiles": profiles,
        "audit": audit_results,
        "duration_seconds": round(elapsed, 3),
        "watermark_start": _watermark_bounds(extraction_metadata, "watermark_start")[0],
        "watermark_end": _watermark_bounds(extraction_metadata, "watermark_end")[1],
    }


def run_etl_pipeline(mode="incremental", max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """Run ETL and record the outcome in ops.etl_run_log."""
    if mode not in {"full", "incremental"}:
        raise ValueError("mode debe ser full o incremental")
    if max_retries < 0:
        raise ValueError("max_retries no puede ser negativo")
    if retry_delay < 0:
        raise ValueError("retry_delay no puede ser negativo")

    run_id = start_run(f"etl_staging_pipeline:{mode}")
    started = time.monotonic()
    try:
        result = _run_etl_pipeline(mode, run_id, max_retries, retry_delay)
        warning = result["rows_rejected"] > 0 or bool(
            result["audit"].get("staging_errors")
        )
        finish_run(
            run_id,
            "warning" if warning else "success",
            rows=result["rows_read"],
            message=(
                f"Pipeline ETL completado con {result['rows_rejected']} rechazos."
                if warning
                else "Pipeline ETL completado."
            ),
            rows_read=result["rows_read"],
            rows_inserted=result["rows_inserted"],
            rows_updated=result["rows_updated"],
            rows_rejected=result["rows_rejected"],
            rows_deleted=result["rows_deleted"],
            watermark_start=result["watermark_start"],
            watermark_end=result["watermark_end"],
            duration_seconds=round(time.monotonic() - started, 3),
        )
        return True
    except Exception as exc:
        finish_run(
            run_id,
            "failed",
            message=str(exc),
            duration_seconds=round(time.monotonic() - started, 3),
        )
        raise


def _parse_args():
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline ETL de staging.")
    parser.add_argument(
        "--mode",
        choices=("incremental", "full"),
        default=os.getenv("ETL_MODE", "incremental"),
        help="incremental por defecto; full reemplaza staging con una carga completa.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES,
        help="Reintentos de carga tras fallos transitorios (por defecto: %(default)s).",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=RETRY_DELAY,
        help="Segundos entre reintentos de carga (por defecto: %(default)s).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        run_etl_pipeline(args.mode, args.max_retries, args.retry_delay)
    except Exception:
        logger.exception("El pipeline ETL terminó con error.")
        sys.exit(1)

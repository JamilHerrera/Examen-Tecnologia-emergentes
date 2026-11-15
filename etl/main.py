"""
Main ETL Pipeline Orchestrator
Runs complete extract → transform → load → audit cycle
"""
import sys
import time
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, "/app" if "/app" in sys.argv[0] else ".")

from etl.config import SQL_SERVER_CONFIG, logger
from etl.extract import extract_phase, DatabaseConnector
from etl.transform import transform_phase
from etl.load import load_phase
from etl.audit import audit_phase


def run_etl_pipeline():
    """Execute complete ETL pipeline"""
    
    start_time = time.time()
    
    logger.info("\n" + "=" * 70)
    logger.info("INICIANDO PIPELINE ETL - PLATAFORMA DE INGENIERÍA DE DATOS")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    try:
        # PHASE 1: EXTRACT
        logger.info("\n📊 INICIANDO FASE 1: EXTRACCIÓN")
        start_extract = time.time()
        extracted_data = extract_phase()
        extract_duration = time.time() - start_extract
        logger.info(f"✅ EXTRACCIÓN COMPLETADA en {extract_duration:.1f}s")
        
        if not extracted_data:
            logger.error("❌ Extracción falló: No se extrajeron datos")
            return False
        
        # PHASE 2: TRANSFORM
        logger.info("\n🔄 INICIANDO FASE 2: TRANSFORMACIÓN")
        start_transform = time.time()
        cleaned_data, validation_report = transform_phase(extracted_data)
        transform_duration = time.time() - start_transform
        logger.info(f"✅ TRANSFORMACIÓN COMPLETADA en {transform_duration:.1f}s")
        
        # PHASE 3: LOAD
        logger.info("\n💾 INICIANDO FASE 3: CARGA")
        connector = DatabaseConnector(SQL_SERVER_CONFIG)
        if not connector.connect():
            logger.error("❌ No se pudo conectar a la base de datos")
            return False
        
        start_load = time.time()
        load_success = load_phase(extracted_data, cleaned_data, connector)
        load_duration = time.time() - start_load
        
        if not load_success:
            logger.error("❌ Carga falló")
            connector.disconnect()
            return False
        
        logger.info(f"✅ CARGA COMPLETADA en {load_duration:.1f}s")
        
        # PHASE 4: AUDIT
        logger.info("\n📋 INICIANDO FASE 4: AUDITORÍA")
        start_audit = time.time()
        audit_results = audit_phase(extracted_data, cleaned_data, connector)
        audit_duration = time.time() - start_audit
        logger.info(f"✅ AUDITORÍA COMPLETADA en {audit_duration:.1f}s")
        
        # Close connection
        connector.disconnect()
        
        # Summary
        total_duration = time.time() - start_time
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE ETL COMPLETADO EXITOSAMENTE ✅")
        logger.info("=" * 70)
        logger.info(f"Extracción:  {extract_duration:.1f}s")
        logger.info(f"Transformación: {transform_duration:.1f}s")
        logger.info(f"Carga:       {load_duration:.1f}s")
        logger.info(f"Auditoría:   {audit_duration:.1f}s")
        logger.info(f"TOTAL:       {total_duration:.1f}s")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ ERROR EN PIPELINE: {e}")
        logger.exception("Stack trace:")
        return False


if __name__ == "__main__":
    success = run_etl_pipeline()
    sys.exit(0 if success else 1)

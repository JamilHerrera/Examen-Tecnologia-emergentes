# ETL Pipeline - Guía de Ejecución

## 📋 Descripción

Pipeline ETL completo para extraer, transformar, cargar y auditar datos desde **WideWorldImporters** hacia las capas de Staging (Raw y Clean) en SQL Server.

**Fases:**
1. **Extract:** Lectura de 10 tablas desde WideWorldImporters
2. **Transform:** Limpieza y validación de datos
3. **Load:** Persistencia en Staging Raw y Clean
4. **Audit:** Reconciliación y cálculo de métricas de calidad

> Para la instalacion completa del producto (restaurar el origen, cargar el DW, aplicar BI/ops y arrancar la app), seguir primero el [runbook](../documentation/07_SEGURIDAD_Y_OPERACION.md). Las salidas y conteos de ejemplo en las secciones historicas de esta guia no son resultados de una ejecucion actual.

---

## Inicio inicial

### 1. Preparar WideWorldImporters

Descargar el backup oficial `WideWorldImporters-Full.bak` desde el release de
[WideWorldImporters](https://github.com/microsoft/sql-server-samples/releases/tag/wide-world-importers-v1.0)
y guardarlo en `database/backups/`. El archivo no se versiona.

### 2. Iniciar SQL Server y Ollama

Desde la raiz del repositorio, completar `.env` con base en `.env.example` y ejecutar:

```powershell
docker compose -f docker-compose-simple.yml up -d
```

El Compose actual inicia `sql-server-2022` y `ollama`. Para restaurar el backup si la base no existe, ejecutar los pasos SQL descritos en el [runbook de instalacion](../documentation/07_SEGURIDAD_Y_OPERACION.md). No restaurar con `WITH REPLACE` sobre una base existente.

### 3. Ejecutar ETL y crear el Data Warehouse

La configuracion Python y el orden de carga inicial (ETL, dimensiones, hechos, capa BI/operativa, reconciliacion y modelo ML) estan en el [runbook de instalacion](../documentation/07_SEGURIDAD_Y_OPERACION.md). Este documento conserva los detalles tecnicos de las fases de staging.

Para validar que SQL Server este disponible:

```powershell
docker compose -f docker-compose-simple.yml ps
```

### Dependencias Python

```bash
pip install -r requirements.txt
```

### Ejecutar solo el pipeline de staging

```bash
python etl/main.py --mode incremental
```

El modo incremental es el predeterminado. En la primera ejecucion, cada tabla sin watermark se carga completa; las siguientes consultan los cambios desde `ops.etl_watermark`, con una ventana de solapamiento de 300 segundos. La carga es transaccional e idempotente: raw y clean se actualizan por clave, los registros rechazados se guardan en `ops.etl_reject` y el watermark avanza solo despues de confirmar la carga.

Para reconstruir staging desde cero, usar explícitamente:

```powershell
python etl/main.py --mode full
```

La opcion `--max-retries` (predeterminada: 3) reintenta solo la carga transaccional, sin repetir la extraccion; `--retry-delay` controla la espera en segundos. La auditoria por ejecucion incluye conteos por tabla/capa en `ops.etl_table_run`, perfiles JSON en `ops.etl_profile` y un informe local en `logs/profiling/`.

Antes de ejecutar el ETL, la capa `ops` debe estar aplicada con `python database/apply_dw_layer.py` despues de crear el DW. El pipeline de staging no sustituye la carga dimensional `dw_schema.py`, `dw_dimensions.py`, `dw_customer_scd2.py`, `dw_facts.py` y `dw_enrich.py`. Carga el historial de clientes despues de las dimensiones y antes de los hechos. Despues de aplicar `database/apply_dw_layer.py`, `dw_analytics.py` carga compras, rentabilidad por factura y movimientos/snapshot de inventario directamente desde WideWorldImporters.

### Orquestacion diaria en Windows

Desde PowerShell, en la raiz del repositorio, registrar una tarea diaria a las 2:00 AM:

```powershell
.\deployment\register-etl-task.ps1
```

La tarea usa el Python del entorno `.venv` (o `python.exe` del PATH si no existe), ejecuta modo incremental, ignora una nueva instancia si ya hay una en curso y reintenta el proceso ante fallos. Se registra con el usuario actual y requiere una sesion iniciada. Para probarla manualmente:

```powershell
Start-ScheduledTask -TaskName 'WideWorldImporters Incremental ETL'
Get-ScheduledTaskInfo -TaskName 'WideWorldImporters Incremental ETL'
```

Para quitarla:

```powershell
Unregister-ScheduledTask -TaskName 'WideWorldImporters Incremental ETL' -Confirm:$false
```

---

## 📊 ARQUITECTURA

### Data Flow
```
WideWorldImporters (Source)
    │
    ▼
EXTRACT (etl/extract.py)
    │ pyodbc + pandas
    ▼
TRANSFORM (etl/transform.py)
    │ pandas + numpy
    ▼
LOAD (etl/reliable_load.py; transaccion atomica)
    ├─ staging_raw / staging_clean
    ├─ ops.etl_watermark / etl_table_run / etl_reject / etl_profile
    └─ logs/profiling/
    │
    ▼
AUDIT (etl/audit.py)
    │ Reconciliation + Quality Scores
    ▼
Logs & Reports
```

### Esquemas en SQL Server
```
- [staging_raw]   → Copia exacta sin transformaciones
- [staging_clean] → Datos procesados y validados
- [dw]            → Dimensiones, ventas por pedido y hechos de analitica de negocio
- [bi]            → Vistas de solo lectura para el dashboard
```

---

## 🔧 CONFIGURACIÓN

### etl/config.py
Archivo central de configuración:

```python
SQL_SERVER_CONFIG = {
    "server": "localhost,1433",
    "database": "WideWorldImporters",
    "user": "sa",
    "password": os.environ["MSSQL_SA_PASSWORD"],  # desde .env
}

BATCH_SIZE = 10000
STAGING_RAW_SCHEMA = "staging_raw"
STAGING_CLEAN_SCHEMA = "staging_clean"
```

### Variables de Entorno (.env)
```bash
MSSQL_SERVER=localhost,1433
MSSQL_SA_USER=sa
MSSQL_SA_PASSWORD=<tu-password-sa>
MSSQL_DATABASE=WideWorldImporters
```

---

## 📁 ESTRUCTURA DE MÓDULOS

```
etl/
├── __init__.py          # Package initialization
├── config.py            # Configuración centralizada
├── extract.py           # Extractor (DatabaseConnector, DataExtractor)
├── transform.py         # Transformaciones (DataCleaner, DataValidator)
├── load.py              # Integracion del cargador transaccional
├── reliable_load.py     # Upsert, reemplazo, auditoria y cuarentena
├── reliability.py       # Watermarks y perfilado reproducible
├── audit.py             # Auditoría (Reconciliation, DataQualityMetrics)
├── ops_log.py           # Registro de ejecuciones en ops.etl_run_log
└── main.py              # Orquestador del pipeline de staging
```

La carga dimensional y reconciliacion del DW se implementan en los modulos `etl/dw_*.py`, ejecutados por separado (ver [runbook](../documentation/07_SEGURIDAD_Y_OPERACION.md)).

---

## Ejemplo historico de ejecucion

```bash
$ python etl/main.py

======================================================================
INICIANDO PIPELINE ETL - PLATAFORMA DE INGENIERÍA DE DATOS
Timestamp: 2024-11-13 19:30:00
======================================================================

📊 INICIANDO FASE 1: EXTRACCIÓN
2024-11-13 19:30:00,123 - etl.extract - INFO - ✓ Connected to localhost,1433
2024-11-13 19:30:02,456 - etl.extract - INFO - ✓ Extracted Sales.Orders: 73000 rows, 15 columns
2024-11-13 19:30:05,789 - etl.extract - INFO - ✓ Extracted Sales.OrderLines: 231000 rows, 13 columns
2024-11-13 19:30:08,123 - etl.extract - INFO - ✓ Extracted Sales.Customers: 663 rows, 10 columns
...
✅ EXTRACCIÓN COMPLETADA en 45.2s

🔄 INICIANDO FASE 2: TRANSFORMACIÓN
2024-11-13 19:30:45,234 - etl.transform - INFO - Cleaning Sales.Orders: 73000 rows input
2024-11-13 19:30:46,567 - etl.transform - INFO - ✓ Cleaned Sales.Orders: 72500 rows output
...
✅ TRANSFORMACIÓN COMPLETADA en 32.1s

💾 INICIANDO FASE 3: CARGA
2024-11-13 19:31:18,456 - etl.load - INFO - === LOADING TO STAGING RAW ===
2024-11-13 19:31:20,789 - etl.load - INFO - ✓ Loaded 73000 rows to staging_raw.Sales_Orders
...
✅ CARGA COMPLETADA en 28.5s

📋 INICIANDO FASE 4: AUDITORÍA
2024-11-13 19:31:47,123 - etl.audit - INFO - === RECONCILIACIÓN: EXTRACTED vs CLEANED ===
2024-11-13 19:31:47,234 - etl.audit - INFO - OK: Sales.Orders | Extracted: 73000 → Cleaned: 72500 | Loss: 0.68%
2024-11-13 19:31:47,567 - etl.audit - INFO - === DATA QUALITY REPORT ===
2024-11-13 19:31:47,678 - etl.audit - INFO - Sales.Orders: | Completeness: 95.2% | Uniqueness: 99.8% | Overall: 97.6%
...
✅ AUDITORÍA COMPLETADA en 5.3s

======================================================================
PIPELINE ETL COMPLETADO EXITOSAMENTE ✅
======================================================================
Extracción:       45.2s
Transformación:   32.1s
Carga:           28.5s
Auditoría:        5.3s
TOTAL:          111.1s
======================================================================
```

Las cifras y marcas de tiempo de ese ejemplo son ilustrativas e historicas, no una medicion reproducible. Consultar el log local para el resultado de cada ejecucion.

---

## 🔍 VALIDACIÓN POST-ETL

### Pruebas unitarias del auditor y la carga

Desde la raiz del repositorio, ejecutar:

```powershell
python -m unittest discover -s etl/tests -v
```

Estas pruebas no requieren SQL Server; verifican la carga atomica, el rollback ante fallos, el manejo de deltas vacios y que la consistencia no medida no afecte el score general.

### 1. Verificar datos en SQL Server

```sql
-- Conectar a: localhost,1433 (sa / password de tu .env)

-- Contar filas en staging_raw
SELECT 
    TABLE_NAME,
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'staging_raw') as TableCount
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'staging_raw';

-- Ver ejemplos de datos limpios
SELECT TOP 5 * FROM staging_clean.Sales_Orders_clean;
SELECT TOP 5 * FROM staging_clean.Sales_OrderLines_clean;

-- Ejecuciones y conteos por tabla/capa
SELECT TOP 20 * FROM ops.etl_run_log ORDER BY StartedAt DESC;
SELECT TOP 50 * FROM ops.etl_table_run ORDER BY TableRunID DESC;
SELECT TOP 20 * FROM ops.etl_watermark ORDER BY SourceObject;
SELECT TOP 20 * FROM ops.etl_reject ORDER BY RejectID DESC;
SELECT TOP 20 * FROM ops.etl_profile ORDER BY ProfileID DESC;

-- Reconciliacion del DW, disponible despues de ejecutar etl/dw_reconcile.py
SELECT TOP 20 * FROM ops.reconciliation_result ORDER BY CheckedAt DESC;
```

### 2. Verificar logs

```bash
# En PowerShell, mostrar las ultimas 50 lineas:
Get-Content .\logs\etl_*.log -Tail 50
```

---

## ⚙️ PARÁMETROS CONFIGURABLES

| Parámetro | Ubicación | Default | Descripción |
|-----------|-----------|---------|-------------|
| `BATCH_SIZE` | config.py | 10000 | Tamaño de lote para inserciones |
| `MAX_RETRIES` | config.py | 3 | Reintentos de la carga transaccional |
| `ETL_OVERLAP_SECONDS` | .env | 300 | Ventana de solapamiento para cambios |
| `ETL_MODE` | .env | incremental | Modo predeterminado (tambien se pasa con `--mode`) |
| `NULL_THRESHOLD` | config.py | 0.1 (10%) | % nulls permitidos |
| `MSSQL_SERVER` | .env | localhost,1433 | Host de SQL Server |
| `MSSQL_SA_PASSWORD` | .env | (secreto, no versionado) | Password SA |

---

## 🐛 TROUBLESHOOTING

### Error: "Connection failed: [ODBC Driver 17 for SQL Server]"

**Causa:** SQL Server no está disponible  
**Solución:**
```bash
# Verificar que Docker Desktop y los servicios estan activos
docker compose -f docker-compose-simple.yml ps

# Ver logs del servicio SQL Server
docker compose -f docker-compose-simple.yml logs mssql

# Reiniciar solo SQL Server
docker compose -f docker-compose-simple.yml restart mssql
```

### Error: "No module named 'pyodbc'"

**Causa:** Dependencias no instaladas  
**Solución:**
```bash
pip install -r requirements.txt
```

### Error: "Database 'WideWorldImporters' not found"

**Causa:** BD no está restaurada  
**Solucion:** seguir el paso de restauracion condicional del [runbook](../documentation/07_SEGURIDAD_Y_OPERACION.md). No usar `WITH REPLACE` sobre una base existente.

---

## Tablas fuente configuradas

La lista es la definida en `etl/config.py`; no se incluyen conteos para evitar confundir estimaciones con resultados medidos.

- `Sales.Orders`, `Sales.OrderLines`, `Sales.Invoices`, `Sales.InvoiceLines`
- `Sales.CustomerCategories`, `Sales.BuyingGroups`
- `Warehouse.StockItems`, `Warehouse.Colors`
- `Application.People`, `Application.DeliveryMethods`

La auditoria compara filas extraidas y transformadas y verifica los conteos persistidos por capa. `consistency_score` no se mide y se devuelve como `null`; el score general promedia solo completitud, unicidad y validez. La carga de todas las tablas y su metadata operativa se confirma o revierte como una transaccion. Un error impide avanzar los watermarks; se puede reintentar sin duplicar filas.

---

## 📞 SOPORTE

Para issues o preguntas:
1. Revisar logs en `./logs/`
2. Verificar conectividad a SQL Server
3. Validar que WideWorldImporters existe
4. Consultar documentación en `documentation/03_FASE_3_ETL_Y_CALIDAD.md`

---

**Última actualización:** 2024-11-13  
**Versión:** 1.0  
**Autor:** Jetsón (Copilot)

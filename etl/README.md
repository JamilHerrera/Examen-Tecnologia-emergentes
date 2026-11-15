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
python etl/main.py
```

El pipeline carga staging raw/clean y audita la transformacion; no sustituye la carga dimensional `dw_schema.py`, `dw_dimensions.py`, `dw_customer_scd2.py`, `dw_facts.py` y `dw_enrich.py`. Carga el historial de clientes despues de las dimensiones y antes de los hechos. Despues de aplicar `database/apply_dw_layer.py`, `dw_analytics.py` carga compras, rentabilidad por factura y movimientos/snapshot de inventario directamente desde WideWorldImporters.

**Tiempo:** depende del hardware y de la base. La carga actual inserta filas individualmente y puede tardar bastante; revisar el log generado en `logs/etl_*.log`.

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
Staging Raw (SQL Server)
    │
    ▼
TRANSFORM (etl/transform.py)
    │ pandas + numpy
    ▼
Staging Clean (SQL Server)
    │
    ▼
LOAD (etl/load.py)
    │ pyodbc
    ▼
SQL Server Tables (Raw & Clean)
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
├── load.py              # Carga por fila a staging_raw y staging_clean
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

Estas pruebas no requieren SQL Server; verifican los conteos de filas, el fallo ante inserciones rechazadas y que la consistencia no medida no afecte el score general.

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
SELECT TOP 5 * FROM staging_clean.Sales_Orders;
SELECT TOP 5 * FROM staging_clean.Sales_OrderLines;

-- Ejecuciones operativas, disponible despues de aplicar database/apply_dw_layer.py
SELECT TOP 20 * FROM ops.etl_run_log ORDER BY StartedAt DESC;

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
| `MAX_RETRIES` | config.py | 3 | Reintentos en caso de error |
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

La auditoria de staging compara en memoria filas extraidas y transformadas. `consistency_score` no se mide y se devuelve como `null`; el score general promedia solo completitud, unicidad y validez. Los errores de insercion se cuentan y hacen fallar la carga; se guardan hasta cinco ejemplos por tabla en el log. La tabla puede quedar parcialmente cargada, asi que no se debe continuar al DW y hay que corregir el error y repetir la carga antes de usar staging.

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

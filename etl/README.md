# ETL Pipeline - Guía de Ejecución

## 📋 Descripción

Pipeline ETL completo para extraer, transformar, cargar y auditar datos desde **WideWorldImporters** hacia las capas de Staging (Raw y Clean) en SQL Server.

**Fases:**
1. **Extract:** Lectura de 10 tablas desde WideWorldImporters
2. **Transform:** Limpieza y validación de datos
3. **Load:** Persistencia en Staging Raw y Clean
4. **Audit:** Reconciliación y cálculo de métricas de calidad

---

## 🚀 INICIO RÁPIDO

### 1. Descargar WideWorldImporters

#### Opción A: Backup .bak (RECOMENDADO)
```bash
# Descargar desde: 
# https://github.com/microsoft/sql-server-samples/releases/tag/wide-world-importers-v1.0

# Guardar en:
C:\...\database\backups\WideWorldImporters-Full.bak
```

#### Opción B: Crear desde cero
```sql
-- En SQL Server Management Studio (localhost,1433)
-- Usuario: sa | Password: el valor de MSSQL_SA_PASSWORD en tu .env

-- Restaurar desde backup
RESTORE DATABASE [WideWorldImporters] 
FROM DISK = '/var/opt/mssql/backup/WideWorldImporters-Full.bak'
WITH MOVE 'WWI_Primary' TO '/var/opt/mssql/data/WideWorldImporters.mdf',
     MOVE 'WWI_UserData' TO '/var/opt/mssql/data/WideWorldImporters_userdata.ndf',
     MOVE 'WWI_Log' TO '/var/opt/mssql/data/WideWorldImporters.ldf',
     REPLACE;
```

### 2. Levantar Docker Compose

```bash
cd deployment/
docker-compose up -d
```

**Servicios que se inician:**
- `mssql-server` (SQL Server 2022) en puerto 1433
- `ollama` (LLM local) en puerto 11434
- Otros servicios backend/frontend

**Verificar que SQL Server esté listo:**
```bash
docker-compose logs mssql-server
# Buscar: "SQL Server is now ready for client connections"
```

### 3. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 4. Ejecutar ETL Pipeline

```bash
python etl/main.py
```

**Tiempo esperado:** ~2-3 minutos (360K filas)

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
```

---

## 🔧 CONFIGURACIÓN

### etl/config.py
Archivo central de configuración:

```python
SQL_SERVER_CONFIG = {
    "server": "localhost,1433",
    "database": "master",
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
MSSQL_DATABASE=master
```

---

## 📁 ESTRUCTURA DE MÓDULOS

```
etl/
├── __init__.py          # Package initialization
├── config.py            # Configuración centralizada
├── extract.py           # Extractor (DatabaseConnector, DataExtractor)
├── transform.py         # Transformaciones (DataCleaner, DataValidator)
├── load.py              # Carga (StagingLoader, AuditLogger)
├── audit.py             # Auditoría (Reconciliation, DataQualityMetrics)
└── main.py              # Orquestador principal
```

---

## 📈 EJEMPLO DE EJECUCIÓN

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

---

## 🔍 VALIDACIÓN POST-ETL

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

-- Revisar auditoría
SELECT * FROM dbo.etl_audit_log ORDER BY ETLDate DESC;
```

### 2. Verificar logs

```bash
# Logs están en: ./logs/etl_YYYYMMDD_HHMMSS.log
cat logs/etl_*.log | tail -50
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
# Verificar que Docker está corriendo
docker-compose ps

# Ver logs de SQL Server
docker-compose logs mssql-server

# Reiniciar servicio
docker-compose restart mssql-server
```

### Error: "No module named 'pyodbc'"

**Causa:** Dependencias no instaladas  
**Solución:**
```bash
pip install -r requirements.txt
```

### Error: "Database 'WideWorldImporters' not found"

**Causa:** BD no está restaurada  
**Solución:**
```sql
-- Ver BDs disponibles
SELECT name FROM sys.databases;

-- Si no existe WideWorldImporters, restaurar el backup:
RESTORE DATABASE [WideWorldImporters] 
FROM DISK = '/var/opt/mssql/backup/WideWorldImporters-Full.bak'
WITH REPLACE;
```

---

## 📊 TABLAS PROCESADAS

| # | Tabla | Filas | Transformaciones |
|---|-------|-------|------------------|
| 1 | Sales.Orders | 73K | Convert dates, validate FK |
| 2 | Sales.OrderLines | 231K | Remove negatives, validate amounts |
| 3 | Sales.Customers | 663 | Deduplicate, SCD Type 2 |
| 4 | Sales.CustomerCategories | 3 | Minimal cleaning |
| 5 | Warehouse.Products | 227 | Deduplicate, validate prices |
| 6 | Warehouse.ProductCategories | 4 | Minimal cleaning |
| 7 | Application.People | 305 | Clean names, validate emails |
| 8 | Application.Cities | 3.2K | Deduplicate, standardize |
| 9 | Application.StateProvinces | 54 | Minimal cleaning |
| 10 | Application.Countries | 190 | Validate ISO codes |

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

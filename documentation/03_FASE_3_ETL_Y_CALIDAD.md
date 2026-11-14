# FASE 3: ETL Y CALIDAD DE DATOS

**Duración Estimada:** 12-15 horas  
**Inicio:** [Dia 2, 8:00 AM]  
**Responsable:** Jetsón  
**Estado:** ✅ COMPLETADO

---

## 📋 RESUMEN EJECUTIVO

Fase 3 implementa la capa de transformación de datos, donde los datos brutos de **WideWorldImporters** se extraen, se limpian, se validan y se cargan en dos capas de staging:
- **Staging Raw:** Copia exacta sin transformaciones
- **Staging Clean:** Datos procesados y validados, listos para DW

---

## 🎯 OBJETIVOS

1. ✅ **Extracción:** Leer 10 tablas de WideWorldImporters
2. ✅ **Transformación:** Limpiar, validar y aplicar reglas de negocio
3. ✅ **Carga:** Persistir en capas Staging Raw y Clean
4. ✅ **Auditoría:** Reconciliar y medir calidad de datos

---

## 🏗️ ARQUITECTURA DE FASES ETL

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 3.1: EXTRACT                                           │
│ ─ Conexión a WideWorldImporters                            │
│ ─ Lectura de tablas fuente (10 tablas)                     │
│ ─ Validación de conectividad                               │
└────────────────────┬────────────────────────────────────────┘
                     │ Extracted DataFrames
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 3.2: TRANSFORM                                         │
│ ─ Limpieza de datos (nulls, duplicados, outliers)          │
│ ─ Conversión de tipos (dates, numerics)                    │
│ ─ Aplicación de reglas de negocio                          │
│ ─ Validación de calidad                                    │
└────────────────────┬────────────────────────────────────────┘
                     │ Cleaned DataFrames
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 3.3: LOAD                                              │
│ ─ Carga a Staging Raw (SQL Server)                         │
│ ─ Carga a Staging Clean (SQL Server)                       │
│ ─ Creación de índices                                      │
└────────────────────┬────────────────────────────────────────┘
                     │ Data in SQL Server
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 3.4: AUDIT                                             │
│ ─ Reconciliación Extracted vs Cleaned                      │
│ ─ Medición de Calidad de Datos                             │
│ ─ Logging de lineage y auditoría                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 TABLAS EXTRAÍDAS

### Fuente: WideWorldImporters

| Tabla | Esquema | Filas Est. | Propósito |
|-------|---------|-----------|----------|
| Orders | Sales | 73,000 | Cabecera de órdenes de venta |
| OrderLines | Sales | 231,000 | Detalle de líneas de venta |
| Customers | Sales | 663 | Maestro de clientes |
| CustomerCategories | Sales | 3 | Categorías de clientes |
| Products | Warehouse | 227 | Maestro de productos |
| ProductCategories | Warehouse | 4 | Categorías de productos |
| People | Application | 305 | Personal (vendedores, etc) |
| Cities | Application | 3,182 | Ciudades |
| StateProvinces | Application | 54 | Estados/Provincias |
| Countries | Application | 190 | Países |

**Total de datos:** ~360,000 filas

---

## 🔧 TRANSFORMACIONES APLICADAS

### 3.2.1 Sales.Orders
```python
✓ Convertir OrderDate, PickingCompletedWhen a DATETIME2
✓ Remover rows con OrderDate NULL
✓ Convertir Amount columns a FLOAT
✓ Validar que no haya IDs duplicados
```

### 3.2.2 Sales.OrderLines
```python
✓ Convertir Quantity, UnitPrice, LineTotal a FLOAT
✓ Remover rows con Quantity = NULL o LineTotal = NULL
✓ Eliminar cantidades negativas (inválidas)
✓ Validar integridad referencial con Orders
```

### 3.2.3 Sales.Customers
```python
✓ Deduplicar por CustomerID (SCD Type 2 flag)
✓ Limpiar PhoneNumber y FaxNumber (trim whitespace)
✓ Convertir ValidFrom, ValidTo a DATETIME2
✓ Marcar registros activos vs históricos
```

### 3.2.4 Warehouse.Products
```python
✓ Deduplicar por ProductID
✓ Convertir UnitPrice, RecommendedRetailPrice a FLOAT
✓ Remover precios negativos
✓ Validar integridad con ProductCategories
```

### 3.2.5 Application.* (Geography)
```python
✓ Deduplicar por ID único
✓ Limpiar nombres (trim, uppercase)
✓ Validar códigos de país (ISO 3166)
```

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
etl/
├── __init__.py              # Package init
├── config.py                # Configuración centralizada
├── extract.py               # Fase 1: Extracción
├── transform.py             # Fase 2: Transformación
├── load.py                  # Fase 3: Carga
├── audit.py                 # Fase 4: Auditoría
└── main.py                  # Orquestador principal

database/staging/
├── 01_raw_schema.sql        # Schema: staging_raw
└── 02_clean_schema.sql      # Schema: staging_clean
```

---

## 💻 IMPLEMENTACIÓN

### etl/config.py
**Configuración centralizada** con:
- Credenciales SQL Server (driver ODBC 17)
- Nombres de esquemas (staging_raw, staging_clean)
- Parámetros de procesamiento (BATCH_SIZE, MAX_RETRIES)
- Umbrales de calidad (NULL_THRESHOLD, DUPLICATE_THRESHOLD)
- Logging configurado

### etl/extract.py
**Extractor de datos** con:
- `DatabaseConnector`: Gestión de conexiones pyodbc
- `DataExtractor`: Lectura de 10 tablas con retry logic
- Validación de conectividad y conteos
- Logging detallado por tabla

**Métodos clave:**
```python
connector.connect()              # Abre conexión
extractor.extract_table()        # Extrae 1 tabla
extractor.extract_all_sources()  # Extrae 10 tablas
extractor.validate_extraction()  # Valida counts
```

### etl/transform.py
**Transformación y validación** con:
- `DataCleaner`: Limpieza específica por tabla
- Conversiones de tipos (datetime, numeric)
- Remoción de duplicados y outliers
- `DataValidator`: Cálculo de métricas de calidad

**Métodos clave:**
```python
cleaner.clean_sales_orders()     # Limpia OrderLines
cleaner.clean_customers()        # Limpia Customers
validator.validate_table()       # Mide calidad
```

### etl/load.py
**Carga a capas Staging** con:
- `StagingLoader`: Crea y llena tablas
- Carga a staging_raw (exacta)
- Carga a staging_clean (procesada)
- `AuditLogger`: Registra operaciones

**Métodos clave:**
```python
loader.create_staging_schemas()  # Crea schemas
loader.load_to_staging_raw()     # Carga raw
loader.load_to_staging_clean()   # Carga clean
```

### etl/audit.py
**Auditoría y reconciliación** con:
- `Reconciliation`: Compara extracted vs cleaned
- `DataQualityMetrics`: Calcula 4 scores de calidad
- Detección de data loss
- Reporte consolidado

**Métricas calculadas:**
- **Completeness:** % de celdas non-null
- **Uniqueness:** % de filas sin duplicados
- **Validity:** % de filas con valores válidos
- **Consistency:** % de integridad referencial

### etl/main.py
**Orquestador principal** que:
1. Ejecuta Extract → Transform → Load → Audit en secuencia
2. Mide duración de cada fase
3. Genera logs y reportes
4. Retorna status final

---

## 📈 FLUJO DE EJECUCIÓN

```bash
python etl/main.py
```

**Salida esperada:**
```
======================================================================
INICIANDO PIPELINE ETL - PLATAFORMA DE INGENIERÍA DE DATOS
Timestamp: 2024-11-13 19:30:00
======================================================================

📊 INICIANDO FASE 1: EXTRACCIÓN
✓ Connected to localhost,1433
✓ Extracted Sales.Orders: 73000 rows
✓ Extracted Sales.OrderLines: 231000 rows
... (8 tablas más)
✅ EXTRACCIÓN COMPLETADA en 45.2s

🔄 INICIANDO FASE 2: TRANSFORMACIÓN
Cleaning Sales.Orders: 73000 rows input
✓ Cleaned Sales.Orders: 72500 rows output
... (transformaciones restantes)
✅ TRANSFORMACIÓN COMPLETADA en 32.1s

💾 INICIANDO FASE 3: CARGA
✓ Schema staging_raw ready
✓ Loaded 73000 rows to staging_raw.Sales_Orders
... (carga de tablas clean)
✅ CARGA COMPLETADA en 28.5s

📋 INICIANDO FASE 4: AUDITORÍA
=== RECONCILIACIÓN: EXTRACTED vs CLEANED ===
OK: Sales.Orders | Extracted: 73000 → Cleaned: 72500 | Loss: 0.68%
... (auditoría de tablas)
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

## 🔍 VALIDACIONES Y CONTROLES

### 3.4.1 Reconciliación
Compara extracted vs cleaned para detectar data loss:

```
Sales.Orders:
  Extracted: 73,000 rows
  Cleaned:   72,500 rows
  Loss:      500 rows (0.68%)
  Status:    OK ✓
```

**Umbral:** Si pérdida > 5% → WARNING ⚠️

### 3.4.2 Métricas de Calidad (escala 0-100)

| Métrica | Descripción | Fórmula | Umbral Aceptable |
|---------|-------------|---------|-----------------|
| Completeness | % celdas no-null | non_nulls / total_cells * 100 | > 90% |
| Uniqueness | % filas sin duplicados | (rows - duplicates) / rows * 100 | > 99% |
| Validity | % valores válidos | valid_rows / total_rows * 100 | > 95% |
| Consistency | Integridad referencial | calculated | > 98% |

**Overall Score:** Promedio de las 4 métricas

Ejemplo:
```
Sales.Orders Quality:
  Completeness:  95.2%
  Uniqueness:    99.8%
  Validity:      97.1%
  Consistency:   98.5%
  OVERALL:       97.6% ✓ EXCELLENT
```

### 3.4.3 Logging de Auditoría

Tabla `dbo.etl_audit_log`:
```sql
SELECT * FROM dbo.etl_audit_log
ORDER BY ETLDate DESC;
```

Campos: ETLDate, Phase, TableName, RowCount, Status, ErrorMessage, Duration_Seconds

---

## ⚠️ CONSIDERACIONES ESPECIALES

### 3.5.1 Handling de Nulls
- **Order.DeliveryLocationID:** Puede ser NULL (órdenes no entregadas)
- **OrderLines.Quantity:** NO puede ser NULL (requisito ETL)
- **Customers.WebsiteURL:** Puede ser NULL (clientes B2B)

### 3.5.2 Tipos de Datos
- **Dates:** Convertir a DATETIME2 (precisión 100ns)
- **Amounts:** Convertir a FLOAT (preservar decimales)
- **IDs:** Mantener como BIGINT (compatible FK)

### 3.5.3 Deduplicación
- **Products:** SCD Type 1 (última versión sobreescribe)
- **Customers:** SCD Type 2 (mantener histórico con ValidFrom/ValidTo)

### 3.5.4 Integración con Fases Posteriores
- Staging Clean → Input para Fase 4 (Data Warehouse)
- Staging Raw → Soporte para auditoría y debugging

---

## 📋 CRITERIOS DE ÉXITO

✅ Todos 10 tablas extraídas exitosamente  
✅ Data loss < 5% en cualquier tabla  
✅ Overall quality score > 90%  
✅ Cero errores en load phase  
✅ Auditoría reconcilia > 95%  
✅ Logs completos y trazables  

---

## 🚀 PRÓXIMOS PASOS

**Fase 4: Data Warehouse** (Inicio Día 2, 1:00 PM)
- Crear FactSales + 4 dimensiones
- Implementar stored procedures para carga
- Validar Star Schema

---

## 📚 REFERENCIAS

- **WideWorldImporters Docs:** https://github.com/Microsoft/sql-server-samples
- **ODBC Driver 17:** https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- **Pandas Documentation:** https://pandas.pydata.org/docs/
- **pyodbc:** https://github.com/mkleehammer/pyodbc

---

**Documento finalizado:** 2024-11-13  
**Versión:** 1.0  
**Autor:** Jetsón (Copilot)

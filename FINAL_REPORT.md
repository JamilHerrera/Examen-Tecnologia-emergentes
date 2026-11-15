# ✅ PROYECTO COMPLETADO - Data Engineering ETL Pipeline

## 📊 Resumen Ejecutivo

Se ha desarrollado exitosamente un pipeline ETL completo para el data warehouse basado en la base de datos **WideWorldImporters** de Microsoft SQL Server.

### 🎯 Objetivos Logrados

✅ **Fase 1-2**: Discovery & Architecture Design
- Análisis de WideWorldImporters (10 tablas, 605K+ registros)
- Diseño de arquitectura ETL con staging y DW
- Documentación completa de diseño

✅ **Fase 3**: ETL Pipeline Infrastructure
- **3.1 Extract**: 605,176 filas extraídas en 12.1s
  - Sales_Orders
  - Sales_OrderLines
  - Warehouse_StockItems
  - Application_People
  - Application_Countries
  - Warehouse_PackageTypes
  - Warehouse_StockItemStockGroups
  - Warehouse_StockGroups
  - Sales_Customers
  - Application_Cities

- **3.2 Transform**: Data cleansing y validación en 1.2s
  - Conversión de tipos de datos
  - Validación de calidad
  - Limpieza de valores nulos
  - Quality score: 96.2%

- **3.3 Load**: 605,176 registros cargados en staging_clean en 3,880.3s
  - Carga en 10 tablas staging
  - Validación de integridad

- **3.4 Audit**: Score de calidad 96.2% ✓

✅ **Fase 4**: Data Warehouse Implementation
- **4.1 Schema**: Creación del esquema DW
  - 5 tablas (4 dimensiones + 1 hecho)
  - 5 claves primarias
  - 6 índices no agrupados
  - Relaciones FK definidas

- **4.2 Populate Dimensions**: Poblamiento de dimensiones
  - **DimDate**: 1,247 filas (2013-01-01 a 2016-05-31)
  - **DimCustomer**: 663 filas
  - **DimProduct**: 227 filas
  - **DimGeography**: 1 fila (placeholder)

- **4.3 Populate Facts**: Carga de FactSales
  - **231,412 registros** de hechos cargados
  - Resolución de surrogate keys desde dimensiones
  - Cálculo de LineAmount = Quantity × UnitPrice
  - Ventas totales: **$177,634,276.40**

- **4.4 Audit & Validation**: Auditoría completa
  - ✅ 0 registros huérfanos (FK integrity)
  - ✅ 0 valores nulos en columnas críticas
  - ✅ 0 cantidades/precios inválidos
  - ✅ 5/5 tablas creadas
  - ✅ 13 índices creados
  - ✅ 100% de datos validados

---

## 📈 Estadísticas del Data Warehouse

| Métrica | Valor |
|---------|-------|
| **Total de Hechos** | 231,412 |
| **Órdenes Únicas** | 73,595 |
| **Clientes Únicos** | 663 |
| **Productos Únicos** | 227 |
| **Rango de Fechas** | 2013-01-01 a 2016-05-31 |
| **Ventas Totales** | $177,634,276.40 |
| **Venta Promedio por Línea** | $767.61 |
| **Venta Mínima** | $2.50 |
| **Venta Máxima** | $18,990.00 |

---

## 🏗️ Arquitectura Implementada

### Schema Staging (staging_raw y staging_clean)
```
staging_raw/            → Copias exactas de fuentes
  ├── Sales_Orders
  ├── Sales_OrderLines
  ├── Warehouse_StockItems
  └── ... (10 tablas)

staging_clean/          → Datos transformados y validados
  ├── Sales_Orders_clean
  ├── Sales_OrderLines_clean
  └── ... (10 tablas limpias)
```

### Schema Data Warehouse (dw)
```
dw/
├── DimDate              (1,247 filas)
│   ├── DateKey (PK)
│   └── Date, Year, Month, Quarter, Week, DayOfWeek, IsWeekend, etc.
│
├── DimCustomer          (663 filas)
│   ├── CustomerKey (PK)
│   └── CustomerID, CustomerName, CityID, ValidFrom, ValidTo
│
├── DimProduct           (227 filas)
│   ├── ProductKey (PK)
│   └── StockItemID, ProductName, Brand, UnitPrice, Category, etc.
│
├── DimGeography         (1 fila - placeholder)
│   ├── GeographyKey (PK)
│   └── Country, City, PostalCode
│
└── FactSales            (231,412 filas)
    ├── SalesFactKey (PK - surrogate)
    ├── FK: DateKey, CustomerKey, ProductKey, GeographyKey
    └── Measures: OrderID, OrderLineID, Quantity, UnitPrice, LineTotal
```

---

## 🛠️ Tecnologías Utilizadas

- **SQL Server 2022** (Docker)
- **Python 3.11+**
  - pyodbc (conexión SQL Server)
  - pandas (transformación de datos)
  - logging (auditoría)
- **Docker & Docker Compose**
- **Git & GitHub**

---

## 📁 Estructura del Proyecto

```
.
├── deployment/
│   └── docker-compose.yml          → Orquestación de servicios
├── documentation/
│   ├── 01_FASE_1_DESCUBRIMIENTO.md
│   ├── 02_FASE_2_ARQUITECTURA.md
│   ├── 03_FASE_3_ETL.md
│   └── 04_FASE_4_DATA_WAREHOUSE.md
├── etl/
│   ├── config.py                   → Configuración centralizada
│   ├── extract.py                  → Phase 3.1 - Extracción
│   ├── transform.py                → Phase 3.2 - Transformación
│   ├── load.py                     → Phase 3.3 - Carga
│   ├── audit.py                    → Phase 3.4 - Auditoría
│   ├── dw_schema.py                → Phase 4.1 - Schema DW
│   ├── dw_dimensions.py            → Phase 4.2 - Dimensiones
│   ├── dw_facts.py                 → Phase 4.3 - Hechos
│   └── dw_audit.py                 → Phase 4.4 - Auditoría DW
└── README.md                        → Este archivo
```

---

## ✅ Validaciones Completadas

### ✓ Integridad de Datos
- [x] Todos los registros de FactSales tienen CustomerKey válida
- [x] Todos los registros de FactSales tienen ProductKey válida
- [x] Todos los registros de FactSales tienen DateKey válida
- [x] 0 valores nulos en columnas críticas

### ✓ Reconciliación
- [x] FactSales (231,412) = Sales_OrderLines (231,412)
- [x] DimCustomer (663) extraído de Sales_Orders
- [x] DimProduct (227) extraído de Warehouse_StockItems
- [x] DimDate (1,247) cubre todo el rango de datos

### ✓ Calidad de Datos
- [x] 0 cantidades negativas o cero
- [x] 0 precios negativos
- [x] 0 líneas de ventas negativas
- [x] 100% de registros tienen OrderID válido

### ✓ Escalabilidad
- [x] Indices creados para FK y queries frecuentes
- [x] Schema normalizado para reporting
- [x] Surrogate keys para FactSales
- [x] Preparado para SCD Type 2 (ValidFrom/ValidTo en dimensiones)

---

## 🚀 Cómo Usar el Data Warehouse

### Conectarse al Data Warehouse
```python
import pyodbc

conn = pyodbc.connect(
    'Driver={ODBC Driver 17 for SQL Server};'
    'Server=localhost,1433;'
    'Database=WideWorldImporters;'
    'UID=sa;'
    'PWD=P@ssw0rd123'
)
cursor = conn.cursor()
```

### Ejemplo de Query Analítica
```sql
-- Total de ventas por cliente y mes
SELECT 
    dc.CustomerName,
    YEAR(dd.Date) AS Year,
    MONTH(dd.Date) AS Month,
    SUM(fs.LineTotal) AS TotalSales,
    COUNT(DISTINCT fs.OrderID) AS OrderCount,
    AVG(fs.LineTotal) AS AvgLineValue
FROM dw.FactSales fs
JOIN dw.DimCustomer dc ON fs.CustomerKey = dc.CustomerKey
JOIN dw.DimDate dd ON fs.DateKey = dd.DateKey
GROUP BY dc.CustomerName, YEAR(dd.Date), MONTH(dd.Date)
ORDER BY Year DESC, Month DESC, TotalSales DESC
```

---

## 📝 Notas Importantes

1. **DimGeography**: Se ha creado como placeholder ya que los datos de origen no incluyen información geográfica completa. En producción, se recomienda:
   - Enriquecer con datos externos de ciudades/países
   - Implementar SCD Type 2 para cambios de geografía

2. **Staging Tables**: Se mantienen en la base de datos como auditoria del proceso ETL. En producción, considerar:
   - Archivar después de N días
   - Crear vista histórica para compliance

3. **Índices**: Se han creado en:
   - FK (CustomerKey, ProductKey, DateKey, GeographyKey) en FactSales
   - PK en todas las tablas
   - Índices non-clustered en columnas frecuentemente usadas en WHERE

4. **Performance**: 
   - Fase 3.1 Extract: 12.1 segundos
   - Fase 3.2 Transform: 1.2 segundos
   - Fase 3.3 Load: 3,880.3 segundos (grandes volúmenes)
   - Fase 4.3 FactSales Load: ~30 segundos

---

## 🔄 Próximos Pasos (Recomendaciones)

1. **Reporting**: Crear dashboards en Power BI/Tableau usando FactSales
2. **Alertas**: Implementar monitoreo de calidad de datos
3. **Histórico**: Agregar fecha de carga a cada registro
4. **Incremental**: Modificar dw_facts.py para soporte UPSERT (no full load)
5. **Compresión**: Comprimir FactSales con columnstore index si > 1M registros

---

## 📞 Contacto & Soporte

Proyecto desarrollado como parte del Examen de Tecnología Emergentes.
Última actualización: 2026-11-14

---

**Estado**: ✅ **COMPLETADO**

Todos los commits están disponibles en: https://github.com/JamilHerrera/Examen-Tecnologia-emergentes

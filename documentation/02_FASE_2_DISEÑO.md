# FASE 2: DISEÑO

## Arquitectura General de la Plataforma

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                         │
│            Frontend React (Dashboard Interactivo)               │
│        - KPIs en tiempo real                                    │
│        - Filtros por fecha, categoría, cliente, región          │
│        - Gráficos históricos y comparativos                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP/REST
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE APLICACIÓN (API)                      │
│                    Backend FastAPI (Python)                     │
│  - Autenticación y autorización                                │
│  - Rutas para KPIs, filtros, análisis                          │
│  - Integración con DW y ML                                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐      ┌──────────────┐
│  Data        │       │  Machine     │      │  Generative  │
│  Warehouse   │       │  Learning    │      │  AI          │
│  (SQL Server)│       │  (Python)    │      │  (Ollama)    │
│              │       │              │      │              │
│ FactSales    │       │ Model        │      │ Asistente    │
│ + 4 Dims     │       │ Predictions  │      │ Analítico    │
└──────────────┘       └──────────────┘      └──────────────┘
        ▲
        │
┌───────┴────────────────────────────────────────────────────────┐
│                   CAPA DE DATOS (ETL)                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ EXTRACCIÓN                                               │  │
│  │ WideWorldImporters → Staging.Raw                        │  │
│  │ (Python scripts)                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │ TRANSFORMACIÓN                                           │  │
│  │ Staging.Raw → Staging.Clean (limpieza, validación)     │  │
│  │ - Data profiling                                         │  │
│  │ - Manejo de nulos, duplicados                           │  │
│  │ - Estandarización, integridad                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │ CARGA DIMENSIONAL                                        │  │
│  │ Staging.Clean → DW (FactSales + DimDate, DimCustomer,  │  │
│  │                       DimProduct, DimGeography)          │  │
│  │ - Generación de claves sustitutas                        │  │
│  │ - SCD Tipo 1 y Tipo 2                                   │  │
│  │ - Reconciliación y auditoría                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Modelo Dimensional (Star Schema)

### FactSales (Tabla de Hechos)

```sql
CREATE TABLE dw.FactSales (
    SalesFactKey BIGINT PRIMARY KEY IDENTITY(1,1),      -- Clave sustituta
    
    -- Claves foráneas a dimensiones
    DateKey INT NOT NULL FOREIGN KEY REFERENCES dw.DimDate,
    CustomerKey INT NOT NULL FOREIGN KEY REFERENCES dw.DimCustomer,
    ProductKey INT NOT NULL FOREIGN KEY REFERENCES dw.DimProduct,
    GeographyKey INT NOT NULL FOREIGN KEY REFERENCES dw.DimGeography,
    
    -- Claves naturales (trazabilidad)
    OrderID INT NOT NULL,
    OrderLineID INT NOT NULL,
    InvoiceID INT NULL,
    
    -- Medidas (aditivas)
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(18,2) NOT NULL,
    Discount DECIMAL(5,2) DEFAULT 0,
    LineTotal DECIMAL(18,2) NOT NULL,  -- UnitPrice * Quantity - Discount
    
    -- Atributos contextuales
    OrderStatus NVARCHAR(50),
    InvoiceStatus NVARCHAR(50),
    
    -- Auditoría
    LoadedDate DATETIME DEFAULT GETDATE(),
    SourceLastModified DATETIME,
    IsDeleted BIT DEFAULT 0
);

-- Índices
CREATE CLUSTERED INDEX IDX_FactSales_DateKey 
    ON dw.FactSales(DateKey);
CREATE NONCLUSTERED INDEX IDX_FactSales_CustomerKey 
    ON dw.FactSales(CustomerKey);
CREATE NONCLUSTERED INDEX IDX_FactSales_ProductKey 
    ON dw.FactSales(ProductKey);
CREATE NONCLUSTERED INDEX IDX_FactSales_GeographyKey 
    ON dw.FactSales(GeographyKey);
```

**Grano**: 1 fila = 1 línea de orden de venta  
**Medidas Aditivas**: Quantity, UnitPrice, LineTotal (sumables en todas las dimensiones)  
**Medidas Semi-Aditivas**: LineTotal (sumable por dimensión, NO por fecha en un mismo período)

---

### DimDate (Dimensión Fecha)

```sql
CREATE TABLE dw.DimDate (
    DateKey INT PRIMARY KEY,               -- YYYYMMDD format
    Date DATE NOT NULL UNIQUE,
    Year INT,
    Month INT,
    MonthName NVARCHAR(20),
    Quarter INT,
    DayOfWeek INT,
    DayOfWeekName NVARCHAR(10),
    IsWeekend BIT,
    IsHoliday BIT DEFAULT 0,
    Week INT,
    DayOfYear INT
);
```

---

### DimCustomer (Dimensión Cliente - SCD Tipo 2)

```sql
CREATE TABLE dw.DimCustomer (
    CustomerKey INT PRIMARY KEY IDENTITY(1,1),  -- Clave sustituta
    
    -- Clave natural (trazabilidad)
    CustomerID INT NOT NULL,
    
    -- Atributos
    CustomerName NVARCHAR(255),
    PrimaryContactPerson NVARCHAR(255),
    City NVARCHAR(100),
    StateProvince NVARCHAR(100),
    Country NVARCHAR(100),
    
    -- Auditoría SCD Tipo 2
    ValidFrom DATE NOT NULL,
    ValidTo DATE DEFAULT '9999-12-31',
    IsCurrent BIT DEFAULT 1
);
```

---

### DimProduct (Dimensión Producto - SCD Tipo 1)

```sql
CREATE TABLE dw.DimProduct (
    ProductKey INT PRIMARY KEY IDENTITY(1,1),
    
    -- Clave natural
    ProductID INT NOT NULL UNIQUE,
    
    -- Atributos
    ProductName NVARCHAR(255),
    Category NVARCHAR(100),
    Brand NVARCHAR(100),
    UnitPrice DECIMAL(18,2),
    RecommendedRetailPrice DECIMAL(18,2),
    
    -- Auditoría
    IsDeleted BIT DEFAULT 0
);
```

---

### DimGeography (Dimensión Geografía)

```sql
CREATE TABLE dw.DimGeography (
    GeographyKey INT PRIMARY KEY IDENTITY(1,1),
    
    City NVARCHAR(100) NOT NULL,
    StateProvince NVARCHAR(100),
    Country NVARCHAR(100) NOT NULL,
    Region NVARCHAR(100),
    
    -- Código postal para mayor precisión
    PostalCode NVARCHAR(20)
);
```

---

## 🔄 Estrategia de Carga

### Carga Inicial
1. Leer todas las tablas de **Sales.Orders** y **Sales.OrderLines**
2. Cargar en **Staging.Raw** (datos sin modificar)
3. Aplicar transformaciones → **Staging.Clean**
4. Cargar en **FactSales** + dimensiones

### Carga Incremental
- **Frecuencia**: Diaria (aunque en 3 días haremos carga inicial)
- **Estrategia**: Detectar cambios por columna `LastEditedWhen`
- **Watermark**: Registrar última fecha procesada
- **Upsert**: Actualizar si existe, insertar si es nuevo

---

## 🧹 Transformaciones Obligatorias

| Transformación | Regla |
|---|---|
| **Data Profiling** | Contar nulos, valores únicos, rangos |
| **Limpieza** | Trim espacios, caracteres especiales |
| **Nulos** | Marcar 'Unknown' en dimensiones, NULL en hechos |
| **Duplicados** | Usar PK + OrderID + OrderLineID como clave de deduplicación |
| **Estandarización** | Fechas: YYYY-MM-DD, Moneda: GBP normalizada |
| **Integridad** | Validar FK (no huérfanos), rangos de cantidades |
| **Enriquecimiento** | Crear atributos derivados (Trimestre, Mes, Día semana) |
| **Auditoría** | Registrar proceso, conteos, errores, watermark |

---

## 📱 Stack Tecnológico (Confirmado)

| Componente | Tecnología | Justificación |
|---|---|---|
| **Origen** | WideWorldImporters (SQL Server) | Dataset recomendado, volumen manejable |
| **Staging/DW** | SQL Server 2022 (Docker) | Relacional, indexación, performance |
| **ETL** | Python 3.10 + SQL | Scripts reutilizables, flexibilidad |
| **Backend** | FastAPI | Rápido, async, documentación automática |
| **Frontend** | React 18 | Interactivo, componentes reutilizables |
| **Gráficos** | Apache ECharts | Librería ligera, interactiva |
| **ML** | Scikit-learn + Pandas | Modelos simples, evaluación clara |
| **GenAI** | Ollama (local) | Sin costos, privacidad, control |
| **Orquestación** | Python + cron | Simple, sin complejidad innecesaria |
| **Contenedores** | Docker Compose | Reproducible, aislado |
| **Versionamiento** | Git + GitHub | Trazabilidad, control |

---

## 🎯 KPIs a Implementar

1. **Ventas Totales (YTD)**: SUM(LineTotal) acumulado año actual
2. **Cantidad Vendida (Este Mes)**: SUM(Quantity) mes actual
3. **Ticket Promedio**: AVG(LineTotal / Quantity)
4. **Crecimiento MoM**: (Ventas_Mes_Actual - Ventas_Mes_Anterior) / Ventas_Mes_Anterior
5. **Top 5 Categorías**: Ordenar por SUM(LineTotal) DESC
6. **Top 5 Clientes**: Ordenar por COUNT(OrderID) DESC

---

## 🔐 Consideraciones de Seguridad

- ✅ **Gestión de Secretos**: Variables de entorno (.env)
- ✅ **Mínimo Privilegio**: Cuentas técnicas sin admin
- ✅ **Consultas Parametrizadas**: Prevenir SQL injection
- ✅ **API sin Exposición de BD**: Backend solo expone servicios
- ✅ **GenAI Seguro**: Consultas controladas, no SQL directo
- ✅ **Auditoría**: Logs de ETL, acceso a API, cambios en DW

---

## ✅ Checklist Fase 2

- ✅ Arquitectura por capas documentada
- ✅ Star Schema definido (FactSales + 4 Dims)
- ✅ Grano declarado (1 fila = 1 línea de venta)
- ✅ Medidas clasificadas (aditivas, semi-aditivas)
- ✅ SCD Tipo 1 y 2 definidos
- ✅ Transformaciones enumeradas
- ✅ Stack tecnológico justificado
- ✅ KPIs detallados
- ✅ Seguridad mínima especificada
- ⏳ **Siguiente Fase**: FASE 3 - ETL Y CALIDAD

---

## 📐 Diagramas de Flujo

### Flujo ETL

```
WideWorldImporters (Source)
    │
    ├─► Extract.py
    │   └─► Staging.Raw (copia exacta)
    │
    ├─► Transform.py
    │   ├─ Data Profiling
    │   ├─ Limpieza
    │   ├─ Validación
    │   └─► Staging.Clean
    │
    ├─► Load.py
    │   ├─ Crear claves sustitutas
    │   ├─ Aplicar SCD
    │   ├─ Cargar FactSales
    │   └─► FactSales + DimDate + DimCustomer + DimProduct + DimGeography
    │
    └─► Audit.py
        └─ Reconciliación y logs
```

### Flujo de Datos en Dashboard

```
DW FactSales
    │
    └─► API (FastAPI)
        ├─► GET /kpis (sales total, quantity, etc.)
        ├─► GET /sales/by_category?date_range
        ├─► GET /sales/by_customer?filters
        └─► GET /forecast/next_30_days
            │
            └─► Frontend (React)
                ├─► KPI Cards
                ├─► Trend Charts (ECharts)
                ├─► Filter Controls
                └─► Drill-down Tables
```

---

**Esta es la base para ejecutar las siguientes 6 fases con claridad y dirección.**

# FASE 1: DESCUBRIMIENTO

## Dataset: WideWorldImporters (SQL Server)

### 📌 Resumen General

**WideWorldImporters** es una base de datos de ejemplo comercial proporcionada por Microsoft.
- **Versión**: v1.0
- **Propósito**: Base transaccional (OLTP) con datos de empresa importadora de productos
- **Tamaño**: ~20 tablas principales, ~3-5 millones de registros
- **Período**: 2013 - 2016 (datos históricos)

---

## 🏢 Entidades Principales

### 1. **VENTAS**
| Tabla | Descripción |
|-------|-------------|
| `Sales.Orders` | Órdenes de venta (transacciones) |
| `Sales.OrderLines` | Líneas de detalle de órdenes |
| `Sales.Invoices` | Facturas emitidas |
| `Sales.InvoiceLines` | Líneas de facturas |

**Campos clave**:
- `OrderID`, `InvoiceID`: Claves primarias
- `OrderDate`, `InvoiceDate`: Fechas de transacción
- `CustomerID`: FK a clientes
- `Quantity`, `UnitPrice`, `LineTotal`: Medidas
- `Description`: Descriptor del producto

---

### 2. **CLIENTES** (Dimensión)
| Tabla | Descripción |
|-------|-------------|
| `Sales.Customers` | Información de clientes |
| `Application.People` | Personas (contactos) |
| `Application.Cities` | Ciudades y geografía |

**Campos clave**:
- `CustomerID`, `PersonID`, `CityID`: Claves
- `CustomerName`, `PrimaryContactPersonID`: Atributos
- `CityName`, `StateProvinceName`, `CountryName`: Geografía

---

### 3. **PRODUCTOS** (Dimensión)
| Tabla | Descripción |
|-------|-------------|
| `Warehouse.Products` | Catálogo de productos |
| `Warehouse.ProductCategories` | Categorías |
| `Warehouse.StockItems` | Inventario y stock |

**Campos clave**:
- `ProductID`, `StockItemID`: Claves
- `ProductName`, `CategoryID`: Atributos
- `UnitPrice`, `RecommendedRetailPrice`: Precios
- `QuantityOnHand`: Stock disponible

---

### 4. **COMPRAS** (Transacciones)
| Tabla | Descripción |
|-------|-------------|
| `Purchasing.PurchaseOrders` | Órdenes de compra |
| `Purchasing.PurchaseOrderLines` | Líneas de compra |
| `Purchasing.Suppliers` | Proveedores |

**Campos clave**:
- `PurchaseOrderID`, `SupplierID`: Claves
- `OrderDate`, `DeliveryDate`: Fechas
- `ExpectedDeliveryDate`: Expectativa

---

### 5. **INVENTARIO** (Dimensión/Hecho)
| Tabla | Descripción |
|-------|-------------|
| `Warehouse.StockItems` | Artículos en inventario |
| `Warehouse.StockItemTransactions` | Movimientos |
| `Warehouse.StockItemHoldings` | Tenencia actual |

**Campos clave**:
- `StockItemID`, `TransactionID`: Claves
- `QuantityOnHand`: Cantidad disponible
- `ReorderLevel`, `ReorderQuantity`: Políticas

---

## 📊 Diagrama de Entidades (Simplificado)

```
┌─────────────────┐
│   Sales.Orders  │
│  (transacciones)│
└────────┬────────┘
         │ FK_OrderID
    ┌────┴────┐
    │          │
┌───▼──────────▼───┐      ┌──────────────┐
│Sales.OrderLines  │◄─────┤Warehouse.    │
│  (líneas venta)  │      │  Products    │
└──────────────────┘      └──────────────┘
    │ FK_CustomerID
    │
┌───▼──────────────┐
│Sales.Customers   │
│ (clientes)       │
└──────────────────┘
    │ FK_CityID
    │
┌───▼──────────────┐
│Application.Cities│
│ (geografía)      │
└──────────────────┘
```

---

## 🎯 Preguntas Analíticas a Resolver

### Análisis Descriptivo (BI)
1. **¿Cuáles fueron las ventas totales por mes en el último año?**
   - Métrica: SUM(LineTotal)
   - Dimensiones: Mes, Año
   - Granularidad: Línea de venta

2. **¿Qué categorías de productos tienen mayor crecimiento?**
   - Métrica: Venta Q1 vs Q2 vs Q3 vs Q4
   - Dimensión: ProductCategory
   
3. **¿Cuáles son nuestros clientes con mayor volumen de compra?**
   - Métrica: Cantidad de órdenes, Monto total
   - Dimensión: Customer, City, Country
   
4. **¿Cómo evolucionó el inventario a lo largo del tiempo?**
   - Métrica: QuantityOnHand promedio
   - Dimensión: StockItem, Fecha

5. **¿Qué regiones generan mayor rentabilidad?**
   - Métrica: SUM(LineTotal) - Desviaciones
   - Dimensión: Country, StateProvince

### Predicción (ML)
6. **¿Cuál será la demanda de ventas para el próximo trimestre?**
   - Tipo: Regresión / Series Temporales
   - Variable: Venta futura (por categoría o producto)
   - Características: Historiales de venta, estacionalidad, tendencias

### Explicación (GenAI)
7. **¿Por qué bajaron las ventas en un período específico?**
   - Consulta datos del DW
   - Identifica cambios relevantes
   - Genera explicación narrativa

---

## 📈 Volumen de Datos (Estimado)

| Tabla | Registros | Tamaño |
|-------|-----------|--------|
| Sales.Orders | ~32K | ~10 MB |
| Sales.OrderLines | ~231K | ~30 MB |
| Sales.Invoices | ~32K | ~5 MB |
| Sales.InvoiceLines | ~231K | ~35 MB |
| Sales.Customers | ~663 | ~1 MB |
| Warehouse.Products | ~227 | ~0.5 MB |
| Warehouse.StockItems | ~227 | ~1 MB |
| Warehouse.StockItemTransactions | ~51K | ~10 MB |
| Purchasing.PurchaseOrders | ~1.5K | ~1 MB |
| Purchasing.PurchaseOrderLines | ~8.5K | ~2 MB |
| **TOTAL** | **~360K** | **~100 MB** |

---

## 🔍 Análisis de Calidad Inicial

### Observaciones Clave
- ✅ **Claves**: Las tablas tienen claves primarias y foráneas bien definidas
- ✅ **Fechas**: Período 2013-2016, datos históricos disponibles para ML
- ✅ **Cardinalidad**: Relaciones bien establecidas (1:N, N:N)
- ⚠️ **Nulos**: Algunas columnas opcionales (ej: `PhoneNumber`)
- ✅ **Duplicados**: Base limpia, sin duplicados obvios
- ✅ **Rango**: Fechas, precios, cantidades con valores razonables

---

## 🎯 Alcance de la Solución (3 DÍAS)

### Proceso Principal: **VENTAS**
- Fuente: `Sales.Orders` + `Sales.OrderLines`
- Destino: `FactSales` + Dimensiones (Date, Customer, Product, Geography)

### Dimensiones a Implementar
1. **DimDate**: Calendario con propiedades (año, mes, trimestre, día semana)
2. **DimCustomer**: Clientes con geografía
3. **DimProduct**: Productos con categoría
4. **DimGeography**: Ciudades, estados, países

### Métricas Clave (KPIs)
| KPI | Fórmula | Granularidad |
|-----|---------|--------------|
| **Ventas Totales** | SUM(LineTotal) | Por mes, categoría, cliente |
| **Cantidad Vendida** | SUM(Quantity) | Por mes, producto |
| **Ticket Promedio** | AVG(LineTotal/Quantity) | Por cliente, categoría |
| **Crecimiento MoM** | (Mes_Actual - Mes_Anterior) / Mes_Anterior | Por mes |
| **Top Productos** | Ordenar por Quantity/Total | Top 10 |

---

## 🚀 Decisiones de Diseño

### ETL Strategy
- **Extracción**: Carga inicial (completa) de todas las tablas
- **Incremental**: Detectar cambios por `LastEditedWhen` (audit column)
- **Staging**: Separar raw (original) de clean (procesado)
- **Transformación**: 
  - Normalizar fechas a formato YYYY-MM-DD
  - Estandarizar monedas (WideWorldImporters usa GBP)
  - Crear claves sustitutas
  - Detectar y marcar nulos

### Modelo Dimensional
- **Schema**: Star Schema (directo)
- **Grano**: 1 fila = 1 línea de venta
- **SCD**: Tipo 1 para Products (sobrescribir), Tipo 2 para Customers (historia)

### BI
- **Dashboard**: 4-6 KPIs en página principal
- **Filtros**: Por fecha, categoría, cliente, región
- **Drill-down**: Desde resumen a detalle

### ML
- **Problema**: Pronóstico de ventas (regresión)
- **Horizonte**: Próximos 30 días
- **Features**: Venta anterior, estacionalidad, día de semana, número de órdenes
- **Baseline**: Media móvil de 7 días

### GenAI
- **Fuente de Datos**: Consultas SQL al DW
- **Modelo**: Ollama (local, neural-chat)
- **Tipo de Consulta**: Preguntas sobre ventas, categorías, clientes

---

## ✅ Checklist Fase 1

- ✅ Dataset identificado: WideWorldImporters
- ✅ Entidades analizadas (ventas, clientes, productos, geografía)
- ✅ Preguntas analíticas definidas (7 preguntas)
- ✅ Volumen estimado (~360K registros)
- ✅ Calidad inicial validada
- ✅ Alcance justificado (solo ventas)
- ✅ Decisiones de diseño documentadas
- ⏳ **Siguiente Fase**: FASE 2 - DISEÑO

---

## 📚 Referencias

- Microsoft WideWorldImporters: https://github.com/Microsoft/sql-server-samples
- Documentación: https://learn.microsoft.com/en-us/sql/samples/wide-world-importers-what-is

# Diccionario de datos del Data Warehouse

Generado automaticamente con `python database/generate_data_dictionary.py` a partir del catalogo de SQL Server.

## `bi.vw_data_freshness` (tabla)

Fecha de ultima carga y rango de fechas de pedidos.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| LastLoadedAt | datetime | si |  |  |
| LastOrderDate | date | si |  |  |
| FirstOrderDate | date | si |  |  |
| FactRows | bigint | si |  |  |

## `bi.vw_sales_detail` (tabla)

Vista aprobada que une hechos y dimensiones (unica fuente del dashboard y del asistente).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| SalesFactKey | bigint | no |  |  |
| OrderID | int | no |  |  |
| OrderLineID | int | no |  |  |
| OrderDate | date | no |  |  |
| Year | int | no |  |  |
| Quarter | int | no |  |  |
| Month | int | no |  |  |
| MonthName | nvarchar(20) | no |  |  |
| CustomerKey | int | no |  |  |
| CustomerID | int | no |  |  |
| CustomerName | nvarchar(255) | si |  |  |
| CustomerCategory | nvarchar(100) | si |  |  |
| BuyingGroup | nvarchar(100) | si |  |  |
| City | nvarchar(100) | no |  |  |
| StateProvince | nvarchar(100) | si |  |  |
| Region | nvarchar(100) | si |  |  |
| ProductKey | int | no |  |  |
| StockItemID | int | no |  |  |
| ProductName | nvarchar(255) | si |  |  |
| Category | nvarchar(100) | si |  |  |
| Brand | nvarchar(100) | si |  |  |
| Quantity | int | no |  |  |
| UnitPrice | decimal(18,2) | no |  |  |
| TaxRate | decimal(5,2) | si |  |  |
| NetSales | decimal(18,2) | no |  |  |

## `bi.vw_weekly_sales` (tabla)

Ventas agregadas por semana (lunes-domingo) para el modelo ML.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| WeekStart | date | si |  |  |
| NetSales | decimal(38,2) | si |  |  |
| Units | int | si |  |  |
| Orders | int | si |  |  |
| ActiveCustomers | int | si |  |  |

## `dw.DimCustomer` (tabla)

Dimension cliente con historial SCD tipo 2 (ValidFrom/ValidTo/IsCurrent).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| CustomerKey | int | no | si | Clave sustituta. |
| CustomerID | int | no |  | Clave natural (Sales.Customers.CustomerID). |
| CustomerName | nvarchar(255) | si |  | Nombre comercial. |
| PrimaryContactPerson | nvarchar(255) | si |  | Persona de contacto (dato personal: NO se expone en BI ni se envia a IA). |
| City | nvarchar(100) | si |  | Ciudad de entrega. |
| StateProvince | nvarchar(100) | si |  | Estado/provincia. |
| Country | nvarchar(100) | si |  | Pais. |
| PostalCode | nvarchar(20) | si |  | Codigo postal de entrega. |
| ValidFrom | date | no |  | Inicio de vigencia de la version. |
| ValidTo | date | si |  | Fin de vigencia (9999-12-31 = vigente). |
| IsCurrent | bit | si |  | 1 si es la version vigente. |
| CustomerCategory | nvarchar(100) | si |  | Categoria de cliente. |
| BuyingGroup | nvarchar(100) | si |  | Grupo de compra. |
| GeographyKey | int | si |  | FK a DimGeography (ciudad de entrega). |

## `dw.DimDate` (tabla)

Dimension calendario (grano: un dia).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| DateKey | int | no | si | Clave sustituta YYYYMMDD. |
| Date | date | no |  | Fecha. |
| Year | int | no |  | Ano. |
| Month | int | no |  | Mes (1-12). |
| MonthName | nvarchar(20) | no |  | Nombre del mes. |
| Quarter | int | no |  | Trimestre (1-4). |
| DayOfWeek | int | no |  | Dia de la semana (0=lunes). |
| DayOfWeekName | nvarchar(10) | no |  | Nombre del dia. |
| IsWeekend | bit | no |  | 1 si es sabado o domingo. |
| IsHoliday | bit | si |  | Reservado; no se cargan festivos. |
| Week | int | si |  | Semana ISO. |
| DayOfYear | int | si |  | Dia del ano. |

## `dw.DimGeography` (tabla)

Dimension geografica (grano: ciudad). GeographyKey=1 es el miembro 'Unknown'.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| GeographyKey | int | no | si | Clave sustituta. |
| City | nvarchar(100) | no |  | Ciudad. |
| StateProvince | nvarchar(100) | si |  | Estado/provincia. |
| Country | nvarchar(100) | no |  | Pais. |
| Region | nvarchar(100) | si |  | Territorio de ventas (SalesTerritory). |
| PostalCode | nvarchar(20) | si |  | No poblado (varia por cliente). |
| CityID | int | si |  | Clave natural (Application.Cities). |

## `dw.DimProduct` (tabla)

Dimension producto (grano: articulo de inventario).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| ProductKey | int | no | si | Clave sustituta. |
| StockItemID | int | no |  | Clave natural (Warehouse.StockItems). |
| ProductName | nvarchar(255) | si |  | Nombre del producto. |
| Category | nvarchar(100) | si |  | Categoria = grupo de inventario principal (menor StockGroupID). |
| Brand | nvarchar(100) | si |  | Marca. |
| UnitPrice | decimal(18,2) | si |  | Precio unitario de catalogo. |
| RecommendedRetailPrice | decimal(18,2) | si |  | Precio recomendado de venta. |
| IsDeleted | bit | si |  |  |
| Color | nvarchar(50) | si |  | Color. |
| Size | nvarchar(50) | si |  | Tamano. |

## `dw.FactSales` (tabla)

Hechos de ventas (grano: una linea de pedido).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| SalesFactKey | bigint | no | si | Clave sustituta del hecho. |
| DateKey | int | no |  | FK a DimDate (fecha del pedido). |
| CustomerKey | int | no |  | FK a DimCustomer. |
| ProductKey | int | no |  | FK a DimProduct. |
| GeographyKey | int | no |  | FK a DimGeography (ciudad de entrega del cliente). |
| OrderID | int | no |  | Pedido de origen (dimension degenerada). |
| OrderLineID | int | no |  | Linea de origen (dimension degenerada). |
| InvoiceID | int | si |  | No poblado (reservado). |
| Quantity | int | no |  | Unidades pedidas (aditiva). |
| UnitPrice | decimal(18,2) | no |  | Precio unitario (no aditiva). |
| TaxRate | decimal(5,2) | si |  | Tasa de impuesto como fraccion (0.15 = 15%). Antes llamada Discount; el origen no registra descuentos. |
| LineTotal | decimal(18,2) | no |  | Venta neta = Quantity x UnitPrice, sin impuestos (aditiva). Es la medida base de los KPIs. |
| OrderStatus | nvarchar(50) | si |  | Estado fijo 'Completed'. |
| InvoiceStatus | nvarchar(50) | si |  | No poblado. |
| LoadedDate | datetime | si |  | Momento de carga en el DW. |
| SourceLastModified | datetime | si |  | No poblado. |
| IsDeleted | bit | si |  | Marca de borrado logico. |

## `ops.alert` (tabla)

Alertas (regla, modelo o IA) con estado y clave anti-duplicados.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| AlertID | bigint | no | si |  |
| CreatedAt | datetime2 | no |  |  |
| AlertType | nvarchar(40) | no |  |  |
| Severity | nvarchar(10) | no |  |  |
| Indicator | nvarchar(100) | no |  |  |
| Entity | nvarchar(150) | si |  |  |
| ObservedValue | decimal(18,2) | si |  |  |
| ThresholdValue | decimal(18,2) | si |  |  |
| ReferencePeriod | nvarchar(80) | si |  |  |
| Source | nvarchar(10) | no |  |  |
| ModelVersion | nvarchar(40) | si |  |  |
| Explanation | nvarchar(2000) | si |  |  |
| RecommendedAction | nvarchar(500) | si |  |  |
| IsSimulated | bit | no |  |  |
| Status | nvarchar(12) | no |  |  |
| StatusChangedAt | datetime2 | si |  |  |
| StatusChangedBy | nvarchar(50) | si |  |  |
| DedupKey | nvarchar(200) | no |  |  |

## `ops.alert_delivery` (tabla)

Intentos de entrega de cada alerta por canal.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| DeliveryID | bigint | no | si |  |
| AlertID | bigint | no |  |  |
| Channel | nvarchar(20) | no |  |  |
| Attempt | int | no |  |  |
| Status | nvarchar(10) | no |  |  |
| Detail | nvarchar(500) | si |  |  |
| AttemptedAt | datetime2 | no |  |  |

## `ops.app_user` (tabla)

Usuarios de la aplicacion (contrasena con bcrypt).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| UserID | int | no | si |  |
| Username | nvarchar(50) | no |  |  |
| PasswordHash | nvarchar(100) | no |  |  |
| Role | nvarchar(20) | no |  |  |
| IsActive | bit | no |  |  |
| CreatedAt | datetime2 | no |  |  |

## `ops.assistant_audit` (tabla)

Auditoria de preguntas al asistente (sin guardar la respuesta).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| AuditID | bigint | no | si |  |
| AskedAt | datetime2 | no |  |  |
| Username | nvarchar(50) | no |  |  |
| Question | nvarchar(1000) | no |  |  |
| Intent | nvarchar(60) | si |  |  |
| Outcome | nvarchar(40) | no |  |  |
| LlmModel | nvarchar(80) | si |  |  |
| LatencyMs | int | si |  |  |

## `ops.etl_run_log` (tabla)

Bitacora de ejecuciones (ETL, reconciliacion, ML, alertas).

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| RunID | bigint | no | si |  |
| Process | nvarchar(100) | no |  |  |
| Status | nvarchar(20) | no |  |  |
| StartedAt | datetime2 | no |  |  |
| FinishedAt | datetime2 | si |  |  |
| RowsProcessed | bigint | si |  |  |
| Message | nvarchar(1000) | si |  |  |

## `ops.ml_model_registry` (tabla)

Registro versionado de modelos con parametros y metricas.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| ModelVersion | nvarchar(40) | no | si |  |
| ModelName | nvarchar(100) | no |  |  |
| Algorithm | nvarchar(100) | no |  |  |
| TargetName | nvarchar(100) | no |  |  |
| Horizon | int | no |  |  |
| TrainedAt | datetime2 | no |  |  |
| TrainPeriod | nvarchar(60) | si |  |  |
| TestPeriod | nvarchar(60) | si |  |  |
| ParamsJson | nvarchar(MAX) | si |  |  |
| MetricsJson | nvarchar(MAX) | no |  |  |
| IsActive | bit | no |  |  |

## `ops.ml_prediction` (tabla)

Predicciones con version de modelo, fecha, horizonte, intervalo y linea base.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| PredictionID | bigint | no | si |  |
| ModelVersion | nvarchar(40) | no |  |  |
| PredictedAt | datetime2 | no |  |  |
| TargetPeriod | date | no |  |  |
| HorizonStep | int | no |  |  |
| PredictedValue | decimal(18,2) | no |  |  |
| LowerBound | decimal(18,2) | si |  |  |
| UpperBound | decimal(18,2) | si |  |  |
| BaselineValue | decimal(18,2) | si |  |  |

## `ops.reconciliation_result` (tabla)

Resultado de cada comprobacion origen vs DW.

| Columna | Tipo | Nulos | PK | Descripcion |
|---|---|---|---|---|
| ResultID | bigint | no | si |  |
| RunID | bigint | si |  |  |
| CheckName | nvarchar(150) | no |  |  |
| SourceValue | decimal(24,2) | si |  |  |
| DwValue | decimal(24,2) | si |  |  |
| Difference | decimal(25,2) | si |  |  |
| Passed | bit | no |  |  |
| Note | nvarchar(500) | si |  |  |
| CheckedAt | datetime2 | no |  |  |

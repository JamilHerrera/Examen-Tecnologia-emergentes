# Catalogo de reglas de transformacion y calidad

Solo se listan reglas que **existen en el codigo** (con su archivo). Las brechas se declaran al final.

## 1. Staging clean (`etl/transform.py`)

| ID | Tabla | Regla | Accion | Registro del impacto |
|---|---|---|---|---|
| T-01 | Sales.Orders | `OrderDate` se convierte a fecha; si no se puede convertir queda nula | Se **descartan** filas con `OrderDate` nula | `ops.etl_reject` y conteo por ejecucion |
| T-02 | Sales.Orders | Columnas `*ID`, `*Amount*`, `*Price*` a numerico (`errors="coerce"`) | Valor invalido → nulo | Contado como nulo en el reporte de validacion |
| T-03 | Sales.OrderLines | `Quantity`, `UnitPrice`, `TaxRate` a numerico | Valor invalido → nulo | Idem |
| T-04 | Sales.OrderLines | `Quantity` y `UnitPrice` obligatorios | Se descartan filas con nulos | `ops.etl_reject` y conteo por ejecucion |
| T-05 | Sales.OrderLines | `Quantity > 0` | Se descartan cantidades ≤ 0 | `ops.etl_reject` y conteo por ejecucion |
| T-06 | Sales.Invoices | `InvoiceDate` obligatoria y de tipo fecha | Se descartan filas con nulo | `ops.etl_reject` y conteo por ejecucion |
| T-07 | Sales.InvoiceLines | `Quantity` y `ExtendedPrice` obligatorios; `Quantity > 0` | Se descartan filas | `ops.etl_reject` y conteo por ejecucion |
| T-08 | Catalogos (`CustomerCategories`, `BuyingGroups`, `StockItems`, `Colors`, `People`, `DeliveryMethods`) | Recorte de espacios en columnas de texto | Se reemplaza el valor | — |
| T-09 | Catalogos | Duplicados por el primer campo `*ID` | Se conserva la **primera** fila (regla de supervivencia) | `ops.etl_reject` y conteo por ejecucion |

**Resultado medido historico** (carga completa anterior a la Fase A, 2026-11-15): 605,176 filas en `staging_raw` y 605,176 en `staging_clean`, sin filas descartadas. Esa ejecucion previa no valida el nuevo watermark ni la tabla de cuarentena; la primera ejecucion del pipeline actualizado debe verificarse en `ops.etl_watermark`, `ops.etl_table_run` y `ops.etl_reject`.

## 2. Auditoria de calidad (`etl/audit.py`)

| Dimension | Formula implementada |
|---|---|
| Completitud | % de celdas no nulas |
| Unicidad | % de filas no duplicadas (fila completa) |
| Validez | % de filas sin `*ID` numerico negativo |
| Consistencia | **No medida** (excluida del puntaje general) |
| Reconciliacion raw vs clean | Conteos por tabla y porcentaje de perdida |

## 3. Pre-controles de carga del DW de negocio (`etl/dw_analytics.py`)
La carga **falla con `RuntimeError`** (y no inserta nada) si algun control devuelve filas:

| Control | Garantiza |
|---|---|
| Factura de proveedor sin orden de compra | Que cada factura se pueda asignar a lineas |
| Ordenes con 0 o mas de 1 factura de proveedor | Asignacion no ambigua del importe |
| Importe de factura ≠ suma de lineas recibidas (± 0.01) | Compras sin diferencias de importe |
| Lineas recibidas sin factura | Gasto respaldado |
| Lineas de factura/compra/movimiento/snapshot sin clave de fecha, producto, cliente (vigente en la fecha) o proveedor | Sin hechos huerfanos |

## 4. Politicas del DW (`etl/dw_*.py`)

| Tema | Politica |
|---|---|
| Huerfanos | Claves foraneas reales en las tablas de hechos; un hecho sin dimension no se puede insertar. La reconciliacion verifica 0 huerfanos |
| Dimension desconocida | `DimGeography.GeographyKey = 1` (`Unknown`); la categoria de producto ausente se rotula `Sin categoria`. Hoy ningun hecho los usa |
| SCD tipo 2 (`DimCustomer`) | Periodos `ValidFrom/ValidTo` (DATETIME2(7)) tomados de la fuente; indice unico para una sola version vigente; intervalos vacios (`ValidFrom = ValidTo`) se omiten (1 fila) |
| Nulos en medidas | No se imputan en los hechos de negocio; las cargas de rentabilidad/compras/inventario no usan valores por defecto |
| Joins 1:N | Cada dimension se une por su clave sustituta unica; la reconciliacion compara el hecho con la vista BI |
| Moneda | GBP (no hay conversion) |

## 5. Reconciliacion (`etl/dw_reconcile.py`, 24 comprobaciones)
Conteos e importes origen vs staging vs DW para ventas, clientes, productos, vistas BI, huerfanos, SCD2, facturas, compras, proveedores, movimientos y snapshot. El resultado se guarda en `ops.reconciliation_result`.

## 6. Brechas
- **Cuarentena:** no existe tabla de registros rechazados con regla fallida, ejecucion y detalle.
- **Perfilado:** no hay reporte de nulos/cardinalidad/rangos/valores frecuentes por columna ni comparativo antes/despues.
- **Outliers:** `OUTLIER_THRESHOLD` esta definido en `etl/config.py` pero ninguna regla lo aplica.
- **Consistencia** entre campos (p. ej. `ExtendedPrice = Quantity × UnitPrice`) no se mide en staging.
- Varias reglas descartan filas sin conservarlas (T-01, T-04 a T-07); con datos sucios eso perderia evidencia.

# API y contratos de datos

Base: `http://localhost:4000/api` (`BACKEND_PORT`). Formato JSON. Salvo `login` y `health`, **todas** las rutas exigen `Authorization: Bearer <JWT>`. Errores: `{ "error": "mensaje" }` con 400 (entrada invalida), 401 (sin token/invalido), 403 (rol insuficiente), 404, 429 (limite de frecuencia) o 500 (sin detalles internos).

Roles: `viewer` < `analyst` < `admin`. La API consulta solo vistas `bi.*` y escribe solo `ops.*` con la cuenta `wwi_app`.

## Autenticacion y salud

| Metodo y ruta | Rol | Descripcion |
|---|---|---|
| `POST /auth/login` | publico | Cuerpo `{ username, password }` → `{ token, user: { username, role } }`. JWT de 8 h. Limite 20 intentos / 15 min. Credenciales invalidas → 401 con el mismo mensaje exista o no el usuario |
| `GET /health` | publico | `{ status: "ok", time }` tras consultar SQL Server |

## Filtros comunes
`from`, `to` (`YYYY-MM-DD`, validados; `from ≤ to`), `category`, `region`, `customerCategory`, `product` (texto ≤ 100 caracteres, siempre como parametro SQL). Si se omite el rango se usan los ultimos 12 meses con datos (hasta 2016-05-31).

## Analitica de ventas (fuente: `bi.vw_sales_detail`)

| Ruta | Parametros extra | Respuesta |
|---|---|---|
| `GET /meta` | — | `{ freshness: { lastLoadedAt, firstOrderDate, lastOrderDate }, dimensions, defaultRange }` |
| `GET /kpis` | filtros | `{ hasData, period, previousPeriod, kpis: { netSales, orders, avgTicket, units, activeCustomers, growth } }`; cada KPI trae `value` y variacion vs periodo anterior |
| `GET /kpis/definitions` | — | Definicion de cada KPI: nombre, proposito, formula, unidad, granularidad, filtros, fuente, responsable |
| `GET /trends` | `granularity` = `month` \| `quarter` \| `week` | `{ granularity, series: [{ period, netSales, previousYearSales, ... }] }` |
| `GET /breakdown` | `by` = `category` \| `region` \| `customerCategory` \| `product` \| `customer` \| `state`; `limit` 1–50 | `{ by, rows: [{ name, netSales, orders, units, sharePct }] }` |
| `GET /detail` | `page`, `pageSize` (max 100), `sort` = `date` \| `netSales` \| `quantity` \| `customer` \| `product`, `dir` = `asc` \| `desc` | `{ page, pageSize, total, totalPages, rows: [...] }` por linea de pedido |
| `GET /orders/:orderId` | — | Pedido con sus lineas y total; 404 si no existe |

## Compras, rentabilidad e inventario (moneda `GBP`)

| Ruta | Respuesta (resumen) |
|---|---|
| `GET /business/purchases` | `{ currency, summary: { purchaseAmount, receivedQuantity, lines, purchaseOrders, suppliers }, series (mensual), suppliers[10], products[10] }` — fuente `bi.vw_purchase_detail` |
| `GET /business/profitability` | `{ currency, summary: { netSales, profit, marginPct, units, lines, invoices }, series, categories[10], products[10] }` — fuente `bi.vw_invoice_profit_detail` |
| `GET /business/inventory` | `{ movements: { transactions, receipts, issues, netMovement, adjustments, series, types }, snapshot: { date, items, unitsOnHand, belowReorder, lowStock[20] } }` — movimientos del periodo y **snapshot** a la fecha indicada (no es saldo historico) |

## Prediccion (ML)

`GET /ml/forecast` → `{ kind: "prediction", model: { version, algorithm, horizon, trainedAt, trainPeriod, testPeriod, metrics, limitations }, history[26 semanas], predictions: [{ period, step, value, lower, upper, baseline, predictedAt }] }`. Todo lo predictivo se etiqueta como PREDICCION; `model: null` si no hay modelo activo.

## Asistente

| Ruta | Descripcion |
|---|---|
| `GET /assistant/status` | Disponibilidad del servicio Ollama y del modelo |
| `POST /assistant/ask` | Cuerpo `{ question }` (3–300 caracteres, se limpian caracteres de control). Limite: 10/min por usuario |

Respuesta de `ask`: `{ answer, facts[], sources[{tool,dataset,period}], period, prediction, interpretation: { text, status, draft? }, intent, outcome, llmUsed, model?, latencyMs, dataAsOf, generated: true, kinds }`. `answer` contiene los **hechos del DW**; `interpretation.text` es el texto del LLM y solo aparece si `status = accepted` (si no, `discarded_*`). `outcome` ∈ `answered`, `answered_interpretation_discarded`, `no_data`, `out_of_scope`, `blocked`, `clarification`, `llm_unavailable`.

## Alertas

| Ruta | Rol | Descripcion |
|---|---|---|
| `GET /alerts?status=&limit=` | cualquiera | Lista (mas recientes primero) |
| `GET /alerts/:id` | cualquiera | Detalle con intentos de entrega (`ops.alert_delivery`) |
| `PATCH /alerts/:id/status` | analyst | Cuerpo `{ status }` con `new`, `attended`, `dismissed`, `resolved` |
| `POST /alerts/evaluate` | admin | `{ dryRun? }` evalua reglas/modelo; `dryRun` no persiste |
| `POST /alerts/simulate` | admin | `{ kind }` = `rule` \| `model` \| `ai`; crea una alerta marcada como **simulada** |

Contrato de alerta: `AlertID`, `CreatedAt`, `AlertType`, `Severity` (`low`…`critical`), `Indicator`, `Entity`, `ObservedValue`, `ThresholdValue`, `ReferencePeriod`, `Source` (`rule` \| `model` \| `ai`), `ModelVersion`, `Explanation`, `RecommendedAction`, `IsSimulated`, `Status`, `StatusChangedAt/By`, `DedupKey` (unica: evita notificaciones duplicadas).

**WebSocket:** `ws://localhost:4000/ws`; el primer mensaje debe llevar el JWT; token invalido cierra con codigo 4401. Emite las alertas nuevas.

## Operacion

| Ruta | Rol | Descripcion |
|---|---|---|
| `GET /ops/etl-status` | cualquiera | Ultima carga, ultima ejecucion exitosa, ultimas 10 ejecuciones y reconciliacion vigente |
| `GET /ops/metrics` | admin | Tiempos de respuesta por ruta |

## Contratos de datos (vistas `bi`)
Las vistas son el contrato entre el DW y la API (`database/dw/10_bi_views.sql`): `vw_sales_detail`, `vw_weekly_sales`, `vw_data_freshness`, `vw_invoice_profit_detail`, `vw_purchase_detail`, `vw_inventory_movement_detail`, `vw_inventory_snapshot`. Columnas y tipos en [DICCIONARIO_DATOS.md](DICCIONARIO_DATOS.md). Cambiar una columna de una vista exige actualizar el servicio y la prueba correspondiente en `backend/test/api.test.js`.

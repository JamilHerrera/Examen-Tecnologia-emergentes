# Fase 5 — Business Intelligence y dashboard web

## Arquitectura
`React (Vite + Recharts)` → `API Node.js/Express` (JWT, rate limiting, consultas parametrizadas) → vistas `bi.*` de SQL Server.
El navegador **nunca** se conecta a SQL Server; el backend usa la cuenta `wwi_app`, que solo puede leer el schema `bi` (verificado en pruebas).

## Funcionalidades (checklist del enunciado)

| Requisito | Implementacion |
|---|---|
| Autenticacion para la demo | Login con usuarios `admin` y `analyst` (bcrypt + JWT 8 h); roles `viewer/analyst/admin` |
| 4–6 KPIs | 6 KPIs (ver tabla) |
| Filtros por fecha y ≥ 2 dimensiones | Rango de fechas + categoria de producto + region + categoria de cliente (+ producto por drill-down) |
| Tendencias y comparacion entre periodos | Grafico mensual/trimestral/semanal contra el mismo periodo del ano anterior; cada KPI muestra variacion vs periodo anterior |
| Visualizaciones por categoria/producto/cliente/region | Barras por dimension seleccionable (categoria, region, categoria de cliente, estado, cliente) y Top 10 productos |
| Tabla de detalle con paginacion | Lineas de pedido, 15 por pagina (maximo 100), ordenable |
| Drill-down | Clic en una barra aplica el filtro; clic en un pedido abre su detalle por linea |
| Fecha y hora de ultima actualizacion | Cabecera y pie (`bi.vw_data_freshness`) |
| Estados de carga, error y sin datos | Componente `Status` en cada panel (con boton Reintentar) |
| Escritorio y movil | CSS responsive (rejilla de 2 columnas → 1 en < 900 px) |
| Informacion predictiva identificada | Panel "Prediccion de ventas semanales" con etiqueta PREDICCION y linea base |

## Definicion de KPIs

Fuente de todos: `bi.vw_sales_detail` (grano linea de pedido). Responsable indicado por area. Filtros: fecha, categoria, region, categoria de cliente, producto. La definicion tambien se sirve en `GET /api/kpis/definitions` y se muestra en la pestana *Operacion*.

| KPI | Proposito | Formula | Unidad | Responsable |
|---|---|---|---|---|
| Ventas netas | Ingreso comercial del periodo | `SUM(Quantity × UnitPrice)`, sin impuestos | USD | Direccion Comercial |
| Pedidos | Volumen de transacciones | `COUNT(DISTINCT OrderID)` | pedidos | Direccion Comercial |
| Ticket promedio | Valor medio por pedido | Ventas netas / Pedidos | USD/pedido | Direccion Comercial |
| Unidades vendidas | Volumen fisico | `SUM(Quantity)` | unidades | Operaciones |
| Clientes activos | Amplitud de la base de clientes | `COUNT(DISTINCT CustomerKey)` | clientes | Marketing |
| Crecimiento de ventas | Variacion vs periodo anterior | (Actual − Anterior) / Anterior × 100 | % | Direccion Comercial |

El **periodo anterior** es el inmediato previo de igual duracion (por defecto, los 12 meses calendario previos al rango).

## Validacion

Pruebas automatizadas: `cd backend && npm test` (`backend/test/api.test.js`, 13 pruebas).

- **KPI vs consulta SQL independiente:** ventas, pedidos, clientes y unidades de 2016-T1 se comparan contra `Sales.Orders`/`Sales.OrderLines` (origen, no DW). Ejemplo: ventas netas T1 2016 = **$13,518,732** en ambos.
- **Sin duplicacion por joins:** con filtros combinados (2015, region Southeast) la suma por categoria iguala el KPI y coincide con el origen.
- **Periodos sin datos:** `from=2030…` devuelve `hasData=false` y ceros.
- **Filtros combinados y entradas hostiles:** fechas invalidas, `by=…;DROP TABLE`, `sort=…;--` → HTTP 400; texto `' OR 1=1 --` en un filtro se trata como valor.
- **Permisos:** sin token → 401; `/ops/metrics` solo admin → 403 para analyst; la cuenta de BD no puede leer `dw.FactSales`.
- **Credenciales:** el frontend solo conoce el token JWT; `.env` esta en `.gitignore`.

## Tiempos de respuesta (20 repeticiones, SQL Server local en Docker, `node backend/scripts/bench.js`)

| Endpoint | Prom. (ms) | p50 (ms) | p95 (ms) |
|---|---|---|---|
| GET /meta | 153 | 141 | 388 |
| GET /kpis (12 meses, sin filtros) | 1203 | 1140 | 2015 |
| GET /kpis (con 3 filtros) | 141 | 131 | 219 |
| GET /trends mensual | 117 | 118 | 131 |
| GET /trends semanal | 138 | 137 | 173 |
| GET /breakdown por categoria | 325 | 335 | 397 |
| GET /breakdown por cliente | 237 | 237 | 300 |
| GET /detail (pagina 1) | 68 | 66 | 93 |
| GET /detail (pagina 2000) | 320 | 311 | 437 |
| GET /ml/forecast | 119 | 113 | 167 |
| GET /ops/etl-status | 8 | 7 | 36 |

El KPI sin filtros es el mas lento (~1.2 s) por sus 4 `COUNT(DISTINCT)` sobre ~150 mil lineas; es aceptable para la demo y se mitigaria con una tabla agregada diaria si el volumen crece.

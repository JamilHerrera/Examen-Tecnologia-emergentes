# Requisitos, alcance y decisiones de arquitectura

## 1. Caso y alcance

**Fuente:** WideWorldImporters (SQL Server 2022, importador/distribuidor ficticio; moneda **GBP**). Se eligio por su volumen (73,595 pedidos, 231,412 lineas de pedido, 236,667 movimientos de inventario), variedad de entidades (ventas, compras, inventario, clientes, proveedores), fechas del 2013-01-01 al 2016-05-31 y relaciones suficientes para un modelo dimensional y un pronostico semanal (≈ 180 semanas).

**Proceso principal:** ventas (grano: linea de pedido). **Extensiones aditivas:** rentabilidad por linea de factura, compras recibidas por linea de orden e inventario (movimientos + snapshot). No se reconstruyen saldos historicos de inventario porque los movimientos no concilian con el snapshot para todos los articulos (9 articulos darian saldo inicial negativo).

### Preguntas analiticas
1. ¿Cuanto se vendio por periodo, categoria, region, categoria de cliente y producto, y como cambia contra el periodo anterior?
2. ¿Que clientes/categorias/regiones crecen o caen de forma relevante?
3. ¿Cuales son las ventas semanales esperadas y que tan confiable es el pronostico frente a una linea base?
4. ¿Cuanto se compra, a que proveedores y a que costo?
5. ¿Que articulos y categorias generan mas utilidad (`LineProfit`)?
6. ¿Que flujo de inventario hubo y que articulos estan bajo el punto de reorden en el snapshot?
7. ¿Que condiciones requieren atencion inmediata (caida de ventas, pronostico bajo)?

## 2. Requisitos funcionales

| ID | Requisito | Donde se cumple |
|---|---|---|
| RF-01 | Extraer tablas de la fuente a staging **raw** sin modificarlas | `etl/extract.py`, `etl/load.py` |
| RF-02 | Limpiar/validar hacia staging **clean** y auditar origen vs staging | `etl/transform.py`, `etl/audit.py` |
| RF-03 | Cargar dimensiones (fecha, cliente SCD2, producto, geografia, proveedor) y hechos | `etl/dw_*.py` |
| RF-04 | Reconciliar conteos e importes entre origen, staging y DW | `etl/dw_reconcile.py` (24 comprobaciones) |
| RF-05 | Dashboard autenticado con 6 KPIs, filtros por fecha + 3 dimensiones, tendencia, detalle paginado y drill-down | `frontend/`, `backend/` |
| RF-06 | Vistas de compras, rentabilidad e inventario | pestana *Negocio*, `/api/business/*` |
| RF-07 | Pronostico semanal versionado con baseline, mostrado como PREDICCION | `machine-learning/`, `/api/ml/forecast` |
| RF-08 | Asistente en lenguaje natural basado solo en datos del DW, con limites y rechazo | `backend/src/assistant/` |
| RF-09 | Alertas por regla, modelo e IA con estado, entrega y deduplicacion | `backend/src/services/alerts.js` |
| RF-10 | Pantalla operativa: ultima carga, ejecuciones, reconciliacion | pestana *Operacion*, `ops.*` |

## 3. Requisitos no funcionales

| ID | Requisito | Medida / estado |
|---|---|---|
| RNF-01 | Seguridad: minimo privilegio, consultas parametrizadas, endpoints protegidos | [07](07_SEGURIDAD_Y_OPERACION.md); `wwi_app` sin acceso a `dw` (prueba automatizada) |
| RNF-02 | Reproducibilidad: ambiente con Docker Compose, `.env.example`, runbook ordenado | README y [07](07_SEGURIDAD_Y_OPERACION.md) |
| RNF-03 | Exactitud: KPIs iguales a SQL independiente sobre el origen | `backend/test/api.test.js` |
| RNF-04 | Rendimiento de consultas del dashboard | Tabla de tiempos en [05](05_BI_Y_KPIS.md) (p95 ≈ 2.0 s en el peor caso, el KPI sin filtros; el resto por debajo de 0.5 s) |
| RNF-05 | Privacidad de IA: sin enviar datos a servicios externos | Ollama local; solo agregados llegan al modelo |
| RNF-06 | Trazabilidad: ejecuciones, reconciliacion, versiones de modelo y entregas de alertas registradas | `ops.etl_run_log`, `ops.reconciliation_result`, `ops.ml_model_registry`, `ops.alert_delivery`, `ops.assistant_audit` |
| RNF-07 | Usabilidad en escritorio y movil | CSS responsive (2 columnas → 1 por debajo de 900 px) |

## 4. Decisiones de arquitectura (con justificacion)

| Decision | Eleccion | Justificacion |
|---|---|---|
| Extraccion | **Batch completo** (carga inicial). La **carga incremental con watermark aun no esta implementada** | El volumen (≈ 605 mil filas en staging) permite recargar; es una brecha declarada frente a la guia |
| Staging | Dos esquemas: `staging_raw` (copia exacta) y `staging_clean` (tipos, limpieza) | Separa lo recibido de lo depurado |
| ETL | Python + SQL (pandas, pyodbc) | Suficiente para el volumen; evita Airflow/Hop sin necesidad |
| Orquestacion | Scripts ejecutados en orden (runbook). No hay planificador | Brecha declarada; ver runbook |
| DW | Estrella en SQL Server; SCD2 en `DimCustomer`, SCD1 en el resto | Historia real disponible solo en `Sales.Customers_Archive` |
| Actualizacion de hechos | Recarga completa idempotente de los hechos de negocio (`DELETE` + insercion dentro de una transaccion) | Evita duplicados al reejecutar |
| Backend / frontend | Node.js (Express) / React + Recharts | Requisito del equipo; el navegador nunca toca SQL Server |
| ML | scikit-learn, series semanales con validacion temporal | Requisito del equipo; ver [machine-learning/README.md](../machine-learning/README.md) |
| IA generativa | Ollama local (`qwen2.5:3b`) con herramientas aprobadas | Sin datos externos; sin costo de API |
| Notificaciones | Panel web + WebSocket + correo SMTP (opcional) | Canales recomendados por la guia |
| Despliegue | Docker Compose para SQL Server y Ollama; API y frontend se ejecutan con npm en desarrollo | Ver [11_ESTRUCTURA_Y_DESPLIEGUE.md](11_ESTRUCTURA_Y_DESPLIEGUE.md) |

### "Tiempo real"
El ETL es por lotes, por lo que no hay tiempo real. Las alertas se evaluan cada **15 minutos** (`ALERT_EVAL_INTERVAL_MIN`); las visibles en la aplicacion se actualizan por WebSocket al generarse. Los eventos de demo se marcan como **SIMULACION**.

### Fallas y reintentos
- Una falla de insercion en staging marca la carga como `failed` con conteos; las filas insertadas antes pueden permanecer hasta repetir la carga.
- Las cargas del DW de negocio hacen `rollback` ante cualquier excepcion y se pueden repetir.
- El correo reintenta 3 veces y registra cada intento.

## 5. Costos
Todo el stack es de codigo abierto o gratuito para desarrollo: SQL Server Developer, Ollama (modelo local), Node.js, React, scikit-learn. El correo es opcional (SMTP propio).

## 6. Brechas conocidas frente a la guia
Carga incremental/watermark, tabla de cuarentena de registros rechazados, reporte de perfilado de datos, auditoria con conteos por etapa (`rows_read/inserted/updated/rejected`) y orquestacion programada no estan implementados. Se priorizan despues de esta documentacion.

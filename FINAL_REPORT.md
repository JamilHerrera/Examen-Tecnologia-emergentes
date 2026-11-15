# Informe de estado del proyecto

## Resumen ejecutivo

La plataforma integra WideWorldImporters con un ETL en Python, un Data Warehouse dimensional en SQL Server, una API Node.js, un dashboard React, un pronostico de ventas con scikit-learn y un asistente/flujo de alertas con Ollama local. En esta reanudacion Docker, SQL Server y Ollama estuvieron disponibles y se repitieron las comprobaciones principales. El informe distingue las validaciones efectivamente ejecutadas de las limitaciones funcionales que aun requieren trabajo.

## Componentes implementados

- ETL de extraccion, transformacion, staging incremental con watermarks, cuarentena, perfilado, auditoria, carga dimensional, enriquecimiento y reconciliacion.
- Modelo dimensional de ventas con `FactSales` a grano de linea de pedido y dimensiones de fecha, cliente (SCD2), producto y geografia; hechos adicionales de rentabilidad por factura, compras recibidas, movimientos de inventario y snapshot de existencias.
- Vistas BI, tablas operativas, controles de acceso para la cuenta de aplicacion y endpoints Node.js protegidos.
- Dashboard React con filtros, KPIs, tendencias, detalle, prediccion, pestana Negocio (compras, rentabilidad, inventario), alertas y operacion. Importes en GBP.
- Pronostico semanal scikit-learn comparado con una linea base; Ollama para interpretaciones y resumen de alertas.
- Documentacion de requisitos, ERD de la fuente, catalogo de reglas, API, instalacion, operacion, seguridad, modelo de datos y guia de usuario.

## Validacion ejecutada en esta reanudacion (2026-11-15)

| Comprobacion | Resultado |
|---|---|
| Docker y servicios | Docker Engine 27.5.1; `sql-server-2022` y `ollama` activos. Ollama tiene `qwen2.5:3b`. |
| Suite completa del backend | 38/38 pruebas pasaron con SQL Server disponible (`npm test` desde `backend`), incluida la nueva consulta de conteos y duracion del ETL y pruebas de conciliacion contra el origen. |
| Compilacion React | Exitosa; Vite transformo 405 modulos. El chunk JavaScript minificado es de 672.64 kB (196.07 kB gzip), sobre el umbral de advertencia de 500 kB. |
| Aplicacion web | API `http://localhost:4000/api/health` y frontend `http://localhost:5173` respondieron HTTP 200; el navegador muestra el inicio de sesion. |
| Reconciliacion de datos | 24/24 comprobaciones pasaron (RunID 10018). Ventas: origen, staging limpio y `dw.FactSales` coinciden en 231,412 lineas y GBP 177,634,276.40. Rentabilidad: 228,265 lineas, GBP 198,043,439.45 de ventas y GBP 85,729,180.90 de utilidad. Compras: 8,358 lineas y GBP 944,343,271.90 conciliados con las facturas de proveedor. Inventario: 236,667 movimientos y 227 articulos en el snapshot. Sin hechos huerfanos, errores SCD2, traslapes ni geografia desconocida. |
| Carga SCD2 de clientes | `dw.DimCustomer` contiene 713 versiones: 663 vigentes y 50 historicas validas. Se omitio 1 fila archivada de duracion cero (`ValidFrom = ValidTo`), que no representa un intervalo consultable. La segunda ejecucion actualizo las mismas 50 filas historicas sin duplicar versiones. |
| Pruebas ETL | 10/10 pruebas unitarias pasaron, incluida la regresion para valores binarios en los perfiles. |
| Fase A ETL | Migracion de confiabilidad aplicada dos veces sin error. En `tempdb` se verificaron inserciones con texto largo/Unicode, reemplazo, upsert, borrado de claves ausentes y cuarentena; las pruebas cubren rollback simulado. Los perfiles omiten valores frecuentes de columnas binarias, incluidos hashes. |
| Migracion de auditoria | Se verifico en SQL Server `ops.assistant_audit.Outcome` como `nvarchar(40)`; se aplico el `ALTER` solo si el ancho anterior lo requeria. |
| Entrenamiento ML | Exitoso; selecciono `rf_leaf5`. MAE de validacion: $87,715 vs $110,552 de la base; MAE de prueba: $127,721 vs $130,476; MAPE de prueba: 12.0% vs 12.1%. Modelo registrado: `sales-weekly-202611151623`. |
| Evaluacion de deriva ML | `predict.py --evaluate` no encontro predicciones cuyo periodo objetivo ya tenga ventas reales completas. Por tanto, no hay una metrica de deriva observada; la prueba temporal de entrenamiento anterior si se evaluo. |
| Evaluacion Ollama | Contrato funcional: 15/15; criterios semanticos por caso: 7/9; resultado integral: 13/15. Los borradores de los casos 3 y 8 fallaron por omitir/cambiar metricas, traducir nombres y citar 16.3% en lugar de 17.3%; el asistente descarto ambos y mostro los hechos del DW. |
| Sintaxis Python | `etl/load.py`, `etl/audit.py` y sus pruebas compilaron con Python 3.15.2; `etl/main.py`, `etl/ops_log.py` y `database/generate_data_dictionary.py` compilaron en una comprobacion previa. |
| ETL actualizado | Primera ejecucion (RunID 10015): 605,176 filas leidas, 1,210,352 inserciones entre raw y clean, 0 rechazadas, 10 tablas por capa; 147.8 s y 10 watermarks creados. Segunda ejecucion (RunID 10017): 726 filas leidas, 1,452 actualizadas por la ventana de solapamiento, 0 nuevas inserciones/rechazos; 3.7 s. |

## Resultados historicos y limites de interpretacion

Consultar [Data Warehouse](documentation/04_DATA_WAREHOUSE.md) y [modelo ML](machine-learning/README.md) para el diseno y resultados documentados de validaciones anteriores. Los valores de ML de arriba son de la ejecucion actual.

El asistente muestra los hechos consultados por separado de la interpretacion de Ollama. El 15/15 corresponde al contrato funcional; los criterios semanticos explicitos cubren 9 casos, no prueban la correccion general del lenguaje y requieren revision humana. Las predicciones tambien deben interpretarse como estimaciones, no como datos historicos.

## Limitaciones conocidas

- El alcance principal es ventas; compras, rentabilidad e inventario se agregaron como extensiones. El inventario muestra movimientos y el snapshot del 31-may-2016, **sin saldos historicos** (no concilian para 9 articulos). La asignacion de compras a producto usa el precio esperado por caja y concilia exactamente con la factura del proveedor; la rentabilidad usa `LineProfit` del origen, no un costo propio. El asistente y las alertas aun solo cubren ventas.
- La primera carga completa y una ejecucion incremental posterior pasaron; la tarea diaria de Windows aun no se ha registrado en esta maquina.
- Los datos de muestra terminan el 31 de mayo de 2016; el modelo semanal tiene una ventaja pequena sobre la linea base en el conjunto de prueba documentado.
- La consistencia de staging no tiene aun una regla implementada: se reporta como no medida y no se incluye en el score general. La nueva carga staging revierte las tablas, registros operativos y watermarks juntos ante fallos.
- La evaluacion semantica usa aserciones especificas para nueve casos y verificaciones deterministas; no certifica el significado en preguntas abiertas. El juez LLM local se descarto porque producia falsos positivos contra respuestas consistentes con los hechos.
- La evaluacion de deriva en produccion requiere que existan semanas objetivo con ventas reales completas; los datos actuales terminan el 31 de mayo de 2016.
- La compilacion del frontend advierte sobre el tamano del bundle. No impidio el build.
- El historial Git conserva una credencial de desarrollo antigua; debe rotarse y evaluarse su exposicion antes de hacer publico el repositorio. Quitarla del HEAD no la elimina del historial.

## Trabajo pendiente para el cierre del proyecto

- Rotar y evaluar la credencial antigua presente en el historial Git antes de hacer publico el repositorio.
- Extender asistente y alertas a compras, rentabilidad e inventario.
- Preparar guion, capturas y video de la demo.

El orden de restauracion inicial y ejecucion, sin sobrescribir una base existente, esta en [el runbook](documentation/07_SEGURIDAD_Y_OPERACION.md).

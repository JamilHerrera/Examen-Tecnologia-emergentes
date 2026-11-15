# Informe de estado del proyecto

## Resumen ejecutivo

La plataforma integra WideWorldImporters con un ETL en Python, un Data Warehouse dimensional en SQL Server, una API Node.js, un dashboard React, un pronostico de ventas con scikit-learn y un asistente/flujo de alertas con Ollama local. En esta reanudacion Docker, SQL Server y Ollama estuvieron disponibles y se repitieron las comprobaciones principales. El informe distingue las validaciones efectivamente ejecutadas de las limitaciones funcionales que aun requieren trabajo.

## Componentes implementados

- ETL de extraccion, transformacion, staging, carga dimensional, enriquecimiento y reconciliacion.
- Modelo dimensional de ventas con `FactSales` a grano de linea de pedido y dimensiones de fecha, cliente, producto y geografia.
- Vistas BI, tablas operativas, controles de acceso para la cuenta de aplicacion y endpoints Node.js protegidos.
- Dashboard React con filtros, KPIs, tendencias, detalle, prediccion, alertas y operacion.
- Pronostico semanal scikit-learn comparado con una linea base; Ollama para interpretaciones y resumen de alertas.
- Documentacion de instalacion, operacion, seguridad, modelo de datos y guia de usuario.

## Validacion ejecutada en esta reanudacion (2026-11-15)

| Comprobacion | Resultado |
|---|---|
| Docker y servicios | Docker Engine 27.5.1; `sql-server-2022` y `ollama` activos. Ollama tiene `qwen2.5:3b`. |
| Suite completa del backend | 33/33 pruebas pasaron con SQL Server disponible (`npm test` desde `backend`). |
| Compilacion React | Exitosa; Vite transformo 403 modulos. El chunk JavaScript minificado es de 664.94 kB (194.31 kB gzip), sobre el umbral de advertencia de 500 kB. |
| Reconciliacion de datos | 10/10 comprobaciones pasaron (RunID 10002). Origen, staging limpio y `dw.FactSales` coinciden en 231,412 lineas y $177,634,276.40 en ventas netas; no hay hechos huerfanos ni geografia desconocida. |
| Migracion de auditoria | Se verifico en SQL Server `ops.assistant_audit.Outcome` como `nvarchar(40)`; se aplico el `ALTER` solo si el ancho anterior lo requeria. |
| Entrenamiento ML | Exitoso; selecciono `rf_leaf5`. MAE de validacion: $87,715 vs $110,552 de la base; MAE de prueba: $127,721 vs $130,476; MAPE de prueba: 12.0% vs 12.1%. Modelo registrado: `sales-weekly-202611151623`. |
| Evaluacion de deriva ML | `predict.py --evaluate` no encontro predicciones cuyo periodo objetivo ya tenga ventas reales completas. Por tanto, no hay una metrica de deriva observada; la prueba temporal de entrenamiento anterior si se evaluo. |
| Evaluacion Ollama | 15/15 casos pasaron los checks automatizados de intencion, resultado y hechos, con corroboracion independiente para los casos configurados. **No mide exactitud semantica.** En los casos 3 y 8 el verificador descarto borradores por traduccion de nombres y direccion contradictoria, respectivamente. |
| Sintaxis Python | `etl/main.py`, `etl/ops_log.py` y `database/generate_data_dictionary.py` compilaron con Python 3.15.2 en una comprobacion previa de esta reanudacion. |
| ETL completo de staging | No se volvio a ejecutar: inserta filas individualmente y puede tardar cerca de una hora. La reconciliacion confirma igualdad de conteos de staging limpio y DW, pero no sustituye una auditoria de cada insercion. |

## Resultados historicos y limites de interpretacion

Consultar [Data Warehouse](documentation/04_DATA_WAREHOUSE.md) y [modelo ML](machine-learning/README.md) para el diseno y resultados documentados de validaciones anteriores. Los valores de ML de arriba son de la ejecucion actual.

El asistente muestra los hechos consultados por separado de la interpretacion de Ollama. Las comprobaciones de cifras, signos y traducciones reducen algunos errores, pero son heuristicas y no prueban la correccion semantica. El 15/15 refleja los checks del script, no que las 15 interpretaciones sean correctas. Las predicciones tambien deben interpretarse como estimaciones, no como datos historicos.

## Limitaciones conocidas

- El historial real SCD tipo 2 de clientes no se carga desde `Sales.Customers_Archive`.
- El alcance analitico implementado es ventas; compras, inventario historico y rentabilidad basada en costos no estan cubiertos.
- Los datos de muestra terminan el 31 de mayo de 2016; el modelo semanal tiene una ventaja pequena sobre la linea base en el conjunto de prueba documentado.
- La auditoria ETL de staging calcula la consistencia con un valor fijo (95.0), y los errores de insercion individuales se omiten con una advertencia; una corrida marcada como exitosa no garantiza por si sola que todas las filas llegaron a staging.
- La evaluacion automatizada de GenAI no califica adecuadamente el significado de las respuestas.
- La evaluacion de deriva en produccion requiere que existan semanas objetivo con ventas reales completas; los datos actuales terminan el 31 de mayo de 2016.
- La compilacion del frontend advierte sobre el tamano del bundle. No impidio el build.
- El historial Git conserva una credencial de desarrollo antigua; debe rotarse y evaluarse su exposicion antes de hacer publico el repositorio. Quitarla del HEAD no la elimina del historial.

## Trabajo pendiente para el cierre del proyecto

- Corregir la auditoria ETL: eliminar la consistencia fija de 95.0 y hacer que los errores de insercion por fila afecten el estado y los conteos de la corrida.
- Implementar/cargar el historial SCD tipo 2 desde `Sales.Customers_Archive`.
- Fortalecer la evaluacion semantica del asistente; los checks actuales no certifican la veracidad general de sus interpretaciones.
- Rotar y evaluar la credencial antigua presente en el historial Git antes de hacer publico el repositorio.
- Ampliar el alcance analitico mas alla de ventas si lo requiere la rubrica.

El orden de restauracion inicial y ejecucion, sin sobrescribir una base existente, esta en [el runbook](documentation/07_SEGURIDAD_Y_OPERACION.md).

# Informe de estado del proyecto

## Resumen ejecutivo

La plataforma integra WideWorldImporters con un ETL en Python, un Data Warehouse dimensional en SQL Server, una API Node.js, un dashboard React, un pronostico de ventas con scikit-learn y un asistente/flujo de alertas con Ollama local. Este informe refleja el estado del repositorio y las comprobaciones que pudieron ejecutarse; **no certifica el flujo integral**, porque SQL Server y Docker no estuvieron disponibles durante esta reanudacion.

## Componentes implementados

- ETL de extraccion, transformacion, staging, carga dimensional, enriquecimiento y reconciliacion.
- Modelo dimensional de ventas con `FactSales` a grano de linea de pedido y dimensiones de fecha, cliente, producto y geografia.
- Vistas BI, tablas operativas, controles de acceso para la cuenta de aplicacion y endpoints Node.js protegidos.
- Dashboard React con filtros, KPIs, tendencias, detalle, prediccion, alertas y operacion.
- Pronostico semanal scikit-learn comparado con una linea base; Ollama para interpretaciones y resumen de alertas.
- Documentacion de instalacion, operacion, seguridad, modelo de datos y guia de usuario.

## Validacion ejecutada en esta revision

| Comprobacion | Resultado |
|---|---|
| Pruebas unitarias del asistente | 10/10 pasaron con `node --test backend/test/assistant.test.js`. |
| Compilacion React | Exitosa; Vite genero el bundle. Emitio una advertencia porque un chunk minificado excede 500 kB. |
| Sintaxis Python | `etl/main.py`, `etl/ops_log.py` y `database/generate_data_dictionary.py` compilaron con Python 3.15.2. |
| Suite completa del backend | No validada: `npm test` no pudo conectar con `localhost:1433`; el servicio de Docker requiere privilegios que esta sesion no tiene. |
| ETL, reconciliacion, entrenamiento y prediccion | No repetidos en esta revision, por la misma indisponibilidad de SQL Server. |
| Evaluacion Ollama | No repetida. El reporte anterior de 15/15 solo verificaba rutas/hechos; la revision manual encontro dos interpretaciones erradas y ese resultado no es una medida de exactitud semantica. |

## Resultados historicos que requieren repeticion

La documentacion del repositorio registra una reconciliacion anterior de 10 comprobaciones y metricas de ML. No se repitieron en esta revision; consultar [Data Warehouse](documentation/04_DATA_WAREHOUSE.md) y [modelo ML](machine-learning/README.md) como evidencia historica, no como una validacion recien ejecutada.

El asistente muestra los hechos consultados por separado de la interpretacion de Ollama. Las comprobaciones de cifras, signos y traducciones reducen algunos errores, pero son heuristicas y no prueban la correccion semantica. Las predicciones tambien deben interpretarse como estimaciones, no como datos historicos.

## Limitaciones conocidas

- El historial real SCD tipo 2 de clientes no se carga desde `Sales.Customers_Archive`.
- El alcance analitico implementado es ventas; compras, inventario historico y rentabilidad basada en costos no estan cubiertos.
- Los datos de muestra terminan el 31 de mayo de 2016; el modelo semanal tiene una ventaja pequena sobre la linea base en el conjunto de prueba documentado.
- La auditoria ETL de staging calcula la consistencia con un valor fijo (95.0), y los errores de insercion individuales se omiten con una advertencia; una corrida marcada como exitosa no garantiza por si sola que todas las filas llegaron a staging.
- La evaluacion automatizada de GenAI no califica adecuadamente el significado de las respuestas.
- La ejecucion de API, alertas, ETL, reconciliacion y ML sigue pendiente hasta que SQL Server y Ollama esten accesibles.
- La compilacion del frontend advierte sobre el tamano del bundle. No impidio el build.
- El historial Git conserva una credencial de desarrollo antigua; debe rotarse y evaluarse su exposicion antes de hacer publico el repositorio. Quitarla del HEAD no la elimina del historial.

## Siguiente paso necesario

Iniciar Docker Desktop con permisos suficientes para que levante el motor. Luego ejecutar `docker compose -f docker-compose-simple.yml ps` y repetir la suite backend, la reconciliacion, las pruebas ML y la evaluacion de Ollama. Los pasos de restauracion inicial —sin sobrescribir una base existente— estan en [el runbook](documentation/07_SEGURIDAD_Y_OPERACION.md).

# Modelo predictivo: pronostico de ventas semanales

## 1. Problema, usuario y decision
- **Problema:** pronosticar las ventas netas de las proximas 1 a 4 semanas (regresion / serie temporal).
- **Usuario:** Direccion Comercial y Operaciones.
- **Decision que apoya:** planificar inventario y metas semanales, y activar alertas cuando la
  demanda esperada cae por debajo de lo habitual (ver Fase 8).

## 2. Datos
- Fuente: `bi.vw_weekly_sales` (vista aprobada sobre `dw.FactSales`), semanas lunes-domingo.
- Se usan solo **semanas completas**: 177 semanas, 2013-01-07 a 2016-05-23. La primera semana
  parcial y la ultima (el DW termina el martes 2016-05-31) se descartan.
- Calidad: sin faltantes; ventas semanales entre 0.80 M y 1.39 M USD, desviacion ~12 % de la media.
- Sesgos/limitaciones: datos de muestra (WideWorldImporters) con una sola zona geografica (EE. UU.),
  sin festivos, promociones ni precios competidores en las variables.

## 3. Variables (sin fuga de datos)
Para un origen `t` solo se usan valores observados hasta `t`: ventas de las ultimas 4 semanas,
media movil 4/8, volatilidad, venta de la misma semana del ano anterior (y vecinas) y calendario de la
semana objetivo (semana del ano como seno/coseno, mes). El objetivo se normaliza por la media de
las ultimas 8 semanas. Codigo: [`features.py`](features.py).

## 4. Validacion respetando el tiempo
Division cronologica por semana objetivo: **entrenamiento** (hasta 2015-05), **validacion**
(26 semanas) y **prueba** (26 semanas, 2015-11-30 a 2016-05-23). El algoritmo se elige solo con
validacion; la prueba se evalua una vez. El modelo final se reentrena con toda la historia.

## 5. Resultados (ejecucion registrada en `ops.ml_model_registry`)
| Conjunto | Modelo (Random Forest) | Linea base (promedio 4 semanas) |
|---|---|---|
| MAE validacion | ~87.7 K USD | ~110.6 K USD |
| MAE prueba | ~127.7 K USD | ~130.5 K USD |
| MAPE prueba | 12.0 % | 12.1 % |

Lectura honesta: en validacion el modelo mejora la base ~20 %, pero **en prueba la mejora es de solo ~2 %**
(en h=1 y h=4 es marginalmente peor). La demanda semanal es muy ruidosa y la serie es corta: el modelo
aporta poca ventaja sobre una prediccion simple. Por eso el dashboard siempre muestra la linea base
y las metricas junto a la prediccion, y se etiqueta como **PREDICCION**.

## 6. Versionado y publicacion
- Artefacto: `machine-learning/models/<version>.joblib` (no se versiona en git).
- Registro: `ops.ml_model_registry` (version, algoritmo, parametros, periodos, metricas, fecha).
- Predicciones: `ops.ml_prediction` (version del modelo, fecha de prediccion, semana objetivo, horizonte,
  intervalo 10-90 % por residuos de prueba, linea base).
- Exposicion: `GET /api/ml/forecast` y panel "Prediccion de ventas semanales" del dashboard.

## 7. Operacion y monitoreo
- `python machine-learning/train.py` — reentrenar (recomendado mensual o si el MAE real supera 1.5x el de prueba).
- `python machine-learning/predict.py` — generar predicciones tras cada carga del DW (idempotente).
- `python machine-learning/predict.py --evaluate` — compara predicciones pasadas con ventas reales (deriva).

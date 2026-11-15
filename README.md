# Plataforma de Ingenieria de Datos y Analitica Inteligente — WideWorldImporters

Plataforma end-to-end sobre la base **WideWorldImporters** (SQL Server): ETL con staging, Data Warehouse dimensional, dashboard web, modelo predictivo, asistente de IA generativa local y alertas automaticas.

```
SQL Server (origen) ─► ETL Python (staging_raw/clean) ─► Data Warehouse (dw) ─► vistas bi
                                                                                   │
        React (Vite + Recharts) ◄── API Node.js/Express (JWT) ◄───────────────────┤
              ▲  WebSocket (alertas)        │                                      │
              │                             ├─► Ollama (qwen2.5:3b, local)         │
              │                             └─► motor de alertas (reglas/ML/IA)    │
              └──────────── scikit-learn: pronostico semanal ──► ops.ml_* ◄────────┘
```

## Estado por fase

| Fase | Contenido | Documentacion |
|---|---|---|
| 1–2 | Descubrimiento y diseno | [01](documentation/01_FASE_1_DESCUBRIMIENTO.md), [02](documentation/02_FASE_2_DISEÑO.md) |
| 3 | ETL y calidad (staging raw/clean) | [03](documentation/03_FASE_3_ETL_Y_CALIDAD.md), [etl/README.md](etl/README.md) |
| 4 | Data Warehouse, SCD, reconciliacion, diccionario | [04](documentation/04_DATA_WAREHOUSE.md), [DICCIONARIO_DATOS.md](documentation/DICCIONARIO_DATOS.md) |
| 5 | BI: backend Node.js + dashboard React, KPIs | [05](documentation/05_BI_Y_KPIS.md) |
| 6 | Machine learning (pronostico de ventas) | [machine-learning/README.md](machine-learning/README.md) |
| 7 | IA generativa con Ollama | [generative-ai/README.md](generative-ai/README.md) |
| 8 | Alertas, WebSocket, correo | [06](documentation/06_AUTOMATIZACION_ALERTAS.md) |
| 9 | Seguridad, operacion, runbook | [07](documentation/07_SEGURIDAD_Y_OPERACION.md) |
| — | Informe final y guia de usuario | [FINAL_REPORT.md](FINAL_REPORT.md), [GUIA_USUARIO.md](documentation/GUIA_USUARIO.md) |

## Puesta en marcha

Requisitos: Docker Desktop, Python 3.11+, Node.js 20+, ODBC Driver 17 para SQL Server, y el respaldo `WideWorldImporters-Full.bak` en `database/backups/` (no se versiona).

```powershell
copy .env.example .env                                       # completa los valores (ver comentarios)
docker compose -f docker-compose-simple.yml up -d            # SQL Server + Ollama
docker exec ollama ollama pull qwen2.5:3b                    # primera vez (~1.9 GB)
pip install -r requirements.txt
python database/apply_dw_layer.py                            # vistas bi, tablas ops, cuenta wwi_app
cd backend;  npm install; npm run seed; npm start            # API http://localhost:4000
cd frontend; npm install; npm run dev                        # UI  http://localhost:5173
```

Si el DW aun no existe, ejecutar primero el ETL (ver runbook en [07](documentation/07_SEGURIDAD_Y_OPERACION.md)). Usuarios demo: `admin` y `analyst`, con las contrasenas `DEMO_ADMIN_PASSWORD` / `DEMO_ANALYST_PASSWORD` de tu `.env`.

## Pruebas

```powershell
cd backend; npm test                      # 39 pruebas: API/KPIs vs origen, seguridad, alertas, WebSocket, asistente
node generative-ai/run_eval.mjs           # 15 preguntas al asistente (requiere Ollama) -> RESULTADOS_PRUEBAS.md
python etl/dw_reconcile.py                # reconciliacion origen vs DW (10 comprobaciones)
python machine-learning/predict.py --evaluate
```

## Estructura

```
backend/            API Node.js (Express, mssql, JWT, ws, nodemailer) + pruebas
frontend/           React + Vite + Recharts
etl/                Extraccion, transformacion, carga, DW, reconciliacion
database/           Scripts SQL (staging, bi, ops) y aplicador
machine-learning/   Variables, entrenamiento, prediccion, model card
generative-ai/      Casos de prueba y evaluacion del asistente (la logica vive en backend/src/assistant)
documentation/      Fases, diccionario de datos, guia de usuario
```

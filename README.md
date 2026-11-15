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
| 0 | Requisitos, alcance y decisiones de arquitectura | [00](documentation/00_REQUISITOS_Y_ALCANCE.md) |
| 1–2 | Descubrimiento y diseno | [01](documentation/01_FASE_1_DESCUBRIMIENTO.md), [02](documentation/02_FASE_2_DISEÑO.md), [ERD de la fuente](documentation/08_ERD_FUENTE.md) |
| 3 | ETL y calidad (staging raw/clean) | [03](documentation/03_FASE_3_ETL_Y_CALIDAD.md), [catalogo de reglas](documentation/09_CATALOGO_REGLAS.md), [etl/README.md](etl/README.md) |
| 4 | Data Warehouse (ventas, rentabilidad, compras, inventario), SCD, reconciliacion, diccionario | [04](documentation/04_DATA_WAREHOUSE.md), [DICCIONARIO_DATOS.md](documentation/DICCIONARIO_DATOS.md) |
| 5 | BI: backend Node.js + dashboard React, KPIs | [05](documentation/05_BI_Y_KPIS.md), [API y contratos](documentation/10_API_Y_CONTRATOS.md) |
| 6 | Machine learning (pronostico de ventas) | [machine-learning/README.md](machine-learning/README.md) |
| 7 | IA generativa con Ollama | [generative-ai/README.md](generative-ai/README.md) |
| 8 | Alertas, WebSocket, correo | [06](documentation/06_AUTOMATIZACION_ALERTAS.md) |
| 9 | Seguridad, operacion, runbook | [07](documentation/07_SEGURIDAD_Y_OPERACION.md) |
| — | Estructura y despliegue | [11](documentation/11_ESTRUCTURA_Y_DESPLIEGUE.md) |
| — | Informe final y guia de usuario | [FINAL_REPORT.md](FINAL_REPORT.md), [GUIA_USUARIO.md](documentation/GUIA_USUARIO.md) |

**Brechas conocidas frente a la guia del proyecto:** carga incremental con watermark, tabla de cuarentena, reporte de perfilado, auditoria con conteos por etapa y orquestacion programada aun no estan implementadas (ver [requisitos](documentation/00_REQUISITOS_Y_ALCANCE.md#6-brechas-conocidas-frente-a-la-guia)).

## Puesta en marcha

Requisitos: Docker Desktop, Python 3.11+, Node.js 20+, ODBC Driver 17 para SQL Server, y el respaldo `WideWorldImporters-Full.bak` en `database/backups/` (no se versiona).

```powershell
copy .env.example .env                                       # completa los valores (ver comentarios)
docker compose -f docker-compose-simple.yml up -d            # SQL Server + Ollama
docker exec ollama ollama pull qwen2.5:3b                    # primera vez (~1.9 GB)
pip install -r requirements.txt
```

**Carga inicial obligatoria:** si `WideWorldImporters` no existe en SQL Server, restaurar el `.bak` sin sobrescribir una base existente. Despues ejecutar el ETL, crear/cargar el DW y aplicar la capa `bi`/`ops` en el orden del [runbook de instalacion](documentation/07_SEGURIDAD_Y_OPERACION.md). No ejecutar `database/apply_dw_layer.py` antes de crear el DW. Usuarios demo: `admin` y `analyst`, con las contrasenas `DEMO_ADMIN_PASSWORD` / `DEMO_ANALYST_PASSWORD` de tu `.env`.

Con el DW listo, iniciar API y frontend en terminales separadas:

Terminal 1 (desde la raiz del repositorio):

```powershell
Set-Location backend
npm install
npm run seed
npm start
```

Terminal 2 (desde la raiz del repositorio):

```powershell
Set-Location frontend
npm install
npm run dev
```

## Pruebas

```powershell
npm --prefix backend test                 # API, alertas, WebSocket y asistente (requiere SQL Server)
node --test backend/test/assistant.test.js # pruebas unitarias del asistente, sin SQL Server
node generative-ai/run_eval.mjs           # evaluacion funcional (requiere SQL Server y Ollama)
python -m unittest discover -s etl/tests  # pruebas unitarias del ETL
python etl/dw_reconcile.py                # reconciliacion origen vs DW (24 comprobaciones)
python machine-learning/predict.py --evaluate
```

## Estructura

```
backend/            API Node.js (Express, mssql, JWT, ws, nodemailer) + pruebas
frontend/           React + Vite + Recharts
etl/                Extraccion, transformacion, carga, DW, reconciliacion
database/           Scripts SQL (staging, dw, bi, ops) y aplicador
machine-learning/   Variables, entrenamiento, prediccion, model card
generative-ai/      Casos de prueba y evaluacion del asistente (la logica vive en backend/src/assistant)
documentation/      Fases, diccionario de datos, guia de usuario
```

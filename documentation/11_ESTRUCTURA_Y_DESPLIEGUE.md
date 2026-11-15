# Estructura del repositorio y despliegue

## 1. Correspondencia con la estructura sugerida por la guia

| Carpeta sugerida | Ubicacion real | Nota |
|---|---|---|
| `documentation/` | [documentation/](.) | Requisitos, ERD, fases, catalogo de reglas, API, manuales |
| `database/` (source, staging, dw, scripts) | `database/init`, `database/staging`, `database/dw`, `database/apply_dw_layer.py` | La fuente es el `.bak` oficial (no se versiona) |
| `etl/` (extraction, transformation, loading) | `etl/extract.py`, `transform.py`, `load.py`, `audit.py`, `dw_*.py` | Modulos planos, un archivo por etapa |
| `frontend/`, `backend/` | `frontend/`, `backend/` | React + Vite / Node.js + Express |
| `machine-learning/` | `machine-learning/` | `features.py`, `train.py`, `predict.py`, `models/` |
| `generative-ai/` | `generative-ai/` (casos y evaluacion) + `backend/src/assistant/` (logica) | El asistente vive en el backend para aplicar autenticacion y limites |
| `notifications/` | `backend/src/services/alerts.js`, `ws.js` y `backend/src/routes/alerts.js` | Las alertas comparten el pool y la autenticacion de la API; no hay carpeta aparte |
| `tests/` | `backend/test/` (API, alertas, asistente), `etl/tests/` (ETL), `generative-ai/run_eval.mjs`, `etl/dw_reconcile.py`, `machine-learning/predict.py --evaluate` | Pruebas junto al codigo que verifican |
| `deployment/` | `docker-compose-simple.yml` en la raiz | Solo SQL Server y Ollama |
| `.env.example`, `README.md` | Raiz | — |

## 2. Docker Compose (`docker-compose-simple.yml`)

| Servicio | Imagen | Contenedor | Puerto | Volumen |
|---|---|---|---|---|
| `mssql` | `mcr.microsoft.com/mssql/server:2022-latest` | `sql-server-2022` | 1433 | `sql_data` (datos) y `./database/backups` → `/var/opt/mssql/backup` |
| `ollama` | `ollama/ollama:latest` | `ollama` | 11434 | `deployment_ollama_data` (modelos) |

Comandos:

```powershell
docker compose -f docker-compose-simple.yml up -d     # iniciar
docker compose -f docker-compose-simple.yml ps        # estado
docker compose -f docker-compose-simple.yml down      # detener (conserva volumenes)
docker exec ollama ollama pull qwen2.5:3b             # primera vez
```

`down -v` **borra** el volumen de SQL Server; usar solo si se acepta volver a restaurar la base. La API (puerto 4000) y el frontend (5173) se ejecutan con `npm` fuera de contenedores; contenerizarlos queda como mejora.

## 3. Variables de entorno (`.env.example`)
Los secretos viven solo en `.env` (excluido de Git): contrasena de `sa`, cuenta de aplicacion `wwi_app`, secreto JWT, contrasenas de usuarios demo, SMTP opcional y parametros de alertas/Ollama. Ver los comentarios del archivo.

## 4. Versiones usadas en las pruebas

| Componente | Version |
|---|---|
| SQL Server | 2022 (16.0.4325, Developer) |
| Docker Engine | 27.5.1 |
| Python | 3.15 (requerido: 3.11+) |
| Node.js | 26 (requerido: 20+) |
| React / Vite / Recharts | 19.3 / 8.3 / 3.10 |
| Ollama | modelo `qwen2.5:3b` |
| ODBC | ODBC Driver 17 for SQL Server |

Dependencias exactas: `requirements.txt`, `backend/package.json`, `frontend/package.json`.

## 5. Reinicio del ambiente de prueba
Orden completo y recuperacion: [07_SEGURIDAD_Y_OPERACION.md](07_SEGURIDAD_Y_OPERACION.md) (runbook, recarga del DW, respaldo).

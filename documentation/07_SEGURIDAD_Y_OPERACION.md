# Fase 10 — Seguridad, calidad, operacion y monitoreo

## Seguridad minima (estado)

| Requisito | Estado | Evidencia |
|---|---|---|
| Sin contrasenas en el repositorio | Cumple | Secretos solo en `.env` (en `.gitignore`); `.env.example` con marcadores; ETL (`etl/config.py`, `dw_*.py`) y compose leen de variables de entorno. Se retiraron las contrasenas que estaban escritas en codigo y docs. **Nota:** el historial de git anterior a este cambio aun contiene la contrasena de desarrollo `SA` del contenedor local; si el repositorio fuera a publicarse, rotar esa contrasena (`ALTER LOGIN sa ...`) |
| Minimo privilegio | Cumple | Cuenta `wwi_app`: `SELECT` en `bi`, `SELECT/INSERT/UPDATE` en `ops`, **sin acceso** a `dw`, `Sales`, `Warehouse` (prueba automatizada). `sa` solo se usa para ETL/administracion |
| Consultas parametrizadas | Cumple | Todo el acceso del backend usa `request.input()`; columnas dinamicas (orden, dimension) salen de listas blancas; pruebas de inyeccion |
| Endpoints protegidos | Cumple | JWT en todos los `/api` salvo `login` y `health`; roles (`/ops/metrics`, `/alerts/evaluate|simulate` = admin; cambiar estado de alertas = analyst+); WebSocket autenticado con primer mensaje; `helmet`, CORS restringido, limite de cuerpo 10 KB, rate limit en login (20/15 min) y asistente (10/min) |
| Datos de muestra/anonimizados | Cumple | WideWorldImporters es un conjunto ficticio; el contacto principal (`PrimaryContactPerson`) no se expone en vistas BI ni a IA |
| Informacion enviada a servicios externos de IA | Ninguna | Ollama local; solo agregados llegan al modelo (ver `generative-ai/README.md`) |

Limitaciones: HTTPS no esta configurado (demo local; poner un proxy TLS en produccion); los usuarios demo se siembran desde `.env`; el JWT se guarda en `sessionStorage`.

## Monitoreo operativo

- Pestana **Operacion** del dashboard: ultima carga del DW, ultima ejecucion exitosa, filas del hecho, reconciliacion origen vs DW (10 comprobaciones), historial de ejecuciones y tiempos de respuesta por ruta (admin).
- `ops.etl_run_log` registra: pipeline ETL (`etl/main.py`), reconciliacion (`etl/dw_reconcile.py`), entrenamiento ML (`machine-learning/train.py`) y evaluaciones de alertas.
- Logs de ETL en `logs/etl_*.log`; el backend registra errores internos en consola sin exponer detalles al cliente.
- Alertas de fallo: una reconciliacion con diferencias deja la corrida en `warning`. (Pendiente como mejora: alerta automatica ante `failed`.)

## Runbook

### Arranque completo (desarrollo)
```powershell
docker compose -f docker-compose-simple.yml up -d            # SQL Server + Ollama
docker exec ollama ollama pull qwen2.5:3b                    # solo la primera vez (1.9 GB)
pip install -r requirements.txt
python database/apply_dw_layer.py                            # vistas bi, tablas ops, cuenta wwi_app
cd backend; npm install; npm run seed; npm start            # API en :4000
cd frontend; npm install; npm run dev                        # UI en :5173
```

### Recarga del DW (si cambia el origen)
1. `python -m etl.main` (staging; ~1 h por la carga fila a fila).
2. `python etl/dw_schema.py`, `dw_dimensions.py`, `dw_facts.py`, `dw_enrich.py` (en ese orden).
3. `python etl/dw_reconcile.py` — debe terminar con 10/10; si no, revisar `ops.reconciliation_result`.
4. `python machine-learning/predict.py` y, mensualmente, `train.py`.

### Problemas frecuentes
| Sintoma | Causa / solucion |
|---|---|
| `Login failed for user 'sa'` | La contrasena de `.env` no coincide con la del contenedor (`MSSQL_SA_PASSWORD` solo se aplica al crear el volumen). Alinear `.env` o recrear el volumen |
| Backend: `Falta la variable de entorno ...` | Completar `.env` segun `.env.example` |
| Asistente responde "Ollama no responde" | `docker ps` (contenedor `ollama`), `docker exec ollama ollama list` (modelo descargado). La primera respuesta tarda ~1 min (carga del modelo) |
| Alertas sin correo | `SMTP_HOST` vacio → canal `skipped` (normal). Revisar `ops.alert_delivery` |
| KPI muy lento | Ver `documentation/05_BI_Y_KPIS.md` (tabla de tiempos) |

### Respaldo
`database/backups/` (ignorado por git) y el volumen `sql_data` del contenedor. Los modelos ML estan en `machine-learning/models/` (reproducibles con `train.py`).

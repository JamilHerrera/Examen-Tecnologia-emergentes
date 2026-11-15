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

### Instalacion inicial (desarrollo)

1. Copiar `.env.example` a `.env` y completar los valores localmente. Descargar `WideWorldImporters-Full.bak` desde el release oficial de WideWorldImporters y guardarlo en `database/backups/`.
2. Iniciar Docker Desktop y, desde la raiz del repositorio, ejecutar:

```powershell
docker compose -f docker-compose-simple.yml up -d
docker exec ollama ollama pull qwen2.5:3b                    # solo la primera vez (~1.9 GB)
```

3. Si la base `WideWorldImporters` aun no existe, conectarse con SSMS a `localhost,1433` usando la cuenta SA y el valor local de `MSSQL_SA_PASSWORD`. Confirmar que el backup esta visible para SQL Server en `/var/opt/mssql/backup/WideWorldImporters-Full.bak`. Obtener los nombres logicos con:

```sql
RESTORE FILELISTONLY
FROM DISK = N'/var/opt/mssql/backup/WideWorldImporters-Full.bak';
```

4. Solo si `WideWorldImporters` no existe, restaurarla. Si los nombres logicos del backup coinciden con `WWI_Primary`, `WWI_UserData` y `WWI_Log`, usar:

```sql
IF DB_ID(N'WideWorldImporters') IS NULL
BEGIN
    RESTORE DATABASE [WideWorldImporters]
    FROM DISK = N'/var/opt/mssql/backup/WideWorldImporters-Full.bak'
    WITH MOVE N'WWI_Primary' TO N'/var/opt/mssql/data/WideWorldImporters.mdf',
         MOVE N'WWI_UserData' TO N'/var/opt/mssql/data/WideWorldImporters_userdata.ndf',
         MOVE N'WWI_Log' TO N'/var/opt/mssql/data/WideWorldImporters.ldf',
         RECOVERY, STATS = 5;
END;
```

No usar `WITH REPLACE` sobre una base existente. Si `RESTORE FILELISTONLY` muestra otros nombres, sustituir solo los nombres logicos de `MOVE`.

5. Instalar dependencias Python desde la raiz y ejecutar el pipeline y las cargas dimensionales en orden:

```powershell
pip install -r requirements.txt
python etl/main.py
python etl/dw_schema.py
python etl/dw_dimensions.py
python etl/dw_customer_scd2.py
python etl/dw_facts.py
python etl/dw_enrich.py
python database/apply_dw_layer.py                            # vistas bi, tablas ops y cuenta wwi_app
python etl/dw_reconcile.py
python machine-learning/train.py
python machine-learning/predict.py
```

6. Abrir dos terminales desde la raiz del repositorio. En la primera:

```powershell
Set-Location backend
npm install
npm run seed
npm start
```

En la segunda:

```powershell
Set-Location frontend
npm install
npm run dev
```

Usuarios demo: `admin` y `analyst`; establecer sus contrasenas en `.env`. El primer ETL puede ejecutarse antes de crear `ops.etl_run_log`; el pipeline continua y registra ejecuciones una vez aplicada la capa operativa.

### Recarga del DW (si cambia el origen)
`etl/dw_schema.py` elimina y vuelve a crear las tablas `dw.*`; ejecutar esta secuencia solo si se acepta reconstruir el DW y se cuenta con el respaldo requerido. No es una recarga incremental.

1. `python -m etl.main` (staging; ~1 h por la carga fila a fila).
2. `python etl/dw_schema.py`, `dw_dimensions.py`, `dw_customer_scd2.py`, `dw_facts.py`, `dw_enrich.py` (en ese orden).
3. `python etl/dw_reconcile.py` — debe terminar con 13/13; si no, revisar `ops.reconciliation_result`.
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

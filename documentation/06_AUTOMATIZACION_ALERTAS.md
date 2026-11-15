# Fase 9 — Automatizacion, eventos y notificaciones

## Flujo de principio a fin

```
Datos del DW / modelo ML ──► motor de reglas (backend/src/services/alerts.js)
                                 │ evalua cada 15 min (ALERT_EVAL_INTERVAL_MIN) o con "Evaluar reglas ahora"
                                 ▼
                       ops.alert  (DedupKey UNIQUE → sin duplicados)
                                 ▼
        ┌──────────────┬───────────────────┬──────────────────────┐
   panel Alertas   WebSocket /ws       correo SMTP (3 intentos,   resumen IA (Ollama) para
   (BD + UI)       (toast en vivo)     backoff 0.5 s/1 s)         anomalias high/critical
                                 ▼
                  ops.alert_delivery (cada intento por canal)
```

**Frecuencia medible:** el ETL es por lotes, asi que las alertas no son "tiempo real". La evaluacion se ejecuta cada **15 minutos** (configurable) y registra cada corrida en `ops.etl_run_log` (`alert_evaluation`). La latencia maxima de deteccion = intervalo de evaluacion + tiempo hasta la siguiente carga del DW. Para inmediatez real habria que incorporar CDC o procesamiento continuo.

## Disparadores implementados

| Tipo | Regla | Referencia |
|---|---|---|
| Regla de negocio (mensual) | Ventas netas del ultimo mes completo caen > 15 % (total y por categoria) | Mismo mes del ano anterior |
| Regla de negocio (semanal) | Ventas de la ultima semana completa caen > 15 % | Promedio de las 4 semanas previas |
| Machine Learning | Prediccion de la proxima semana < 85 % del promedio de 8 semanas | Promedio de las ultimas 8 semanas |
| IA generativa | Ante una anomalia `high/critical` Ollama genera explicacion y accion (JSON); se descarta si trae cifras no verificadas | Hechos de la anomalia + crecimiento por categoria |

Con los datos actuales (hasta 2016-05-31) **ninguna regla se dispara** (la ultima semana completa esta ~13 % bajo su referencia, por debajo del umbral de 15 %); es el resultado correcto, y la condicion verdadera se prueba con umbrales permisivos y con eventos **simulados**.

## Contenido de la alerta
ID y fecha/hora · tipo y severidad (`low/medium/high/critical` segun magnitud) · indicador y entidad · valor observado y umbral · periodo de referencia · origen (`rule`/`model`/`ai`) y version del modelo · explicacion y accion recomendada · estado (`new → attended / dismissed / resolved`, con quien y cuando) · marca `simulada`.
Las alertas de origen IA se rotulan "[Texto generado por IA]" / "[Generado por IA]" y las de modelo empiezan con "PREDICCION".

## Simulacion
`POST /api/alerts/simulate {kind: rule|model|ai}` (solo admin; botones en la pestana *Alertas*). Todo evento simulado lleva `IsSimulated = 1`, la palabra SIMULACION en el periodo/explicacion y una insignia en la UI.

## Correo
Configurar `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO` en `.env`. Sin `SMTP_HOST` el canal queda `skipped` (queda registrado, no rompe el flujo).

## Pruebas (`backend/test/alerts.test.js`)
Condicion falsa y verdadera · `dryRun` no persiste · mismo evento no genera dos alertas · reintentos de correo (falla, falla, envia → 3 registros) · fallo total (3 `failed`) · SMTP no configurado (`skipped`) · WebSocket (cliente autenticado recibe la alerta; token invalido se cierra con 4401) · API: detalle con entregas, cambio de estado, 400/403/404 · severidad.

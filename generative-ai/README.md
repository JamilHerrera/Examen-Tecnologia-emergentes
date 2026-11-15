# Fase 8 — IA generativa: asistente analitico (Ollama)

## Arquitectura segura

```
Usuario → chat web → POST /api/assistant/ask
        → JWT + rate limit (10 preguntas/min/usuario) + validacion (3–300 caracteres)
        → enrutador (reglas deterministas; respaldo: Ollama solo CLASIFICA la intencion)
        → herramienta analitica APROBADA (consultas parametrizadas sobre bi.vw_sales_detail / ops.ml_*)
        → hechos + periodo + fuentes
        → Ollama (modelo local) redacta una INTERPRETACION
        → verificacion de cifras → respuesta
```

- El modelo **no escribe ni ejecuta SQL**. Solo existen 7 herramientas (`backend/src/assistant/tools.js`): resumen de ventas, comparacion de periodos, crecimiento por categoria/region, top, explicacion de KPI, prediccion y siguientes analisis.
- **Ollama corre en local** (`docker compose -f docker-compose-simple.yml up -d ollama`, modelo `qwen2.5:3b`): ningun dato sale del equipo. Solo se envian al modelo hechos **agregados** (periodos, categorias, regiones, productos, KPIs). Nunca se envian nombres de clientes, personas de contacto, correos ni credenciales.
- Bloqueos previos al modelo: SQL arbitrario, intentos de inyeccion de prompt ("ignora tus instrucciones", "system prompt"), contrasenas/tokens y datos personales.

## Como se distinguen hechos, predicciones e interpretaciones

Cada respuesta separa tres capas (y la interfaz las rotula):

1. **Dato historico del DW** — bloque "Datos consultados" generado por codigo (siempre correcto, con periodo y fuente).
2. **PREDICCION** — solo en preguntas de pronostico; encabezado y badge propios, con linea base y error del modelo.
3. **Interpretacion generada por IA** — texto del LLM, etiquetado con el modelo. Si contiene cifras que no estan en los hechos (verificador `verify.js`, tolerancia 1 % y escalas "millones/mil") o es inutilizable, **se descarta** y se informa.

Otras reglas: periodos relativos ("ultimo trimestre") se calculan sobre la **ultima fecha con datos del DW** (2016-05-31), no sobre el reloj; si el usuario no indica periodo se asume el ultimo trimestre completo y se dice explicitamente; fuera del rango de datos o sin periodo comparable → "No hay datos suficientes para responder"; siempre se muestra "datos hasta" y la fecha de ultima carga. Si Ollama no responde, el asistente degrada a mostrar solo los hechos.

## Registro de consultas
`ops.assistant_audit`: usuario, pregunta (max. 1000 car.), intencion, resultado, modelo y latencia. **No** se guarda la respuesta ni los datos consultados.

## Pruebas del asistente
- 15 preguntas (`test_cases.json`): 7 del enunciado + periodos explicitos + top + **2 sin datos** (2020 y junio-2016) + 1 ambigua + 1 fuera de alcance + 2 de seguridad. Cada caso valida intencion/resultado esperado, que los hechos esten presentes y, cuando aplica, **compara la cifra con una consulta independiente al origen** (`Sales.Orders`/`OrderLines`).
- Ejecutar: `node generative-ai/run_eval.mjs` → genera [RESULTADOS_PRUEBAS.md](RESULTADOS_PRUEBAS.md) (pregunta, esperado, respaldo, respuesta, interpretacion, cifras no verificadas).
- Pruebas unitarias sin LLM (periodos, enrutador, bloqueo, verificador): `backend/test/assistant.test.js`.
- Revision manual de la interpretacion y limitaciones del modelo pequeno: [REVISION_MANUAL.md](REVISION_MANUAL.md).

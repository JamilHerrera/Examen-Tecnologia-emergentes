# Guia de usuario

## 1. Ingreso
Abre <http://localhost:5173> e ingresa con `admin` (todas las funciones) o `analyst` (consulta, asistente y gestion de alertas). La sesion dura 8 horas.

## 2. Dashboard
- **Filtros** (parte superior): rango de fechas, categoria de producto, region y categoria de cliente. *Restablecer* vuelve a los ultimos 12 meses con datos.
- **KPIs:** ventas netas, pedidos, ticket promedio, unidades, clientes activos y crecimiento; cada tarjeta muestra la variacion contra el periodo anterior (pasa el cursor para ver sus fechas).
- **Tendencia:** barras del periodo y linea del mismo periodo del ano anterior; cambia entre mensual, trimestral y semanal.
- **Ventas por dimension:** elige la dimension; haz clic en una barra de categoria, region o categoria de cliente para filtrar (drill-down); vuelve a hacer clic para quitar el filtro. En *Top 10 productos* el clic filtra por producto (chip *Producto* en los filtros).
- **Prediccion de ventas semanales:** area morada = PREDICCION del modelo (no es dato historico), con intervalo y linea base; la tabla compara el error del modelo con el de la linea base.
- **Detalle de ventas:** tabla paginada y ordenable; el numero de pedido abre su detalle por linea.
- Estados: *Cargando…*, mensajes de error con *Reintentar* y aviso cuando no hay datos para los filtros.

## 3. Alertas
Lista de alertas con severidad, origen (regla / modelo / IA generativa) y estado. Llegan en vivo (aviso emergente arriba a la derecha). Puedes marcarlas *atendida*, *resuelta* o *descartada* y ver los intentos de entrega por canal. Solo `admin` ve los botones **Evaluar reglas ahora** y **Simular** (los eventos simulados se marcan como SIMULACION).

## 4. Asistente IA
Escribe una pregunta (max. 300 caracteres) o usa los ejemplos. La respuesta muestra: los datos consultados al DW con su periodo, la **interpretacion generada por IA** (si supera la verificacion de cifras), las fuentes y la fecha de los datos. Si pides algo sin respaldo en los datos, responde "No hay datos suficientes". No ejecuta SQL ni entrega datos personales. La primera respuesta puede tardar ~1 minuto mientras Ollama carga el modelo.

## 5. Operacion
Estado del ETL y del DW (ultima carga, reconciliacion origen vs DW, historial de ejecuciones), definicion de cada KPI y, para `admin`, tiempos de respuesta de la API.

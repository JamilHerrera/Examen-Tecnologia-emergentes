import { normalize } from './periods.js';
import { chat } from './ollama.js';

export const INTENTS = [
  'sales_summary', 'period_comparison', 'growth_by_dimension', 'top_entities',
  'explain_kpi', 'forecast', 'next_analysis',
];

const BLOCKED = [
  /\b(select|insert|update|delete|drop|alter|truncate|exec|union)\b.*\b(from|table|into|database|set)\b/,
  /ignora.*(instrucciones|reglas)|olvida.*(instrucciones|reglas)|ignore.*instructions/,
  /prompt (del )?sistema|system prompt|revela.*(prompt|instrucciones)/,
  /contrasena|password|credencial|token|secret/,
  /(correo|email|telefono|direccion) de(l)? (contacto|cliente|persona)|datos personales|persona de contacto/,
];

const KPI_KEYWORDS = [
  ['avgTicket', /ticket|valor promedio del pedido/],
  ['activeCustomers', /clientes activos|clientes/],
  ['orders', /pedidos|ordenes/],
  ['units', /unidades/],
  ['growth', /crecimiento/],
  ['netSales', /ventas netas|ventas|ingresos/],
];

function dimensionFrom(t, fallback) {
  if (/region|zona|territorio/.test(t)) return 'region';
  if (/categoria de cliente|tipo de cliente/.test(t)) return 'customerCategory';
  if (/categoria/.test(t)) return 'category';
  if (/producto|articulo/.test(t)) return 'product';
  return fallback;
}

/** Enrutador determinista: pregunta -> herramienta aprobada. Devuelve null si no hay coincidencia. */
export function routeByRules(question) {
  const t = normalize(question);
  if (BLOCKED.some((r) => r.test(t))) return { intent: 'blocked' };
  if (/prediccion|pronostico|proyeccion|proximas? (semanas?|\d+ semanas)|a futuro/.test(t)) return { intent: 'forecast' };
  if (/analisis adicional|convendria|que mas (deberia|podria|conviene)? ?(analizar|revisar)|siguiente analisis/.test(t)) {
    return { intent: 'next_analysis' };
  }
  if (/\b(explica|explicame|que es|como se calcula|define|significa)\b/.test(t)) {
    const kpi = KPI_KEYWORDS.find(([, re]) => re.test(t));
    return kpi ? { intent: 'explain_kpi', kpiId: kpi[0] } : { intent: 'clarify_kpi' };
  }
  if (/crecimiento|crecieron|crecio|aumento|aumentaron|disminu|caida|cayeron|bajaron|decrecimiento|descenso/.test(t)) {
    return { intent: 'growth_by_dimension', dimension: dimensionFrom(t, 'category') === 'region' ? 'region' : 'category' };
  }
  if (/respecto al periodo anterior|periodo anterior|compar|cambios|resume|resumen|versus|\bvs\b/.test(t)) {
    return { intent: 'period_comparison' };
  }
  if (/mas vendid|\btop\b|mayores ventas|principales (productos|categorias|regiones)|mejores/.test(t)) {
    return { intent: 'top_entities', dimension: dimensionFrom(t, 'product') };
  }
  if (/ventas|vendimos|ingresos|facturacion|pedidos/.test(t)) return { intent: 'sales_summary' };
  return null;
}

/** Respaldo: el LLM solo CLASIFICA entre intenciones permitidas (no genera SQL ni cifras). */
export async function routeByLlm(question) {
  const system =
    'Clasifica la pregunta de un usuario de un dashboard de ventas en UNA intencion. ' +
    `Intenciones permitidas: ${INTENTS.join(', ')}, out_of_scope. ` +
    'Usa out_of_scope si la pregunta no trata de ventas, clientes, productos, regiones, indicadores o predicciones. ' +
    'Responde solo JSON: {"intent":"<una intencion>"}.';
  const raw = await chat([{ role: 'system', content: system }, { role: 'user', content: `Pregunta: """${question}"""` }], { json: true, maxTokens: 40 });
  try {
    const { intent } = JSON.parse(raw);
    if (INTENTS.includes(intent)) {
      return { intent, dimension: intent === 'growth_by_dimension' ? 'category' : 'product' };
    }
  } catch { /* se trata como fuera de alcance */ }
  return { intent: 'out_of_scope' };
}

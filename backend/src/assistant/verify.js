/**
 * Verificacion de cifras: toda cifra relevante de la respuesta generada debe aparecer
 * (con tolerancia de redondeo) en los hechos consultados al DW. Las que no, se reportan
 * como "no verificadas" para que el usuario no las tome como dato.
 */
const NUM = /\$?\d[\d,]*(?:\.\d+)?%?/g;

const toNumber = (s) => Number(s.replace(/[$,%]/g, '').replace(/,/g, ''));

export function extractNumbers(text) {
  return (text.match(NUM) ?? []).map((raw) => ({ raw, value: toNumber(raw), relevant: /[$%]/.test(raw) || /\./.test(raw) || toNumber(raw) >= 100 }))
    .filter((n) => Number.isFinite(n.value));
}

const isYearOrDay = (n) => Number.isInteger(n.value) && ((n.value >= 1990 && n.value <= 2100) || n.value <= 31);

const strip = (s) => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const DOWN = /(disminu|descenso|descendi|caida|cayo|cayeron|bajo\b|bajaron|reduccion|redujo|decrec|retroced)/g;
const UP = /(aument|crecimiento|crecieron|crecio|increment|subio|subieron|alza|mejora)/g;

function lastKeyword(window) {
  const hit = (re) => [...window.matchAll(re)].map((m) => m.index).pop() ?? -1;
  const down = hit(DOWN);
  const up = hit(UP);
  if (down === up) return null;
  return down > up ? 'down' : 'up';
}

/**
 * Detecta contradicciones de direccion: un porcentaje descrito como "disminucion" cuyo hecho es positivo
 * (o "aumento" con hecho negativo). Compara el signo del hecho con la palabra mas cercana que lo precede.
 */
export function findDirectionContradictions(answer, facts) {
  const factSigns = new Map();
  for (const m of facts.join('\n').matchAll(/([+-]?)(\d[\d,]*(?:\.\d+)?)%/g)) {
    const key = Math.abs(Number(m[2].replace(/,/g, ''))).toFixed(1);
    if (!factSigns.has(key)) factSigns.set(key, new Set());
    factSigns.get(key).add(m[1] === '-' ? 'down' : 'up');
  }
  const text = strip(answer);
  const bad = [];
  for (const m of text.matchAll(/([+-]?)(\d[\d,]*(?:\.\d+)?)%/g)) {
    const signs = factSigns.get(Math.abs(Number(m[2].replace(/,/g, ''))).toFixed(1));
    if (!signs) continue; // cifra no verificada: la maneja findUnverifiedNumbers
    // Alcance del verbo: la oracion actual (hasta 120 caracteres antes de la cifra).
    const before = text.slice(0, m.index);
    const window = before.slice(Math.max(before.lastIndexOf('. ') + 1, m.index - 120));
    const keyword = lastKeyword(window);
    const explicit = m[1] ? (m[1] === '-' ? 'down' : 'up') : null;
    // Un signo explicito y la palabra deben coincidir entre si y con el hecho.
    const conflict = (explicit && keyword && explicit !== keyword) || [explicit, keyword].some((d) => d && !signs.has(d));
    if (conflict) bad.push(m[0]);
  }
  return [...new Set(bad)];
}

/** El modelo pequeno a veces traduce nombres de categorias; los nombres deben citarse tal cual estan en los hechos. */
export function findTranslatedNames(answer, facts) {
  const re = /novedad(es)?\b|vestimenta|juguetes|materiales de (embalaje|empaque)|\bropa\b/i;
  const m = strip(answer).match(re);
  return m && !re.test(strip(facts.join(' '))) ? [m[0]] : [];
}

export function findUnverifiedNumbers(answer, facts) {
  const factNumbers = extractNumbers(facts.join('\n')).map((n) => Math.abs(n.value));
  const close = (a, b) => Math.abs(a - b) <= Math.max(0.011, Math.abs(b) * 0.01);
  const unverified = [];
  const scaled = /millon|mill\.|\bM\b/i.test(answer) ? 1e6 : /\bmil\b|\bK\b/i.test(answer) ? 1e3 : 1;
  for (const n of extractNumbers(answer)) {
    if (!n.relevant || isYearOrDay(n)) continue;
    const v = Math.abs(n.value);
    const ok = factNumbers.some((f) => close(v, f) || close(v * scaled, f) || close(v * 1e6, f) || close(v * 1e3, f));
    if (!ok) unverified.push(n.raw);
  }
  return [...new Set(unverified)];
}

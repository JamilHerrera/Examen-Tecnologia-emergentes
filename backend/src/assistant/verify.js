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

import { iso } from '../services/analytics.js';

const MONTHS = {
  enero: 1, febrero: 2, marzo: 3, abril: 4, mayo: 5, junio: 6,
  julio: 7, agosto: 8, septiembre: 9, setiembre: 9, octubre: 10, noviembre: 11, diciembre: 12,
};
const MONTH_NAMES = Object.keys(MONTHS).join('|');
const ORDINALS = { primer: 1, primero: 1, segundo: 2, tercer: 3, tercero: 3, cuarto: 4 };

export const normalize = (s) =>
  s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim();

const ymd = (y, m, d) => iso(new Date(Date.UTC(y, m - 1, d)));
/** Ultimo dia del mes m (1-12). */
const eom = (y, m) => iso(new Date(Date.UTC(y, m, 0)));
const parts = (s) => ({ y: Number(s.slice(0, 4)), m: Number(s.slice(5, 7)), d: Number(s.slice(8, 10)) });

export function shiftMonths(dateStr, n) {
  const { y, m, d } = parts(dateStr);
  const wasEom = dateStr === eom(y, m);
  const total = y * 12 + (m - 1) + n;
  const ny = Math.floor(total / 12);
  const nm = (total % 12) + 1;
  return wasEom ? eom(ny, nm) : ymd(ny, nm, d);
}

function monthRange(y, m, count) {
  const from = ymd(y, m, 1);
  const end = parts(shiftMonths(from, count - 1));
  return { from, to: eom(end.y, end.m) };
}

/** Ultimo mes calendario completo segun la fecha final de los datos (no segun el reloj). */
function lastCompleteMonth(lastDate) {
  const { y, m } = parts(lastDate);
  return lastDate === eom(y, m) ? { y, m } : parts(shiftMonths(ymd(y, m, 1), -1));
}

function lastCompleteQuarter(last) {
  const endMonth = last.m - (last.m % 3);
  return endMonth === 0 ? { y: last.y - 1, m: 10, count: 3 } : { y: last.y, m: endMonth - 2, count: 3 };
}

/**
 * Interpreta el periodo de una pregunta en espanol. Todo es relativo a la ultima fecha
 * con datos del DW, para que "ultimo trimestre" sea reproducible aunque el reloj avance.
 */
export function parsePeriod(question, { firstDate, lastDate }) {
  const t = normalize(question);
  const last = lastCompleteMonth(lastDate);
  let spec; // { y, m, count, label }
  let assumed = false;
  let mm;

  const quarterLabel = ({ y, m }) => `ultimo trimestre completo (${ymd(y, m, 1).slice(0, 7)} a ${ymd(y, m + 2, 1).slice(0, 7)})`;

  if ((mm = t.match(/\b(?:q|t)([1-4])\s*(?:de|del)?\s*(20\d{2})\b/)) ||
      (mm = t.match(/\b(primer|primero|segundo|tercer|tercero|cuarto) (?:trimestre|cuarto)(?: de(?:l)?)?\s*(20\d{2})\b/))) {
    const q = Number(mm[1]) || ORDINALS[mm[1]];
    spec = { y: Number(mm[2]), m: (q - 1) * 3 + 1, count: 3, label: `T${q} ${mm[2]}` };
  } else if ((mm = t.match(new RegExp(`\\b(${MONTH_NAMES})\\s*(?:de|del)?\\s*(20\\d{2})\\b`)))) {
    spec = { y: Number(mm[2]), m: MONTHS[mm[1]], count: 1, label: `${mm[1]} ${mm[2]}` };
  } else if ((mm = t.match(/\b(20\d{2})\b/))) {
    spec = { y: Number(mm[1]), m: 1, count: 12, label: `ano ${mm[1]}` };
  } else if (/(ultimo|ultimos) (trimestre|cuarto)|trimestre pasado/.test(t)) {
    const q = lastCompleteQuarter(last);
    spec = { ...q, label: quarterLabel(q) };
  } else if (/ultimo semestre/.test(t)) {
    const s = parts(shiftMonths(ymd(last.y, last.m, 1), -5));
    spec = { y: s.y, m: s.m, count: 6, label: 'ultimos 6 meses completos' };
  } else if (/(ultimo|ultimos) (ano|12 meses)|ano pasado/.test(t)) {
    const s = parts(shiftMonths(ymd(last.y, last.m, 1), -11));
    spec = { y: s.y, m: s.m, count: 12, label: 'ultimos 12 meses completos' };
  } else if (/(ultimo mes|mes pasado|este mes|mes actual)/.test(t)) {
    spec = { y: last.y, m: last.m, count: 1, label: `ultimo mes completo (${ymd(last.y, last.m, 1).slice(0, 7)})` };
  } else if ((mm = t.match(new RegExp(`\\b(${MONTH_NAMES})\\b`)))) {
    const month = MONTHS[mm[1]];
    const y = month <= last.m ? last.y : last.y - 1;
    spec = { y, m: month, count: 1, label: `${mm[1]} ${y}` };
  } else {
    const q = lastCompleteQuarter(last);
    spec = { ...q, label: quarterLabel(q) };
    assumed = true;
  }

  const range = monthRange(spec.y, spec.m, spec.count);
  const result = { ...range, label: spec.label, months: spec.count, assumed, firstDate, lastDate };
  if (range.to < firstDate || range.from > lastDate) return { ...result, outOfRange: true };

  if (range.to > lastDate) {
    result.to = lastDate;
    result.partial = true;
  }
  // Periodo comparable: se desplaza la misma cantidad de meses (el inmediato anterior).
  result.previous = { from: shiftMonths(result.from, -spec.count), to: shiftMonths(result.to, -spec.count) };
  result.previousAvailable = result.previous.from >= firstDate;
  return result;
}

import { KPI_DEFINITIONS, getBreakdown, getFreshness, getKpis } from '../services/analytics.js';
import { loadForecast } from '../routes/ml.js';

/**
 * Herramientas analiticas APROBADAS del asistente. El modelo de lenguaje nunca escribe ni
 * ejecuta SQL: solo se ejecutan estas funciones con parametros validados (periodo y dimension).
 */
const usd = (v) => `$${Math.round(v).toLocaleString('en-US')}`;
const usd2 = (v) => `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pct = (v) => (v == null ? 'n/d' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`);
const growth = (cur, prev) => (prev ? ((cur - prev) / prev) * 100 : null);
const range = (p) => `${p.from} a ${p.to}`;

const source = (tool, period) => ({
  tool, dataset: 'Data Warehouse (bi.vw_sales_detail)', period: range(period),
});

async function totals(p) {
  const { kpis, hasData } = await getKpis({ from: p.from, to: p.to });
  return { hasData, ...Object.fromEntries(Object.entries(kpis).map(([k, v]) => [k, v.value])) };
}

async function growthByDimension(period, by) {
  const [cur, prev] = await Promise.all([
    getBreakdown({ from: period.from, to: period.to }, by, 50),
    period.previousAvailable ? getBreakdown({ from: period.previous.from, to: period.previous.to }, by, 50) : [],
  ]);
  const prevMap = new Map(prev.map((r) => [r.name, r.netSales]));
  return cur.map((r) => ({
    name: r.name, current: r.netSales, previous: prevMap.get(r.name) ?? null,
    growthPct: prevMap.has(r.name) ? growth(r.netSales, prevMap.get(r.name)) : null,
  }));
}

export const TOOLS = {
  async sales_summary({ period }) {
    const cur = await totals(period);
    if (!cur.hasData) return { hasData: false, facts: [], sources: [] };
    const facts = [
      `Periodo analizado: ${period.label} (${range(period)}).`,
      `Ventas netas del periodo: ${usd(cur.netSales)}.`,
      `Pedidos: ${cur.orders.toLocaleString('en-US')}; ticket promedio: ${usd2(cur.avgTicket)}; unidades: ${cur.units.toLocaleString('en-US')}; clientes activos: ${cur.activeCustomers.toLocaleString('en-US')}.`,
    ];
    if (period.previousAvailable) {
      const prev = await totals(period.previous);
      facts.push(`Periodo anterior (${range(period.previous)}): ventas netas ${usd(prev.netSales)}; variacion ${pct(growth(cur.netSales, prev.netSales))}.`);
    }
    return { hasData: true, facts, sources: [source('sales_summary', period)] };
  },

  async period_comparison({ period }) {
    const cur = await totals(period);
    if (!cur.hasData) return { hasData: false, facts: [], sources: [] };
    if (!period.previousAvailable) {
      return {
        hasData: false, facts: [], sources: [],
        reason: `No hay datos del periodo anterior (${range(period.previous)}) para comparar.`,
      };
    }
    const prev = await totals(period.previous);
    const row = (label, c, p, f) => `${label}: ${f(c)} vs ${f(p)} (${pct(growth(c, p))}).`;
    const facts = [
      `Comparacion de ${period.label} (${range(period)}) contra el periodo anterior (${range(period.previous)}).`,
      row('Ventas netas', cur.netSales, prev.netSales, usd),
      row('Pedidos', cur.orders, prev.orders, (v) => v.toLocaleString('en-US')),
      row('Ticket promedio', cur.avgTicket, prev.avgTicket, usd2),
      row('Unidades', cur.units, prev.units, (v) => v.toLocaleString('en-US')),
      row('Clientes activos', cur.activeCustomers, prev.activeCustomers, (v) => v.toLocaleString('en-US')),
    ];
    const cats = (await growthByDimension(period, 'category')).filter((c) => c.growthPct != null).sort((a, b) => b.growthPct - a.growthPct);
    if (cats.length) {
      facts.push(`Categoria con mayor cambio positivo: ${cats[0].name} (${pct(cats[0].growthPct)}); con mayor cambio negativo: ${cats.at(-1).name} (${pct(cats.at(-1).growthPct)}).`);
    }
    return { hasData: true, facts, sources: [source('period_comparison', period), source('period_comparison', period.previous)] };
  },

  async growth_by_dimension({ period, dimension }) {
    const label = dimension === 'region' ? 'Region' : 'Categoria';
    const rows = await growthByDimension(period, dimension);
    if (!rows.length) return { hasData: false, facts: [], sources: [] };
    if (!period.previousAvailable) {
      return { hasData: false, facts: [], sources: [], reason: `No hay datos del periodo anterior (${range(period.previous)}) para calcular crecimiento.` };
    }
    const sorted = [...rows].filter((r) => r.growthPct != null).sort((a, b) => b.growthPct - a.growthPct);
    const facts = [
      `${label}s: ${period.label} (${range(period)}) vs periodo anterior (${range(period.previous)}).`,
      ...sorted.map((r) => `${label} ${r.name}: ${usd(r.current)} vs ${usd(r.previous)} (${pct(r.growthPct)}).`),
    ];
    const declines = sorted.filter((r) => r.growthPct <= -5);
    facts.push(declines.length
      ? `${label}s con disminucion relevante (5% o mas): ${declines.map((r) => `${r.name} (${pct(r.growthPct)})`).join(', ')}.`
      : `Ninguna ${label.toLowerCase()} presenta una disminucion de 5% o mas.`);
    return { hasData: true, facts, sources: [source('growth_by_dimension', period), source('growth_by_dimension', period.previous)] };
  },

  async top_entities({ period, dimension }) {
    const names = { product: 'Producto', category: 'Categoria', region: 'Region', customerCategory: 'Categoria de cliente' };
    const rows = await getBreakdown({ from: period.from, to: period.to }, dimension, 5);
    if (!rows.length) return { hasData: false, facts: [], sources: [] };
    const facts = [
      `Top ${rows.length} por ventas netas en ${period.label} (${range(period)}), dimension ${names[dimension] ?? dimension}:`,
      ...rows.map((r, i) => `${i + 1}. ${r.name}: ${usd(r.netSales)} (${r.sharePct.toFixed(1)}% del total).`),
    ];
    return { hasData: true, facts, sources: [source('top_entities', period)] };
  },

  async explain_kpi({ period, kpiId }) {
    const def = KPI_DEFINITIONS.find((k) => k.id === kpiId);
    if (!def) return { hasData: false, facts: [], sources: [], reason: 'No reconozco ese indicador.' };
    const cur = await totals(period);
    const value = cur[def.id];
    const fmtValue = def.id === 'growth' ? pct(value) : ['netSales'].includes(def.id) ? usd(value) : def.id === 'avgTicket' ? usd2(value) : Number(value).toLocaleString('en-US');
    const facts = [
      `Indicador: ${def.name} (${def.unit}). Proposito: ${def.purpose}`,
      `Formula: ${def.formula}. Fuente: ${def.source}. Responsable: ${def.owner}.`,
    ];
    if (cur.hasData) facts.push(`Valor en ${period.label} (${range(period)}): ${fmtValue}.`);
    return { hasData: true, facts, sources: [source('explain_kpi', period)] };
  },

  async forecast() {
    const f = await loadForecast();
    if (!f.model) return { hasData: false, facts: [], sources: [] };
    const t = f.model.metrics.test;
    const facts = [
      `PREDICCION (no es dato historico) del modelo ${f.model.version} (${f.model.algorithm}), horizonte ${f.model.horizon} semanas.`,
      ...f.predictions.map((p) => `Semana ${p.period}: prediccion ${usd(p.value)} (intervalo ${usd(p.lower)} a ${usd(p.upper)}); linea base ${usd(p.baseline)}.`),
      `Error medio absoluto en prueba: modelo ${usd(t.model.mae)} vs linea base ${usd(t.baseline.mae)} (MAPE ${t.model.mape.toFixed(1)}% vs ${t.baseline.mape.toFixed(1)}%).`,
    ];
    return { hasData: true, facts, sources: [{ tool: 'forecast', dataset: 'ops.ml_prediction / ops.ml_model_registry', period: f.model.testPeriod }], prediction: true };
  },

  async next_analysis({ period }) {
    const [cats, regs] = await Promise.all([growthByDimension(period, 'category'), growthByDimension(period, 'region')]);
    if (!cats.length) return { hasData: false, facts: [], sources: [] };
    const worst = (rows) => rows.filter((r) => r.growthPct != null).sort((a, b) => a.growthPct - b.growthPct)[0];
    const wc = worst(cats);
    const wr = worst(regs);
    const facts = [`Periodo de referencia: ${period.label} (${range(period)}).`];
    if (wc) facts.push(`Categoria con peor variacion: ${wc.name} (${pct(wc.growthPct)}).`);
    if (wr) facts.push(`Region con peor variacion: ${wr.name} (${pct(wr.growthPct)}).`);
    facts.push('Dimensiones disponibles para profundizar: categoria de producto, region, categoria de cliente, producto, cliente.');
    return { hasData: true, facts, sources: [source('next_analysis', period)] };
  },
};

export async function dataAsOf() {
  const f = await getFreshness();
  return { lastLoadedAt: f.lastLoadedAt, firstOrderDate: f.firstOrderDate, lastOrderDate: f.lastOrderDate };
}

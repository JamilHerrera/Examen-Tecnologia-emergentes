// Evalua el asistente con generative-ai/test_cases.json y genera RESULTADOS_PRUEBAS.md.
//   node generative-ai/run_eval.mjs            (requiere SQL Server y Ollama activos)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sql from '../backend/node_modules/mssql/index.js';
import '../backend/src/config.js';
import { ask } from '../backend/src/assistant/service.js';
import { closePool } from '../backend/src/db.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const cases = JSON.parse(fs.readFileSync(path.join(here, 'test_cases.json'), 'utf8'));

const sa = await new sql.ConnectionPool({
  server: 'localhost', port: 1433, database: 'WideWorldImporters',
  user: 'sa', password: process.env.MSSQL_SA_PASSWORD,
  options: { encrypt: false, trustServerCertificate: true },
}).connect();

// Verificaciones independientes contra el ORIGEN (no contra el DW) de las cifras de los hechos.
async function independentCheck(spec, facts) {
  const [kind, from, to] = spec.split(':');
  if (kind === 'sales') {
    const r = await sa.request().query(`
      SELECT SUM(CAST(ol.Quantity AS DECIMAL(24,2))*ol.UnitPrice) v FROM Sales.Orders o
      JOIN Sales.OrderLines ol ON ol.OrderID=o.OrderID WHERE o.OrderDate BETWEEN '${from}' AND '${to}'`);
    const expected = Math.round(r.recordset[0].v).toLocaleString('en-US');
    return facts.some((f) => f.includes(`$${expected}`)) ? `OK (origen: $${expected})` : `FALLO (esperado $${expected})`;
  }
  if (kind === 'topProduct') {
    const r = await sa.request().query(`
      SELECT TOP 1 si.StockItemName n FROM Sales.Orders o JOIN Sales.OrderLines ol ON ol.OrderID=o.OrderID
      JOIN Warehouse.StockItems si ON si.StockItemID=ol.StockItemID WHERE o.OrderDate BETWEEN '${from}' AND '${to}'
      GROUP BY si.StockItemName ORDER BY SUM(ol.Quantity*ol.UnitPrice) DESC`);
    const name = r.recordset[0].n;
    return facts.some((f) => f.startsWith('1. ') && f.includes(name)) ? `OK (origen: ${name})` : `FALLO (esperado ${name})`;
  }
  return '';
}

const rows = [];
for (const c of cases) {
  process.stdout.write(`#${c.id} ${c.question} ... `);
  const t0 = Date.now();
  const res = await ask({ username: 'eval', question: c.question });
  const factsOk = c.factsMatch ? res.facts.some((f) => new RegExp(c.factsMatch).test(f)) : true;
  const answerHasFacts = res.facts.length === 0 || res.facts.every((f) => res.answer.includes(f));
  const passed = res.intent === c.intent && res.outcome.startsWith(c.outcome) && factsOk && answerHasFacts;
  const check = c.check ? await independentCheck(c.check, res.facts) : '';
  console.log(`${passed ? 'OK' : 'FALLO'} (${res.intent}/${res.outcome}, ${((Date.now() - t0) / 1000).toFixed(1)}s)`);
  rows.push({ c, res, passed: passed && !check.startsWith('FALLO'), check });
}

const esc = (s) => String(s ?? '').replace(/\|/g, '\\|').replace(/\n/g, '<br>');
let md = `# Resultados de las pruebas del asistente analitico\n\n` +
  `Ejecucion: ${new Date().toISOString()} · modelo: ${rows.find((r) => r.res.model)?.res.model ?? 'n/d'} · ` +
  `datos hasta ${rows[0].res.dataAsOf?.lastOrderDate}\n\n` +
  `Resultado: **${rows.filter((r) => r.passed).length}/${rows.length}** casos conformes.\n\n` +
  `| # | Pregunta | Resultado esperado | Consulta/metrica de respaldo | Respuesta obtenida (hechos del DW) | Interpretacion generada por IA | Cifras no verificadas en el borrador | Verificacion independiente | OK |\n|---|---|---|---|---|---|---|---|---|\n`;
for (const { c, res, passed, check } of rows) {
  const interp = res.interpretation
    ? (res.interpretation.text ? esc(res.interpretation.text) : `(${res.interpretation.status}${res.interpretation.draft ? `; borrador descartado: ${esc(res.interpretation.draft)}` : ''})`)
    : 'n/a';
  md += `| ${c.id} | ${esc(c.question)} | intent \`${c.intent}\` / \`${c.outcome}\` | ${esc(c.support)} | ${esc(res.answer)} | ${interp} | ${res.unverifiedNumbers?.length ? esc(res.unverifiedNumbers.join(', ')) : 'ninguna'} | ${esc(check)} | ${passed ? 'si' : 'NO'} |\n`;
}
fs.writeFileSync(path.join(here, 'RESULTADOS_PRUEBAS.md'), md);
console.log(`\n${rows.filter((r) => r.passed).length}/${rows.length} casos conformes -> generative-ai/RESULTADOS_PRUEBAS.md`);
await closePool();
await sa.close();

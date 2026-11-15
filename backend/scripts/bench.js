// Mide tiempos de respuesta de los endpoints principales (backend en ejecucion).
//   node backend/scripts/bench.js [repeticiones]
import '../src/config.js';

const base = `http://localhost:${process.env.BACKEND_PORT || 4000}/api`;
const runs = Number(process.argv[2] || 20);

const login = await fetch(`${base}/auth/login`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'analyst', password: process.env.DEMO_ANALYST_PASSWORD }),
});
const { token } = await login.json();

const range = 'from=2015-06-01&to=2016-05-31';
const endpoints = [
  ['GET /meta', '/meta'],
  ['GET /kpis (12 meses)', `/kpis?${range}`],
  ['GET /kpis (todos los filtros)', `/kpis?${range}&category=Clothing&region=Southeast&customerCategory=Novelty%20Shop`],
  ['GET /trends mensual', `/trends?${range}&granularity=month`],
  ['GET /trends semanal', `/trends?${range}&granularity=week`],
  ['GET /breakdown por categoria', `/breakdown?${range}&by=category`],
  ['GET /breakdown por cliente', `/breakdown?${range}&by=customer&limit=12`],
  ['GET /detail (pagina 1)', `/detail?${range}&pageSize=15`],
  ['GET /detail (pagina 2000)', `/detail?${range}&pageSize=15&page=2000`],
  ['GET /ml/forecast', '/ml/forecast'],
  ['GET /ops/etl-status', '/ops/etl-status'],
];

const rows = [];
for (const [label, path] of endpoints) {
  const times = [];
  for (let i = 0; i < runs; i += 1) {
    const t0 = performance.now();
    const res = await fetch(`${base}${path}`, { headers: { Authorization: `Bearer ${token}` } });
    await res.json();
    if (!res.ok) throw new Error(`${label}: HTTP ${res.status}`);
    times.push(performance.now() - t0);
  }
  times.sort((a, b) => a - b);
  const pick = (p) => times[Math.min(times.length - 1, Math.floor(p * times.length))];
  rows.push({ label, avg: times.reduce((a, b) => a + b, 0) / times.length, p50: pick(0.5), p95: pick(0.95) });
}
console.log(`| Endpoint | Prom. (ms) | p50 (ms) | p95 (ms) |\n|---|---|---|---|`);
for (const r of rows) console.log(`| ${r.label} | ${r.avg.toFixed(0)} | ${r.p50.toFixed(0)} | ${r.p95.toFixed(0)} |`);

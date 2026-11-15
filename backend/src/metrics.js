/** Metricas de latencia por ruta en memoria (para documentar tiempos de respuesta). */
const stats = new Map();

export function metricsMiddleware(req, res, next) {
  const start = process.hrtime.bigint();
  res.on('finish', () => {
    const ms = Number(process.hrtime.bigint() - start) / 1e6;
    const route = `${req.method} ${req.route?.path ? req.baseUrl + req.route.path : req.path}`;
    const s = stats.get(route) ?? { count: 0, samples: [] };
    s.count += 1;
    s.samples.push(ms);
    if (s.samples.length > 500) s.samples.shift();
    stats.set(route, s);
  });
  next();
}

export function snapshotMetrics() {
  return [...stats.entries()].map(([route, s]) => {
    const sorted = [...s.samples].sort((a, b) => a - b);
    const pick = (p) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
    return {
      route,
      count: s.count,
      avgMs: Math.round(s.samples.reduce((a, b) => a + b, 0) / s.samples.length),
      p50Ms: Math.round(pick(0.5)),
      p95Ms: Math.round(pick(0.95)),
    };
  });
}

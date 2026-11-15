import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import sql from 'mssql';
import { createApp } from '../src/app.js';
import { closePool } from '../src/db.js';

let server;
let base;
let token;
let adminToken;
let sa;

const get = (path, tok = token) =>
  fetch(`${base}/api${path}`, { headers: tok ? { Authorization: `Bearer ${tok}` } : {} });

async function loginAs(username, password) {
  const res = await fetch(`${base}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return res.json();
}

before(async () => {
  server = createApp().listen(0);
  base = `http://127.0.0.1:${server.address().port}`;
  token = (await loginAs('analyst', process.env.DEMO_ANALYST_PASSWORD)).token;
  adminToken = (await loginAs('admin', process.env.DEMO_ADMIN_PASSWORD)).token;
  // Conexion con privilegios SOLO para validar contra el origen independiente del DW.
  sa = await new sql.ConnectionPool({
    server: 'localhost', port: 1433, database: 'WideWorldImporters',
    user: 'sa', password: process.env.MSSQL_SA_PASSWORD,
    options: { encrypt: false, trustServerCertificate: true },
  }).connect();
});

after(async () => {
  server.close();
  await closePool();
  await sa.close();
});

test('login invalido devuelve 401 y no revela si el usuario existe', async () => {
  const bad = await fetch(`${base}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'analyst', password: 'incorrecta' }),
  });
  const ghost = await fetch(`${base}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'noexiste', password: 'x' }),
  });
  assert.equal(bad.status, 401);
  assert.equal(ghost.status, 401);
  assert.deepEqual(await bad.json(), await ghost.json());
});

test('los endpoints exigen autenticacion', async () => {
  assert.equal((await get('/kpis', null)).status, 401);
  assert.equal((await get('/kpis', 'token-falso')).status, 401);
});

test('solo admin accede a metricas operativas', async () => {
  assert.equal((await get('/ops/metrics', token)).status, 403);
  assert.equal((await get('/ops/metrics', adminToken)).status, 200);
});

test('KPI de ventas netas coincide con consulta independiente al origen', async () => {
  const res = await get('/kpis?from=2016-01-01&to=2016-03-31');
  assert.equal(res.status, 200);
  const body = await res.json();
  const src = await sa.request().query(`
    SELECT SUM(CAST(ol.Quantity AS DECIMAL(24,2)) * ol.UnitPrice) AS sales,
           COUNT(DISTINCT o.OrderID) AS orders,
           COUNT(DISTINCT o.CustomerID) AS customers,
           SUM(CAST(ol.Quantity AS BIGINT)) AS units
    FROM Sales.Orders o JOIN Sales.OrderLines ol ON ol.OrderID = o.OrderID
    WHERE o.OrderDate BETWEEN '2016-01-01' AND '2016-03-31'`);
  const s = src.recordset[0];
  assert.ok(Math.abs(body.kpis.netSales.value - Number(s.sales)) < 0.01);
  assert.equal(body.kpis.orders.value, s.orders);
  assert.equal(body.kpis.activeCustomers.value, s.customers);
  assert.equal(body.kpis.units.value, Number(s.units));
  assert.ok(Math.abs(body.kpis.avgTicket.value - Number(s.sales) / s.orders) < 0.01);
});

test('filtros combinados no duplican importes y la suma por categoria iguala el total', async () => {
  const f = 'from=2015-01-01&to=2015-12-31&region=Southeast';
  const kpis = await (await get(`/kpis?${f}`)).json();
  const br = await (await get(`/breakdown?${f}&by=category&limit=50`)).json();
  const sum = br.rows.reduce((a, r) => a + r.netSales, 0);
  assert.ok(Math.abs(sum - kpis.kpis.netSales.value) < 0.01);
  const ref = await sa.request().query(`
    SELECT SUM(CAST(ol.Quantity AS DECIMAL(24,2)) * ol.UnitPrice) AS sales
    FROM Sales.Orders o JOIN Sales.OrderLines ol ON ol.OrderID = o.OrderID
    JOIN Sales.Customers c ON c.CustomerID = o.CustomerID
    JOIN Application.Cities ci ON ci.CityID = c.DeliveryCityID
    JOIN Application.StateProvinces sp ON sp.StateProvinceID = ci.StateProvinceID
    WHERE o.OrderDate BETWEEN '2015-01-01' AND '2015-12-31' AND sp.SalesTerritory = 'Southeast'`);
  assert.ok(Math.abs(kpis.kpis.netSales.value - Number(ref.recordset[0].sales)) < 0.01);
});

test('periodo sin datos devuelve hasData=false y ceros (sin error)', async () => {
  const body = await (await get('/kpis?from=2030-01-01&to=2030-12-31')).json();
  assert.equal(body.hasData, false);
  assert.equal(body.kpis.netSales.value, 0);
});

test('tendencia incluye comparacion contra el mismo periodo del ano anterior', async () => {
  const body = await (await get('/trends?from=2016-01-01&to=2016-05-31&granularity=month')).json();
  assert.equal(body.series.length, 5);
  assert.ok(body.series.every((p) => p.previousYearSales !== null));
});

test('detalle respeta paginacion y limite maximo', async () => {
  const body = await (await get('/detail?from=2016-01-01&to=2016-05-31&pageSize=5000&page=2')).json();
  assert.equal(body.pageSize, 100);
  assert.equal(body.rows.length, 100);
  assert.equal(body.page, 2);
});

test('drill-down a pedido devuelve sus lineas y el total cuadra', async () => {
  const detail = await (await get('/detail?from=2016-05-01&to=2016-05-31&pageSize=1')).json();
  const order = await (await get(`/orders/${detail.rows[0].orderId}`)).json();
  assert.ok(order.lines.length >= 1);
  assert.ok(Math.abs(order.lines.reduce((a, l) => a + l.netSales, 0) - order.total) < 0.01);
});

test('entradas invalidas se rechazan con 400 y la inyeccion SQL es inocua', async () => {
  assert.equal((await get('/kpis?from=ayer&to=hoy')).status, 400);
  assert.equal((await get('/breakdown?by=CustomerName;DROP TABLE x')).status, 400);
  assert.equal((await get('/detail?sort=NetSales;--')).status, 400);
  const inj = await get("/kpis?from=2016-01-01&to=2016-03-31&category=' OR 1=1 --");
  const body = await inj.json();
  assert.equal(body.hasData, false); // el texto se trata como valor, no como SQL
});

test('metadatos exponen fecha de ultima actualizacion y dimensiones', async () => {
  const body = await (await get('/meta')).json();
  assert.ok(body.freshness.lastLoadedAt);
  assert.equal(body.freshness.lastOrderDate, '2016-05-31');
  assert.ok(body.dimensions.categories.length >= 4);
  assert.ok(body.dimensions.regions.length >= 8);
});

test('el backend no puede leer tablas del DW directamente (minimo privilegio)', async () => {
  const { query } = await import('../src/db.js');
  await assert.rejects(() => query('SELECT TOP 1 * FROM dw.FactSales'));
});

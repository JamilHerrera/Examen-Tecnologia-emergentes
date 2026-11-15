import { query, sql } from '../db.js';

const MAX_TEXT = 100;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.status = 400;
  }
}

function parseDate(value, name) {
  if (value === undefined || value === '') return undefined;
  if (typeof value !== 'string' || !ISO_DATE.test(value) || Number.isNaN(Date.parse(value))) {
    throw new ValidationError(`${name} debe tener formato YYYY-MM-DD`);
  }
  return value;
}

function parseText(value, name) {
  if (value === undefined || value === '') return undefined;
  if (typeof value !== 'string' || value.length > MAX_TEXT) {
    throw new ValidationError(`${name} invalido`);
  }
  return value;
}

/** Valida y normaliza los filtros del dashboard (fechas + 3 dimensiones + busqueda). */
export function parseFilters(q) {
  const filters = {
    from: parseDate(q.from, 'from'),
    to: parseDate(q.to, 'to'),
    category: parseText(q.category, 'category'),
    region: parseText(q.region, 'region'),
    customerCategory: parseText(q.customerCategory, 'customerCategory'),
    product: parseText(q.product, 'product'),
  };
  if (filters.from && filters.to && filters.from > filters.to) {
    throw new ValidationError('from no puede ser mayor que to');
  }
  return filters;
}

const DIMENSION_COLUMNS = {
  category: 'Category',
  region: 'Region',
  customerCategory: 'CustomerCategory',
  product: 'ProductName',
};

/**
 * Construye la clausula WHERE con parametros. `range` permite sobreescribir el
 * rango de fechas (p. ej. para el periodo anterior) sin tocar el resto de filtros.
 */
export function buildWhere(filters, range = {}) {
  const clauses = [];
  const params = {};
  const from = range.from ?? filters.from;
  const to = range.to ?? filters.to;
  if (from) {
    clauses.push('OrderDate >= @from');
    params.from = { type: sql.Date, value: from };
  }
  if (to) {
    clauses.push('OrderDate <= @to');
    params.to = { type: sql.Date, value: to };
  }
  for (const [key, column] of Object.entries(DIMENSION_COLUMNS)) {
    if (filters[key]) {
      clauses.push(`${column} = @${key}`);
      params[key] = { type: sql.NVarChar(MAX_TEXT), value: filters[key] };
    }
  }
  return { where: clauses.length ? `WHERE ${clauses.join(' AND ')}` : '', params };
}

export const iso = (d) => (d instanceof Date ? d.toISOString().slice(0, 10) : String(d).slice(0, 10));

export function addDays(dateStr, days) {
  const d = new Date(`${dateStr}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return iso(d);
}

export function addMonths(dateStr, months) {
  const d = new Date(`${dateStr}T00:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() + months);
  return iso(d);
}

export function daysBetween(from, to) {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86400000) + 1;
}

// ---------------------------------------------------------------------------
// Metadatos
// ---------------------------------------------------------------------------

export async function getFreshness() {
  const [row] = await query('SELECT LastLoadedAt, LastOrderDate, FirstOrderDate, FactRows FROM bi.vw_data_freshness');
  return {
    lastLoadedAt: row.LastLoadedAt,
    firstOrderDate: iso(row.FirstOrderDate),
    lastOrderDate: iso(row.LastOrderDate),
    factRows: Number(row.FactRows),
  };
}

export async function getDimensionValues() {
  const [categories, regions, customerCategories] = await Promise.all([
    query('SELECT DISTINCT Category AS v FROM bi.vw_sales_detail ORDER BY Category'),
    query('SELECT DISTINCT Region AS v FROM bi.vw_sales_detail ORDER BY Region'),
    query('SELECT DISTINCT CustomerCategory AS v FROM bi.vw_sales_detail ORDER BY CustomerCategory'),
  ]);
  return {
    categories: categories.map((r) => r.v),
    regions: regions.map((r) => r.v),
    customerCategories: customerCategories.map((r) => r.v),
  };
}

// ---------------------------------------------------------------------------
// KPIs
// ---------------------------------------------------------------------------

export const KPI_DEFINITIONS = [
  {
    id: 'netSales', name: 'Ventas netas', unit: 'GBP',
    purpose: 'Medir el ingreso comercial antes de impuestos en el periodo.',
    formula: 'SUM(Quantity x UnitPrice) por linea de pedido (impuestos excluidos; sin devoluciones porque el origen no las registra en pedidos)',
    granularity: 'Linea de pedido', filters: 'Fecha, categoria, region, categoria de cliente, producto',
    source: 'bi.vw_sales_detail (dw.FactSales)', owner: 'Direccion Comercial',
  },
  {
    id: 'orders', name: 'Pedidos', unit: 'pedidos',
    purpose: 'Volumen de transacciones comerciales.',
    formula: 'COUNT(DISTINCT OrderID)', granularity: 'Pedido',
    filters: 'Fecha, categoria, region, categoria de cliente, producto',
    source: 'bi.vw_sales_detail', owner: 'Direccion Comercial',
  },
  {
    id: 'avgTicket', name: 'Ticket promedio', unit: 'GBP / pedido',
    purpose: 'Valor medio de cada pedido; detecta cambios en el mix de compra.',
    formula: 'Ventas netas / Pedidos', granularity: 'Pedido',
    filters: 'Fecha, categoria, region, categoria de cliente, producto',
    source: 'bi.vw_sales_detail', owner: 'Direccion Comercial',
  },
  {
    id: 'units', name: 'Unidades vendidas', unit: 'unidades',
    purpose: 'Volumen fisico vendido, independiente del precio.',
    formula: 'SUM(Quantity)', granularity: 'Linea de pedido',
    filters: 'Fecha, categoria, region, categoria de cliente, producto',
    source: 'bi.vw_sales_detail', owner: 'Operaciones',
  },
  {
    id: 'activeCustomers', name: 'Clientes activos', unit: 'clientes',
    purpose: 'Amplitud de la base de clientes que compra en el periodo.',
    formula: 'COUNT(DISTINCT CustomerKey) con al menos una linea en el periodo', granularity: 'Cliente',
    filters: 'Fecha, categoria, region, categoria de cliente, producto',
    source: 'bi.vw_sales_detail', owner: 'Marketing',
  },
  {
    id: 'growth', name: 'Crecimiento de ventas', unit: '%',
    purpose: 'Variacion de ventas netas frente al periodo inmediatamente anterior de igual duracion.',
    formula: '(Ventas netas periodo - Ventas netas periodo anterior) / Ventas netas periodo anterior x 100',
    granularity: 'Periodo seleccionado', filters: 'Fecha, categoria, region, categoria de cliente, producto',
    source: 'bi.vw_sales_detail', owner: 'Direccion Comercial',
  },
];

/** Devuelve el periodo anterior inmediato de igual duracion. */
export function previousPeriod(from, to) {
  const days = daysBetween(from, to);
  return { from: addDays(from, -days), to: addDays(from, -1) };
}

const pct = (cur, prev) => (prev ? ((cur - prev) / prev) * 100 : null);

export async function getKpis(filters) {
  const { from, to } = filters;
  const prev = previousPeriod(from, to);
  const { where, params } = buildWhere(filters, { from: prev.from, to });
  const rows = await query(
    `SELECT
        SUM(CASE WHEN OrderDate >= @curFrom THEN NetSales END)                       AS curSales,
        COUNT(DISTINCT CASE WHEN OrderDate >= @curFrom THEN OrderID END)             AS curOrders,
        SUM(CASE WHEN OrderDate >= @curFrom THEN CAST(Quantity AS BIGINT) END)       AS curUnits,
        COUNT(DISTINCT CASE WHEN OrderDate >= @curFrom THEN CustomerKey END)         AS curCustomers,
        SUM(CASE WHEN OrderDate <  @curFrom THEN NetSales END)                       AS prevSales,
        COUNT(DISTINCT CASE WHEN OrderDate <  @curFrom THEN OrderID END)             AS prevOrders,
        SUM(CASE WHEN OrderDate <  @curFrom THEN CAST(Quantity AS BIGINT) END)       AS prevUnits,
        COUNT(DISTINCT CASE WHEN OrderDate <  @curFrom THEN CustomerKey END)         AS prevCustomers
     FROM bi.vw_sales_detail ${where}`,
    { ...params, curFrom: { type: sql.Date, value: from } },
  );
  const r = rows[0];
  const n = (v) => Number(v ?? 0);
  const cur = { netSales: n(r.curSales), orders: n(r.curOrders), units: n(r.curUnits), activeCustomers: n(r.curCustomers) };
  const pre = { netSales: n(r.prevSales), orders: n(r.prevOrders), units: n(r.prevUnits), activeCustomers: n(r.prevCustomers) };
  cur.avgTicket = cur.orders ? cur.netSales / cur.orders : 0;
  pre.avgTicket = pre.orders ? pre.netSales / pre.orders : 0;

  const kpis = {};
  for (const def of KPI_DEFINITIONS) {
    if (def.id === 'growth') continue;
    kpis[def.id] = { value: cur[def.id], previous: pre[def.id], deltaPct: pct(cur[def.id], pre[def.id]) };
  }
  kpis.growth = { value: pct(cur.netSales, pre.netSales), previous: null, deltaPct: null };
  return {
    period: { from, to },
    previousPeriod: prev,
    hasData: cur.orders > 0,
    kpis,
  };
}

// ---------------------------------------------------------------------------
// Tendencias
// ---------------------------------------------------------------------------

const BUCKETS = {
  month: 'DATEFROMPARTS([Year], [Month], 1)',
  quarter: 'DATEFROMPARTS([Year], ([Quarter] - 1) * 3 + 1, 1)',
  week: 'DATEADD(DAY, -((DATEPART(WEEKDAY, OrderDate) + @@DATEFIRST - 2) % 7), OrderDate)',
};

export async function getTrend(filters, granularity = 'month') {
  const bucket = BUCKETS[granularity];
  if (!bucket) throw new ValidationError('granularity debe ser month, quarter o week');
  const shift = (d, dir) => (granularity === 'week' ? addDays(d, dir * 364) : addMonths(d, dir * 12));

  const run = async (range) => {
    const { where, params } = buildWhere(filters, range);
    return query(
      `SELECT ${bucket} AS period, SUM(NetSales) AS netSales, COUNT(DISTINCT OrderID) AS orders
       FROM bi.vw_sales_detail ${where}
       GROUP BY ${bucket} ORDER BY period`,
      params,
    );
  };
  const [current, previous] = await Promise.all([
    run({}),
    run({ from: shift(filters.from, -1), to: shift(filters.to, -1) }),
  ]);
  const prevMap = new Map(previous.map((r) => [iso(shift(iso(r.period), 1)), Number(r.netSales)]));
  return current.map((r) => ({
    period: iso(r.period),
    netSales: Number(r.netSales),
    orders: Number(r.orders),
    previousYearSales: prevMap.get(iso(r.period)) ?? null,
  }));
}

// ---------------------------------------------------------------------------
// Desgloses
// ---------------------------------------------------------------------------

const BREAKDOWNS = {
  category: 'Category',
  region: 'Region',
  customerCategory: 'CustomerCategory',
  product: 'ProductName',
  customer: 'CustomerName',
  state: 'StateProvince',
};

export async function getBreakdown(filters, by = 'category', limit = 10) {
  const column = BREAKDOWNS[by];
  if (!column) throw new ValidationError(`by debe ser uno de: ${Object.keys(BREAKDOWNS).join(', ')}`);
  const top = Math.min(Math.max(parseInt(limit, 10) || 10, 1), 50);
  const { where, params } = buildWhere(filters);
  const rows = await query(
    `SELECT TOP (${top}) ${column} AS name, SUM(NetSales) AS netSales,
            COUNT(DISTINCT OrderID) AS orders, SUM(CAST(Quantity AS BIGINT)) AS units
     FROM bi.vw_sales_detail ${where}
     GROUP BY ${column} ORDER BY SUM(NetSales) DESC`,
    params,
  );
  const [{ total }] = await query(`SELECT SUM(NetSales) AS total FROM bi.vw_sales_detail ${where}`, params);
  const totalSales = Number(total ?? 0);
  return rows.map((r) => ({
    name: r.name,
    netSales: Number(r.netSales),
    orders: Number(r.orders),
    units: Number(r.units),
    sharePct: totalSales ? (Number(r.netSales) / totalSales) * 100 : 0,
  }));
}

// ---------------------------------------------------------------------------
// Detalle paginado y drill-down a pedido
// ---------------------------------------------------------------------------

const SORTS = {
  date: 'OrderDate',
  netSales: 'NetSales',
  quantity: 'Quantity',
  customer: 'CustomerName',
  product: 'ProductName',
};

export async function getDetail(filters, { page = 1, pageSize = 25, sort = 'date', dir = 'desc' } = {}) {
  const sortColumn = SORTS[sort];
  if (!sortColumn) throw new ValidationError(`sort debe ser uno de: ${Object.keys(SORTS).join(', ')}`);
  const size = Math.min(Math.max(parseInt(pageSize, 10) || 25, 1), 100);
  const pageNo = Math.max(parseInt(page, 10) || 1, 1);
  const direction = String(dir).toLowerCase() === 'asc' ? 'ASC' : 'DESC';
  const { where, params } = buildWhere(filters);

  const [{ total }] = await query(`SELECT COUNT_BIG(*) AS total FROM bi.vw_sales_detail ${where}`, params);
  const rows = await query(
    `SELECT OrderID, OrderLineID, OrderDate, CustomerName, CustomerCategory, Region, City,
            Category, ProductName, Quantity, UnitPrice, NetSales
     FROM bi.vw_sales_detail ${where}
     ORDER BY ${sortColumn} ${direction}, SalesFactKey
     OFFSET @offset ROWS FETCH NEXT @size ROWS ONLY`,
    { ...params, offset: { type: sql.Int, value: (pageNo - 1) * size }, size: { type: sql.Int, value: size } },
  );
  return {
    page: pageNo,
    pageSize: size,
    total: Number(total),
    totalPages: Math.ceil(Number(total) / size),
    rows: rows.map((r) => ({
      orderId: r.OrderID, orderLineId: r.OrderLineID, orderDate: iso(r.OrderDate),
      customer: r.CustomerName, customerCategory: r.CustomerCategory, region: r.Region, city: r.City,
      category: r.Category, product: r.ProductName, quantity: r.Quantity,
      unitPrice: Number(r.UnitPrice), netSales: Number(r.NetSales),
    })),
  };
}

export async function getOrder(orderId) {
  const rows = await query(
    `SELECT OrderID, OrderLineID, OrderDate, CustomerName, City, Region, Category, ProductName,
            Quantity, UnitPrice, NetSales
     FROM bi.vw_sales_detail WHERE OrderID = @orderId ORDER BY OrderLineID`,
    { orderId: { type: sql.Int, value: orderId } },
  );
  if (!rows.length) return null;
  return {
    orderId: rows[0].OrderID,
    orderDate: iso(rows[0].OrderDate),
    customer: rows[0].CustomerName,
    city: rows[0].City,
    region: rows[0].Region,
    total: rows.reduce((s, r) => s + Number(r.NetSales), 0),
    lines: rows.map((r) => ({
      orderLineId: r.OrderLineID, category: r.Category, product: r.ProductName,
      quantity: r.Quantity, unitPrice: Number(r.UnitPrice), netSales: Number(r.NetSales),
    })),
  };
}

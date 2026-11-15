import { query, sql } from '../db.js';
import { iso } from './analytics.js';

const rangeParams = (filters) => ({
  from: { type: sql.Date, value: filters.from },
  to: { type: sql.Date, value: filters.to },
});

const number = (value) => Number(value ?? 0);

export async function getPurchasingAnalytics(filters) {
  const params = rangeParams(filters);
  const [summaryRows, seriesRows, suppliers, products] = await Promise.all([
    query(
      `SELECT SUM(PurchaseAmountExclTax) AS purchaseAmount,
              SUM(ReceivedQuantity) AS receivedQuantity,
              COUNT_BIG(*) AS lines,
              COUNT(DISTINCT PurchaseOrderID) AS purchaseOrders,
              COUNT(DISTINCT SupplierID) AS suppliers
       FROM bi.vw_purchase_detail
       WHERE PurchaseDate BETWEEN @from AND @to`,
      params,
    ),
    query(
      `SELECT DATEFROMPARTS([Year], [Month], 1) AS period,
              SUM(PurchaseAmountExclTax) AS purchaseAmount,
              SUM(ReceivedQuantity) AS receivedQuantity
       FROM bi.vw_purchase_detail
       WHERE PurchaseDate BETWEEN @from AND @to
       GROUP BY [Year], [Month]
       ORDER BY period`,
      params,
    ),
    query(
      `SELECT TOP (10) SupplierName AS name,
              SUM(PurchaseAmountExclTax) AS purchaseAmount,
              SUM(ReceivedQuantity) AS receivedQuantity,
              COUNT(DISTINCT PurchaseOrderID) AS purchaseOrders
       FROM bi.vw_purchase_detail
       WHERE PurchaseDate BETWEEN @from AND @to
       GROUP BY SupplierName
       ORDER BY purchaseAmount DESC, name`,
      params,
    ),
    query(
      `SELECT TOP (10) ProductName AS name,
              SUM(PurchaseAmountExclTax) AS purchaseAmount,
              SUM(ReceivedQuantity) AS receivedQuantity
       FROM bi.vw_purchase_detail
       WHERE PurchaseDate BETWEEN @from AND @to
       GROUP BY ProductName
       ORDER BY purchaseAmount DESC, name`,
      params,
    ),
  ]);
  const summary = summaryRows[0];
  return {
    period: { from: filters.from, to: filters.to },
    currency: 'GBP',
    summary: {
      purchaseAmount: number(summary.purchaseAmount),
      receivedQuantity: number(summary.receivedQuantity),
      lines: number(summary.lines),
      purchaseOrders: number(summary.purchaseOrders),
      suppliers: number(summary.suppliers),
    },
    series: seriesRows.map((row) => ({
      period: iso(row.period),
      purchaseAmount: number(row.purchaseAmount),
      receivedQuantity: number(row.receivedQuantity),
    })),
    suppliers: suppliers.map((row) => ({
      name: row.name,
      purchaseAmount: number(row.purchaseAmount),
      receivedQuantity: number(row.receivedQuantity),
      purchaseOrders: number(row.purchaseOrders),
    })),
    products: products.map((row) => ({
      name: row.name,
      purchaseAmount: number(row.purchaseAmount),
      receivedQuantity: number(row.receivedQuantity),
    })),
  };
}

export async function getProfitabilityAnalytics(filters) {
  const params = rangeParams(filters);
  const [summaryRows, seriesRows, categories, products] = await Promise.all([
    query(
      `SELECT SUM(NetSales) AS netSales,
              SUM(LineProfit) AS profit,
              SUM(Quantity) AS units,
              COUNT_BIG(*) AS lines,
              COUNT(DISTINCT InvoiceID) AS invoices
       FROM bi.vw_invoice_profit_detail
       WHERE InvoiceDate BETWEEN @from AND @to`,
      params,
    ),
    query(
      `SELECT DATEFROMPARTS([Year], [Month], 1) AS period,
              SUM(NetSales) AS netSales,
              SUM(LineProfit) AS profit
       FROM bi.vw_invoice_profit_detail
       WHERE InvoiceDate BETWEEN @from AND @to
       GROUP BY [Year], [Month]
       ORDER BY period`,
      params,
    ),
    query(
      `SELECT TOP (10) ISNULL(Category, N'Sin categoria') AS name,
              SUM(NetSales) AS netSales,
              SUM(LineProfit) AS profit
       FROM bi.vw_invoice_profit_detail
       WHERE InvoiceDate BETWEEN @from AND @to
       GROUP BY Category
       ORDER BY profit DESC, name`,
      params,
    ),
    query(
      `SELECT TOP (10) ProductName AS name,
              SUM(NetSales) AS netSales,
              SUM(LineProfit) AS profit,
              COUNT(DISTINCT InvoiceID) AS invoices
       FROM bi.vw_invoice_profit_detail
       WHERE InvoiceDate BETWEEN @from AND @to
       GROUP BY ProductName
       ORDER BY profit DESC, name`,
      params,
    ),
  ]);
  const summary = summaryRows[0];
  const netSales = number(summary.netSales);
  const profit = number(summary.profit);
  return {
    period: { from: filters.from, to: filters.to },
    currency: 'GBP',
    summary: {
      netSales,
      profit,
      marginPct: netSales ? (profit / netSales) * 100 : null,
      units: number(summary.units),
      lines: number(summary.lines),
      invoices: number(summary.invoices),
    },
    series: seriesRows.map((row) => {
      const monthSales = number(row.netSales);
      const monthProfit = number(row.profit);
      return {
        period: iso(row.period),
        netSales: monthSales,
        profit: monthProfit,
        marginPct: monthSales ? (monthProfit / monthSales) * 100 : null,
      };
    }),
    categories: categories.map((row) => ({
      name: row.name,
      netSales: number(row.netSales),
      profit: number(row.profit),
      marginPct: row.netSales ? (number(row.profit) / number(row.netSales)) * 100 : null,
    })),
    products: products.map((row) => ({
      name: row.name,
      netSales: number(row.netSales),
      profit: number(row.profit),
      invoices: number(row.invoices),
    })),
  };
}

export async function getInventoryAnalytics(filters) {
  const params = rangeParams(filters);
  const [movementRows, seriesRows, types, snapshotRows, lowStock] = await Promise.all([
    query(
      `SELECT COUNT_BIG(*) AS transactions,
              SUM(CASE WHEN Quantity > 0 THEN Quantity ELSE 0 END) AS receipts,
              SUM(CASE WHEN Quantity < 0 THEN -Quantity ELSE 0 END) AS issues,
              SUM(Quantity) AS netMovement,
              SUM(CASE WHEN TransactionTypeName LIKE N'%Adjustment%' THEN Quantity ELSE 0 END) AS adjustments
       FROM bi.vw_inventory_movement_detail
       WHERE TransactionDate BETWEEN @from AND @to`,
      params,
    ),
    query(
      `SELECT DATEFROMPARTS([Year], [Month], 1) AS period,
              SUM(CASE WHEN Quantity > 0 THEN Quantity ELSE 0 END) AS receipts,
              SUM(CASE WHEN Quantity < 0 THEN -Quantity ELSE 0 END) AS issues,
              SUM(CASE WHEN TransactionTypeName LIKE N'%Adjustment%' THEN Quantity ELSE 0 END) AS adjustments,
              SUM(Quantity) AS netMovement
       FROM bi.vw_inventory_movement_detail
       WHERE TransactionDate BETWEEN @from AND @to
       GROUP BY [Year], [Month]
       ORDER BY period`,
      params,
    ),
    query(
      `SELECT TransactionTypeID AS id, TransactionTypeName AS name,
              COUNT_BIG(*) AS transactions, SUM(Quantity) AS netQuantity
       FROM bi.vw_inventory_movement_detail
       WHERE TransactionDate BETWEEN @from AND @to
       GROUP BY TransactionTypeID, TransactionTypeName
       ORDER BY TransactionTypeID`,
      params,
    ),
    query(
      `SELECT MAX(SnapshotDate) AS snapshotDate,
              COUNT_BIG(*) AS items,
              SUM(QuantityOnHand) AS unitsOnHand,
              SUM(CASE WHEN StockStatus IN (N'Bajo de minimo', N'Agotado') THEN 1 ELSE 0 END) AS belowReorder
       FROM bi.vw_inventory_snapshot`,
    ),
    query(
      `SELECT TOP (20) ProductName AS name, Category AS category,
              QuantityOnHand AS quantityOnHand, ReorderLevel AS reorderLevel,
              TargetStockLevel AS targetStockLevel, StockStatus AS status
       FROM bi.vw_inventory_snapshot
       WHERE StockStatus IN (N'Bajo de minimo', N'Agotado')
       ORDER BY ReorderLevel - QuantityOnHand DESC, ProductName`,
    ),
  ]);
  const movement = movementRows[0];
  const snapshot = snapshotRows[0];
  return {
    period: { from: filters.from, to: filters.to },
    movements: {
      transactions: number(movement.transactions),
      receipts: number(movement.receipts),
      issues: number(movement.issues),
      netMovement: number(movement.netMovement),
      adjustments: number(movement.adjustments),
      series: seriesRows.map((row) => ({
        period: iso(row.period),
        receipts: number(row.receipts),
        issues: number(row.issues),
        adjustments: number(row.adjustments),
        netMovement: number(row.netMovement),
      })),
      types: types.map((row) => ({
        id: number(row.id),
        name: row.name,
        transactions: number(row.transactions),
        netQuantity: number(row.netQuantity),
      })),
    },
    snapshot: {
      date: snapshot.snapshotDate ? iso(snapshot.snapshotDate) : null,
      items: number(snapshot.items),
      unitsOnHand: number(snapshot.unitsOnHand),
      belowReorder: number(snapshot.belowReorder),
      lowStock: lowStock.map((row) => ({
        name: row.name,
        category: row.category,
        quantityOnHand: number(row.quantityOnHand),
        reorderLevel: number(row.reorderLevel),
        targetStockLevel: number(row.targetStockLevel),
        status: row.status,
      })),
    },
  };
}

import { Router } from 'express';
import { query } from '../db.js';
import { iso } from '../services/analytics.js';

export const mlRouter = Router();

const wrap = (fn) => (req, res, next) => fn(req, res).catch(next);

/** Modelo activo, sus metricas, historial reciente y predicciones vigentes. */
export async function loadForecast() {
  const [model] = await query(
    `SELECT TOP 1 ModelVersion, Algorithm, Horizon, TrainedAt, TrainPeriod, TestPeriod, ParamsJson, MetricsJson
     FROM ops.ml_model_registry WHERE IsActive = 1 ORDER BY TrainedAt DESC`,
  );
  if (!model) return { model: null, history: [], predictions: [] };

  const [history, predictions] = await Promise.all([
    query(
      `SELECT TOP 26 w.WeekStart, w.NetSales
       FROM bi.vw_weekly_sales w CROSS JOIN bi.vw_data_freshness f
       WHERE w.WeekStart >= f.FirstOrderDate AND DATEADD(DAY, 6, w.WeekStart) <= f.LastOrderDate
       ORDER BY w.WeekStart DESC`,
    ),
    query(
      `SELECT TargetPeriod, HorizonStep, PredictedValue, LowerBound, UpperBound, BaselineValue, PredictedAt
       FROM ops.ml_prediction WHERE ModelVersion = @v ORDER BY TargetPeriod`,
      { v: model.ModelVersion },
    ),
  ]);
  const params = JSON.parse(model.ParamsJson ?? '{}');
  return {
    model: {
      version: model.ModelVersion,
      algorithm: model.Algorithm,
      horizon: model.Horizon,
      trainedAt: model.TrainedAt,
      trainPeriod: model.TrainPeriod,
      testPeriod: model.TestPeriod,
      metrics: JSON.parse(model.MetricsJson),
      limitations: params.limitations ?? '',
    },
    history: history.reverse().map((r) => ({ period: iso(r.WeekStart), netSales: Number(r.NetSales) })),
    predictions: predictions.map((r) => ({
      period: iso(r.TargetPeriod), step: r.HorizonStep, value: Number(r.PredictedValue),
      lower: Number(r.LowerBound), upper: Number(r.UpperBound), baseline: Number(r.BaselineValue),
      predictedAt: r.PredictedAt,
    })),
    kind: 'prediction',
  };
}

mlRouter.get('/forecast', wrap(async (_req, res) => res.json(await loadForecast())));

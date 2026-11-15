"""Proceso programable de prediccion y monitoreo del modelo activo.

  python machine-learning/predict.py             # genera predicciones con el modelo activo
  python machine-learning/predict.py --evaluate  # compara predicciones pasadas con ventas reales

Programacion sugerida: tras cada carga del DW (p. ej. diaria) y reentrenar con train.py cada mes.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MODELS_DIR, connect, load_weekly_sales  # noqa: E402
from features import FEATURES, baseline_forecast, build_row  # noqa: E402


def active_model(conn):
    cur = conn.cursor()
    cur.execute("SELECT TOP 1 ModelVersion FROM ops.ml_model_registry WHERE IsActive = 1 ORDER BY TrainedAt DESC")
    row = cur.fetchone()
    if not row:
        sys.exit("No hay modelo activo; ejecuta machine-learning/train.py")
    return joblib.load(MODELS_DIR / f"{row[0]}.joblib")


def predict(conn):
    bundle = active_model(conn)
    df = load_weekly_sales(conn)
    y, dates, t = df["net_sales"].to_numpy(), pd.DatetimeIndex(df["week_start"]), len(df) - 1
    q_low, q_high = bundle["interval"]
    cur, created = conn.cursor(), 0
    for h, model in bundle["models"].items():
        row = build_row(y, dates, t, h)
        pred = float(model.predict(pd.DataFrame([row])[FEATURES])[0] * row["_base"])
        cur.execute(
            "SELECT 1 FROM ops.ml_prediction WHERE ModelVersion = ? AND TargetPeriod = ? AND HorizonStep = ?",
            bundle["version"], row["_target_date"].date(), h,
        )
        if cur.fetchone():
            continue  # evita duplicar predicciones para el mismo objetivo
        cur.execute(
            "INSERT INTO ops.ml_prediction (ModelVersion, TargetPeriod, HorizonStep, PredictedValue, LowerBound, UpperBound, BaselineValue) "
            "VALUES (?,?,?,?,?,?,?)",
            bundle["version"], row["_target_date"].date(), h, round(pred, 2),
            round(pred * (1 + q_low), 2), round(pred * (1 + q_high), 2), round(baseline_forecast(df, t), 2),
        )
        created += 1
    conn.commit()
    print(f"Modelo {bundle['version']}: {created} predicciones nuevas")


def evaluate(conn):
    df = load_weekly_sales(conn).set_index("week_start")["net_sales"]
    cur = conn.cursor()
    cur.execute("SELECT ModelVersion, TargetPeriod, PredictedValue, BaselineValue FROM ops.ml_prediction")
    rows = [(v, pd.Timestamp(d), float(p), float(b)) for v, d, p, b in cur.fetchall() if pd.Timestamp(d) in df.index]
    if not rows:
        print("Aun no hay semanas objetivo con datos reales completos para evaluar.")
        return
    true = np.array([df[d] for _, d, _, _ in rows])
    pred = np.array([p for _, _, p, _ in rows])
    base = np.array([b for _, _, _, b in rows])
    print(f"{len(rows)} predicciones evaluadas | MAE modelo {np.abs(true - pred).mean():,.0f} "
          f"vs linea base {np.abs(true - base).mean():,.0f} | MAPE modelo {(np.abs(true - pred) / true).mean() * 100:.1f}%")


if __name__ == "__main__":
    connection = connect()
    evaluate(connection) if "--evaluate" in sys.argv else predict(connection)

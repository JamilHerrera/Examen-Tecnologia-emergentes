"""Entrena, evalua, versiona y publica el pronostico de ventas semanales (horizonte 1-4 semanas).

Flujo (ver README.md): extraer de bi.vw_weekly_sales -> variables sin fuga -> split temporal
entrenamiento/validacion/prueba -> linea base -> seleccion SOLO con validacion -> evaluacion
unica en prueba -> reentrenar con todo -> guardar modelo, registrar metricas y predicciones.

Uso:  python machine-learning/train.py
"""
import json
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import MODELS_DIR, connect, load_weekly_sales  # noqa: E402
from features import FEATURES, MIN_HISTORY, baseline_forecast, build_row, supervised  # noqa: E402

HORIZON = 4
N_VAL = 26
N_TEST = 26
SEED = 42

CANDIDATES = {
    "ridge_a10": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
    "ridge_a100": make_pipeline(StandardScaler(), Ridge(alpha=100.0)),
    "gbr_d2": GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=SEED),
    "rf_leaf5": RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=SEED),
}


def metrics(y_true, y_pred) -> dict:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    err = y_true - y_pred
    return {
        "mae": float(np.abs(err).mean()),
        "rmse": float(np.sqrt((err ** 2).mean())),
        "mape": float((np.abs(err) / y_true).mean() * 100),
        "smape": float((2 * np.abs(err) / (np.abs(y_true) + np.abs(y_pred))).mean() * 100),
    }


def split(sup: pd.DataFrame, val_start, test_start):
    d = sup["_target_date"]
    return sup[d < val_start], sup[(d >= val_start) & (d < test_start)], sup[d >= test_start]


def fit_predict(estimator, fit_df, pred_df):
    model = clone(estimator).fit(fit_df[FEATURES], fit_df["target"])
    return model, model.predict(pred_df[FEATURES]) * pred_df["_base"].to_numpy()


def baseline_pred(df, sup):
    """Linea base por fila: promedio de las 4 ultimas semanas en el origen."""
    idx = {d: i for i, d in enumerate(df["week_start"])}
    return np.array([baseline_forecast(df, idx[o]) for o in sup["_origin"]])


def main():
    conn = connect()
    df = load_weekly_sales(conn)
    print(f"Semanas completas: {len(df)} ({df.week_start.min().date()} a {df.week_start.max().date()})")
    if len(df) < MIN_HISTORY + HORIZON + N_VAL + N_TEST + 20:
        sys.exit("Datos insuficientes para entrenar con validacion y prueba; reducir el alcance.")

    test_start = df["week_start"].iloc[-N_TEST]
    val_start = df["week_start"].iloc[-(N_TEST + N_VAL)]
    sups = {h: supervised(df, h) for h in range(1, HORIZON + 1)}

    # ---- Seleccion de algoritmo: solo entrenamiento -> validacion ----
    val_mae, base_val_mae = {}, []
    for name, est in CANDIDATES.items():
        maes = []
        for h, sup in sups.items():
            tr, va, _ = split(sup, val_start, test_start)
            _, pred = fit_predict(est, tr, va)
            maes.append(np.abs(va["y_true"].to_numpy() - pred).mean())
        val_mae[name] = float(np.mean(maes))
    for h, sup in sups.items():
        _, va, _ = split(sup, val_start, test_start)
        base_val_mae.append(np.abs(va["y_true"].to_numpy() - baseline_pred(df, va)).mean())
    best = min(val_mae, key=val_mae.get)
    print("MAE validacion:", {k: round(v) for k, v in val_mae.items()}, "| linea base:", round(float(np.mean(base_val_mae))))
    print("Algoritmo seleccionado:", best)

    # ---- Evaluacion unica en prueba (entrenado con train+val) ----
    per_h, pooled_true, pooled_pred, pooled_base, rel_resid = {}, [], [], [], []
    for h, sup in sups.items():
        tr, va, te = split(sup, val_start, test_start)
        _, pred = fit_predict(CANDIDATES[best], pd.concat([tr, va]), te)
        base = baseline_pred(df, te)
        per_h[h] = {"model": metrics(te["y_true"], pred), "baseline": metrics(te["y_true"], base), "n": int(len(te))}
        pooled_true += list(te["y_true"]); pooled_pred += list(pred); pooled_base += list(base)
        rel_resid += list((te["y_true"].to_numpy() - pred) / pred)
    test = {"model": metrics(pooled_true, pooled_pred), "baseline": metrics(pooled_true, pooled_base), "by_horizon": per_h}
    q_low, q_high = (float(np.quantile(rel_resid, q)) for q in (0.10, 0.90))
    beats = test["model"]["mae"] < test["baseline"]["mae"]
    print(f"TEST MAE modelo={test['model']['mae']:.0f}  linea base={test['baseline']['mae']:.0f}  "
          f"MAPE modelo={test['model']['mape']:.1f}%  base={test['baseline']['mape']:.1f}%  supera base: {beats}")

    # ---- Modelo final: reentrenado con toda la historia ----
    final = {}
    for h, sup in sups.items():
        final[h] = clone(CANDIDATES[best]).fit(sup[FEATURES], sup["target"])

    now = datetime.now(timezone.utc)
    version = f"sales-weekly-{now:%Y%m%d%H%M}"
    params = {"algorithm": best, "estimator": str(CANDIDATES[best]), "features": FEATURES, "horizon": HORIZON,
              "seed": SEED, "interval_rel_residual_q10_q90": [q_low, q_high]}
    all_metrics = {
        "validation_mae_by_candidate": val_mae, "validation_mae_baseline": float(np.mean(base_val_mae)),
        "test": test, "beats_baseline": beats,
        "n_weeks": int(len(df)),
    }
    train_period = f"{df.week_start.min().date()} a {(val_start - pd.Timedelta(days=1)).date()}"
    test_period = f"{test_start.date()} a {df.week_start.max().date()}"
    limitations = (
        "Serie corta (3.4 anos), sin festivos ni promociones en las variables; el intervalo usa residuos "
        "de solo 26 semanas de prueba. Reentrenar mensualmente y vigilar el MAE contra la linea base."
    )
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"version": version, "models": final, "features": FEATURES, "params": params,
                 "interval": [q_low, q_high]}, MODELS_DIR / f"{version}.joblib")

    # ---- Registro y predicciones futuras desde el ultimo origen conocido ----
    y = df["net_sales"].to_numpy()
    dates = pd.DatetimeIndex(df["week_start"])
    t = len(y) - 1
    cur = conn.cursor()
    cur.execute("UPDATE ops.ml_model_registry SET IsActive = 0")
    cur.execute(
        "INSERT INTO ops.ml_model_registry (ModelVersion, ModelName, Algorithm, TargetName, Horizon, TrainedAt, "
        "TrainPeriod, TestPeriod, ParamsJson, MetricsJson, IsActive) VALUES (?,?,?,?,?,?,?,?,?,?,1)",
        version, "weekly_net_sales_forecast", best, "net_sales_week", HORIZON, now.replace(tzinfo=None),
        train_period, test_period,
        json.dumps({**params, "limitations": limitations}), json.dumps(all_metrics),
    )
    for h in range(1, HORIZON + 1):
        row = build_row(y, dates, t, h)
        pred = float(final[h].predict(pd.DataFrame([row])[FEATURES])[0] * row["_base"])
        base = baseline_forecast(df, t)
        cur.execute(
            "INSERT INTO ops.ml_prediction (ModelVersion, TargetPeriod, HorizonStep, PredictedValue, LowerBound, UpperBound, BaselineValue) "
            "VALUES (?,?,?,?,?,?,?)",
            version, row["_target_date"].date(), h, round(pred, 2),
            round(pred * (1 + q_low), 2), round(pred * (1 + q_high), 2), round(base, 2),
        )
        print(f"  h={h} semana {row['_target_date'].date()}: prediccion {pred:,.0f} (base {base:,.0f})")
    cur.execute(
        "INSERT INTO ops.etl_run_log (Process, Status, FinishedAt, RowsProcessed, Message) VALUES (?,?,SYSUTCDATETIME(),?,?)",
        "ml_train_weekly_forecast", "success", len(df), f"{version} {best}; MAE prueba {test['model']['mae']:.0f} vs base {test['baseline']['mae']:.0f}",
    )
    conn.commit()
    print(f"Modelo registrado: {version}")


if __name__ == "__main__":
    main()

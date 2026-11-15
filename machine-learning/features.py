"""Ingenieria de variables para pronosticar ventas semanales.

Reglas anti-fuga (data leakage): para un origen `t` (ultima semana conocida) solo se usan
valores con indice <= t. De la semana objetivo (t+h) unicamente se usan variables de
calendario, que se conocen de antemano, y la venta de hace 52 semanas (ya observada).
El objetivo se normaliza por la media de las ultimas 8 semanas para que el modelo
no tenga que extrapolar el nivel de ventas (los arboles no extrapolan).
"""
import numpy as np
import pandas as pd

LAGS = 4
WINDOW = 8
YEAR = 52
MIN_HISTORY = YEAR + WINDOW  # semanas necesarias para construir ly_rel
FEATURES = [
    "lag0", "lag1", "lag2", "lag3", "ma4", "volatility", "ly_rel", "ly_neighbors",
    "woy_sin", "woy_cos", "month",
]


def _ma(y: np.ndarray, t: int, window: int) -> float:
    return float(y[t - window + 1 : t + 1].mean())


def build_row(y: np.ndarray, dates: pd.DatetimeIndex, t: int, h: int) -> dict:
    """Variables disponibles en el origen t para predecir la semana t+h."""
    base = _ma(y, t, WINDOW)
    target_date = dates[t] + pd.Timedelta(weeks=h)
    ly = t + h - YEAR  # misma semana del ano anterior (siempre <= t si h <= 52)
    base_ly = _ma(y, t - YEAR, WINDOW)
    woy = int(target_date.isocalendar().week)
    return {
        "lag0": y[t] / base, "lag1": y[t - 1] / base, "lag2": y[t - 2] / base, "lag3": y[t - 3] / base,
        "ma4": _ma(y, t, 4) / base,
        "volatility": float(y[t - WINDOW + 1 : t + 1].std()) / base,
        "ly_rel": y[ly] / base_ly,
        "ly_neighbors": float(y[ly - 1 : ly + 2].mean()) / base_ly,
        "woy_sin": np.sin(2 * np.pi * woy / 52.0),
        "woy_cos": np.cos(2 * np.pi * woy / 52.0),
        "month": target_date.month,
        "_base": base,
        "_target_date": target_date,
        "_origin": dates[t],
    }


def supervised(df: pd.DataFrame, h: int) -> pd.DataFrame:
    """Matriz supervisada para el horizonte h con una fila por origen valido."""
    y = df["net_sales"].to_numpy()
    dates = pd.DatetimeIndex(df["week_start"])
    rows = []
    for t in range(MIN_HISTORY - 1, len(y) - h):
        r = build_row(y, dates, t, h)
        r["target"] = y[t + h] / r["_base"]
        r["y_true"] = y[t + h]
        rows.append(r)
    return pd.DataFrame(rows)


def baseline_forecast(df: pd.DataFrame, t: int) -> float:
    """Linea base: promedio de las ultimas 4 semanas (prediccion simple)."""
    return _ma(df["net_sales"].to_numpy(), t, 4)

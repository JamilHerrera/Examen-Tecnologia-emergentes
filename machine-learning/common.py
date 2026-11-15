"""Utilidades compartidas del modulo de ML: conexion con la cuenta de minimo privilegio y carga de datos."""
import os
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = Path(__file__).resolve().parent / "models"
load_dotenv(ROOT / ".env")


def connect():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={os.getenv('MSSQL_SERVER', 'localhost,1433')};"
        f"DATABASE={os.getenv('MSSQL_DATABASE', 'WideWorldImporters')};"
        f"UID={os.environ['APP_DB_USER']};PWD={os.environ['APP_DB_PASSWORD']};"
        "TrustServerCertificate=yes"
    )


def load_weekly_sales(conn) -> pd.DataFrame:
    """Ventas semanales completas (lunes-domingo) desde la vista analitica bi.vw_weekly_sales.

    La primera semana (empieza el 2012-12-31, antes del primer pedido) y la ultima
    (el DW termina un martes) estan incompletas y se descartan para no sesgar el modelo.
    """
    cur = conn.cursor()
    cur.execute("SELECT MIN(FirstOrderDate), MAX(LastOrderDate) FROM bi.vw_data_freshness")
    first, last = cur.fetchone()
    cur.execute("SELECT WeekStart, NetSales, Orders FROM bi.vw_weekly_sales ORDER BY WeekStart")
    rows = cur.fetchall()
    df = pd.DataFrame([tuple(r) for r in rows], columns=["week_start", "net_sales", "orders"])
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["net_sales"] = df["net_sales"].astype(float)
    first, last = pd.Timestamp(first), pd.Timestamp(last)
    # Una semana es completa si el DW cubre sus 7 dias (desde el primer pedido hasta el ultimo).
    complete = (df["week_start"] >= first) & (df["week_start"] + pd.Timedelta(days=6) <= last)
    return df[complete].reset_index(drop=True)

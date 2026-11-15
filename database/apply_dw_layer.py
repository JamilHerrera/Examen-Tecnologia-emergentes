"""
Aplica la capa analitica y operativa del DW (database/dw/*.sql) y crea la cuenta
de minimo privilegio usada por backend y ML. Es idempotente.

Uso:  python database/apply_dw_layer.py
"""
import os
import re
import sys
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent


def connect(user, password, database):
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={os.getenv('MSSQL_SERVER', 'localhost,1433')};DATABASE={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes",
        autocommit=True,
    )


def run_script(cur, path):
    text = path.read_text(encoding="utf-8")
    for batch in re.split(r"^\s*GO\s*$", text, flags=re.MULTILINE | re.IGNORECASE):
        if batch.strip():
            cur.execute(batch)
    print(f"  OK {path.name}")


def main():
    db = os.getenv("MSSQL_DATABASE", "WideWorldImporters")
    app_user = os.environ["APP_DB_USER"]
    app_pw = os.environ["APP_DB_PASSWORD"]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", app_user):
        sys.exit("APP_DB_USER invalido")

    conn = connect(os.getenv("MSSQL_SA_USER", "sa"), os.environ["MSSQL_SA_PASSWORD"], db)
    cur = conn.cursor()
    for sql_file in sorted((ROOT / "dw").glob("*.sql")):
        run_script(cur, sql_file)

    # La contrasena se pasa como literal escapado porque CREATE LOGIN no admite parametros.
    pw_literal = app_pw.replace("'", "''")
    cur.execute(
        f"IF SUSER_ID('{app_user}') IS NULL CREATE LOGIN [{app_user}] "
        f"WITH PASSWORD = N'{pw_literal}', CHECK_POLICY = OFF; "
        f"ELSE ALTER LOGIN [{app_user}] WITH PASSWORD = N'{pw_literal}';"
    )
    cur.execute(f"IF USER_ID('{app_user}') IS NULL CREATE USER [{app_user}] FOR LOGIN [{app_user}];")
    # Solo vistas aprobadas (bi) + tablas operativas (ops). Sin acceso a dw/Sales/Warehouse.
    cur.execute(f"GRANT SELECT ON SCHEMA::bi TO [{app_user}];")
    cur.execute(f"GRANT SELECT, INSERT, UPDATE ON SCHEMA::ops TO [{app_user}];")
    print(f"  OK cuenta de minimo privilegio [{app_user}]")
    conn.close()

    check = connect(app_user, app_pw, db).cursor()
    check.execute("SELECT COUNT(*) FROM bi.vw_sales_detail")
    print(f"  Verificacion con [{app_user}]: bi.vw_sales_detail = {check.fetchone()[0]:,} filas")
    try:
        check.execute("SELECT TOP 1 * FROM dw.FactSales")
        print("  AVISO: la cuenta puede leer dw.FactSales directamente")
    except pyodbc.Error:
        print("  OK acceso directo a dw.FactSales denegado (esperado)")


if __name__ == "__main__":
    main()

"""
Genera documentation/DICCIONARIO_DATOS.md a partir del catalogo real del Data Warehouse
(schemas dw, bi y ops) mas las descripciones de negocio definidas aqui.

Uso:  python database/generate_data_dictionary.py
"""
import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DESCRIPTIONS = {
    "dw.DimDate": ("Dimension calendario (grano: un dia).", {
        "DateKey": "Clave sustituta YYYYMMDD.", "Date": "Fecha.", "Year": "Ano.", "Month": "Mes (1-12).",
        "MonthName": "Nombre del mes.", "Quarter": "Trimestre (1-4).", "DayOfWeek": "Dia de la semana (0=lunes).",
        "DayOfWeekName": "Nombre del dia.", "IsWeekend": "1 si es sabado o domingo.", "IsHoliday": "Reservado; no se cargan festivos.",
        "Week": "Semana ISO.", "DayOfYear": "Dia del ano."}),
    "dw.DimCustomer": ("Dimension cliente con historial SCD tipo 2 (ValidFrom/ValidTo/IsCurrent).", {
        "CustomerKey": "Clave sustituta.", "CustomerID": "Clave natural (Sales.Customers.CustomerID).",
        "CustomerName": "Nombre comercial.", "PrimaryContactPerson": "Persona de contacto (dato personal: NO se expone en BI ni se envia a IA).",
        "City": "Ciudad de entrega.", "StateProvince": "Estado/provincia.", "Country": "Pais.", "PostalCode": "Codigo postal de entrega.",
        "ValidFrom": "Inicio de vigencia de la version.", "ValidTo": "Fin de vigencia (9999-12-31 = vigente).",
        "IsCurrent": "1 si es la version vigente.", "CustomerCategory": "Categoria de cliente.", "BuyingGroup": "Grupo de compra.",
        "GeographyKey": "FK a DimGeography (ciudad de entrega)."}),
    "dw.DimProduct": ("Dimension producto (grano: articulo de inventario).", {
        "ProductKey": "Clave sustituta.", "StockItemID": "Clave natural (Warehouse.StockItems).", "ProductName": "Nombre del producto.",
        "Category": "Categoria = grupo de inventario principal (menor StockGroupID).", "Brand": "Marca.",
        "UnitPrice": "Precio unitario de catalogo.", "RecommendedRetailPrice": "Precio recomendado de venta.",
        "Color": "Color.", "Size": "Tamano."}),
    "dw.DimGeography": ("Dimension geografica (grano: ciudad). GeographyKey=1 es el miembro 'Unknown'.", {
        "GeographyKey": "Clave sustituta.", "CityID": "Clave natural (Application.Cities).", "City": "Ciudad.",
        "StateProvince": "Estado/provincia.", "Country": "Pais.", "Region": "Territorio de ventas (SalesTerritory).",
        "PostalCode": "No poblado (varia por cliente)."}),
    "dw.FactSales": ("Hechos de ventas (grano: una linea de pedido).", {
        "SalesFactKey": "Clave sustituta del hecho.", "DateKey": "FK a DimDate (fecha del pedido).", "CustomerKey": "FK a DimCustomer.",
        "ProductKey": "FK a DimProduct.", "GeographyKey": "FK a DimGeography (ciudad de entrega del cliente).",
        "OrderID": "Pedido de origen (dimension degenerada).", "OrderLineID": "Linea de origen (dimension degenerada).",
        "InvoiceID": "No poblado (reservado).", "Quantity": "Unidades pedidas (aditiva).", "UnitPrice": "Precio unitario (no aditiva).",
        "TaxRate": "Tasa de impuesto como fraccion (0.15 = 15%). Antes llamada Discount; el origen no registra descuentos.",
        "LineTotal": "Venta neta = Quantity x UnitPrice, sin impuestos (aditiva). Es la medida base de los KPIs.",
        "OrderStatus": "Estado fijo 'Completed'.", "InvoiceStatus": "No poblado.", "LoadedDate": "Momento de carga en el DW.",
        "SourceLastModified": "No poblado.", "IsDeleted": "Marca de borrado logico."}),
    "bi.vw_sales_detail": ("Vista aprobada que une hechos y dimensiones (unica fuente del dashboard y del asistente).", {}),
    "bi.vw_weekly_sales": ("Ventas agregadas por semana (lunes-domingo) para el modelo ML.", {}),
    "bi.vw_data_freshness": ("Fecha de ultima carga y rango de fechas de pedidos.", {}),
    "ops.app_user": ("Usuarios de la aplicacion (contrasena con bcrypt).", {}),
    "ops.etl_run_log": ("Bitacora de ejecuciones (ETL, reconciliacion, ML, alertas).", {}),
    "ops.reconciliation_result": ("Resultado de cada comprobacion origen vs DW.", {}),
    "ops.ml_model_registry": ("Registro versionado de modelos con parametros y metricas.", {}),
    "ops.ml_prediction": ("Predicciones con version de modelo, fecha, horizonte, intervalo y linea base.", {}),
    "ops.alert": ("Alertas (regla, modelo o IA) con estado y clave anti-duplicados.", {}),
    "ops.alert_delivery": ("Intentos de entrega de cada alerta por canal.", {}),
    "ops.assistant_audit": ("Auditoria de preguntas al asistente (sin guardar la respuesta).", {}),
}


def main():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=" + os.getenv("MSSQL_SERVER", "localhost,1433")
        + ";DATABASE=" + os.getenv("MSSQL_DATABASE", "WideWorldImporters")
        + ";UID=" + os.getenv("MSSQL_SA_USER", "sa") + ";PWD=" + os.environ["MSSQL_SA_PASSWORD"] + ";TrustServerCertificate=yes"
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.name, o.name, o.type, c.name, ty.name, c.max_length, c.precision, c.scale, c.is_nullable,
               CASE WHEN pk.column_id IS NOT NULL THEN 1 ELSE 0 END
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id AND s.name IN ('dw','bi','ops')
        JOIN sys.columns c ON c.object_id = o.object_id
        JOIN sys.types ty ON ty.user_type_id = c.user_type_id
        LEFT JOIN (SELECT ic.object_id, ic.column_id FROM sys.indexes i
                   JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                   WHERE i.is_primary_key = 1) pk ON pk.object_id = o.object_id AND pk.column_id = c.column_id
        WHERE o.type IN ('U','V')
        ORDER BY s.name, o.name, c.column_id
        """
    )
    tables = {}
    for schema, table, kind, col, ty, length, prec, scale, nullable, is_pk in cur.fetchall():
        if ty in ("nvarchar", "varchar", "char", "nchar"):
            ty = f"{ty}({'MAX' if length == -1 else length // 2 if ty.startswith('n') else length})"
        elif ty == "decimal":
            ty = f"decimal({prec},{scale})"
        tables.setdefault((schema, table, kind), []).append((col, ty, nullable, is_pk))

    out = [
        "# Diccionario de datos del Data Warehouse",
        "",
        "Generado automaticamente con `python database/generate_data_dictionary.py` a partir del catalogo de SQL Server.",
        "",
    ]
    for (schema, table, kind), cols in tables.items():
        key = f"{schema}.{table}"
        desc, col_desc = DESCRIPTIONS.get(key, ("", {}))
        out += [f"## `{key}` ({'vista' if kind == 'V' else 'tabla'})", "", desc, "",
                "| Columna | Tipo | Nulos | PK | Descripcion |", "|---|---|---|---|---|"]
        for col, ty, nullable, is_pk in cols:
            out.append(f"| {col} | {ty} | {'si' if nullable else 'no'} | {'si' if is_pk else ''} | {col_desc.get(col, '')} |")
        out.append("")
    path = ROOT / "documentation" / "DICCIONARIO_DATOS.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"Escrito {path} ({len(tables)} objetos)")


if __name__ == "__main__":
    main()

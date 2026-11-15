#!/usr/bin/env python3
"""Check table structure"""
import sys
sys.path.insert(0, '.')
from etl.extract import DatabaseConnector
from etl.config import SQL_SERVER_CONFIG

conn = DatabaseConnector(SQL_SERVER_CONFIG)
conn.connect()
cursor = conn.connection.cursor()

cursor.execute("SELECT TOP 1 * FROM staging_clean.Application_People_clean")
cols = [desc[0] for desc in cursor.description]
print("Application_People_clean columns:", cols)

conn.disconnect()

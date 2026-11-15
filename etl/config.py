"""
ETL Configuration
Centralized settings for database connections, logging, and processing parameters
"""
import os
from typing import Dict, Any
from datetime import datetime
import logging

# Database Connections
SQL_SERVER_CONFIG: Dict[str, Any] = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": os.getenv("MSSQL_SERVER", "localhost,1433"),
    "database": os.getenv("MSSQL_DATABASE", "WideWorldImporters"),
    "user": os.getenv("MSSQL_SA_USER", "sa"),
    "password": os.getenv("MSSQL_SA_PASSWORD", "P@ssw0rd123"),
    "encrypt": "no",
    "trust_certificate": "yes",
}

# Logging Configuration
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# ETL Parameters
BATCH_SIZE = 10000
CHUNK_SIZE = 5000
MAX_RETRIES = 3
RETRY_DELAY = 5

# Data Quality Thresholds
NULL_THRESHOLD = 0.1  # 10% nulls allowed per column
DUPLICATE_THRESHOLD = 0.01  # 1% duplicates allowed
OUTLIER_THRESHOLD = 3.0  # Standard deviations for outlier detection

# Staging Schemas
STAGING_RAW_SCHEMA = "staging_raw"
STAGING_CLEAN_SCHEMA = "staging_clean"
DW_SCHEMA = "dw"

# Source Database (WideWorldImporters)
SOURCE_DATABASE = "WideWorldImporters"

# Tables to Extract
# Note: Excluding tables with unsupported ODBC types (e.g., Geography/Geometry in -151)
SOURCE_TABLES = [
    "Sales.Orders",
    "Sales.OrderLines",
    "Sales.Invoices",
    "Sales.InvoiceLines",
    "Sales.CustomerCategories",
    "Sales.BuyingGroups",
    "Warehouse.StockItems",
    "Warehouse.Colors",
    "Application.People",
    "Application.DeliveryMethods",
]

print(f"✓ Configuration loaded: {SQL_SERVER_CONFIG['server']} | {SOURCE_DATABASE}")

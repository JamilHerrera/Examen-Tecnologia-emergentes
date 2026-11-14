-- ============================================================================
-- STAGING RAW SCHEMA
-- Purpose: Exact copy of source data from WideWorldImporters
-- No transformations, no cleanup - raw extraction layer
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging_raw')
    CREATE SCHEMA staging_raw;
GO

-- Note: Tables in this layer are created dynamically by Python ETL
-- This schema serves as a landing zone for extracted data

-- Sample audit table for tracking extractions
CREATE TABLE staging_raw.extraction_log (
    extraction_id BIGINT PRIMARY KEY IDENTITY(1,1),
    extraction_date DATETIME2 DEFAULT GETDATE(),
    table_name VARCHAR(200),
    row_count BIGINT,
    source_system VARCHAR(100) DEFAULT 'WideWorldImporters',
    status VARCHAR(50),
    duration_seconds INT
);

CREATE INDEX idx_extraction_log_date ON staging_raw.extraction_log(extraction_date);
CREATE INDEX idx_extraction_log_table ON staging_raw.extraction_log(table_name);

PRINT '✓ Staging Raw schema created'

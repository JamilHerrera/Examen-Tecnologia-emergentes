-- ============================================================================
-- STAGING CLEAN SCHEMA
-- Purpose: Cleaned, validated, and standardized data
-- Ready for loading into Data Warehouse
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging_clean')
    CREATE SCHEMA staging_clean;
GO

-- Audit table for tracking cleaning operations
CREATE TABLE staging_clean.data_quality_log (
    quality_check_id BIGINT PRIMARY KEY IDENTITY(1,1),
    check_date DATETIME2 DEFAULT GETDATE(),
    table_name VARCHAR(200),
    rows_in BIGINT,
    rows_out BIGINT,
    rows_rejected BIGINT,
    rejection_percentage FLOAT,
    quality_score FLOAT,
    status VARCHAR(50),
    issues VARCHAR(MAX)
);

CREATE INDEX idx_quality_log_date ON staging_clean.data_quality_log(check_date);
CREATE INDEX idx_quality_log_table ON staging_clean.data_quality_log(table_name);

-- Lineage tracking table
CREATE TABLE staging_clean.data_lineage (
    lineage_id BIGINT PRIMARY KEY IDENTITY(1,1),
    source_table VARCHAR(200),
    target_table VARCHAR(200),
    transformation_description VARCHAR(MAX),
    row_count BIGINT,
    created_date DATETIME2 DEFAULT GETDATE(),
    last_modified DATETIME2 DEFAULT GETDATE()
);

CREATE INDEX idx_lineage_source ON staging_clean.data_lineage(source_table);
CREATE INDEX idx_lineage_target ON staging_clean.data_lineage(target_table);

PRINT '✓ Staging Clean schema created'

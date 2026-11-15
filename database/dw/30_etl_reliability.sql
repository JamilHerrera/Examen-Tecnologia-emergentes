-- ETL watermarks, per-table execution details, rejected rows, and profiles.
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ops')
    EXEC('CREATE SCHEMA ops');
GO

IF COL_LENGTH('ops.etl_run_log', 'RowsRead') IS NULL
    ALTER TABLE ops.etl_run_log ADD RowsRead BIGINT NULL;
IF COL_LENGTH('ops.etl_run_log', 'RowsInserted') IS NULL
    ALTER TABLE ops.etl_run_log ADD RowsInserted BIGINT NULL;
IF COL_LENGTH('ops.etl_run_log', 'RowsUpdated') IS NULL
    ALTER TABLE ops.etl_run_log ADD RowsUpdated BIGINT NULL;
IF COL_LENGTH('ops.etl_run_log', 'RowsRejected') IS NULL
    ALTER TABLE ops.etl_run_log ADD RowsRejected BIGINT NULL;
IF COL_LENGTH('ops.etl_run_log', 'RowsDeleted') IS NULL
    ALTER TABLE ops.etl_run_log ADD RowsDeleted BIGINT NULL;
IF COL_LENGTH('ops.etl_run_log', 'WatermarkStart') IS NULL
    ALTER TABLE ops.etl_run_log ADD WatermarkStart DATETIME2(7) NULL;
IF COL_LENGTH('ops.etl_run_log', 'WatermarkEnd') IS NULL
    ALTER TABLE ops.etl_run_log ADD WatermarkEnd DATETIME2(7) NULL;
IF COL_LENGTH('ops.etl_run_log', 'DurationSeconds') IS NULL
    ALTER TABLE ops.etl_run_log ADD DurationSeconds DECIMAL(18,3) NULL;
GO

IF OBJECT_ID('ops.etl_watermark', 'U') IS NULL
CREATE TABLE ops.etl_watermark (
    PipelineName   NVARCHAR(100) NOT NULL,
    SourceObject   NVARCHAR(256) NOT NULL,
    WatermarkColumn SYSNAME NOT NULL,
    WatermarkValue DATETIME2(7) NOT NULL,
    OverlapSeconds INT NOT NULL,
    UpdatedAt      DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_etl_watermark PRIMARY KEY (PipelineName, SourceObject)
);
GO

IF OBJECT_ID('ops.etl_table_run', 'U') IS NULL
CREATE TABLE ops.etl_table_run (
    TableRunID      BIGINT IDENTITY(1,1) PRIMARY KEY,
    RunID           BIGINT NULL REFERENCES ops.etl_run_log(RunID),
    Mode            NVARCHAR(20) NOT NULL,
    SourceObject    NVARCHAR(256) NOT NULL,
    TargetObject    NVARCHAR(256) NOT NULL,
    WatermarkColumn SYSNAME NULL,
    WatermarkStart  DATETIME2(7) NULL,
    WatermarkEnd    DATETIME2(7) NULL,
    RowsRead        BIGINT NOT NULL DEFAULT 0,
    RowsInserted    BIGINT NOT NULL DEFAULT 0,
    RowsUpdated     BIGINT NOT NULL DEFAULT 0,
    RowsRejected    BIGINT NOT NULL DEFAULT 0,
    RowsDeleted     BIGINT NOT NULL DEFAULT 0,
    DurationSeconds DECIMAL(18,3) NOT NULL DEFAULT 0,
    Status          NVARCHAR(20) NOT NULL,
    ErrorDetail     NVARCHAR(2000) NULL,
    StartedAt       DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    FinishedAt      DATETIME2(7) NULL
);
GO

IF OBJECT_ID('ops.etl_reject', 'U') IS NULL
CREATE TABLE ops.etl_reject (
    RejectID      BIGINT IDENTITY(1,1) PRIMARY KEY,
    RunID         BIGINT NULL REFERENCES ops.etl_run_log(RunID),
    SourceObject  NVARCHAR(256) NOT NULL,
    RuleName      NVARCHAR(150) NOT NULL,
    BusinessKey   NVARCHAR(450) NULL,
    RowData       NVARCHAR(MAX) NOT NULL,
    Detail        NVARCHAR(2000) NULL,
    RejectedAt    DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('ops.etl_profile', 'U') IS NULL
CREATE TABLE ops.etl_profile (
    ProfileID   BIGINT IDENTITY(1,1) PRIMARY KEY,
    RunID       BIGINT NULL REFERENCES ops.etl_run_log(RunID),
    SourceObject NVARCHAR(256) NOT NULL,
    Layer       NVARCHAR(30) NOT NULL,
    ProfileJson NVARCHAR(MAX) NOT NULL,
    CreatedAt   DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('ops.etl_table_run') AND name = 'IX_etl_table_run_RunID')
    CREATE INDEX IX_etl_table_run_RunID ON ops.etl_table_run(RunID, SourceObject);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('ops.etl_reject') AND name = 'IX_etl_reject_RunID')
    CREATE INDEX IX_etl_reject_RunID ON ops.etl_reject(RunID, SourceObject);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('ops.etl_profile') AND name = 'IX_etl_profile_RunID')
    CREATE INDEX IX_etl_profile_RunID ON ops.etl_profile(RunID, SourceObject, Layer);
GO

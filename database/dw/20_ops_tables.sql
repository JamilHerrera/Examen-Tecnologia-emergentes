-- FASE 5-9 - Tablas operativas (schema ops): usuarios demo, monitoreo ETL,
-- registro de modelos ML, predicciones, alertas y auditoria del asistente.
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ops') EXEC('CREATE SCHEMA ops');
GO

IF OBJECT_ID('ops.app_user','U') IS NULL
CREATE TABLE ops.app_user (
    UserID        INT IDENTITY(1,1) PRIMARY KEY,
    Username      NVARCHAR(50)  NOT NULL UNIQUE,
    PasswordHash  NVARCHAR(100) NOT NULL,
    Role          NVARCHAR(20)  NOT NULL CHECK (Role IN ('viewer','analyst','admin')),
    IsActive      BIT NOT NULL DEFAULT 1,
    CreatedAt     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('ops.etl_run_log','U') IS NULL
CREATE TABLE ops.etl_run_log (
    RunID         BIGINT IDENTITY(1,1) PRIMARY KEY,
    Process       NVARCHAR(100) NOT NULL,
    Status        NVARCHAR(20)  NOT NULL CHECK (Status IN ('running','success','failed','warning')),
    StartedAt     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    FinishedAt    DATETIME2 NULL,
    RowsProcessed BIGINT NULL,
    Message       NVARCHAR(1000) NULL
);
GO

IF OBJECT_ID('ops.reconciliation_result','U') IS NULL
CREATE TABLE ops.reconciliation_result (
    ResultID      BIGINT IDENTITY(1,1) PRIMARY KEY,
    RunID         BIGINT NULL REFERENCES ops.etl_run_log(RunID),
    CheckName     NVARCHAR(150) NOT NULL,
    SourceValue   DECIMAL(24,2) NULL,
    DwValue       DECIMAL(24,2) NULL,
    Difference    AS (DwValue - SourceValue),
    Passed        BIT NOT NULL,
    Note          NVARCHAR(500) NULL,
    CheckedAt     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('ops.ml_model_registry','U') IS NULL
CREATE TABLE ops.ml_model_registry (
    ModelVersion  NVARCHAR(40) NOT NULL PRIMARY KEY,
    ModelName     NVARCHAR(100) NOT NULL,
    Algorithm     NVARCHAR(100) NOT NULL,
    TargetName    NVARCHAR(100) NOT NULL,
    Horizon       INT NOT NULL,
    TrainedAt     DATETIME2 NOT NULL,
    TrainPeriod   NVARCHAR(60) NULL,
    TestPeriod    NVARCHAR(60) NULL,
    ParamsJson    NVARCHAR(MAX) NULL,
    MetricsJson   NVARCHAR(MAX) NOT NULL,
    IsActive      BIT NOT NULL DEFAULT 1
);
GO

IF OBJECT_ID('ops.ml_prediction','U') IS NULL
CREATE TABLE ops.ml_prediction (
    PredictionID    BIGINT IDENTITY(1,1) PRIMARY KEY,
    ModelVersion    NVARCHAR(40) NOT NULL REFERENCES ops.ml_model_registry(ModelVersion),
    PredictedAt     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    TargetPeriod    DATE NOT NULL,
    HorizonStep     INT NOT NULL,
    PredictedValue  DECIMAL(18,2) NOT NULL,
    LowerBound      DECIMAL(18,2) NULL,
    UpperBound      DECIMAL(18,2) NULL,
    BaselineValue   DECIMAL(18,2) NULL
);
GO

IF OBJECT_ID('ops.alert','U') IS NULL
CREATE TABLE ops.alert (
    AlertID          BIGINT IDENTITY(1,1) PRIMARY KEY,
    CreatedAt        DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    AlertType        NVARCHAR(40)  NOT NULL,
    Severity         NVARCHAR(10)  NOT NULL CHECK (Severity IN ('low','medium','high','critical')),
    Indicator        NVARCHAR(100) NOT NULL,
    Entity           NVARCHAR(150) NULL,
    ObservedValue    DECIMAL(18,2) NULL,
    ThresholdValue   DECIMAL(18,2) NULL,
    ReferencePeriod  NVARCHAR(80)  NULL,
    Source           NVARCHAR(10)  NOT NULL CHECK (Source IN ('rule','model','ai')),
    ModelVersion     NVARCHAR(40)  NULL,
    Explanation      NVARCHAR(2000) NULL,
    RecommendedAction NVARCHAR(500) NULL,
    IsSimulated      BIT NOT NULL DEFAULT 0,
    Status           NVARCHAR(12) NOT NULL DEFAULT 'new' CHECK (Status IN ('new','attended','dismissed','resolved')),
    StatusChangedAt  DATETIME2 NULL,
    StatusChangedBy  NVARCHAR(50) NULL,
    DedupKey         NVARCHAR(200) NOT NULL
);
CREATE UNIQUE INDEX UX_alert_dedup ON ops.alert(DedupKey);
GO

IF OBJECT_ID('ops.alert_delivery','U') IS NULL
CREATE TABLE ops.alert_delivery (
    DeliveryID  BIGINT IDENTITY(1,1) PRIMARY KEY,
    AlertID     BIGINT NOT NULL REFERENCES ops.alert(AlertID),
    Channel     NVARCHAR(20) NOT NULL,
    Attempt     INT NOT NULL,
    Status      NVARCHAR(10) NOT NULL CHECK (Status IN ('sent','failed','skipped')),
    Detail      NVARCHAR(500) NULL,
    AttemptedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('ops.assistant_audit','U') IS NULL
CREATE TABLE ops.assistant_audit (
    AuditID      BIGINT IDENTITY(1,1) PRIMARY KEY,
    AskedAt      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    Username     NVARCHAR(50) NOT NULL,
    Question     NVARCHAR(1000) NOT NULL,
    Intent       NVARCHAR(60) NULL,
    Outcome      NVARCHAR(20) NOT NULL,
    LlmModel     NVARCHAR(80) NULL,
    LatencyMs    INT NULL
);
GO

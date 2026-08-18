-- ============================================================
-- Standard ETL support tables (SQL Server syntax).
-- Run this ONCE per database that will host etl_toolkit pipelines.
-- For Postgres/MySQL: swap IDENTITY -> SERIAL/AUTO_INCREMENT and
-- DATETIME2 -> TIMESTAMP, NVARCHAR(MAX) -> TEXT.
-- ============================================================

IF OBJECT_ID('dbo.ETL_Load_Log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ETL_Load_Log (
        run_id          INT IDENTITY(1,1) PRIMARY KEY,
        pipeline_name   NVARCHAR(200)   NOT NULL,
        table_name      NVARCHAR(200)   NULL,
        start_ts        DATETIME2       NOT NULL,
        end_ts          DATETIME2       NULL,
        status          NVARCHAR(20)    NOT NULL,   -- RUNNING / SUCCESS / FAILED
        rows_processed  INT             NULL,
        error_message   NVARCHAR(MAX)   NULL
    );
END;

IF OBJECT_ID('dbo.ETL_DQ_Results', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ETL_DQ_Results (
        dq_id           INT IDENTITY(1,1) PRIMARY KEY,
        pipeline_name   NVARCHAR(200)   NOT NULL,
        table_name      NVARCHAR(200)   NOT NULL,
        run_ts          DATETIME2       NOT NULL,
        row_count       INT             NULL,
        overall_status  NVARCHAR(20)    NOT NULL,   -- PASS / WARN / FAIL / FAIL_BLOCKING
        check_details   NVARCHAR(MAX)   NULL        -- JSON array of individual check results
    );
END;

-- Helpful indexes for dashboarding / trend queries
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ETL_Load_Log_Pipeline_StartTs')
    CREATE INDEX IX_ETL_Load_Log_Pipeline_StartTs ON dbo.ETL_Load_Log (pipeline_name, start_ts DESC);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ETL_DQ_Results_Table_RunTs')
    CREATE INDEX IX_ETL_DQ_Results_Table_RunTs ON dbo.ETL_DQ_Results (table_name, run_ts DESC);

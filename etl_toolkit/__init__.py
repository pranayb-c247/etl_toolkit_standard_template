"""
etl_toolkit
===========
Standardized, reusable ETL framework for office data engineering projects.

Modules:
    config            -> load config.yaml / .env into a single settings object
    connectors        -> DB connection factory (SQL Server, Postgres, MySQL)
    cleaning          -> reusable data-cleaning functions
    quality           -> data quality checks + monitoring
    loaders           -> staging -> main load patterns (bulk insert, upsert/merge)
    logging_utils     -> ETL_Load_Log style run logging (console + DB)
    orchestration     -> Pipeline/Task classes, dependency-based CLI runner (no Airflow needed)
    reporting         -> HTML/Excel run + DQ report generator
    utils             -> retry decorator, alert/notify helpers

Typical usage:
    from etl_toolkit.orchestration.pipeline import Pipeline, Task
    from etl_toolkit.config import load_config
"""

__version__ = "1.0.0"

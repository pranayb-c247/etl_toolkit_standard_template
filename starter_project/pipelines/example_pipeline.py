"""
example_pipeline.py
--------------------
Reference pipeline showing how EVERY new project should be wired using
etl_toolkit, so nobody re-writes connection/cleaning/DQ/load/logging code
from scratch. Copy this file as a starting point for a new pipeline.

Run it with:
    python main.py --pipeline pipelines.example_pipeline
"""

import pandas as pd

from etl_toolkit.connectors.factory import get_connector
from etl_toolkit.cleaning import cleaners
from etl_toolkit.quality import checks
from etl_toolkit.quality.monitor import DQMonitor
from etl_toolkit.loaders.sql_loader import bulk_insert_staging, merge_staging_to_main
from etl_toolkit.logging_utils.etl_logger import get_logger
from etl_toolkit.orchestration.pipeline import Pipeline, Task

logger = get_logger("example_pipeline")


# ---------------------------------------------------------------
# TASK FUNCTIONS  (each takes `ctx` and returns whatever it wants
# to hand to the next task via ctx['results'][task_name])
# ---------------------------------------------------------------

def extract(ctx) -> pd.DataFrame:
    """Replace this with your real extract: API call, CSV read, DB query, etc."""
    cfg = ctx["config"]
    logger.info("Extracting data from source...")

    # --- demo data; swap for real extraction logic ---
    df = pd.DataFrame({
        "project_number": ["P001", "P002", "P002", None],
        "project_status": ["Active", "Active", "Active", "Active"],
        "project_name  ": ["Tower A", "Tower B", "Tower B", "Tower C"],
        "contract_date": ["2024-01-15", "15-02-2024", "2024/03/10", None],
        "contract_amount": [1500000.456, 2200000.1, 2200000.1, 900000],
    })
    return df


def clean(ctx) -> pd.DataFrame:
    df = ctx["results"]["extract"]
    logger.info("Cleaning %d raw rows...", len(df))

    df = cleaners.clean_pipeline(df, steps=[
        ("standardize_column_names", {}),
        ("strip_whitespace", {}),
        ("parse_dates", {"columns": ["contract_date"]}),
        ("cast_numeric", {"columns": ["contract_amount"], "decimal_places": 2}),
        ("drop_empty_rows", {"required_cols": ["project_number"]}),
        # composite key dedup - never dedupe on a single column when the
        # real natural key is composite (see cleaners.py docstring)
        ("dedup_dataframe", {"key_cols": ["project_number", "project_status"]}),
    ])
    return df


def run_data_quality(ctx) -> dict:
    df = ctx["results"]["clean"]
    cfg = ctx["config"]

    dq = DQMonitor(pipeline_name="example_pipeline", table_name="example_table")
    dq.add_check(checks.check_row_count, {"min_rows": cfg.get("dq.min_rows", 1)}, blocking=True)
    dq.add_check(checks.check_not_null, {"column": "project_number", "threshold_pct": 0}, blocking=True)
    dq.add_check(checks.check_unique, {"columns": ["project_number", "project_status"]}, blocking=False)
    dq.add_check(checks.check_value_range, {"column": "contract_amount", "min_val": 0}, blocking=False)

    result = dq.run(df)
    dq.raise_if_failed(result)  # stops the pipeline if a blocking check fails
    ctx["results"]["dq_result"] = result
    return result


def load(ctx):
    df = ctx["results"]["clean"]
    cfg = ctx["config"]

    connector = get_connector(cfg.get("db").as_dict())
    with connector:
        staging_table = cfg.get("staging_tables.example_table")
        main_table = cfg.get("main_tables.example_table")

        bulk_insert_staging(connector, df, staging_table, truncate_first=True)

        merge_staging_to_main(
            connector,
            staging_table=staging_table,
            main_table=main_table,
            key_columns=["project_number", "project_status"],
            update_columns=["project_name", "contract_date", "contract_amount"],
            insert_columns=["project_number", "project_status", "project_name",
                             "contract_date", "contract_amount"],
        )
    return {"rows_loaded": len(df)}


# ---------------------------------------------------------------
# PIPELINE WIRING - this is the part every new pipeline customizes
# ---------------------------------------------------------------

def build_pipeline(config) -> Pipeline:
    pipeline = Pipeline("example_pipeline")
    pipeline.add_task(Task("extract", extract, retries=2, retry_delay_sec=10))
    pipeline.add_task(Task("clean", clean, depends_on=["extract"]))
    pipeline.add_task(Task("data_quality", run_data_quality, depends_on=["clean"], critical=True))
    pipeline.add_task(Task("load", load, depends_on=["data_quality"]))
    return pipeline


if __name__ == "__main__":
    # allows: python pipelines/example_pipeline.py  (quick local test without the CLI wrapper)
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from etl_toolkit.config import load_config
    from etl_toolkit.reporting.report_generator import save_run_report_html

    cfg = load_config("config/config.yaml")
    pl = build_pipeline(cfg)
    report = pl.run(context={"config": cfg})
    print(save_run_report_html(report))

# etl_toolkit — Office Standard ETL Framework

Reusable framework so every new pipeline (SQL Server / Postgres / MySQL, API or CSV
sourced) starts from the same building blocks instead of being written from scratch.
No Airflow dependency — orchestration runs as a plain Python process, schedulable via
cron or Windows Task Scheduler.

## What's inside

| Module | Purpose |
|---|---|
| `etl_toolkit/config.py` | Load `config.yaml` + `.env`, with `${ENV_VAR}` secret substitution |
| `etl_toolkit/connectors/` | `get_connector()` factory for SQL Server / Postgres / MySQL, incl. `fast_executemany` |
| `etl_toolkit/cleaning/` | Reusable cleaning functions: dates, dedup (composite-key safe), whitespace, BIGINT casting, etc. |
| `etl_toolkit/quality/` | Atomic DQ checks (`checks.py`) + `DQMonitor` to compose/run/persist a full DQ suite |
| `etl_toolkit/loaders/` | `bulk_insert_staging`, `merge_staging_to_main` (upsert), `append_only_load` |
| `etl_toolkit/logging_utils/` | Console+file logger, plus `ETLRunLogger` writing to `ETL_Load_Log` table |
| `etl_toolkit/orchestration/` | `Pipeline` / `Task` — dependency-graph runner + generic CLI (`etl-run`) |
| `etl_toolkit/reporting/` | HTML/Excel run reports + DQ reports |
| `etl_toolkit/utils/` | `@retry` decorator, email/Slack failure alerts |

## Install (per machine / venv)

```bash
cd etl_toolkit
pip install -e .
```

This registers the `etl_toolkit` package **and** an `etl-run` console command.

## One-time DB setup

Run `sql/create_etl_tables.sql` against each database that will host pipelines. It
creates `ETL_Load_Log` (run history) and `ETL_DQ_Results` (data quality history).

## Starting a new pipeline project

1. Copy the `starter_project/` folder, rename it for the new project.
2. `pip install -e ../etl_toolkit` inside the new project's venv.
3. Copy `.env.example` → `.env`, fill in real credentials (never commit `.env`).
4. Edit `config/config.yaml` for the project's tables/API endpoints.
5. Copy `pipelines/example_pipeline.py` → `pipelines/<your_pipeline>.py` and edit the
   `extract` / `clean` / `run_data_quality` / `load` functions + `build_pipeline()`.
6. Run it:
   ```bash
   python main.py --pipeline pipelines.your_pipeline
   ```
7. Schedule it:
   - **Cron:** `0 3 * * * cd /path/to/project && venv/bin/python main.py --pipeline pipelines.your_pipeline`
   - **Windows Task Scheduler:** program = venv `python.exe`, arguments =
     `main.py --pipeline pipelines.your_pipeline`, start-in = project folder.

Every run automatically gets: retries per task, dependency-aware skip-on-failure,
an HTML run report under `logs/reports/`, and a Slack/email alert on failure (if
configured in `config.yaml`).

## Example: wiring a pipeline

```python
from etl_toolkit.orchestration.pipeline import Pipeline, Task

def extract(ctx): ...      # returns a DataFrame
def clean(ctx): ...        # ctx["results"]["extract"] -> cleaned DataFrame
def run_dq(ctx): ...        # runs DQMonitor, raises if a blocking check fails
def load(ctx): ...         # staging load + merge to main

def build_pipeline(config):
    p = Pipeline("my_pipeline")
    p.add_task(Task("extract", extract, retries=2))
    p.add_task(Task("clean", clean, depends_on=["extract"]))
    p.add_task(Task("data_quality", run_dq, depends_on=["clean"], critical=True))
    p.add_task(Task("load", load, depends_on=["data_quality"]))
    return p
```

## Why these design choices

- **No Airflow**: one less service to install/maintain per client machine; a plain
  Python process + OS scheduler covers 95% of the office's ETL needs.
- **Composite-key-safe dedup**: `dedup_dataframe()` always requires an explicit key
  list — this class of bug (single-column dedupe silently dropping valid rows) has
  bitten past pipelines and is now impossible by construction.
- **Blocking vs non-blocking DQ checks**: critical checks (e.g. primary key not null)
  stop the pipeline before bad data reaches production; non-critical checks (e.g.
  referential integrity) just warn.
- **BIGINT-safe loads**: `enforce_dtype_for_bigint()` + explicit `setinputsizes` in
  the loader prevent pyodbc mis-inferring large IDs as INT and overflowing.

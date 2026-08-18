# Project Starter (built on etl_toolkit)

Copy this whole folder to start a new ETL project. It already wires up config
loading, connectors, cleaning, data quality, loading, and orchestration via
`etl_toolkit` — you only fill in the extract/clean/load logic specific to
this project.

## Setup

```bash
# 1. install the shared framework (editable, so team updates to etl_toolkit
#    are picked up automatically)
pip install -e ../etl_toolkit

# 2. project-specific deps (if any) go in this folder's requirements.txt

# 3. secrets
cp .env.example .env
# fill in DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, etc.

# 4. one-time: run sql/create_etl_tables.sql (in ../etl_toolkit/sql/) against
#    this project's database if it hasn't been run there before
```

## Folder layout

```
config/
  config.yaml       <- non-secret settings, ${ENV_VAR} for secrets
.env                <- real secrets (gitignored)
.env.example        <- template, safe to commit
pipelines/
  example_pipeline.py  <- copy this per new pipeline
logs/               <- run logs + HTML/Excel reports land here
main.py             <- generic entry point, don't need to touch this
```

## Run a pipeline

```bash
python main.py --pipeline pipelines.example_pipeline
```

## Add a new pipeline

1. `cp pipelines/example_pipeline.py pipelines/new_pipeline.py`
2. Edit `extract()`, `clean()`, `run_data_quality()`, `load()`.
3. Add any new tables to `config/config.yaml` under `staging_tables:` / `main_tables:`.
4. `python main.py --pipeline pipelines.new_pipeline`

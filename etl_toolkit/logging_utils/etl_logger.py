"""
etl_logger.py
-------------
Standardized run logging - console + rotating file + optional DB table
(ETL_Load_Log, schema in sql/create_etl_tables.sql), consistent across every
pipeline in the office so run history is queryable in one place.

Usage:
    logger = get_logger("dld_etl_pipeline")   # console + file logging

    run_log = ETLRunLogger(connector, pipeline_name="dld_etl_pipeline")
    run_id = run_log.start_run(table_name="projects")
    ... do work ...
    run_log.end_run(run_id, status="SUCCESS", rows_processed=1200)
    # or on error:
    run_log.end_run(run_id, status="FAILED", error_message=str(e))
"""

import logging
import os
import datetime
from logging.handlers import RotatingFileHandler


def get_logger(pipeline_name: str, log_dir: str = "logs", level=logging.INFO) -> logging.Logger:
    """Console + rotating file logger, one file per pipeline."""
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(pipeline_name)
    logger.setLevel(level)

    if logger.handlers:  # avoid duplicate handlers on repeated calls
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f"{pipeline_name}.log"), maxBytes=5_000_000, backupCount=5
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


class ETLRunLogger:
    """Writes pipeline run start/end records into ETL_Load_Log table."""

    def __init__(self, connector, pipeline_name: str, table: str = "ETL_Load_Log"):
        self.connector = connector
        self.pipeline_name = pipeline_name
        self.table = table
        self.logger = get_logger(pipeline_name)

    def start_run(self, table_name: str) -> int:
        if self.connector.conn is None:
            self.connector.connect()
        cur = self.connector.conn.cursor()
        cur.execute(
            f"""INSERT INTO {self.table} (pipeline_name, table_name, start_ts, status)
                OUTPUT INSERTED.run_id
                VALUES (?, ?, ?, ?)""",
            (self.pipeline_name, table_name, datetime.datetime.now(), "RUNNING"),
        )
        run_id = cur.fetchone()[0]
        self.connector.conn.commit()
        self.logger.info("Run started: run_id=%s table=%s", run_id, table_name)
        return run_id

    def end_run(self, run_id: int, status: str, rows_processed: int = None, error_message: str = None):
        cur = self.connector.conn.cursor()
        cur.execute(
            f"""UPDATE {self.table}
                SET end_ts = ?, status = ?, rows_processed = ?, error_message = ?
                WHERE run_id = ?""",
            (datetime.datetime.now(), status, rows_processed, error_message, run_id),
        )
        self.connector.conn.commit()
        log_fn = self.logger.info if status == "SUCCESS" else self.logger.error
        log_fn("Run finished: run_id=%s status=%s rows=%s error=%s",
               run_id, status, rows_processed, error_message)

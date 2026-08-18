"""
monitor.py
----------
Runs a declarative list of DQ checks against a dataframe, aggregates the
result, optionally persists it to an ETL_DQ_Results table (see
sql/create_etl_tables.sql), and raises if any check marked "blocking" fails.

Usage:
    from etl_toolkit.quality.monitor import DQMonitor

    dq = DQMonitor(pipeline_name="dld_etl_pipeline", table_name="projects")
    dq.add_check(checks.check_row_count, {"min_rows": 100})
    dq.add_check(checks.check_unique, {"columns": ["project_number", "project_status"]})
    dq.add_check(checks.check_not_null, {"column": "project_number"}, blocking=True)

    result = dq.run(df)
    dq.persist(connector, result)   # optional, writes to ETL_DQ_Results
    dq.raise_if_failed(result)      # optional, stops the pipeline on blocking failures
"""

import datetime
import json
import logging

logger = logging.getLogger("etl_toolkit.quality")


class DQMonitor:
    def __init__(self, pipeline_name: str, table_name: str):
        self.pipeline_name = pipeline_name
        self.table_name = table_name
        self._checks = []  # list of (fn, kwargs, blocking)

    def add_check(self, fn, kwargs: dict, blocking: bool = False):
        self._checks.append((fn, kwargs, blocking))
        return self

    def run(self, df) -> dict:
        run_ts = datetime.datetime.now()
        results = []
        for fn, kwargs, blocking in self._checks:
            res = fn(df, **kwargs)
            res["blocking"] = blocking
            results.append(res)
            log_fn = logger.info if res["status"] == "PASS" else logger.warning
            log_fn("[DQ] %s.%s | %s | %s", self.table_name, res["check"], res["status"], res["details"])

        overall_status = "PASS"
        if any(r["status"] == "FAIL" and r["blocking"] for r in results):
            overall_status = "FAIL_BLOCKING"
        elif any(r["status"] == "FAIL" for r in results):
            overall_status = "FAIL"
        elif any(r["status"] == "WARN" for r in results):
            overall_status = "WARN"

        return {
            "pipeline_name": self.pipeline_name,
            "table_name": self.table_name,
            "run_ts": run_ts,
            "row_count": len(df),
            "overall_status": overall_status,
            "checks": results,
        }

    def raise_if_failed(self, result: dict):
        if result["overall_status"] == "FAIL_BLOCKING":
            failed = [r for r in result["checks"] if r["status"] == "FAIL" and r["blocking"]]
            raise RuntimeError(
                f"Blocking DQ check(s) failed for {result['table_name']}: {failed}"
            )

    def persist(self, connector, result: dict, table: str = "ETL_DQ_Results"):
        """
        Writes one summary row per DQ run into `table` (schema in
        sql/create_etl_tables.sql). connector must be a connected BaseConnector.
        """
        cur = connector.conn.cursor()
        cur.execute(
            f"""INSERT INTO {table}
                (pipeline_name, table_name, run_ts, row_count, overall_status, check_details)
                VALUES (?, ?, ?, ?, ?, ?)""",
            (
                result["pipeline_name"],
                result["table_name"],
                result["run_ts"],
                result["row_count"],
                result["overall_status"],
                json.dumps(result["checks"], default=str),
            ),
        )
        connector.conn.commit()

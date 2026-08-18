"""
pipeline.py
-----------
Lightweight, Airflow-free orchestration for ETL pipelines built from
independent Python functions ("Tasks") with declared dependencies.

Design goals:
    - Zero extra infra (no scheduler daemon, no metadata DB required to run)
    - Dependency-graph execution (topological sort) so tasks run in the
      right order and independent branches could be parallelized later
    - Per-task retry, timing, and status tracking
    - Fails fast but always produces a full run report (see reporting/)
    - Runs from CLI, cron, Windows Task Scheduler, or plain `python main.py`

Usage:
    from etl_toolkit.orchestration.pipeline import Pipeline, Task

    def extract_projects(ctx): ...
    def clean_projects(ctx): ...
    def load_projects(ctx): ...

    pipeline = Pipeline("dld_etl_pipeline")
    pipeline.add_task(Task("extract", extract_projects))
    pipeline.add_task(Task("clean", clean_projects, depends_on=["extract"]))
    pipeline.add_task(Task("load", load_projects, depends_on=["clean"]))

    result = pipeline.run(context={"config": cfg})
"""

import time
import logging
import datetime
import traceback

logger = logging.getLogger("etl_toolkit.orchestration")


class Task:
    def __init__(self, name: str, fn, depends_on: list = None, retries: int = 0,
                 retry_delay_sec: float = 5.0, critical: bool = True):
        """
        fn(ctx) -> anything; return value is stored in ctx['results'][name]
        depends_on : list of task names that must SUCCEED before this runs
        critical   : if True and this task fails, downstream tasks + the run
                     are marked FAILED. If False, failure is logged but the
                     pipeline continues (use for optional/best-effort steps).
        """
        self.name = name
        self.fn = fn
        self.depends_on = depends_on or []
        self.retries = retries
        self.retry_delay_sec = retry_delay_sec
        self.critical = critical


class Pipeline:
    def __init__(self, name: str):
        self.name = name
        self.tasks = {}
        self._order = []  # insertion order, used for stable tie-breaking

    def add_task(self, task: Task):
        if task.name in self.tasks:
            raise ValueError(f"Duplicate task name '{task.name}'")
        self.tasks[task.name] = task
        self._order.append(task.name)
        return self

    def _topological_order(self):
        """Kahn's algorithm; raises on circular dependencies."""
        in_degree = {name: 0 for name in self.tasks}
        graph = {name: [] for name in self.tasks}

        for name, task in self.tasks.items():
            for dep in task.depends_on:
                if dep not in self.tasks:
                    raise ValueError(f"Task '{name}' depends on unknown task '{dep}'")
                graph[dep].append(name)
                in_degree[name] += 1

        queue = [n for n in self._order if in_degree[n] == 0]
        ordered = []
        while queue:
            n = queue.pop(0)
            ordered.append(n)
            for nxt in graph[n]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(ordered) != len(self.tasks):
            remaining = set(self.tasks) - set(ordered)
            raise ValueError(f"Circular dependency detected among tasks: {remaining}")

        return ordered

    def run(self, context: dict = None) -> dict:
        """
        Executes tasks in dependency order. Returns a run report dict that
        reporting.report_generator can turn into an HTML/Excel summary.
        """
        ctx = context or {}
        ctx.setdefault("results", {})

        run_started = datetime.datetime.now()
        task_reports = []
        failed_tasks = set()
        order = self._topological_order()

        logger.info("Pipeline '%s' starting. Task order: %s", self.name, order)

        for task_name in order:
            task = self.tasks[task_name]

            blocked_by = [d for d in task.depends_on if d in failed_tasks]
            if blocked_by:
                logger.warning("Skipping task '%s' - upstream failed: %s", task_name, blocked_by)
                task_reports.append({
                    "task": task_name, "status": "SKIPPED",
                    "duration_sec": 0, "error": f"Skipped due to failed dependency: {blocked_by}",
                })
                failed_tasks.add(task_name)
                continue

            status, error, duration = self._run_task_with_retry(task, ctx)
            task_reports.append({
                "task": task_name, "status": status, "duration_sec": round(duration, 2), "error": error,
            })

            if status == "FAILED":
                failed_tasks.add(task_name)
                if task.critical:
                    logger.error("Critical task '%s' failed - downstream tasks will be skipped.", task_name)

        run_ended = datetime.datetime.now()
        overall_status = "FAILED" if any(t["status"] == "FAILED" for t in task_reports) else "SUCCESS"

        report = {
            "pipeline_name": self.name,
            "started_at": run_started,
            "ended_at": run_ended,
            "duration_sec": (run_ended - run_started).total_seconds(),
            "overall_status": overall_status,
            "tasks": task_reports,
        }
        logger.info("Pipeline '%s' finished with status %s in %.2fs",
                    self.name, overall_status, report["duration_sec"])
        return report

    @staticmethod
    def _run_task_with_retry(task: Task, ctx: dict):
        attempts = task.retries + 1
        last_error = None
        start = time.time()

        for attempt in range(1, attempts + 1):
            try:
                logger.info("Running task '%s' (attempt %d/%d)", task.name, attempt, attempts)
                result = task.fn(ctx)
                ctx["results"][task.name] = result
                return "SUCCESS", None, time.time() - start
            except Exception as e:
                last_error = f"{e}\n{traceback.format_exc()}"
                logger.error("Task '%s' failed on attempt %d/%d: %s", task.name, attempt, attempts, e)
                if attempt < attempts:
                    time.sleep(task.retry_delay_sec)

        return "FAILED", last_error, time.time() - start

"""
cli.py
------
Generic command-line entry point so any Pipeline can be scheduled with
plain cron (Linux) or Windows Task Scheduler - no orchestrator daemon needed.

Each pipeline script (see starter_project/pipelines/) exposes a
`build_pipeline(config) -> Pipeline` function. This CLI imports that,
runs it, prints/saves the report, sends alerts on failure, and sets the
process exit code (0 = success, 1 = failure) so schedulers can detect failures.

Usage:
    python -m etl_toolkit.orchestration.cli --pipeline pipelines.example_pipeline --config config/config.yaml
"""

import argparse
import importlib
import sys
import logging

from etl_toolkit.config import load_config
from etl_toolkit.logging_utils.etl_logger import get_logger
from etl_toolkit.reporting.report_generator import save_run_report_html
from etl_toolkit.utils.notify import notify_pipeline_failure


def main():
    parser = argparse.ArgumentParser(description="Run an etl_toolkit pipeline.")
    parser.add_argument("--pipeline", required=True,
                         help="Python module path exposing build_pipeline(config), e.g. pipelines.example_pipeline")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--report-dir", default="logs/reports")
    args = parser.parse_args()

    cfg = load_config(args.config, args.env)
    module = importlib.import_module(args.pipeline)

    if not hasattr(module, "build_pipeline"):
        print(f"ERROR: {args.pipeline} does not expose build_pipeline(config)")
        sys.exit(1)

    pipeline = module.build_pipeline(cfg)
    logger = get_logger(pipeline.name)

    report = pipeline.run(context={"config": cfg})

    report_path = save_run_report_html(report, output_dir=args.report_dir)
    logger.info("Run report saved: %s", report_path)

    if report["overall_status"] == "FAILED":
        failed_tasks = [t["task"] for t in report["tasks"] if t["status"] == "FAILED"]
        error_summary = f"Failed tasks: {failed_tasks}"
        notify_pipeline_failure(cfg, pipeline.name, error_summary)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

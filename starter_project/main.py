"""
main.py
-------
Entry point for this project. Delegates to etl_toolkit's generic CLI so
every pipeline in this repo runs the same way and every run gets the same
logging / DQ / reporting / alerting behaviour for free.

Examples:
    python main.py --pipeline pipelines.example_pipeline
    python main.py --pipeline pipelines.example_pipeline --config config/config.yaml

Schedule with cron:
    0 3 * * * cd /path/to/project && venv/bin/python main.py --pipeline pipelines.example_pipeline

Schedule with Windows Task Scheduler:
    Program: C:\\path\\to\\venv\\Scripts\\python.exe
    Arguments: main.py --pipeline pipelines.example_pipeline
    Start in: C:\\path\\to\\project
"""

from etl_toolkit.orchestration.cli import main

if __name__ == "__main__":
    main()

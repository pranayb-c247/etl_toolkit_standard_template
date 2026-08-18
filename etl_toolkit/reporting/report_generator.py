"""
report_generator.py
--------------------
Turns Pipeline.run() reports and DQMonitor.run() results into shareable
HTML (and optionally Excel) reports - so pipeline health / DQ status can be
glanced at without digging through logs.
"""

import os
import datetime
import pandas as pd

_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; background:#f5f6fa; margin:0; padding:24px; }}
  h1 {{ font-size:20px; }}
  .summary {{ background:#fff; border-radius:8px; padding:16px 20px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .status {{ display:inline-block; padding:4px 10px; border-radius:4px; font-weight:600; color:#fff; }}
  .SUCCESS, .PASS {{ background:#2ecc71; }}
  .FAILED, .FAIL, .FAIL_BLOCKING {{ background:#e74c3c; }}
  .WARN {{ background:#f39c12; }}
  .SKIPPED {{ background:#95a5a6; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:8px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  th, td {{ text-align:left; padding:10px 14px; border-bottom:1px solid #eee; font-size:13px; }}
  th {{ background:#2c3e50; color:#fff; }}
  tr:last-child td {{ border-bottom:none; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <div class="summary">{summary_html}</div>
  {table_html}
</body>
</html>
"""


def save_run_report_html(report: dict, output_dir: str = "logs/reports") -> str:
    """report = output of Pipeline.run()"""
    os.makedirs(output_dir, exist_ok=True)
    ts = report["started_at"].strftime("%Y%m%d_%H%M%S")
    filename = f"{report['pipeline_name']}_{ts}.html"
    path = os.path.join(output_dir, filename)

    summary_html = f"""
        <b>Pipeline:</b> {report['pipeline_name']}<br>
        <b>Status:</b> <span class="status {report['overall_status']}">{report['overall_status']}</span><br>
        <b>Started:</b> {report['started_at']}<br>
        <b>Duration:</b> {report['duration_sec']:.2f}s
    """

    rows = "".join(
        f"""<tr>
                <td>{t['task']}</td>
                <td><span class="status {t['status']}">{t['status']}</span></td>
                <td>{t['duration_sec']}</td>
                <td>{(t['error'] or '')[:300]}</td>
            </tr>"""
        for t in report["tasks"]
    )
    table_html = f"""
        <table>
            <tr><th>Task</th><th>Status</th><th>Duration (s)</th><th>Error</th></tr>
            {rows}
        </table>
    """

    html = _HTML_TEMPLATE.format(
        title=f"ETL Run Report - {report['pipeline_name']}",
        summary_html=summary_html,
        table_html=table_html,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def save_dq_report_html(dq_result: dict, output_dir: str = "logs/reports") -> str:
    """dq_result = output of DQMonitor.run()"""
    os.makedirs(output_dir, exist_ok=True)
    ts = dq_result["run_ts"].strftime("%Y%m%d_%H%M%S")
    filename = f"DQ_{dq_result['table_name']}_{ts}.html"
    path = os.path.join(output_dir, filename)

    summary_html = f"""
        <b>Pipeline:</b> {dq_result['pipeline_name']}<br>
        <b>Table:</b> {dq_result['table_name']}<br>
        <b>Row Count:</b> {dq_result['row_count']}<br>
        <b>Overall Status:</b> <span class="status {dq_result['overall_status']}">{dq_result['overall_status']}</span>
    """

    rows = "".join(
        f"""<tr>
                <td>{c['check']}</td>
                <td>{c.get('column') or ''}</td>
                <td><span class="status {c['status']}">{c['status']}</span></td>
                <td>{'Yes' if c.get('blocking') else 'No'}</td>
                <td>{c['details']}</td>
            </tr>"""
        for c in dq_result["checks"]
    )
    table_html = f"""
        <table>
            <tr><th>Check</th><th>Column</th><th>Status</th><th>Blocking</th><th>Details</th></tr>
            {rows}
        </table>
    """

    html = _HTML_TEMPLATE.format(
        title=f"DQ Report - {dq_result['table_name']}",
        summary_html=summary_html,
        table_html=table_html,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def save_report_excel(report: dict, output_dir: str = "logs/reports") -> str:
    """Export a Pipeline.run() report as .xlsx (one sheet: task summary)."""
    os.makedirs(output_dir, exist_ok=True)
    ts = report["started_at"].strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{report['pipeline_name']}_{ts}.xlsx")

    df = pd.DataFrame(report["tasks"])
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Task Summary", index=False)
        meta = pd.DataFrame([{
            "pipeline_name": report["pipeline_name"],
            "overall_status": report["overall_status"],
            "started_at": report["started_at"],
            "duration_sec": report["duration_sec"],
        }])
        meta.to_excel(writer, sheet_name="Run Meta", index=False)

    return path

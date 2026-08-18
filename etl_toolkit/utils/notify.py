"""
notify.py
---------
Minimal alerting helpers so pipeline failures don't go unnoticed.
Extend send_email / send_slack with your office's real SMTP/webhook creds
via config.yaml - kept optional/best-effort so a notify failure never
crashes the pipeline itself.
"""

import logging
import smtplib
from email.mime.text import MIMEText

import requests

logger = logging.getLogger("etl_toolkit.utils")


def send_email(smtp_config: dict, subject: str, body: str):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_config["from_addr"]
        msg["To"] = ", ".join(smtp_config["to_addrs"])

        with smtplib.SMTP(smtp_config["host"], smtp_config.get("port", 587)) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["from_addr"], smtp_config["to_addrs"], msg.as_string())
        logger.info("notify: email sent - %s", subject)
    except Exception as e:
        logger.warning("notify: failed to send email: %s", e)


def send_slack(webhook_url: str, message: str):
    try:
        resp = requests.post(webhook_url, json={"text": message}, timeout=10)
        resp.raise_for_status()
        logger.info("notify: slack message sent")
    except Exception as e:
        logger.warning("notify: failed to send slack message: %s", e)


def notify_pipeline_failure(config, pipeline_name: str, error_message: str):
    """Convenience wrapper - reads config.notifications.* if present."""
    subject = f"[ETL FAILED] {pipeline_name}"
    body = f"Pipeline '{pipeline_name}' failed.\n\nError:\n{error_message}"

    smtp_cfg = config.get("notifications.email")
    if smtp_cfg:
        send_email(smtp_cfg, subject, body)

    slack_url = config.get("notifications.slack_webhook")
    if slack_url:
        send_slack(slack_url, f"{subject}\n{error_message}")

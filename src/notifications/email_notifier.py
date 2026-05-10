"""
Email notification for CRITICAL and HIGH severity alerts.

Configuration (all from environment):
  SMTP_HOST                 — SMTP server hostname (required to enable email)
  SMTP_PORT                 — port, default 587
  SMTP_USER                 — login username (optional for relays that trust source IP)
  SMTP_PASSWORD             — login password
  SMTP_FROM                 — From address, defaults to SMTP_USER
  ALERT_EMAIL_RECIPIENTS    — comma-separated list of recipient addresses
  SENTINEL_URL              — dashboard base URL for the alert link

If SMTP_HOST is not set, send_alert_email() logs a warning and returns False.
It never raises — a notification failure must never crash the dispatch pipeline.
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

_DASHBOARD_URL = os.environ.get(
    "SENTINEL_URL",
    "https://proactive-sentinel-production.up.railway.app/dashboard",
)


def _smtp_config() -> Optional[dict]:
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return None
    return {
        "host": host,
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_addr": (
            os.environ.get("SMTP_FROM", "")
            or os.environ.get("SMTP_USER", "sentinel@proactive-sentinel.internal")
        ),
    }


def _recipients() -> list:
    raw = os.environ.get("ALERT_EMAIL_RECIPIENTS", "").strip()
    return [r.strip() for r in raw.split(",") if r.strip()]


def _mask_ip(ip: str) -> str:
    """Partially mask an IP address. 192.168.1.100 → 192.168.xxx.xxx"""
    parts = str(ip or "").split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.xxx.xxx"
    return "xxx.xxx.xxx.xxx"


def send_alert_email(alert) -> bool:
    """
    Send an email notification for a CRITICAL or HIGH alert.

    Returns True if the message was accepted by the SMTP server.
    Returns False (and logs a warning) if SMTP is not configured,
    recipients are not set, or the send fails for any reason.
    Never raises.
    """
    config = _smtp_config()
    if not config:
        logger.warning(
            "Email notification skipped for alert %s: SMTP_HOST not configured",
            alert.id,
        )
        return False

    recipients = _recipients()
    if not recipients:
        logger.warning(
            "Email notification skipped for alert %s: ALERT_EMAIL_RECIPIENTS not set",
            alert.id,
        )
        return False

    severity = str(alert.severity or "").upper()
    subject = f"[{severity}] Proactive Sentinel Alert — {alert.title}"

    raw = alert.raw_data or {}
    source_ip = raw.get("source_ip") or raw.get("ip") or "unknown"
    masked_ip = _mask_ip(source_ip)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    dashboard_link = os.environ.get("SENTINEL_URL", _DASHBOARD_URL)

    body = (
        f"Proactive Sentinel Alert\n"
        f"{'=' * 40}\n\n"
        f"Title      : {alert.title}\n"
        f"Severity   : {severity}\n"
        f"Category   : {alert.category or 'unknown'}\n"
        f"Source IP  : {masked_ip}\n"
        f"Timestamp  : {timestamp}\n"
        f"Status     : {alert.status or 'open'}\n\n"
        f"Dashboard  : {dashboard_link}\n\n"
        f"{'=' * 40}\n"
        f"Automated alert from Proactive Sentinel SOC.\n"
        f"Reply to this message to contact the IT Security team.\n"
    )

    msg = MIMEMultipart()
    msg["From"] = config["from_addr"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config["host"], config["port"]) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if config["user"]:
                smtp.login(config["user"], config["password"])
            smtp.send_message(msg)
        logger.info(
            "Email alert sent for alert %s (%s) to %d recipient(s)",
            alert.id,
            severity,
            len(recipients),
        )
        return True
    except Exception as exc:
        logger.warning(
            "Email alert failed for alert %s: %s",
            alert.id,
            exc,
        )
        return False

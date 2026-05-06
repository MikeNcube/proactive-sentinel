"""
Action Dispatcher — post-detection automated response.

Severity routing:
  CRITICAL  →  FLAG + BLOCK + REPORT
  HIGH      →  FLAG + REPORT
  MEDIUM    →  FLAG
  LOW       →  log only
"""

import logging
import os
import re

from src.extensions import db, get_redis
from src.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

BLOCK_TTL_SECONDS = int(os.environ.get("BLOCK_TTL_SECONDS", "86400"))  # 24 h default
BLOCKED_IP_PREFIX = "blocked_ip:"

_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _extract_ip(alert) -> str | None:
    """Return a source IP from alert.raw_data, or None if absent."""
    raw = alert.raw_data or {}
    return raw.get("source_ip") or raw.get("ip") or None


class ActionDispatcher:
    """Dispatch automated actions based on alert severity."""

    @staticmethod
    def flag(alert) -> None:
        """FLAG: the persisted alert is the dashboard entry — log the dispatch."""
        logger.info(
            "FLAG: alert %s (severity=%s, category=%s) visible on dashboard",
            alert.id,
            alert.severity,
            alert.category,
        )

    @staticmethod
    def block(alert) -> bool:
        """BLOCK: write source IP to Redis with TTL. Returns True if blocked."""
        ip = _extract_ip(alert)
        if not ip:
            logger.debug("BLOCK skipped for alert %s: no source IP in raw_data", alert.id)
            return False
        try:
            r = get_redis()
            r.setex(f"{BLOCKED_IP_PREFIX}{ip}", BLOCK_TTL_SECONDS, str(alert.id))
            logger.info(
                "BLOCK: %s blocked for %ds (alert %s)", ip, BLOCK_TTL_SECONDS, alert.id
            )
            return True
        except Exception as exc:
            logger.warning("BLOCK failed (Redis unavailable): %s", exc)
            return False

    @staticmethod
    def report(alert) -> bool:
        """REPORT: write a structured AuditLog entry. Returns True on success."""
        from src.models.user import User

        # AuditLog.actor_id is a non-nullable FK → look up the tenant's first user.
        try:
            user = User.query.filter_by(tenant_id=str(alert.tenant_id)).first()
        except Exception as exc:
            logger.warning("REPORT skipped: user lookup failed for tenant %s: %s", alert.tenant_id, exc)
            return False

        if not user:
            logger.warning(
                "REPORT skipped for alert %s: no user found for tenant %s",
                alert.id,
                alert.tenant_id,
            )
            return False

        try:
            entry = AuditLog(
                tenant_id=str(alert.tenant_id),
                actor_id=str(user.id),
                action="alert_auto_dispatched",
                resource_type="alert",
                resource_id=str(alert.id),
                new_value={
                    "severity": alert.severity,
                    "category": alert.category,
                    "source": alert.source,
                    "title": alert.title,
                },
            )
            db.session.add(entry)
            db.session.commit()
            logger.info("REPORT: audit entry written for alert %s", alert.id)
            return True
        except Exception as exc:
            db.session.rollback()
            logger.exception("REPORT failed: %s", exc)
            return False

    @classmethod
    def dispatch(cls, alert) -> dict:
        """
        Route actions by severity.

        Returns a dict:
          {"flag": bool, "block": bool, "report": bool}
        """
        severity = str(alert.severity or "low").lower()
        result = {"flag": False, "block": False, "report": False}

        if severity == "critical":
            cls.flag(alert)
            result["flag"] = True
            result["block"] = cls.block(alert)
            result["report"] = cls.report(alert)

        elif severity == "high":
            cls.flag(alert)
            result["flag"] = True
            result["report"] = cls.report(alert)

        elif severity == "medium":
            cls.flag(alert)
            result["flag"] = True

        else:
            logger.debug("LOW alert %s: log only, no automated action", alert.id)

        return result

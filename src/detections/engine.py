import logging
from typing import Dict, Optional

from src.actions.dispatcher import ActionDispatcher
from src.detections.correlation_engine import CorrelationEngine
from src.detections.rules import classify_severity
from src.extensions import db
from src.models.alert import Alert

logger = logging.getLogger(__name__)


class DetectionEngine:
    def __init__(self):
        self.correlation = CorrelationEngine()

    def process_alert(self, alert_data: Dict) -> Optional[Alert]:
        """Deduplicate, construct, persist, and return an Alert, or None if suppressed."""
        # Dedup via Redis fingerprint â€” fail-open so a Redis outage never drops events.
        try:
            if not self.correlation.should_alert(alert_data):
                return None
        except Exception as exc:
            logger.warning("Redis dedup unavailable, allowing alert through: %s", exc)

        valid_fields = {c.name for c in Alert.__table__.columns}
        clean_data = {k: v for k, v in alert_data.items() if k in valid_fields}
        if not clean_data.get("title"):
            category = clean_data.get("category") or "unknown"
            source = clean_data.get("source") or "unknown"
            clean_data["title"] = f"{category.replace('_', ' ').title()} from {source}"
        # Severity override: rules engine classifies by event_type, ignoring sender's claim.
        clean_data["severity"] = classify_severity(clean_data.get("category") or "")
        alert = Alert(**clean_data)

        try:
            db.session.add(alert)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to persist alert: %s", exc)
            raise

        try:
            ActionDispatcher.dispatch(alert)
        except Exception as exc:
            logger.warning("ActionDispatcher.dispatch failed (non-fatal): %s", exc)

        return alert


from datetime import datetime

from sqlalchemy import Boolean, DateTime, String

from src.extensions import db
from src.models.types import CrossJSON, ArrayOfStrings


class Integration(db.Model):
    """Runtime-registered integration. Built-in systems live in zororo_systems.py."""

    __tablename__ = "integrations"

    key = db.Column(String(100), primary_key=True)
    name = db.Column(String(200), nullable=False)
    description = db.Column(String(500), default="")
    url = db.Column(String(500), default="")
    webhook_secret = db.Column(String(255), default="")
    alert_thresholds = db.Column(CrossJSON(), default=dict)
    pii_fields = db.Column(ArrayOfStrings(), default=list)
    enabled = db.Column(Boolean, default=True, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "webhook_secret": "",  # never expose raw secret in API responses
            "alert_thresholds": self.alert_thresholds or {},
            "pii_fields": self.pii_fields or [],
            "enabled": self.enabled,
            "builtin": False,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

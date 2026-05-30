from datetime import datetime
import uuid

from sqlalchemy import DateTime, Enum, String

from src.extensions import db
from src.models.types import ArrayOfStrings, UUID
from src.utils.encryption import EncryptedJSON


class Alert(db.Model):
    """Security/operations alert record bound to a tenant."""

    __tablename__ = "alerts"

    id = db.Column(UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(UUID(), db.ForeignKey("tenants.id"), nullable=False)
    title = db.Column(String(500), nullable=False)
    severity = db.Column(
        Enum("critical", "high", "medium", "low", name="alert_severity"),
        nullable=False,
    )
    status = db.Column(
        Enum("open", "investigating", "resolved", "dismissed", name="alert_status"),
        default="open",
    )
    category = db.Column(String(100))  # ransomware, data_exfil, etc.
    mitre_techniques = db.Column(ArrayOfStrings(), default=list)  # T1046, T1570
    source = db.Column(String(255))  # detection_engine, ai_classifier, etc.
    description = db.Column(db.Text)
    raw_data = db.Column(EncryptedJSON(), default=dict)
    confidence = db.Column(db.Float, default=0.5)  # 0-1
    assigned_to = db.Column(UUID(), db.ForeignKey("users.id"))
    created_at = db.Column(DateTime, default=datetime.utcnow)
    resolved_at = db.Column(DateTime)

    __table_args__ = (
        db.Index("idx_alert_tenant_severity", "tenant_id", "severity"),
        db.Index("idx_alert_tenant_status", "tenant_id", "status"),
        db.Index("idx_alert_created", "created_at"),
    )


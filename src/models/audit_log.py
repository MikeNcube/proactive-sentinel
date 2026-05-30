from datetime import datetime
import uuid

from sqlalchemy import DateTime, String

from src.extensions import db
from src.models.types import CrossJSON, UUID


class AuditLog(db.Model):
    """Immutable audit trail entry for tenant-scoped state changes."""

    __tablename__ = "audit_logs"

    id = db.Column(UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(UUID(), db.ForeignKey("tenants.id"), nullable=False)
    actor_id = db.Column(UUID(), db.ForeignKey("users.id"), nullable=False)
    action = db.Column(String(255), nullable=False)
    resource_type = db.Column(String(100), nullable=False)
    resource_id = db.Column(String(255), nullable=False)
    old_value = db.Column(CrossJSON())
    new_value = db.Column(CrossJSON())
    timestamp = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    source_ip = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    correlation_id = db.Column(UUID())

    __table_args__ = (
        db.Index("idx_audit_tenant_action", "tenant_id", "action"),
        db.Index("idx_audit_timestamp", "timestamp"),
        db.Index("idx_audit_actor", "actor_id"),
    )

    def to_dict(self) -> dict:
        metadata = self.new_value if isinstance(self.new_value, dict) else {}
        return {
            'id': str(self.id),
            'actor_id': str(self.actor_id),
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'timestamp': self.timestamp.isoformat(),
            'source_ip': self.source_ip,
            'ip_address': self.source_ip,
            'success': bool(metadata.get("success")) if metadata else None,
            'details': metadata.get("details"),
            'correlation_id': str(self.correlation_id) if self.correlation_id else None
        }


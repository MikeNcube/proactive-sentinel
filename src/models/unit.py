from datetime import datetime
import uuid

from sqlalchemy import DateTime, String

from src.extensions import db
from src.models.types import CrossJSON, UUID


class Unit(db.Model):
    __tablename__ = "units"

    id = db.Column(UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(UUID(), db.ForeignKey("tenants.id"), nullable=False)
    device_id = db.Column(String(128), nullable=False, unique=True)
    name = db.Column(String(255))
    token_hash = db.Column(String(255), nullable=False)
    secret_key_hash = db.Column(String(255), nullable=False)
    status = db.Column(String(32), default="online")
    last_seen_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = db.Column(CrossJSON(), default=dict)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index("idx_units_tenant_last_seen", "tenant_id", "last_seen_at"),
        db.Index("idx_units_status", "status"),
    )

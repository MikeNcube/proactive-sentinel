from datetime import datetime
import uuid

from sqlalchemy import DateTime, Enum, JSON, String

from src.extensions import db
from src.models.types import UUID


class Tenant(db.Model):
    """Tenant account model for multi-tenant data isolation."""

    __tablename__ = "tenants"

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(255), nullable=False)
    slug = db.Column(String(255), unique=True, nullable=True)
    plan = db.Column(String(64), default="enterprise")
    subdomain = db.Column(String(255), unique=True, nullable=True)
    status = db.Column(
        Enum("active", "suspended", "trial", name="tenant_status"),
        default="trial",
    )
    settings = db.Column(JSON, default=dict)  # Store tenant-specific settings
    quota_limit = db.Column(db.Integer, default=10000)  # alerts per day
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship("User", backref="tenant", lazy="dynamic")
    alerts = db.relationship("Alert", backref="tenant", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", backref="tenant", lazy="dynamic")

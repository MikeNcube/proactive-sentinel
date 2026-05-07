"""Centralized audit logging helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import g, request

from src.extensions import db
from src.models.audit_log import AuditLog


def write_audit_event(
    *,
    tenant_id: Any,
    actor_id: Any,
    action: str,
    resource_type: str,
    resource_id: str,
    success: bool,
    details: dict[str, Any] | None = None,
) -> None:
    """Persist a sanitized audit event."""
    sanitized_details = details or {}
    payload = {
        "success": bool(success),
        "details": sanitized_details,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    entry = AuditLog(
        tenant_id=str(tenant_id),
        actor_id=str(actor_id),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_value=None,
        new_value=payload,
        source_ip=(request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()),
        user_agent=request.headers.get("User-Agent", "unknown"),
        correlation_id=getattr(g, "correlation_id", None),
    )
    db.session.add(entry)

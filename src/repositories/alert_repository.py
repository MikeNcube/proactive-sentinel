from datetime import datetime
from typing import Any, Optional

from flask import g, request

from src.models.alert import Alert
from src.models.audit_log import AuditLog
from src.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository):
    """Tenant-aware repository for alert operations."""

    def __init__(self, db):
        super().__init__(Alert, db)

    def get_by_severity(self, severity: str, limit: int = 100) -> list[Alert]:
        query = Alert.query.filter_by(severity=severity)
        query = self._apply_tenant_filter(query)
        return query.order_by(Alert.created_at.desc()).limit(limit).all()

    def get_unresolved(self) -> list[Alert]:
        query = Alert.query.filter(Alert.status.in_(["open", "investigating"]))
        query = self._apply_tenant_filter(query)
        return query.order_by(Alert.severity.desc()).all()

    def dismiss(self, alert_id: Any, user_id: Any) -> Optional[Alert]:
        """Dismiss an alert and create the matching audit log entry."""
        alert = self.get_by_id(alert_id)
        if alert:
            try:
                old_status = alert.status
                alert.status = "dismissed"
                alert.resolved_at = datetime.utcnow()

                # Create audit log
                tenant_id = getattr(g, "tenant_id", None) or alert.tenant_id
                audit_log = AuditLog(
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    action="alert_dismissed",
                    resource_type="alert",
                    resource_id=str(alert_id),
                    old_value={"status": old_status},
                    new_value={"status": "dismissed"},
                    source_ip=request.remote_addr,
                    user_agent=request.user_agent.string,
                    correlation_id=getattr(g, "correlation_id", None),
                )
                self.db.session.add(audit_log)
                self.db.session.commit()
            except Exception:
                self.db.session.rollback()
                raise

        return alert


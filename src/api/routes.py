from flask import Blueprint, g, jsonify

from src.api.decorators import require_auth, require_tenant
from src.api.rate_limits import RATE_LIMITS, limiter
from src.extensions import db
from src.models.alert import Alert
from src.repositories.alert_repository import AlertRepository

api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health():
    """Public health check."""
    return jsonify({"status": "ok"}), 200


@api_bp.route("/alerts", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["alerts_list"])
def get_alerts():
    """Get alerts for current tenant."""
    repo = AlertRepository(db)
    alerts = repo.get_all()
    return (
        jsonify(
            {
                "alerts": [
                    {
                        "id": str(alert.id),
                        "title": alert.title,
                        "severity": alert.severity,
                        "status": alert.status,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                    }
                    for alert in alerts
                ]
            }
        ),
        200,
    )


@api_bp.route("/alerts/<alert_id>/dismiss", methods=["POST"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["alerts_dismiss"])
def dismiss_alert(alert_id):
    """Dismiss an alert."""
    repo = AlertRepository(db)
    alert = repo.dismiss(alert_id, g.user_id)

    if alert:
        return jsonify({"message": "Alert dismissed", "alert_id": alert_id}), 200
    return jsonify({"error": "Alert not found"}), 404


@api_bp.route("/tenants/current", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["tenants_current"])
def get_current_tenant():
    """Get current tenant information."""
    return (
        jsonify(
            {
                "tenant_id": str(g.tenant_id),
                "tenant_name": g.tenant.name,
                "user_id": g.user_id,
                "correlation_id": getattr(g, "correlation_id", None),
            }
        ),
        200,
    )


@api_bp.route("/stats", methods=["GET"])
@require_auth
@require_tenant
def get_stats():
    """Get alert statistics for dashboard."""
    severity_counts = (
        db.session.query(Alert.severity, db.func.count(Alert.id))
        .filter(Alert.tenant_id == g.tenant_id)
        .group_by(Alert.severity)
        .all()
    )
    status_counts = (
        db.session.query(Alert.status, db.func.count(Alert.id))
        .filter(Alert.tenant_id == g.tenant_id)
        .group_by(Alert.status)
        .all()
    )

    stats = {
        "total": Alert.query.filter_by(tenant_id=g.tenant_id).count(),
        "by_severity": {severity: count for severity, count in severity_counts},
        "by_status": {status: count for status, count in status_counts},
    }
    return jsonify({"stats": stats}), 200

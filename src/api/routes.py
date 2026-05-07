from flask import Blueprint, g, jsonify, request

from src.actions.dispatcher import BLOCKED_IP_PREFIX
from src.api.validators import validate_string, validate_uuid_string
from src.api.decorators import require_auth, require_tenant
from src.api.rate_limits import RATE_LIMITS, limiter, get_user_rate_limit_key
from src.auth.decorators import require_role
from src.extensions import db, get_redis
from src.models.alert import Alert
from src.repositories.alert_repository import AlertRepository
from src.services.audit_service import write_audit_event
from sqlalchemy import text

api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health():
    """Public health check with database connectivity verification."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "reachable"}), 200
    except Exception:
        return jsonify({"status": "degraded", "database": "unreachable"}), 503


@api_bp.route("/alerts", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["alerts_list"], key_func=get_user_rate_limit_key)
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
                        "category": alert.category,
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
@limiter.limit(RATE_LIMITS["alerts_dismiss"], key_func=get_user_rate_limit_key)
def dismiss_alert(alert_id):
    """Dismiss an alert."""
    try:
        cleaned_alert_id = validate_uuid_string(alert_id, "alert_id")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    repo = AlertRepository(db)
    alert = repo.dismiss(cleaned_alert_id, g.user_id)

    if alert:
        write_audit_event(
            tenant_id=g.tenant_id,
            actor_id=g.user_id,
            action="alert_dismissed",
            resource_type="alert",
            resource_id=str(cleaned_alert_id),
            success=True,
            details={"status": "dismissed"},
        )
        return jsonify({"message": "Alert dismissed", "alert_id": cleaned_alert_id}), 200
    return jsonify({"error": "Alert not found"}), 404


@api_bp.route("/tenants/current", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["tenants_current"], key_func=get_user_rate_limit_key)
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
@limiter.limit("60 per minute", key_func=get_user_rate_limit_key)
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
    category_counts = (
        db.session.query(Alert.category, db.func.count(Alert.id))
        .filter(Alert.tenant_id == g.tenant_id, Alert.category.isnot(None))
        .group_by(Alert.category)
        .all()
    )

    stats = {
        "total": Alert.query.filter_by(tenant_id=g.tenant_id).count(),
        "by_severity": {severity: count for severity, count in severity_counts},
        "by_status": {status: count for status, count in status_counts},
        "by_category": {cat: count for cat, count in category_counts},
    }
    return jsonify({"stats": stats}), 200


@api_bp.route("/security/unban-ip", methods=["POST"])
@require_auth
@require_tenant
@require_role(["IT_ADMIN", "MANAGEMENT", "SECURITY_ANALYST"])
@limiter.limit(RATE_LIMITS["security_unban"], key_func=get_user_rate_limit_key)
def unban_ip():
    """Manually remove a source IP from the Redis block list."""
    data = request.get_json(silent=True) or {}
    try:
        ip = validate_string(data.get("ip"), "ip", max_length=64)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    try:
        r = get_redis()
        deleted = r.delete(f"{BLOCKED_IP_PREFIX}{ip}")
        write_audit_event(
            tenant_id=g.tenant_id,
            actor_id=g.user_id,
            action="admin_unban_ip",
            resource_type="security_ip_blocklist",
            resource_id=ip,
            success=True,
            details={"unbanned": bool(deleted)},
        )
        return jsonify({"unbanned": bool(deleted), "ip": ip}), 200
    except Exception:
        return jsonify({"error": "Redis unavailable"}), 503


@api_bp.route("/systems/health", methods=["GET"])
@require_auth
@require_tenant
@require_role(["IT_ADMIN", "SECURITY_ANALYST", "MANAGEMENT"])
@limiter.limit(RATE_LIMITS["systems_health"], key_func=get_user_rate_limit_key)
async def systems_health_check():
    """
    Returns health status of all integrated Zororo systems.
    Requires authentication. Management level and above only.
    """
    from src.monitoring.health_checker import check_all_systems

    results = await check_all_systems()
    return jsonify({"systems": results, "total": len(results)}), 200

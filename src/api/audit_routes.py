"""
Audit log endpoints for POPIA compliance.
"""

import csv
import io
from datetime import datetime, timedelta

from flask import Blueprint, Response, g, jsonify, request

from src.api.rate_limits import RATE_LIMITS, limiter
from src.auth.decorators import require_auth, require_tenant
from src.models.audit_log import AuditLog

audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")


@audit_bp.route("/logs", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["audit_logs"])
def get_audit_logs():
    """Get audit logs for current tenant."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    action = request.args.get("action")
    start_date_raw = request.args.get("start_date")
    end_date_raw = request.args.get("end_date")

    query = AuditLog.query.filter_by(tenant_id=g.tenant_id)

    if action:
        query = query.filter_by(action=action)
    if start_date_raw:
        try:
            start_date = datetime.fromisoformat(start_date_raw)
            query = query.filter(AuditLog.timestamp >= start_date)
        except ValueError:
            return jsonify({"error": "Invalid start_date format. Use ISO 8601."}), 400
    if end_date_raw:
        try:
            end_date = datetime.fromisoformat(end_date_raw)
            query = query.filter(AuditLog.timestamp <= end_date)
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use ISO 8601."}), 400

    paginated = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return (
        jsonify(
            {
                "logs": [log.to_dict() for log in paginated.items],
                "total": paginated.total,
                "page": page,
                "per_page": per_page,
                "pages": paginated.pages,
            }
        ),
        200,
    )


@audit_bp.route("/export", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["audit_logs"])
def export_audit_logs():
    """Export audit logs as CSV for compliance audits."""
    days = request.args.get("days", 90, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)

    logs = (
        AuditLog.query.filter(
            AuditLog.tenant_id == g.tenant_id,
            AuditLog.timestamp >= start_date,
        )
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Timestamp",
            "Actor",
            "Action",
            "Resource Type",
            "Resource ID",
            "Old Value",
            "New Value",
            "Source IP",
        ]
    )

    for log in logs:
        writer.writerow(
            [
                log.timestamp.isoformat() if log.timestamp else "",
                str(log.actor_id) if log.actor_id else "",
                log.action,
                log.resource_type,
                log.resource_id,
                log.old_value,
                log.new_value,
                log.source_ip,
            ]
        )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment;filename=audit_logs_{g.tenant_id}_{start_date.date()}.csv"
            )
        },
    )


@audit_bp.route("/retention", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["audit_logs"])
def get_retention_info():
    """Get data retention information for compliance."""
    retention_days = 365
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    old_logs_count = AuditLog.query.filter(
        AuditLog.tenant_id == g.tenant_id,
        AuditLog.timestamp < cutoff_date,
    ).count()

    return (
        jsonify(
            {
                "retention_days": retention_days,
                "retention_policy": "1 year hot storage, 7 years cold storage",
                "old_logs_count": old_logs_count,
                "next_archive_date": (cutoff_date + timedelta(days=30)).date().isoformat(),
            }
        ),
        200,
    )

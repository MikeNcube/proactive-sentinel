"""
Generic event ingest endpoint.

Accepts telemetry from any authenticated source (log shippers, internal services,
the CLI sentinel) without requiring a pre-registered unit token.

Security events flow through DetectionEngine (Redis dedup + MITRE correlation).
UX/operational events flow through UXObserver (business-signal detection).
"""

import logging
from typing import Any

from flask import Blueprint, g, jsonify, request
from marshmallow import Schema, ValidationError, fields, validate

from src.api.rate_limits import RATE_LIMITS, limiter
from src.auth.decorators import require_auth, require_tenant
from detections.vrl_filter import mask_text as _mask_text
from src.detections.engine import DetectionEngine
from src.extensions import db
from src.models.alert import Alert

logger = logging.getLogger(__name__)

events_bp = Blueprint("events", __name__)

# UX event types routed through UXObserver rather than DetectionEngine.
_UX_EVENT_TYPES = frozenset({
    "slow_claims",
    "whatsapp_frustration",
    "web_error",
    "social_outcry",
    "zendesk_latency",
    "lead_leakage",
})

_VALID_SEVERITIES = {"critical", "high", "medium", "low"}

# Module-level engine instance — CorrelationEngine lazily connects to Redis on first use.
_detection_engine = DetectionEngine()


class IngestEventSchema(Schema):
    source = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    event_type = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    severity = fields.Str(
        load_default="low",
        validate=validate.OneOf(list(_VALID_SEVERITIES)),
    )
    raw_data = fields.Dict(load_default=dict)
    tenant_id = fields.Str(load_default=None)
    title = fields.Str(load_default=None, validate=validate.Length(max=500))
    description = fields.Str(load_default=None)
    confidence = fields.Float(
        load_default=0.7,
        validate=validate.Range(min=0.0, max=1.0),
    )


_schema = IngestEventSchema()


@events_bp.route("/ingest", methods=["POST"])
@require_auth
@require_tenant
@limiter.limit(RATE_LIMITS["events_ingest"])
def ingest_event():
    """
    Ingest a security or operational event.

    Request body (JSON):
      source      (str, required)  — origin of the event, e.g. "wazuh", "app-server-01"
      event_type  (str, required)  — e.g. "ransomware", "slow_claims", "web_error"
      severity    (str, optional)  — critical | high | medium | low  (default: low)
      raw_data    (dict, optional) — full event payload
      tenant_id   (str, optional)  — must match the JWT tenant when supplied
      title       (str, optional)  — human-readable title (derived from event_type if absent)
      description (str, optional)  — free-text detail
      confidence  (float, optional)— 0.0–1.0 (default: 0.7)

    Returns:
      201 { created: true, alert_id, severity }           — new alert persisted
      200 { created: false, reason: "duplicate suppressed" } — dedup hit
      400 { error, details }                              — validation failure
      403 { error }                                       — tenant mismatch
    """
    raw_body = request.get_json(silent=True) or {}
    try:
        data = _schema.load(raw_body)
    except ValidationError as exc:
        return jsonify({"error": "Invalid payload", "details": exc.messages}), 400

    # tenant_id in payload, when present, must match the authenticated tenant.
    jwt_tenant_id = str(g.tenant_id)
    payload_tenant_id = data.get("tenant_id")
    if payload_tenant_id and str(payload_tenant_id) != jwt_tenant_id:
        return jsonify({"error": "tenant_id in payload does not match authenticated tenant"}), 403

    event_type = data["event_type"]
    source = data["source"]
    severity = data["severity"]
    raw_data = data.get("raw_data") or {}
    confidence = data.get("confidence", 0.7)
    title = data.get("title") or f"{event_type.replace('_', ' ').title()} from {source}"
    description = data.get("description") or raw_data.get("description")

    # Credential check: any credential detected in the raw payload forces critical severity.
    _, _cred_report = _mask_text(str(raw_data))
    _cred_types = [t for t in _cred_report.pii_types_found if t.startswith("CRED_")]
    if _cred_types:
        severity = "critical"
        logger.warning(
            "Credential detected in event from %s; severity forced to critical. types=%s",
            source, _cred_types,
        )

    if event_type in _UX_EVENT_TYPES:
        return _handle_ux_event(
            event_type, source, severity, raw_data, jwt_tenant_id, confidence, title
        )

    # Security path: DetectionEngine handles dedup and MITRE correlation.
    alert_data = {
        "tenant_id": jwt_tenant_id,
        "title": title,
        "severity": severity,
        "category": event_type,
        "source": source,
        "description": description,
        "raw_data": raw_data,
        "confidence": confidence,
        "host": raw_data.get("host"),
    }

    try:
        alert = _detection_engine.process_alert(alert_data)
    except Exception as exc:
        logger.exception("DetectionEngine.process_alert failed: %s", exc)
        return jsonify({"error": "Detection pipeline error"}), 500

    if alert is None:
        return jsonify({"created": False, "reason": "duplicate suppressed"}), 200

    return jsonify({
        "created": True,
        "alert_id": str(alert.id),
        "severity": alert.severity,
    }), 201


def _handle_ux_event(
    event_type: str,
    source: str,
    severity: str,
    raw_data: dict,
    tenant_id: str,
    confidence: float,
    title: str,
) -> Any:
    """Route operational/business-signal events through UXObserver."""
    from detections.ux_observer import UXObserver

    log_entry = {"source": source, **raw_data}
    try:
        ux_alerts = UXObserver.detect([log_entry])
    except Exception as exc:
        logger.exception("UXObserver.detect failed: %s", exc)
        return jsonify({"error": "UX detection pipeline error"}), 500

    if not ux_alerts:
        return jsonify({"created": False, "reason": "no ux signals detected"}), 200

    created_ids = []
    for ux in ux_alerts:
        raw_severity = str(ux.get("severity", severity)).lower()
        mapped_severity = raw_severity if raw_severity in _VALID_SEVERITIES else "low"
        alert = Alert(
            tenant_id=tenant_id,
            title=ux.get("description") or title,
            severity=mapped_severity,
            status="open",
            category=event_type,
            source=source,
            description=ux.get("description"),
            raw_data=raw_data,
            confidence=confidence,
        )
        db.session.add(alert)
        created_ids.append(str(alert.id))

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to persist UX alerts: %s", exc)
        return jsonify({"error": "Failed to persist alerts"}), 500

    return jsonify({
        "created": True,
        "alert_ids": created_ids,
        "count": len(created_ids),
    }), 201

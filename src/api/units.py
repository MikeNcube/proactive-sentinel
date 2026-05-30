import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy import or_

from src.api.rate_limits import RATE_LIMITS, limiter
from src.api.validators import validate_string, validate_tenant_id
from src.extensions import db
from src.models.alert import Alert
from src.models.tenant import Tenant
from src.models.unit import Unit
from src.security.threat_detector import ThreatDetector

units_bp = Blueprint("units", __name__)
threat_detector = ThreatDetector()
logger = logging.getLogger(__name__)


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_error(msg: str, status: int):
    return jsonify({"error": msg}), status


def _validate_payload_size():
    max_bytes = int(os.environ.get("MAX_REQUEST_BYTES", "1048576"))
    if request.content_length and request.content_length > max_bytes:
        return _json_error("Payload too large", 413)
    return None


def _validate_unit_whitelist(device_id: str):
    allowed = {
        d.strip() for d in os.environ.get("UNIT_ID_WHITELIST", "").split(",") if d.strip()
    }
    if allowed and device_id not in allowed:
        return _json_error("Unit is not in whitelist", 403)
    return None


def _authenticate_unit() -> tuple[Unit | None, Any]:
    token = request.headers.get("X-Unit-Token", "")
    device_id = request.headers.get("X-Unit-Id", "")
    if not token or not device_id:
        return None, _json_error("Missing unit authentication headers", 401)
    unit = Unit.query.filter_by(device_id=device_id).first()
    if not unit or unit.token_hash != _hash_value(token):
        return None, _json_error("Invalid unit token", 401)
    return unit, None


def _resolve_tenant_id(raw_tenant_identifier: str) -> tuple[str | None, Any]:
    """Resolve tenant identifier to canonical tenant UUID string."""
    if not raw_tenant_identifier:
        return None, _json_error("tenant_id is required", 400)
    try:
        normalized = validate_tenant_id(raw_tenant_identifier)
    except ValueError:
        normalized = str(raw_tenant_identifier).strip()

    try:
        return str(uuid.UUID(normalized)), None
    except ValueError:
        pass

    tenant = Tenant.query.filter(
        or_(
            Tenant.subdomain == normalized,
            Tenant.slug == normalized,
            Tenant.name == normalized,
        )
    ).first()
    if tenant:
        return str(tenant.id), None

    fallback = normalized.lower().replace("_", "-")
    tenant = Tenant.query.filter(
        or_(
            Tenant.subdomain == fallback,
            Tenant.slug == fallback,
        )
    ).first()
    if tenant:
        return str(tenant.id), None
    return None, _json_error("Unknown tenant identifier", 400)


@units_bp.route("/register", methods=["POST"])
@limiter.limit(RATE_LIMITS["units_register"])
def register_unit():
    payload_err = _validate_payload_size()
    if payload_err:
        return payload_err
    data = request.get_json(silent=True) or {}
    try:
        tenant_id_raw = validate_string(data.get("tenant_id"), "tenant_id", max_length=64)
        device_id = validate_string(data.get("device_id"), "device_id", max_length=128)
        secret_key = validate_string(data.get("secret_key"), "secret_key", max_length=512)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    tenant_id, tenant_err = _resolve_tenant_id(str(tenant_id_raw))
    if tenant_err:
        return tenant_err
    whitelist_err = _validate_unit_whitelist(device_id)
    if whitelist_err:
        return whitelist_err

    token_plain = os.urandom(24).hex()
    try:
        existing = Unit.query.filter_by(device_id=device_id).first()
        if not existing:
            unit = Unit(
                tenant_id=tenant_id,
                device_id=device_id,
                name=validate_string(data.get("name"), "name", max_length=128) if data.get("name") else None,
                token_hash=_hash_value(token_plain),
                secret_key_hash=_hash_value(secret_key),
            )
            db.session.add(unit)
        else:
            existing.token_hash = _hash_value(token_plain)
            existing.secret_key_hash = _hash_value(secret_key)
            existing.status = "online"
            existing.last_seen_at = datetime.utcnow()
            unit = existing

        db.session.commit()
        return jsonify({"device_id": unit.device_id, "unit_token": token_plain}), 201
    except OperationalError as exc:
        db.session.rollback()
        logger.exception("Unit registration failed due to database schema issue: %s", exc)
        return _json_error(
            "Unit registration unavailable: database schema is not up to date. Run migrations.",
            503,
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("Unit registration database error: %s", exc)
        return _json_error("Unit registration failed due to database error", 500)


@units_bp.route("/heartbeat", methods=["POST"])
@limiter.limit(RATE_LIMITS["units_heartbeat"])
def unit_heartbeat():
    payload_err = _validate_payload_size()
    if payload_err:
        return payload_err
    unit, err = _authenticate_unit()
    if err:
        return err
    unit.last_seen_at = datetime.utcnow()
    unit.status = "online"
    db.session.commit()
    return jsonify({"status": "ok", "device_id": unit.device_id}), 200


@units_bp.route("/report", methods=["POST"])
@limiter.limit(RATE_LIMITS["units_report"])
def unit_report():
    payload_err = _validate_payload_size()
    if payload_err:
        return payload_err
    unit, err = _authenticate_unit()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    required = ["title", "category", "source_ip", "event_type"]
    if any(not data.get(k) for k in required):
        return _json_error("Missing required report fields", 400)
    try:
        data["title"] = validate_string(data.get("title"), "title", max_length=500)
        data["category"] = validate_string(data.get("category"), "category", max_length=120)
        data["source_ip"] = validate_string(data.get("source_ip"), "source_ip", max_length=64)
        data["event_type"] = validate_string(data.get("event_type"), "event_type", max_length=120)
        if data.get("description"):
            data["description"] = validate_string(data.get("description"), "description", max_length=1000)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    rep = threat_detector.evaluate_ip_reputation(data.get("source_ip", ""))
    vel = threat_detector.evaluate_request_velocity(request.remote_addr or "unknown")
    unit_vel = threat_detector.evaluate_unit_velocity(unit.device_id)
    if not rep.get("allowed"):
        return _json_error("Blocked source IP", 403)
    if not vel.get("allowed"):
        return _json_error("Rate anomaly detected", 429)
    if not unit_vel.get("allowed"):
        compromised_alert = Alert(
            tenant_id=unit.tenant_id,
            title=f"Unit Compromise Suspected: {unit.device_id}",
            severity="critical",
            status="open",
            category="unit_compromise",
            description="Unit exceeded velocity threshold and has been auto-quarantined.",
            source=f"threat_detector:{unit.device_id}",
            confidence=0.95,
            raw_data={"reason": unit_vel.get("reason"), "unit_id": unit.device_id},
        )
        db.session.add(compromised_alert)
        db.session.commit()
        return _json_error("Unit quarantined due to suspicious velocity", 429)

    severity = "low"
    if data["event_type"] in {"malware", "ransomware"}:
        severity = "critical"
    elif data["event_type"] in {"fraud", "exfiltration"}:
        severity = "high"
    elif data["event_type"] in {"scan", "recon"}:
        severity = "medium"

    alert = Alert(
        tenant_id=unit.tenant_id,
        title=data["title"],
        severity=severity,
        status="open" if severity == "critical" else "investigating",
        category=data["category"],
        description=data.get("description", "Threat report from monitored unit"),
        source=f"unit:{unit.device_id}",
        confidence=float(data.get("confidence", 0.7)),
        raw_data=data,
    )
    db.session.add(alert)
    unit.last_seen_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"alert_id": str(alert.id), "severity": severity}), 201


@units_bp.route("/status", methods=["GET"])
@limiter.limit(RATE_LIMITS["units_status"])
def units_status():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    units = Unit.query.all()
    out = []
    for unit in units:
        is_online = unit.last_seen_at >= cutoff
        if not is_online and unit.status != "offline":
            unit.status = "offline"
        out.append(
            {
                "device_id": unit.device_id,
                "tenant_id": str(unit.tenant_id),
                "status": "online" if is_online else "offline",
                "last_seen_at": unit.last_seen_at.isoformat() if unit.last_seen_at else None,
            }
        )
    db.session.commit()
    return jsonify({"units": out}), 200


import hashlib
import os
from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, request

from src.api.rate_limits import RATE_LIMITS, limiter
from src.extensions import db
from src.models.alert import Alert
from src.models.unit import Unit
from src.security.threat_detector import ThreatDetector

units_bp = Blueprint("units", __name__, url_prefix="/api/units")
threat_detector = ThreatDetector()


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


def _authenticate_unit():
    token = request.headers.get("X-Unit-Token", "")
    device_id = request.headers.get("X-Unit-Id", "")
    if not token or not device_id:
        return None, _json_error("Missing unit authentication headers", 401)
    unit = Unit.query.filter_by(device_id=device_id).first()
    if not unit or unit.token_hash != _hash_value(token):
        return None, _json_error("Invalid unit token", 401)
    return unit, None


@units_bp.route("/register", methods=["POST"])
@limiter.limit(RATE_LIMITS["units_register"])
def register_unit():
    payload_err = _validate_payload_size()
    if payload_err:
        return payload_err
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    device_id = data.get("device_id")
    secret_key = data.get("secret_key")
    if not tenant_id or not device_id or not secret_key:
        return _json_error("tenant_id, device_id and secret_key required", 400)
    whitelist_err = _validate_unit_whitelist(device_id)
    if whitelist_err:
        return whitelist_err

    existing = Unit.query.filter_by(device_id=device_id).first()
    token_plain = os.urandom(24).hex()
    if not existing:
        unit = Unit(
            tenant_id=tenant_id,
            device_id=device_id,
            name=data.get("name"),
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

    rep = threat_detector.evaluate_ip_reputation(data.get("source_ip", ""))
    vel = threat_detector.evaluate_request_velocity(request.remote_addr or "unknown")
    if not rep.get("allowed"):
        return _json_error("Blocked source IP", 403)
    if not vel.get("allowed"):
        return _json_error("Rate anomaly detected", 429)

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

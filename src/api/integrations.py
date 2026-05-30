"""
Plugin registry API.

GET  /api/integrations          â€” list all systems (static + DB)
POST /api/integrations/register â€” add a new system at runtime (IT_ADMIN only)

No code deploy is needed to add a new integration: POST the config and it is
persisted to the integrations table and immediately visible via GET.
"""

import logging

from flask import Blueprint, g, jsonify, request

from src.api.rate_limits import RATE_LIMITS, limiter, get_user_rate_limit_key
from src.api.validators import validate_string
from src.auth.decorators import require_auth, require_role, require_tenant
from src.extensions import db
from src.integrations.zororo_systems import ZORORO_SYSTEMS, get_all_systems
from src.models.integration import Integration
from src.services.audit_service import write_audit_event

logger = logging.getLogger(__name__)

integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.route("", methods=["GET"])
@require_auth
@require_tenant
@limiter.limit("60 per minute", key_func=get_user_rate_limit_key)
def list_integrations():
    """List all registered systems (built-ins + runtime additions)."""
    systems = get_all_systems()
    safe = []
    for key, cfg in systems.items():
        entry = dict(cfg)
        entry["key"] = key
        entry.pop("webhook_secret", None)  # never expose secret
        safe.append(entry)
    safe.sort(key=lambda x: (not x.get("builtin", False), x["key"]))
    return jsonify({"integrations": safe, "total": len(safe)}), 200


@integrations_bp.route("/register", methods=["POST"])
@require_auth
@require_tenant
@require_role(["IT_ADMIN", "admin"])
@limiter.limit("10 per minute", key_func=get_user_rate_limit_key)
def register_integration():
    """
    Register a new integration system at runtime.

    Body (JSON):
      key             (str, required) â€” unique slug, e.g. "kga_life_api"
      name            (str, required) â€” human-readable name
      url             (str, optional) â€” base URL of the system
      webhook_secret  (str, optional) â€” shared secret for inbound webhooks
      alert_thresholds (dict, optional)
      pii_fields      (list, optional)
      enabled         (bool, optional, default true)
      description     (str, optional)

    Returns 201 on creation, 409 if the key is already registered.
    """
    data = request.get_json(silent=True) or {}

    try:
        key = validate_string(data.get("key", ""), "key", max_length=100)
        name = validate_string(data.get("name", ""), "name", max_length=200)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if key in ZORORO_SYSTEMS:
        return jsonify({"error": f"'{key}' is a built-in system and cannot be overwritten"}), 409

    existing = Integration.query.get(key)
    if existing:
        return jsonify({"error": f"Integration '{key}' is already registered"}), 409

    url = str(data.get("url", ""))[:500]
    webhook_secret = str(data.get("webhook_secret", ""))[:255]
    description = str(data.get("description", ""))[:500]
    alert_thresholds = data.get("alert_thresholds") or {}
    pii_fields = data.get("pii_fields") or []
    enabled = bool(data.get("enabled", True))

    if not isinstance(alert_thresholds, dict):
        return jsonify({"error": "alert_thresholds must be an object"}), 400
    if not isinstance(pii_fields, list):
        return jsonify({"error": "pii_fields must be an array"}), 400

    integration = Integration(
        key=key,
        name=name,
        description=description,
        url=url,
        webhook_secret=webhook_secret,
        alert_thresholds=alert_thresholds,
        pii_fields=pii_fields,
        enabled=enabled,
    )
    db.session.add(integration)
    db.session.commit()

    write_audit_event(
        tenant_id=g.tenant_id,
        actor_id=g.user_id,
        action="integration_registered",
        resource_type="integration",
        resource_id=key,
        success=True,
        details={"name": name, "url": url},
    )
    db.session.commit()

    logger.info("Integration '%s' registered by user %s", key, g.user_id)
    return jsonify({"registered": True, "key": key, "name": name}), 201


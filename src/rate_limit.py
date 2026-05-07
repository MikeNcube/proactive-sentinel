from flask import g
from src.extensions import get_remote_address, limiter


RATE_LIMITS = {
    "auth_register": "5 per hour",
    "auth_login": "5 per minute",
    "alerts_list": "60 per minute",
    "alerts_dismiss": "10 per minute",
    "tenants_current": "60 per minute",
    "audit_logs": "10 per minute",
    "units_register": "10 per minute",
    "units_heartbeat": "120 per minute",
    "units_report": "60 per minute",
    "units_status": "60 per minute",
    "events_ingest": "60 per minute",
    "security_unban": "10 per minute",
    "systems_health": "10 per minute",
}


def get_tenant_rate_limit_key():
    """Return rate limit key based on tenant if authenticated."""
    if hasattr(g, "tenant_id") and g.tenant_id:
        return f"tenant:{g.tenant_id}"
    return get_remote_address()


def get_user_rate_limit_key():
    """Return user-aware limit key for authenticated routes."""
    if hasattr(g, "user_id") and g.user_id:
        return f"user:{g.user_id}"
    return get_remote_address()

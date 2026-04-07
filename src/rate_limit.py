from flask import g
from src.extensions import get_remote_address, limiter


RATE_LIMITS = {
    "auth_register": "5 per hour",
    "auth_login": "10 per minute",
    "alerts_list": "100 per hour",
    "alerts_dismiss": "50 per hour",
    "tenants_current": "200 per hour",
    "audit_logs": "50 per hour",
}


def get_tenant_rate_limit_key():
    """Return rate limit key based on tenant if authenticated."""
    if hasattr(g, "tenant_id") and g.tenant_id:
        return f"tenant:{g.tenant_id}"
    return get_remote_address()

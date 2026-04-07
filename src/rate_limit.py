"""
Rate limiting configuration for API endpoints.
Uses Redis backend for distributed rate limiting.
"""

import os

from flask import g
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:  # pragma: no cover - fallback for local/test envs without limiter
    class Limiter:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            pass

        def init_app(self, app):
            return None

        def limit(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    def get_remote_address():  # type: ignore[return-value]
        return "127.0.0.1"

# Get Redis URL from environment, with fallback.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["30 per minute"],
    storage_uri=REDIS_URL,
    strategy="fixed-window",
)


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

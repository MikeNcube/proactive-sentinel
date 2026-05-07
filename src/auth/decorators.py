import logging
import uuid
from functools import wraps
from typing import Any, Callable, TypeVar

from flask import g, jsonify, request

from src.auth.tenant_context import TenantContextError, set_tenant_context

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def require_tenant(f: F) -> F:
    """Decorator that injects tenant_id from JWT or header.

    Also pins the PostgreSQL ``app.current_tenant_id`` GUC so that
    Row Level Security policies can enforce per-tenant isolation at the
    database layer. If the GUC cannot be set (e.g. bad/missing tenant,
    DB error), the request is rejected **before** any business query runs.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        # Prefer the tenant_id from the validated JWT; only fall back to the
        # X-Tenant-ID header when no authenticated user context exists.
        # Mixing the two is how horizontal privilege-escalation bugs appear.
        tenant_id = None
        if hasattr(g, "user") and g.user:
            tenant_id = g.user.get("tenant_id")
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400

        # Validate UUID shape before touching the DB. Otherwise the query
        # below raises a raw psycopg2 cast error that we'd leak in the
        # response body via the existing 401 handler.
        try:
            uuid.UUID(str(tenant_id))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid tenant ID"}), 400

        from src.models.tenant import Tenant

        tenant = Tenant.query.filter_by(id=tenant_id, status="active").first()
        if not tenant:
            return jsonify({"error": "Invalid or inactive tenant"}), 403

        try:
            set_tenant_context(tenant_id)
        except TenantContextError as exc:
            # Fail-closed: never run tenant-scoped queries without a pinned
            # database tenant context. Returning 500 (not 400/403) because
            # the caller cannot fix a server-side RLS wiring failure.
            logger.error("Refusing request: tenant context unavailable: %s", exc)
            return jsonify({"error": "Tenant context unavailable"}), 500

        g.tenant_id = tenant_id
        g.tenant = tenant
        g.tenant_context_set = True

        return f(*args, **kwargs)

    return decorated  # type: ignore[return-value]


def require_auth(f: F) -> F:
    """Decorator that validates JWT token."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401

        token = auth_header.split(" ")[1]

        try:
            from src.auth.jwt_manager import JWTManager

            jwt_manager = JWTManager()
            payload = jwt_manager.decode_token(token)

            # Store user context
            g.user = payload
            g.user_id = payload["user_id"]
            g.tenant_id = payload["tenant_id"]

            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 401

    return decorated  # type: ignore[return-value]


def generate_correlation_id() -> str:
    """Generate correlation ID for request tracing."""
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    g.correlation_id = correlation_id
    return correlation_id

import uuid
from functools import wraps
from typing import Any, Callable, TypeVar

from flask import g, jsonify, request
from sqlalchemy import text

from src.extensions import db

F = TypeVar("F", bound=Callable[..., Any])


def require_tenant(f: F) -> F:
    """Decorator that injects tenant_id from JWT or header."""

    @wraps(f)
    def decorated(*args, **kwargs):
        # Get tenant_id from JWT first
        tenant_id = None
        if hasattr(g, "user") and g.user:
            tenant_id = g.user.get("tenant_id")

        # Fallback to header
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400

        # Validate tenant exists and is active
        from src.models.tenant import Tenant

        tenant = Tenant.query.filter_by(id=tenant_id, status="active").first()
        if not tenant:
            return jsonify({"error": "Invalid or inactive tenant"}), 403

        # Set tenant context for request
        g.tenant_id = tenant_id
        g.tenant = tenant

        # Set PostgreSQL tenant context for RLS when supported.
        if db.engine.dialect.name == "postgresql":
            db.session.execute(text("SET app.current_tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})

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

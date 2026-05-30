from datetime import datetime
import time
import traceback

from flask import Blueprint, current_app, g, jsonify, request

from src.api.rate_limits import RATE_LIMITS, limiter, get_user_rate_limit_key
from src.api.validators import validate_email, validate_string
from src.auth.decorators import require_auth
from src.auth.jwt_manager import JWTManager
from src.extensions import db
from src.models.tenant import Tenant
from src.models.user import User
from src.services.audit_service import write_audit_event

auth_bp = Blueprint("auth", __name__)
FAILED_LOGINS = {}
IP_ACCOUNT_PROBES = {}
LOCKED_UNTIL = {}


@auth_bp.post("/register")
@limiter.limit(RATE_LIMITS["auth_register"])
def register():
    """Register a new tenant and admin user."""
    data = request.get_json(silent=True) or {}

    try:
        email = validate_email(data.get("email"))
        password = validate_string(data.get("password"), "password", max_length=256)
        tenant_name = validate_string(data.get("tenant_name"), "tenant_name", max_length=128)
        raw_subdomain = data.get("subdomain")
        subdomain = validate_string(raw_subdomain, "subdomain", max_length=64) if raw_subdomain else None
        tenant_slug = data.get("tenant_slug")
        if tenant_slug is not None:
            tenant_slug = validate_string(tenant_slug, "tenant_slug", max_length=64)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    slug = tenant_slug or subdomain
    if not slug:
        return jsonify({"error": "subdomain or tenant_slug is required"}), 400

    import re
    if len(password) < 12:
        return jsonify({"error": "Password must be at least 12 characters"}), 400
    if not re.search(r"[A-Z]", password):
        return jsonify({"error": "Password must contain uppercase letter"}), 400
    if not re.search(r"[0-9]", password):
        return jsonify({"error": "Password must contain a number"}), 400
    if not re.search(r"[^A-Za-z0-9]", password):
        return jsonify({"error": "Password must contain a special character"}), 400

    existing_tenant = Tenant.query.filter_by(subdomain=slug).first() or Tenant.query.filter_by(slug=slug).first()
    if existing_tenant:
        return jsonify({"error": "Tenant already exists"}), 409

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered"}), 409

    tenant = Tenant(name=tenant_name, subdomain=slug, slug=slug, status="active")
    db.session.add(tenant)
    db.session.flush()

    user = User(tenant_id=tenant.id, email=email, role="admin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    write_audit_event(
        tenant_id=tenant.id,
        actor_id=user.id,
        action="tenant_created",
        resource_type="tenant",
        resource_id=str(tenant.id),
        success=True,
        details={"name": tenant.name, "slug": slug},
    )
    write_audit_event(
        tenant_id=tenant.id,
        actor_id=user.id,
        action="user_role_change",
        resource_type="user",
        resource_id=str(user.id),
        success=True,
        details={"assigned_role": "admin"},
    )
    db.session.commit()

    jwt_manager = JWTManager()
    access_token = jwt_manager.create_access_token(user.id, tenant.id, user.role)

    return jsonify(
        {
            "message": "Registration successful",
            "access_token": access_token,
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
        }
    ), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit(RATE_LIMITS["auth_login"])
def login():
    """Login and get JWT token."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        try:
            email = validate_email(data.get("email", ""))
            password = validate_string(data.get("password", ""), "password", max_length=256)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        now = time.time()
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
        lock_key = f"{ip}:{email}"
        if lock_key in LOCKED_UNTIL and now < LOCKED_UNTIL[lock_key]:
            return jsonify({"error": "Account temporarily locked. Try later."}), 423

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            # Progressive delay: 1, 2, 4, 8 seconds capped
            count = FAILED_LOGINS.get(lock_key, 0) + 1
            FAILED_LOGINS[lock_key] = count
            delay = min(2 ** (count - 1), 8)
            time.sleep(delay)

            if count >= 5:
                LOCKED_UNTIL[lock_key] = now + 900  # 15 min lockout

            ip_accounts = IP_ACCOUNT_PROBES.get(ip, set())
            ip_accounts.add(email)
            IP_ACCOUNT_PROBES[ip] = ip_accounts
            captcha_required = count >= 3
            warn_multiple_accounts = len(ip_accounts) >= 3
            current_app.logger.warning(
                "Failed login attempt",
                extra={
                    "email": email,
                    "ip": ip,
                    "failed_attempts": count,
                    "user_agent": request.headers.get("User-Agent", "unknown"),
                    "captcha_required": captcha_required,
                    "warn_multiple_accounts": warn_multiple_accounts,
                },
            )
            if user:
                write_audit_event(
                    tenant_id=user.tenant_id,
                    actor_id=user.id,
                    action="user_login",
                    resource_type="auth",
                    resource_id=str(user.id),
                    success=False,
                    details={"reason": "invalid_credentials"},
                )
            return jsonify(
                {
                    "error": "Invalid credentials",
                    "captcha_required": captcha_required,
                    "warn_multiple_accounts": warn_multiple_accounts,
                    "retry_after_seconds": delay,
                }
            ), 401

        # Successful login clears counters
        FAILED_LOGINS.pop(lock_key, None)
        LOCKED_UNTIL.pop(lock_key, None)
        user.last_login = datetime.utcnow()
        db.session.commit()
        write_audit_event(
            tenant_id=user.tenant_id,
            actor_id=user.id,
            action="user_login",
            resource_type="auth",
            resource_id=str(user.id),
            success=True,
            details={"role": user.role},
        )
        db.session.commit()

        jwt_manager = JWTManager()
        access_token = jwt_manager.create_access_token(user.id, user.tenant_id, user.role)
        return jsonify(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "tenant_id": str(user.tenant_id),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "tenant_id": str(user.tenant_id),
                },
            }
        ), 200
    except Exception:
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/me", methods=["GET"])
@require_auth
@limiter.limit("60 per minute", key_func=get_user_rate_limit_key)
def get_current_user():
    """Get current authenticated user."""
    return jsonify(
        {
            "user_id": str(g.user_id),
            "tenant_id": str(g.tenant_id),
            "role": g.user.get("role"),
        }
    ), 200


@auth_bp.route("/logout", methods=["POST"])
@require_auth
@limiter.limit("60 per minute", key_func=get_user_rate_limit_key)
def logout():
    """Stateless logout endpoint for audit tracking."""
    write_audit_event(
        tenant_id=g.tenant_id,
        actor_id=g.user_id,
        action="user_logout",
        resource_type="auth",
        resource_id=str(g.user_id),
        success=True,
        details={},
    )
    db.session.commit()
    return jsonify({"message": "Logged out"}), 200


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
@limiter.limit("60 per minute", key_func=get_user_rate_limit_key)
def change_password():
    """Change current authenticated user's password."""
    data = request.get_json(silent=True) or {}
    try:
        current_password = validate_string(data.get("current_password"), "current_password", max_length=256)
        new_password = validate_string(data.get("new_password"), "new_password", max_length=256)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    user = User.query.filter_by(id=g.user_id, tenant_id=g.tenant_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.check_password(current_password):
        write_audit_event(
            tenant_id=g.tenant_id,
            actor_id=g.user_id,
            action="password_change",
            resource_type="user",
            resource_id=str(g.user_id),
            success=False,
            details={"reason": "invalid_current_password"},
        )
        db.session.commit()
        return jsonify({"error": "Current password is incorrect"}), 400

    user.set_password(new_password)
    db.session.commit()
    write_audit_event(
        tenant_id=g.tenant_id,
        actor_id=g.user_id,
        action="password_change",
        resource_type="user",
        resource_id=str(g.user_id),
        success=True,
        details={},
    )
    db.session.commit()
    return jsonify({"message": "Password updated"}), 200


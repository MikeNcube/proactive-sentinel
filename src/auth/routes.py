from datetime import datetime
import time
import traceback

from flask import Blueprint, current_app, g, jsonify, request

from src.api.rate_limits import RATE_LIMITS, limiter
from src.auth.decorators import require_auth
from src.auth.jwt_manager import JWTManager
from src.extensions import db
from src.models.tenant import Tenant
from src.models.user import User

auth_bp = Blueprint("auth", __name__)
FAILED_LOGINS = {}
IP_ACCOUNT_PROBES = {}
LOCKED_UNTIL = {}


@auth_bp.post("/register")
@limiter.limit(RATE_LIMITS["auth_register"])
def register():
    """Register a new tenant and admin user."""
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")
    tenant_name = data.get("tenant_name")
    subdomain = data.get("subdomain")
    tenant_slug = data.get("tenant_slug")
    slug = tenant_slug or subdomain

    if not email or not password or not tenant_name or not slug:
        return jsonify({"error": "Missing required fields: email, password, tenant_name, subdomain"}), 400

    import re
    if not isinstance(password, str):
        password = str(password)
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
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

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
@limiter.limit("60 per minute")
def get_current_user():
    """Get current authenticated user."""
    return jsonify(
        {
            "user_id": str(g.user_id),
            "tenant_id": str(g.tenant_id),
            "role": g.user.get("role"),
        }
    ), 200

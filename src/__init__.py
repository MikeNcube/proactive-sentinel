"""
Proactive Sentinel - Application Factory
"""

import logging
import os
import time
import uuid
from logging.config import dictConfig

from flask import Flask, g, jsonify, request
from sqlalchemy import text

from src.auth.jwt_manager import JWTManager
from src.extensions import db, get_redis, migrate

LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}
dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def create_app(config_name=None) -> Flask:
    """Application factory."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    )

    database_url = os.environ.get("DATABASE_URL", "sqlite:///app.db")

    # Railway uses postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_REQUEST_BYTES", "1048576"))
    _engine_options: dict = {"pool_pre_ping": True}
    if not database_url.startswith("sqlite"):
        _engine_options["pool_recycle"] = 1800
        _engine_options["pool_size"] = int(os.environ.get("DB_POOL_SIZE", "5"))
        _engine_options["max_overflow"] = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _engine_options
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY is required.")
    if "dev" in jwt_secret.lower() or "change" in jwt_secret.lower():
        logger.warning(
            "SECURITY WARNING: JWT_SECRET_KEY appears weak. "
            "Set a strong random secret in production."
        )
    app.config["JWT_SECRET_KEY"] = jwt_secret
    app.config["TESTING"] = config_name == "testing"

    if isinstance(config_name, dict):
        app.config.update(config_name)

    try:
        db.init_app(app)
    except Exception as exc:
        logger.exception("Failed to initialize database extension: %s", exc)
        raise

    try:
        migrate.init_app(app, db)
    except Exception as exc:
        logger.exception("Failed to initialize migration extension: %s", exc)
        raise
    from flask_cors import CORS as FlaskCORS

    allowed_origins = os.environ.get(
        "ALLOWED_ORIGINS",
        "https://proactive-sentinel-production.up.railway.app,https://*.railway.app,http://localhost:5000,http://localhost:5001",
    ).split(",")
    try:
        FlaskCORS(
            app,
            resources={
                r"/api/*": {
                    "origins": allowed_origins,
                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "allow_headers": ["Authorization", "Content-Type"],
                    "supports_credentials": True,
                }
            }
        )
    except Exception as exc:
        logger.exception("Failed to initialize CORS: %s", exc)
        raise

    try:
        jwt = JWTManager()
        jwt.init_app(app)
        app.jwt = jwt
    except Exception as exc:
        logger.exception("Failed to initialize JWT manager: %s", exc)
        raise

    from src.api.rate_limits import limiter

    try:
        limiter.init_app(app)
    except Exception as exc:
        logger.exception("Failed to initialize rate limiter: %s", exc)
        raise

    @app.before_request
    def before_request():
        g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        g.request_start_time = time.time()
        if request.content_length and request.content_length > app.config["MAX_CONTENT_LENGTH"]:
            return jsonify({"error": "Payload too large"}), 413

    @app.after_request
    def after_request(response):
        if hasattr(request, "rate_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.rate_limit.limit)
            response.headers["X-RateLimit-Remaining"] = str(request.rate_limit.remaining)
            response.headers["X-RateLimit-Reset"] = str(request.rate_limit.reset_time)
        if hasattr(g, "request_start_time"):
            duration = (time.time() - g.request_start_time) * 1000
            app.logger.info(
                f"{request.method} {request.path} - {response.status_code} - {duration:.2f}ms"
            )
        return response

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # Import models in app factory so metadata is fully registered.
    from src.models import Alert, AuditLog, Tenant, User  # noqa: F401

    @app.route("/", methods=["GET"])
    def home():
        return jsonify(
            {
                "status": "online",
                "service": "Proactive Sentinel SOC",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/api/health",
                    "login": "/api/auth/login",
                    "alerts": "/api/alerts",
                },
            }
        ), 200

    @app.route("/health", methods=["GET"])
    def global_health():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "reachable"}, 200
        except Exception:
            return {"status": "degraded", "database": "unreachable"}, 503

    @app.route("/dashboard")
    def dashboard():
        try:
            template_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "templates",
                "dashboard.html",
            )
            with open(template_path, "r", encoding="utf-8") as f:
                html = f.read()
            from flask import Response
            return Response(html, mimetype="text/html")
        except Exception as e:
            app.logger.error(f"Dashboard error: {e}")
            return f"Dashboard error: {e}", 500

    @app.route("/api/audit/logs", methods=["GET"])
    def audit_logs_proxy():
        try:
            from src.auth.decorators import require_auth, require_tenant
            from src.models.audit_log import AuditLog

            @require_auth
            @require_tenant
            def _inner():
                logs = (
                    AuditLog.query.filter_by(tenant_id=g.tenant_id)
                    .order_by(AuditLog.timestamp.desc())
                    .limit(50)
                    .all()
                )
                return jsonify(
                    {
                        "logs": [
                            {
                                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                                "actor_id": str(log.actor_id) if log.actor_id else None,
                                "action": log.action,
                                "resource_type": log.resource_type,
                                "resource_id": log.resource_id,
                                "source_ip": log.source_ip,
                            }
                            for log in logs
                        ]
                    }
                ), 200

            return _inner()
        except Exception as exc:
            app.logger.error("Audit logs route error: %s", exc)
            return jsonify({"logs": [], "error": "Audit logging active"}), 200

    try:
        from src.api.routes import api_bp
        from src.auth.routes import auth_bp
        from src.api.audit_routes import audit_bp
        from src.api.units import units_bp
        from src.api.events import events_bp
        from src.api.integrations import integrations_bp

        app.register_blueprint(api_bp, url_prefix="/api")
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(audit_bp)
        app.register_blueprint(units_bp, url_prefix="/api/units")
        app.register_blueprint(events_bp, url_prefix="/api/events")
        app.register_blueprint(integrations_bp, url_prefix="/api/integrations")
    except Exception as exc:
        logger.exception("Failed to register blueprints: %s", exc)
        raise

    # ── Background health checker ──────────────────────────────────────────
    # Not started in TESTING mode to avoid interfering with test isolation.
    # Check both app.config and the TESTING env var: conftest sets the env
    # var before calling create_app() but sets app.config["TESTING"] after.
    _is_testing = app.config.get("TESTING") or os.environ.get("TESTING", "").lower() in ("true", "1")
    if not _is_testing and not os.environ.get("HEALTH_CHECK_DISABLED"):
        import threading
        from src.monitoring.health_checker import run_health_loop

        hc_thread = threading.Thread(
            target=run_health_loop,
            args=(app,),
            daemon=True,
            name="health-checker",
        )
        hc_thread.start()
        logger.info("Health checker background thread started (interval=60s)")

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(429)
    def ratelimit_error(error):
        app.logger.warning(
            "Rate limit exceeded",
            extra={
                "path": request.path,
                "method": request.method,
                "source_ip": request.headers.get("X-Forwarded-For", request.remote_addr),
                "user_agent": request.headers.get("User-Agent", "unknown"),
            },
        )
        return jsonify({"error": "Rate limit exceeded", "retry_after": error.description}), 429

    return app


__all__ = ["create_app", "db"]

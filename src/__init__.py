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


def create_app(config_name=None):
    """Application factory."""
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
    if not jwt_secret or "dev" in jwt_secret.lower() or "change" in jwt_secret.lower():
        logging.getLogger(__name__).warning(
            "SECURITY WARNING: JWT_SECRET_KEY is weak or not set. "
            "Set a strong random secret in production."
        )
    app.config["JWT_SECRET_KEY"] = jwt_secret or "fallback-for-dev-only"
    app.config["TESTING"] = config_name == "testing"

    if isinstance(config_name, dict):
        app.config.update(config_name)

    db.init_app(app)
    migrate.init_app(app, db)
    from flask_cors import CORS as FlaskCORS

    allowed_origins = os.environ.get(
        "ALLOWED_ORIGINS",
        "https://*.railway.app,http://localhost:5000,http://localhost:5001",
    ).split(",")
    FlaskCORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Authorization", "Content-Type"],
                "supports_credentials": True,
            }
        },
    )

    jwt = JWTManager()
    jwt.init_app(app)
    app.jwt = jwt

    from src.api.rate_limits import limiter

    limiter.init_app(app)

    @app.before_request
    def before_request():
        g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        g.request_start_time = time.time()

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

    @app.route("/health", methods=["GET"])
    def health():
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {},
        }

        try:
            db.session.execute(text("SELECT 1"))
            health_status["services"]["database"] = "healthy"
        except Exception as exc:
            health_status["services"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
            app.logger.error(f"Database health check failed: {exc}")

        try:
            redis_client = get_redis()
            redis_client.ping()
            health_status["services"]["redis"] = "healthy"
        except Exception as exc:
            health_status["services"]["redis"] = "unhealthy"
            app.logger.warning(f"Redis health check failed: {exc}")

        return jsonify(health_status), 200 if health_status["status"] == "healthy" else 503

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

    from src.api.routes import api_bp
    from src.auth.routes import auth_bp
    from src.api.audit_routes import audit_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(audit_bp)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(429)
    def ratelimit_error(error):
        return jsonify({"error": "Rate limit exceeded", "retry_after": error.description}), 429

    return app


__all__ = ["create_app", "db"]

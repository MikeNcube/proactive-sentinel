from datetime import datetime, timedelta
from typing import Any, Dict

import jwt


class JWTManager:
    """Helper for issuing and validating JWT access/refresh tokens."""

    def __init__(self, app=None):
        self.secret_key = None
        self.access_expires = 3600
        self.refresh_expires = 86400 * 7
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Bind manager configuration from a Flask app instance."""
        self.secret_key = app.config["JWT_SECRET_KEY"]
        self.access_expires = app.config.get("JWT_ACCESS_EXPIRES", 3600)
        self.refresh_expires = app.config.get("JWT_REFRESH_EXPIRES", 86400 * 7)

    def create_access_token(self, user_id: Any, tenant_id: Any, role: str) -> str:
        """Create a signed short-lived access token."""
        from flask import current_app

        secret = current_app.config["JWT_SECRET_KEY"]
        payload = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def create_refresh_token(self, user_id: Any, tenant_id: Any) -> str:
        """Create a signed long-lived refresh token."""
        from flask import current_app

        secret = current_app.config["JWT_SECRET_KEY"]
        payload = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "exp": datetime.utcnow() + timedelta(seconds=self.refresh_expires),
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a token."""
        from flask import current_app

        secret = current_app.config["JWT_SECRET_KEY"]
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise Exception("Token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise Exception("Invalid token") from exc

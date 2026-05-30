"""Compatibility route blueprints for app bootstrap."""

from flask import Blueprint, jsonify

from src.api.routes import get_alerts

auth_bp = Blueprint("auth", __name__)
alerts_bp = Blueprint("alerts", __name__)


@auth_bp.route("/health", methods=["GET"])
def auth_health():
    """Lightweight auth blueprint health endpoint."""
    return jsonify({"status": "ok"}), 200


@alerts_bp.route("", methods=["GET"], strict_slashes=False)
@alerts_bp.route("/", methods=["GET"], strict_slashes=False)
def alerts_index():
    """Expose alert list endpoint under /api/alerts."""
    return get_alerts()


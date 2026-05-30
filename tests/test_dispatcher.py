"""
Tests for ActionDispatcher (FLAG / BLOCK / REPORT) and the unban endpoint.

All Redis calls are mocked â€” no live Redis required.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.actions.dispatcher import BLOCKED_IP_PREFIX, ActionDispatcher
from src.extensions import db
from src.models.alert import Alert
from src.models.audit_log import AuditLog
from src.models.tenant import Tenant
from src.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant_and_user(suffix: str):
    """Create a unique tenant + admin user and return (tenant, user)."""
    slug = f"disp-{suffix}"
    tenant = Tenant(
        name=f"Dispatcher Tenant {suffix}",
        slug=slug,
        subdomain=slug,
        status="active",
    )
    db.session.add(tenant)
    db.session.flush()

    user = User(tenant_id=tenant.id, email=f"disp-{suffix}@test.local", role="admin")
    user.set_password("Dispatch1234!X")
    db.session.add(user)
    db.session.flush()

    return tenant, user


def _make_alert(tenant_id: str, severity: str, source_ip: str | None = None) -> Alert:
    raw = {"source_ip": source_ip} if source_ip else {}
    alert = Alert(
        tenant_id=tenant_id,
        title=f"{severity.upper()} test alert",
        severity=severity,
        status="open",
        category="test_category",
        source="test-agent",
        raw_data=raw,
    )
    db.session.add(alert)
    db.session.commit()
    return alert


# ---------------------------------------------------------------------------
# Dispatcher unit tests (direct Python API)
# ---------------------------------------------------------------------------

class TestDispatcherActions:

    def test_critical_triggers_flag_block_report(self, app):
        with app.app_context():
            tenant, _ = _make_tenant_and_user(str(uuid.uuid4())[:8])
            alert = _make_alert(str(tenant.id), "critical", source_ip="192.168.1.1")

            mock_redis = MagicMock()
            with patch("src.actions.dispatcher.get_redis", return_value=mock_redis):
                result = ActionDispatcher.dispatch(alert)

            assert result["flag"] is True
            assert result["block"] is True
            assert result["report"] is True

            # Redis SETEX was called with the correct key
            mock_redis.setex.assert_called_once()
            key_arg = mock_redis.setex.call_args[0][0]
            assert key_arg == f"{BLOCKED_IP_PREFIX}192.168.1.1"

            # AuditLog entry was written
            log = AuditLog.query.filter_by(resource_id=str(alert.id)).first()
            assert log is not None
            assert log.action == "alert_auto_dispatched"
            assert log.new_value["severity"] == "critical"

    def test_high_skips_block(self, app):
        with app.app_context():
            tenant, _ = _make_tenant_and_user(str(uuid.uuid4())[:8])
            alert = _make_alert(str(tenant.id), "high", source_ip="10.0.0.5")

            mock_redis = MagicMock()
            with patch("src.actions.dispatcher.get_redis", return_value=mock_redis):
                result = ActionDispatcher.dispatch(alert)

            assert result["flag"] is True
            assert result["block"] is False      # BLOCK not attempted for HIGH
            assert result["report"] is True

            mock_redis.setex.assert_not_called()

            log = AuditLog.query.filter_by(resource_id=str(alert.id)).first()
            assert log is not None

    def test_medium_skips_block_and_report(self, app):
        with app.app_context():
            tenant, _ = _make_tenant_and_user(str(uuid.uuid4())[:8])
            alert = _make_alert(str(tenant.id), "medium", source_ip="10.0.0.6")

            mock_redis = MagicMock()
            with patch("src.actions.dispatcher.get_redis", return_value=mock_redis):
                result = ActionDispatcher.dispatch(alert)

            assert result["flag"] is True
            assert result["block"] is False
            assert result["report"] is False

            mock_redis.setex.assert_not_called()

            log = AuditLog.query.filter_by(resource_id=str(alert.id)).first()
            assert log is None

    def test_low_takes_no_action(self, app):
        with app.app_context():
            tenant, _ = _make_tenant_and_user(str(uuid.uuid4())[:8])
            alert = _make_alert(str(tenant.id), "low", source_ip="10.0.0.7")

            mock_redis = MagicMock()
            with patch("src.actions.dispatcher.get_redis", return_value=mock_redis):
                result = ActionDispatcher.dispatch(alert)

            assert result["flag"] is False
            assert result["block"] is False
            assert result["report"] is False

            mock_redis.setex.assert_not_called()

    def test_block_skipped_when_no_source_ip(self, app):
        with app.app_context():
            tenant, _ = _make_tenant_and_user(str(uuid.uuid4())[:8])
            alert = _make_alert(str(tenant.id), "critical", source_ip=None)

            mock_redis = MagicMock()
            with patch("src.actions.dispatcher.get_redis", return_value=mock_redis):
                result = ActionDispatcher.dispatch(alert)

            assert result["flag"] is True
            assert result["block"] is False      # no IP to block
            assert result["report"] is True


# ---------------------------------------------------------------------------
# Unban endpoint tests
# ---------------------------------------------------------------------------

class TestUnbanEndpoint:

    @pytest.fixture(scope="class")
    def unban_auth_headers(self, client):
        client.post(
            "/api/auth/register",
            json={
                "email": "unban-test@zororo.co.za",
                "password": "Unban1234!Xz",
                "tenant_name": "Unban Test Tenant",
                "tenant_slug": "unban-test-tenant",
            },
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "unban-test@zororo.co.za", "password": "Unban1234!Xz"},
        )
        data = resp.get_json()
        token = data.get("access_token", "")
        assert token, f"Login failed: {data}"
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def test_unban_removes_ip_from_redis(self, client, unban_auth_headers):
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        with patch("src.api.routes.get_redis", return_value=mock_redis):
            resp = client.post(
                "/api/security/unban-ip",
                json={"ip": "10.1.2.3"},
                headers=unban_auth_headers,
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["unbanned"] is True
        assert body["ip"] == "10.1.2.3"
        mock_redis.delete.assert_called_once_with(f"{BLOCKED_IP_PREFIX}10.1.2.3")

    def test_unban_returns_false_when_ip_not_blocked(self, client, unban_auth_headers):
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 0  # key did not exist
        with patch("src.api.routes.get_redis", return_value=mock_redis):
            resp = client.post(
                "/api/security/unban-ip",
                json={"ip": "10.9.9.9"},
                headers=unban_auth_headers,
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["unbanned"] is False

    def test_unban_missing_ip_returns_400(self, client, unban_auth_headers):
        resp = client.post(
            "/api/security/unban-ip",
            json={},
            headers=unban_auth_headers,
        )
        assert resp.status_code == 400
        assert "ip" in resp.get_json().get("error", "")

    def test_unban_unauthenticated_returns_401(self, client):
        resp = client.post("/api/security/unban-ip", json={"ip": "1.2.3.4"})
        assert resp.status_code == 401


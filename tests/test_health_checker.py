"""
Tests for src/monitoring/health_checker.py.

Covers:
  - check_system_health: healthy, timeout, unreachable, unconfigured
  - check_all_systems: skips disabled entries
  - _get_failure_severity: default HIGH, CRITICAL for self_down-flagged systems
  - report_failure: persists Alert with correct severity; skips when no tenant
  - run_health_loop: does not start in TESTING mode (verified via flag check)
"""
from __future__ import annotations

import asyncio
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# â”€â”€ check_system_health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_check_system_health_returns_healthy_on_200():
    from src.monitoring.health_checker import check_system_health

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.042

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.monitoring.health_checker.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(
            check_system_health("test_svc", {"url": "http://test.local", "health_endpoint": "/health"})
        )

    assert result["status"] == "healthy"
    assert result["status_code"] == 200
    assert result["response_time_ms"] == 42
    assert result["system"] == "test_svc"


def test_check_system_health_returns_degraded_on_non_200():
    from src.monitoring.health_checker import check_system_health

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 503
    mock_response.elapsed.total_seconds.return_value = 0.1

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.monitoring.health_checker.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(
            check_system_health("svc_503", {"url": "http://test.local"})
        )

    assert result["status"] == "degraded"
    assert result["status_code"] == 503


def test_check_system_health_returns_timeout_on_timeout_exception():
    from src.monitoring.health_checker import check_system_health

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.monitoring.health_checker.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(
            check_system_health("slow_svc", {"url": "http://slow.local"})
        )

    assert result["status"] == "timeout"
    assert "timed out" in result["message"].lower() or "timeout" in result["message"].lower()


def test_check_system_health_returns_unreachable_on_connection_error():
    from src.monitoring.health_checker import check_system_health

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.monitoring.health_checker.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(
            check_system_health("down_svc", {"url": "http://down.local"})
        )

    assert result["status"] == "unreachable"


def test_check_system_health_returns_unconfigured_when_no_url():
    from src.monitoring.health_checker import check_system_health

    result = asyncio.run(
        check_system_health("unconfigured_svc", {"url": "", "health_endpoint": "/health"})
    )

    assert result["status"] == "unconfigured"
    assert result["system"] == "unconfigured_svc"


def test_check_system_health_uses_url_field_not_base_url():
    """Regression: old code read config.get('base_url'), registry stores 'url'."""
    from src.monitoring.health_checker import check_system_health

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.01

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    # Pass config with 'url', NOT 'base_url'
    config = {"url": "http://valid.local", "health_endpoint": "/ping"}
    with patch("src.monitoring.health_checker.httpx.AsyncClient", return_value=mock_client) as cls:
        asyncio.run(check_system_health("url_field_svc", config))
        # The get call should have been made against the 'url' field
        mock_client.get.assert_called_once()
        called_url = mock_client.get.call_args[0][0]
        assert called_url == "http://valid.local/ping"


# â”€â”€ check_all_systems â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_check_all_systems_skips_disabled_entries():
    from src.monitoring.health_checker import check_all_systems

    fake_systems = {
        "enabled_svc": {"url": "http://enabled.local", "health_endpoint": "/h", "enabled": True},
        "disabled_svc": {"url": "http://disabled.local", "health_endpoint": "/h", "enabled": False},
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.01

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.monitoring.health_checker.get_all_systems", return_value=fake_systems):
        with patch("src.monitoring.health_checker.httpx.AsyncClient", return_value=mock_client):
            results = asyncio.run(check_all_systems())

    system_keys = [r["system"] for r in results]
    assert "enabled_svc" in system_keys
    assert "disabled_svc" not in system_keys


# â”€â”€ _get_failure_severity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_get_failure_severity_returns_high_as_default():
    from src.monitoring.health_checker import _get_failure_severity

    assert _get_failure_severity({}) == "high"
    assert _get_failure_severity({"event_severities": {}}) == "high"
    assert _get_failure_severity({"event_severities": {"pipeline_failure": "HIGH"}}) == "high"


def test_get_failure_severity_returns_critical_for_self_down():
    from src.monitoring.health_checker import _get_failure_severity

    config = {"event_severities": {"self_down": "CRITICAL"}}
    assert _get_failure_severity(config) == "critical"


def test_get_failure_severity_returns_critical_for_redis_unreachable():
    from src.monitoring.health_checker import _get_failure_severity

    config = {"event_severities": {"redis_unreachable": "CRITICAL", "db_unreachable": "CRITICAL"}}
    assert _get_failure_severity(config) == "critical"


def test_get_failure_severity_case_insensitive_critical():
    from src.monitoring.health_checker import _get_failure_severity

    config = {"event_severities": {"self_down": "critical"}}
    assert _get_failure_severity(config) == "critical"


def test_get_failure_severity_high_when_only_non_availability_critical():
    """audit_chain_break is CRITICAL but is not an availability event â€” should still return high."""
    from src.monitoring.health_checker import _get_failure_severity

    config = {"event_severities": {"audit_chain_break": "CRITICAL", "pipeline_failure": "HIGH"}}
    assert _get_failure_severity(config) == "high"


# â”€â”€ report_failure â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_report_failure_creates_alert_with_correct_severity(app, monkeypatch):
    from src.monitoring.health_checker import report_failure
    from src.models.alert import Alert
    from src.models.tenant import Tenant
    from src.extensions import db

    config = {
        "name": "Test Monitored System",
        "event_severities": {"self_down": "CRITICAL"},
    }
    result = {
        "system": "test_monitored",
        "status": "unreachable",
        "message": "Connection refused on port 8000",
        "checked_at": "2026-05-10T12:00:00Z",
    }

    with app.app_context():
        tenant = Tenant(
            name="HC Test Tenant",
            subdomain=f"hc-test-{uuid.uuid4().hex[:8]}",
            slug=f"hc-test-{uuid.uuid4().hex[:8]}",
        )
        db.session.add(tenant)
        db.session.commit()
        # Force the health checker to use our specific tenant (avoids
        # picking up a stale tenant created by other tests in the suite).
        monkeypatch.setenv("HEALTH_CHECK_TENANT_ID", str(tenant.id))

        try:
            report_failure(app, "test_monitored", config, result)

            alert = (
                Alert.query.filter_by(
                    source="health_checker",
                    category="health_check_failure",
                    tenant_id=str(tenant.id),
                )
                .order_by(Alert.created_at.desc())
                .first()
            )
            assert alert is not None
            assert alert.severity == "critical"
            assert "Test Monitored System" in alert.title
            assert "unreachable" in alert.title
            assert str(alert.tenant_id) == str(tenant.id)
        finally:
            Alert.query.filter_by(source="health_checker", tenant_id=str(tenant.id)).delete()
            db.session.delete(tenant)
            db.session.commit()


def test_report_failure_skips_gracefully_when_no_tenants(app):
    """report_failure should log and return cleanly when no tenant exists."""
    from src.monitoring.health_checker import report_failure

    config = {"name": "Orphan System", "event_severities": {}}
    result = {
        "system": "orphan",
        "status": "unreachable",
        "checked_at": "2026-05-10T12:00:00Z",
    }

    with app.app_context():
        # Tenant is imported locally inside report_failure, so patch at source.
        with patch("src.models.tenant.Tenant") as mock_tenant_cls:
            mock_tenant_cls.query.first.return_value = None
            # Should not raise; should just log and return without creating an alert.
            report_failure(app, "orphan", config, result)


def test_report_failure_uses_env_tenant_id(app, monkeypatch):
    """HEALTH_CHECK_TENANT_ID env var bypasses the Tenant.query.first() lookup."""
    from src.monitoring.health_checker import report_failure
    from src.models.alert import Alert
    from src.models.tenant import Tenant
    from src.extensions import db

    with app.app_context():
        tenant = Tenant(
            name="Env Tenant",
            subdomain=f"env-tenant-{uuid.uuid4().hex[:8]}",
            slug=f"env-tenant-{uuid.uuid4().hex[:8]}",
        )
        db.session.add(tenant)
        db.session.commit()
        monkeypatch.setenv("HEALTH_CHECK_TENANT_ID", str(tenant.id))

        try:
            config = {"name": "Env System", "event_severities": {}}
            result = {"system": "env_sys", "status": "timeout", "checked_at": "2026-05-10T12:00:00Z"}
            report_failure(app, "env_sys", config, result)

            alert = (
                Alert.query.filter_by(source="health_checker")
                .order_by(Alert.created_at.desc())
                .first()
            )
            assert alert is not None
            assert str(alert.tenant_id) == str(tenant.id)
        finally:
            Alert.query.filter_by(source="health_checker").delete()
            db.session.delete(tenant)
            db.session.commit()
            monkeypatch.delenv("HEALTH_CHECK_TENANT_ID", raising=False)


# â”€â”€ Thread / app integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_health_checker_thread_not_started_in_testing_mode(app):
    """
    Verifies the guard in create_app(): when app.config['TESTING'] is True,
    no health-checker thread is started. We check by confirming no thread
    named 'health-checker' exists after the test app is created.
    """
    import threading

    hc_threads = [t for t in threading.enumerate() if t.name == "health-checker"]
    assert len(hc_threads) == 0, (
        "health-checker thread should not start when TESTING=True"
    )


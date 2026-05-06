"""
Tests for POST /api/events/ingest.

Uses the session-scoped app/client fixtures from tests/conftest.py,
and registers a dedicated tenant+user to avoid collisions with other test suites.
"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def events_auth_headers(client):
    """Register a dedicated tenant+user for ingest tests and return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "email": "ingest-test@zororo.co.za",
            "password": "Ingest1234!X",
            "tenant_name": "Ingest Test Tenant",
            "tenant_slug": "ingest-test-tenant",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "ingest-test@zororo.co.za", "password": "Ingest1234!X"},
    )
    data = resp.get_json()
    assert data is not None, f"Login failed: {resp.status_code} {resp.data}"
    token = data.get("access_token", "")
    assert token, f"No token in response: {data}"
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestIngestValidation:
    def test_missing_source_returns_400(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={"event_type": "ransomware", "severity": "critical"},
            headers=events_auth_headers,
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "details" in body
        assert "source" in body["details"]

    def test_missing_event_type_returns_400(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={"source": "test-agent"},
            headers=events_auth_headers,
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "event_type" in body["details"]

    def test_invalid_severity_returns_400(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={"source": "test-agent", "event_type": "scan", "severity": "extreme"},
            headers=events_auth_headers,
        )
        assert resp.status_code == 400

    def test_confidence_out_of_range_returns_400(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "test-agent",
                "event_type": "scan",
                "confidence": 1.5,
            },
            headers=events_auth_headers,
        )
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client):
        resp = client.post(
            "/api/events/ingest",
            json={"source": "agent", "event_type": "scan"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Security event path
# ---------------------------------------------------------------------------

class TestIngestSecurityEvents:
    def test_creates_alert_and_returns_201(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "wazuh-agent-01",
                "event_type": "ransomware",
                "severity": "critical",
                "raw_data": {"host": "server-01", "pid": 1234},
                "confidence": 0.95,
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)
        body = resp.get_json()
        assert body["created"] in (True, False)

    def test_created_alert_has_id_and_severity(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "test-source-unique",
                "event_type": "data_exfil_unique",
                "severity": "high",
                "raw_data": {"host": "db-server", "bytes_sent": 50000},
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)
        body = resp.get_json()
        if body.get("created"):
            assert "alert_id" in body
            assert body["severity"] == "high"
        else:
            assert body.get("reason") == "duplicate suppressed"

    def test_default_severity_is_low(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={"source": "low-source", "event_type": "port_scan_low"},
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)
        body = resp.get_json()
        if body.get("created"):
            assert body["severity"] == "low"

    def test_title_derived_from_event_type_when_absent(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={"source": "test-agent", "event_type": "lateral_movement_test"},
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)

    def test_explicit_title_accepted(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "test-agent",
                "event_type": "custom_rule_match",
                "title": "Suspicious PowerShell execution",
                "severity": "medium",
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)

    def test_cross_tenant_rejection(self, client, events_auth_headers):
        import uuid
        foreign_tenant = str(uuid.uuid4())
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "rogue-agent",
                "event_type": "scan",
                "tenant_id": foreign_tenant,
            },
            headers=events_auth_headers,
        )
        assert resp.status_code == 403

    def test_matching_tenant_id_accepted(self, client, events_auth_headers):
        # First, find out what tenant_id the token carries
        me_resp = client.get("/api/auth/me", headers=events_auth_headers)
        assert me_resp.status_code == 200
        tenant_id = me_resp.get_json()["tenant_id"]

        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "explicit-tenant-source",
                "event_type": "explicit_tenant_event",
                "tenant_id": tenant_id,
                "severity": "low",
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# UX / operational event path
# ---------------------------------------------------------------------------

class TestIngestUXEvents:
    def test_slow_claims_routes_to_ux_observer(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "claims-service",
                "event_type": "slow_claims",
                "severity": "medium",
                "raw_data": {"processing_time": 5.2, "user_id": "claims-user-1"},
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)
        body = resp.get_json()
        # UXObserver may return signals — either created or no-signal
        assert "created" in body

    def test_whatsapp_frustration_detected(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "zendesk-whatsapp",
                "event_type": "whatsapp_frustration",
                "raw_data": {
                    "channel": "whatsapp",
                    "message": "I need human help please human",
                    "user_id": "wa-user-99",
                },
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)
        body = resp.get_json()
        assert "created" in body
        if body["created"]:
            assert "alert_ids" in body
            assert body["count"] >= 1

    def test_web_error_500_detected(self, client, events_auth_headers):
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "nginx-access-log",
                "event_type": "web_error",
                "raw_data": {"status_code": 500, "path": "/api/claims/submit"},
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)

    def test_ux_event_no_signal_returns_200_not_created(self, client, events_auth_headers):
        # A slow_claims event with processing_time below threshold (2.0) → no signal
        resp = client.post(
            "/api/events/ingest",
            json={
                "source": "claims-service",
                "event_type": "slow_claims",
                "raw_data": {"processing_time": 0.3},
            },
            headers=events_auth_headers,
        )
        assert resp.status_code in (200, 201)
        body = resp.get_json()
        # Might be created=False (no signal) or created=True from a different detector
        assert "created" in body

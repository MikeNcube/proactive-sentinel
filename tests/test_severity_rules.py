"""
Tests for severity classification rules and DetectionEngine override behaviour.
"""
import uuid
from unittest.mock import patch

import pytest

from src.detections.rules import SEVERITY_RULES, classify_severity


class TestClassifySeverity:
    """Pure unit tests â€” no app context needed."""

    def test_all_critical_event_types(self):
        for ev in SEVERITY_RULES["critical"]:
            assert classify_severity(ev) == "critical", f"Expected critical for '{ev}'"

    def test_all_high_event_types(self):
        for ev in SEVERITY_RULES["high"]:
            assert classify_severity(ev) == "high", f"Expected high for '{ev}'"

    def test_all_medium_event_types(self):
        for ev in SEVERITY_RULES["medium"]:
            assert classify_severity(ev) == "medium", f"Expected medium for '{ev}'"

    def test_unknown_event_type_defaults_to_low(self):
        assert classify_severity("some_unknown_event") == "low"
        assert classify_severity("port_scan_custom") == "low"
        assert classify_severity("lateral_movement_custom") == "low"

    def test_empty_and_none_default_to_low(self):
        assert classify_severity("") == "low"
        assert classify_severity(None) == "low"

    def test_lookup_is_case_insensitive(self):
        assert classify_severity("RANSOMWARE") == "critical"
        assert classify_severity("Login_Anomaly") == "high"
        assert classify_severity("UNUSUAL_NAVIGATION") == "medium"

    def test_severity_tiers_are_disjoint(self):
        all_events = []
        for events in SEVERITY_RULES.values():
            all_events.extend(events)
        assert len(all_events) == len(set(all_events)), "Event types must not appear in multiple tiers"


class TestEngineOverride:
    """Integration test â€” requires app context via conftest fixture."""

    def test_sender_severity_is_overridden_by_rules(self, app):
        """Engine must classify by rule, ignoring whatever severity the sender claims."""
        from src.detections.engine import DetectionEngine
        from src.extensions import db
        from src.models.tenant import Tenant
        from src.models.user import User

        with app.app_context():
            suffix = str(uuid.uuid4())[:8]
            slug = f"rules-{suffix}"
            tenant = Tenant(
                name=f"Rules Tenant {suffix}",
                slug=slug,
                subdomain=slug,
                status="active",
            )
            db.session.add(tenant)
            db.session.flush()
            user = User(
                tenant_id=tenant.id,
                email=f"rules-{suffix}@test.local",
                role="admin",
            )
            user.set_password("Rules1234!X")
            db.session.add(user)
            db.session.commit()

            engine = DetectionEngine()
            alert_data = {
                "tenant_id": str(tenant.id),
                "source": "test-agent",
                "category": "ransomware",   # maps to critical
                "severity": "low",          # sender claims low â€” must be overridden
                "raw_data": {},
                "confidence": 0.9,
            }

            with patch("src.actions.dispatcher.get_redis") as mock_redis:
                mock_redis.return_value.setex.return_value = 1
                with patch.object(engine.correlation, "should_alert", return_value=True):
                    alert = engine.process_alert(alert_data)

            assert alert is not None
            assert alert.severity == "critical", (
                f"Expected 'critical' (rule-based), got '{alert.severity}' "
                f"(sender claimed 'low')"
            )


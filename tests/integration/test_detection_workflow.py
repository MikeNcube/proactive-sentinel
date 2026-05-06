"""
Integration tests for detection engine and alert workflow.
"""

import pytest
import uuid

from app import create_app
from src.extensions import db
from src.models.tenant import Tenant
from src.detections.detection_engine import DetectionEngine
from src.detections.correlation_engine import CorrelationEngine


class TestDetectionEngine:
    """Test detection and correlation functionality."""

    @pytest.fixture(scope="module")
    def app(self):
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "JWT_SECRET_KEY": "test-secret-key",
            }
        )
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    @pytest.fixture(scope="module")
    def test_tenant(self, app):
        with app.app_context():
            tenant = Tenant.query.filter_by(slug="detection-test").first()
            if not tenant:
                tenant = Tenant(
                    id=str(uuid.uuid4()),
                    name="Detection Test Tenant",
                    slug="detection-test",
                    plan="enterprise",
                    status="active",
                )
                db.session.add(tenant)
                db.session.commit()
            yield {
                "id": str(tenant.id),
                "slug": tenant.slug,
                "name": tenant.name,
                "status": tenant.status,
            }

    def test_alert_deduplication(self, app, test_tenant):
        """Test that duplicate alerts are suppressed."""
        with app.app_context():
            engine = DetectionEngine()

            alert_data = {
                "tenant_id": test_tenant["id"],
                "category": "suspicious_login",
                "source": "auth_logs",
                "host": "server01",
            }

            alert1 = engine.process_alert(alert_data)
            assert alert1 is not None

            alert2 = engine.process_alert(alert_data)
            assert alert2 is None

    def test_attack_chain_correlation(self, app, test_tenant):
        """Test attack chain detection."""
        with app.app_context():
            engine = CorrelationEngine()

            alerts = [
                {"source_ip": "10.0.0.1", "mitre_techniques": ["T1046"]},
                {"source_ip": "10.0.0.1", "mitre_techniques": ["T1592"]},
                {"source_ip": "10.0.0.1", "mitre_techniques": ["T1021"]},
                {"source_ip": "10.0.0.1", "mitre_techniques": ["T1020"]},
            ]

            chains = engine.correlate_attack_chain(alerts)
            assert len(chains) > 0
            assert chains[0]["severity"] == "critical"
            assert len(chains[0]["stages"]) >= 3

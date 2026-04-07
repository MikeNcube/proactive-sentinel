import pytest
from app import create_app, db
from src.auth.jwt_manager import JWTManager
from src.models.tenant import Tenant
from src.models.user import User
from src.models.alert import Alert


class TestTenantIsolation:
    @pytest.fixture
    def app(self):
        app = create_app("testing")
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    def test_data_isolation_between_tenants(self, app):
        """Test that Tenant A cannot see Tenant B's data"""
        with app.app_context():
            # Create two tenants
            tenant_a = Tenant(name="Company A", subdomain="a")
            tenant_b = Tenant(name="Company B", subdomain="b")
            db.session.add_all([tenant_a, tenant_b])
            db.session.commit()

            # Create alerts for each tenant
            alert_a = Alert(tenant_id=tenant_a.id, title="Alert A", severity="high")
            alert_b = Alert(tenant_id=tenant_b.id, title="Alert B", severity="high")
            db.session.add_all([alert_a, alert_b])
            db.session.commit()

            # Query as Tenant A
            with app.test_request_context(headers={"X-Tenant-ID": str(tenant_a.id)}):
                from src.repositories.alert_repository import AlertRepository

                repo = AlertRepository(db)
                alerts = repo.get_all()

                assert len(alerts) == 1
                assert alerts[0].title == "Alert A"

    def test_tenant_suspension_blocks_access(self, app):
        """Test that suspended tenants cannot access data"""
        with app.app_context():
            tenant = Tenant(name="Suspended Co", subdomain="suspended", status="suspended")
            db.session.add(tenant)
            db.session.commit()
            jwt_manager = JWTManager(app)
            token = jwt_manager.create_access_token(user_id="u-test", tenant_id=tenant.id, role="analyst")

            with app.test_request_context(headers={"X-Tenant-ID": str(tenant.id)}):
                from src.auth.decorators import require_tenant

                # This should raise 403
                response = app.test_client().get(
                    "/api/alerts",
                    headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)},
                )
                assert response.status_code == 403

    def test_audit_logs_track_all_changes(self, app):
        """Test that all state changes are audited"""
        with app.app_context():
            tenant = Tenant(name="Audit Co", subdomain="audit")
            db.session.add(tenant)
            db.session.commit()
            user = User(
                tenant_id=tenant.id,
                email="auditor@audit.com",
                password_hash="hash",
                role="admin",
            )
            db.session.add(user)
            db.session.commit()

            # Create alert
            alert = Alert(tenant_id=tenant.id, title="Test", severity="high")
            db.session.add(alert)
            db.session.commit()

            # Dismiss alert
            with app.test_request_context(headers={"X-Tenant-ID": str(tenant.id)}):
                from src.repositories.alert_repository import AlertRepository

                repo = AlertRepository(db)
                repo.dismiss(alert.id, user_id=user.id)

                # Verify audit log created
                from src.models.audit_log import AuditLog

                audit = AuditLog.query.filter_by(resource_id=str(alert.id)).first()
                assert audit is not None
                assert audit.action == "alert_dismissed"
                assert audit.old_value["status"] == "open"
                assert audit.new_value["status"] == "dismissed"

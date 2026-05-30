"""Integration tests for API flow with authentication and multi-tenancy"""

import os
import pytest
import uuid
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

    from src import create_app
    from src.extensions import db

    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["JWT_SECRET_KEY"] = "test-secret-key"
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope='module')
def test_tenant(app):
    from src.models.tenant import Tenant
    from src.extensions import db
    with app.app_context():
        tenant = Tenant.query.filter_by(slug='integration-test').first()
        if not tenant:
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name='Integration Test Tenant',
                slug='integration-test',
                plan='enterprise',
                status='active'
            )
            db.session.add(tenant)
            db.session.commit()
        yield tenant


@pytest.fixture(scope='module')
def test_user(app, test_tenant):
    from src.models.user import User
    from src.extensions import db
    with app.app_context():
        user = User.query.filter_by(
            email='integration@zororo.co.za'
        ).first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email='integration@zororo.co.za',
                password_hash=generate_password_hash('YOUR_PASSWORD_HERE'),
                tenant_id=test_tenant.id,
                role='admin'
            )
            db.session.add(user)
            db.session.commit()
        yield user


@pytest.fixture(scope="module")
def auth_headers(client, test_tenant, test_user):
    resp = client.post('/api/auth/login', json={
        'email': 'integration@zororo.co.za',
        'password': 'YOUR_PASSWORD_HERE'
    })
    data = resp.get_json()
    assert data is not None, f"Login failed. Status: {resp.status_code}, Body: {resp.data}"
    assert 'access_token' in data, f"No token in: {data}"
    return {'Authorization': f'Bearer {data["access_token"]}'}


def test_health_endpoint(client):
    """Test public health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_get_alerts_with_auth(client, auth_headers, test_tenant):
    """Test authenticated alert retrieval"""
    response = client.get('/api/alerts', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert 'alerts' in data


def test_tenant_isolation(client, auth_headers, test_tenant):
    """Test that tenant cannot access other tenant's data"""
    # Create alert for test tenant
    from src.extensions import db
    from src.models.alert import Alert

    alert = Alert(
        tenant_id=test_tenant.id,
        title="Test Alert",
        severity="high",
        status="open"
    )
    db.session.add(alert)
    db.session.commit()

    # Query alerts
    response = client.get('/api/alerts', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['alerts']) == 1
    assert data['alerts'][0]['title'] == "Test Alert"


def test_get_current_tenant(client, auth_headers, test_tenant):
    """Test tenant info endpoint"""
    response = client.get('/api/tenants/current', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['tenant_id'] == str(test_tenant.id)
    assert 'correlation_id' in data


import base64
import pytest
import os

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('JWT_SECRET_KEY', 'test-secret-key')
os.environ.setdefault(
    'ENCRYPTION_KEY',
    base64.b64encode(b'sentinel-test-encryption-key-32b').decode(),
)

from src import create_app
from src.extensions import db

@pytest.fixture(scope='session')
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture(scope='session')
def test_tenant(app):
    from src.extensions import db
    from src.models.tenant import Tenant
    import uuid

    with app.app_context():
        tenant = Tenant.query.filter_by(slug='integration-test').first()
        if not tenant:
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name='Integration Test Tenant',
                slug='integration-test',
                plan='enterprise',
                status='active',
            )
            db.session.add(tenant)
            db.session.commit()
        yield tenant


@pytest.fixture(scope='session')
def test_user(app, test_tenant):
    from src.extensions import db
    from src.models.user import User
    from werkzeug.security import generate_password_hash
    import uuid

    with app.app_context():
        user = User.query.filter_by(email='integration@zororo.co.za').first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email='integration@zororo.co.za',
                password_hash=generate_password_hash('Admin1234!'),
                tenant_id=test_tenant.id,
                role='admin',
            )
            db.session.add(user)
            db.session.commit()
        yield user


@pytest.fixture(scope='session')
def auth_headers(client, test_tenant, test_user):
    resp = client.post('/api/auth/login', json={
        'email': 'integration@zororo.co.za',
        'password': 'Admin1234!'
    })
    data = resp.get_json()
    assert data is not None, f"Login failed. Status: {resp.status_code}, Body: {resp.data}"
    assert 'access_token' in data, f"No token in: {data}"
    return {'Authorization': f'Bearer {data["access_token"]}'}

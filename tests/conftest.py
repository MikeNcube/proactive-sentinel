import base64
import pytest
import os

# Set env vars BEFORE importing app -- this is critical
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["TESTING"] = "true"
# Fixed 32-byte test key so EncryptedJSON works without RuntimeWarning.
os.environ.setdefault(
    "ENCRYPTION_KEY",
    base64.b64encode(b"sentinel-test-encryption-key-32b").decode(),
)

from src import create_app
from src.extensions import db


@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def auth_headers_unit(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "test@zororo.co.za",
            "password": "YOUR_PASSWORD_HERE",
            "tenant_slug": "test-zororo",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "test@zororo.co.za", "password": "YOUR_PASSWORD_HERE"},
    )
    data = resp.get_json()
    token = data.get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


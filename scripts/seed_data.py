#!/usr/bin/env python
"""
Seed sample tenants, users and alerts for local development / CI.

This script used to hardcode demo passwords ('password123', 'Admin1234!')
inline, which leaked into git. It now:

* Reads every user password from environment variables.
* Refuses to run in FLASK_ENV=production without SEED_ALLOW_PROD=1.
* Refuses to run without SEED_ALLOW=1 to prevent accidental execution
  against a populated database.
* Never prints plaintext passwords.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

from app import create_app  # noqa: E402
from src.extensions import db  # noqa: E402
from src.models.alert import Alert  # noqa: E402
from src.models.tenant import Tenant  # noqa: E402
from src.models.user import User  # noqa: E402


def _env_password(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Refusing to seed: {name} is required. "
            "This script never uses hardcoded passwords."
        )
    if len(value) < 12:
        raise SystemExit(
            f"Refusing to seed: {name} must be at least 12 characters."
        )
    return value


def seed():
    if os.environ.get("SEED_ALLOW") != "1":
        raise SystemExit(
            "Refusing to seed: set SEED_ALLOW=1 to confirm you intend to "
            "mutate this database with sample data."
        )
    if (
        os.environ.get("FLASK_ENV", "").lower() == "production"
        and os.environ.get("SEED_ALLOW_PROD") != "1"
    ):
        raise SystemExit(
            "Refusing to seed in FLASK_ENV=production without "
            "SEED_ALLOW_PROD=1."
        )

    acme_admin_pw = _env_password("SEED_ACME_ADMIN_PASSWORD")
    acme_analyst_pw = _env_password("SEED_ACME_ANALYST_PASSWORD")
    acme_viewer_pw = _env_password("SEED_ACME_VIEWER_PASSWORD")
    zororo_admin_pw = _env_password("SEED_ZORORO_ADMIN_PASSWORD")
    zororo_analyst_pw = _env_password("SEED_ZORORO_ANALYST_PASSWORD")

    app = create_app()

    with app.app_context():
        print("Seeding database...")

        tenants = [
            {"name": "Acme Insurance", "subdomain": "acme", "status": "active"},
            {
                "name": "Zororo Phumulani",
                "subdomain": "zororo",
                "status": "active",
            },
        ]

        created_tenants = []
        for t_data in tenants:
            tenant = Tenant.query.filter_by(subdomain=t_data["subdomain"]).first()
            if not tenant:
                tenant = Tenant(
                    id=uuid.uuid4(),
                    name=t_data["name"],
                    subdomain=t_data["subdomain"],
                    status=t_data["status"],
                )
                db.session.add(tenant)
                print(f"Created tenant: {tenant.name}")
            else:
                print(f"Tenant exists: {tenant.name}")
            created_tenants.append(tenant)

        db.session.commit()

        users_data = [
            {"tenant": "acme", "email": "admin@acme.com", "password": acme_admin_pw, "role": "admin"},
            {"tenant": "acme", "email": "analyst@acme.com", "password": acme_analyst_pw, "role": "analyst"},
            {"tenant": "acme", "email": "viewer@acme.com", "password": acme_viewer_pw, "role": "viewer"},
            {"tenant": "zororo", "email": "admin@zororo.co.za", "password": zororo_admin_pw, "role": "admin"},
            {"tenant": "zororo", "email": "analyst@zororo.co.za", "password": zororo_analyst_pw, "role": "analyst"},
        ]

        for u_data in users_data:
            tenant = Tenant.query.filter_by(subdomain=u_data["tenant"]).first()
            if not tenant:
                print(f" Tenant not found: {u_data['tenant']}")
                continue

            user = User.query.filter_by(email=u_data["email"]).first()
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    email=u_data["email"],
                    role=u_data["role"],
                )
                db.session.add(user)
                print(f"Created user: {user.email}")
            else:
                print(f"Updating user: {user.email}")

            user.set_password(u_data["password"])

        db.session.commit()

        severities = ["critical", "high", "medium", "low"]
        categories = ["ransomware", "data_exfil", "unauthorized_access", "suspicious_activity"]

        for tenant in created_tenants:
            existing_alerts = Alert.query.filter_by(tenant_id=tenant.id).count()
            if existing_alerts == 0:
                for i in range(10):
                    alert = Alert(
                        id=uuid.uuid4(),
                        tenant_id=tenant.id,
                        title=f"Sample Alert {i + 1} - {categories[i % len(categories)]}",
                        severity=severities[i % len(severities)],
                        status="open" if i < 7 else "investigating",
                        category=categories[i % len(categories)],
                        description=f"Test alert for {tenant.name}",
                        source="seed_script",
                        confidence=0.5 + (i * 0.05),
                        created_at=datetime.utcnow() - timedelta(hours=i),
                        mitre_techniques=[f"T{1000 + i}", f"T{2000 + i}"],
                    )
                    db.session.add(alert)
                print(f"Added 10 alerts for {tenant.name}")

        db.session.commit()

        print("\n" + "=" * 50)
        print("Seeding complete!" + "\n" + "=" * 50)
        print(f"Tenants: {Tenant.query.count()}")
        print(f"Users: {User.query.count()}")
        print(f"Alerts: {Alert.query.count()}")
        # Emails only -- plaintext passwords never logged.
        print("\n Users created / updated:")
        for u_data in users_data:
            print(f"  {u_data['email']}")
        print("=" * 50)


if __name__ == "__main__":
    seed()

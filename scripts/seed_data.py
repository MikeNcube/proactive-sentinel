#!/usr/bin/env python
"""Seed database with test data for development"""

import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, "/app")
from app import create_app
from src.extensions import db
from src.models.tenant import Tenant
from src.models.user import User
from src.models.alert import Alert


def seed():
    app = create_app()

    with app.app_context():
        print("Seeding database...")

        # Create tenants
        tenants = [
            {
                "name": "Acme Insurance",
                "subdomain": "acme",
                "status": "active",
            },
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

        # Users data with consistent password hashing
        users_data = [
            # Acme Insurance users
            {"tenant": "acme", "email": "admin@acme.com", "password": "password123", "role": "admin"},
            {"tenant": "acme", "email": "analyst@acme.com", "password": "password123", "role": "analyst"},
            {"tenant": "acme", "email": "viewer@acme.com", "password": "password123", "role": "viewer"},
            # Zororo Phumulani users
            {"tenant": "zororo", "email": "admin@zororo.co.za", "password": "Admin1234!", "role": "admin"},
            {"tenant": "zororo", "email": "analyst@zororo.co.za", "password": "Admin1234!", "role": "analyst"},
        ]

        for u_data in users_data:
            # Find tenant
            tenant = Tenant.query.filter_by(subdomain=u_data["tenant"]).first()
            if not tenant:
                print(f" Tenant not found: {u_data['tenant']}")
                continue

            # Create or update user
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

            # ALWAYS use set_password for consistent bcrypt hashing
            user.set_password(u_data["password"])

        db.session.commit()

        # Create sample alerts
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

        # Display summary
        print("\n" + "=" * 50)
        print("Seeding complete!" + "\n" + "=" * 50)
        print(f"Tenants: {Tenant.query.count()}")
        print(f"Users: {User.query.count()}")
        print(f"Alerts: {Alert.query.count()}")
        print("\n Login credentials:")
        for u_data in users_data:
            print(f"  {u_data['email']} / {u_data['password']}")
        print("=" * 50)


if __name__ == "__main__":
    seed()

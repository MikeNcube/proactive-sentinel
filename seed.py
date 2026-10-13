import os
import sys
sys.path.insert(0, ".")

from src import create_app
from src.extensions import db
from src.models.tenant import Tenant
from src.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    if Tenant.query.count() == 0:
        tenant = Tenant(
            name="Demo Insurance Co",
            slug="demo",
            plan="enterprise",
            status="active",
        )
        db.session.add(tenant)
        db.session.flush()

        admin = User(
            email="demo@example.com",
            password_hash=generate_password_hash("YOUR_PASSWORD_HERE"),
            tenant_id=tenant.id,
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        print("Seed complete: demo@example.com / YOUR_PASSWORD_HERE")
    else:
        demo_tenant = Tenant.query.filter_by(slug="demo").first()
        if demo_tenant and demo_tenant.status != "active":
            demo_tenant.status = "active"
            db.session.commit()
            print("Updated demo tenant -> active")
        else:
            print("Already seeded - skipping")


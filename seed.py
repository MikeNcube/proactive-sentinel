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
            name="Zororo Phumulani",
            slug="zororo",
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
        zororo = Tenant.query.filter_by(slug="zororo").first()
        if zororo and zororo.status != "active":
            zororo.status = "active"
            db.session.commit()
            print("Updated zororo tenant -> active")
        else:
            print("Already seeded - skipping")


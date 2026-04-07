import os, sys

from werkzeug.security import generate_password_hash

sys.path.insert(0, ".")

from app import create_app, db
from models import Tenant, User

app = create_app()

with app.app_context():
    # Only seed if tables are empty
    if Tenant.query.count() == 0:
        tenant = Tenant(
            name="Zororo Phumulani",
            slug="zororo",
            plan="enterprise",
            # Must be active so @require_tenant passes after a fresh Docker rebuild.
            status="active",
        )
        db.session.add(tenant)
        db.session.flush()

        password_hash = generate_password_hash("Admin1234!")

        admin = User(
            email="admin@zororo.co.za",
            password_hash=password_hash,
            tenant_id=tenant.id,
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        print("Seed complete: admin@zororo.co.za / Admin1234!")
    else:
        # Docker-compose often reuses volumes, so an old "trial" tenant can persist.
        # Ensure the seeded Zororo tenant is active so @require_tenant never rejects it.
        zororo = Tenant.query.filter_by(slug="zororo").first()
        if zororo and zororo.status != "active":
            zororo.status = "active"
            db.session.commit()
            print('Updated existing "zororo" tenant status -> active')
        else:
            print("Already seeded — skipping")

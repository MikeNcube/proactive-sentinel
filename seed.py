"""
One-shot seed: creates the initial Zororo tenant + admin user.

Prior versions hardcoded 'Admin1234!' as the admin password. This version:

* Requires SEED_ADMIN_PASSWORD to be supplied via environment variable.
* Requires at least 12 characters.
* Refuses to run in FLASK_ENV=production without SEED_ALLOW_PROD=1.
* Never prints the plaintext password.

Usage (local dev / one-time bootstrap):

    SEED_ADMIN_PASSWORD='...' python seed.py
"""

import os
import sys

sys.path.insert(0, ".")

from src import create_app  # noqa: E402
from src.extensions import db  # noqa: E402
from src.models.tenant import Tenant  # noqa: E402
from src.models.user import User  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


def _seed_password() -> str:
    password = os.environ.get("SEED_ADMIN_PASSWORD", "").strip()
    if not password:
        raise SystemExit(
            "Refusing to seed: SEED_ADMIN_PASSWORD is required. "
            "This script never hardcodes credentials."
        )
    if len(password) < 12:
        raise SystemExit(
            "Refusing to seed: SEED_ADMIN_PASSWORD must be at least 12 characters."
        )
    return password


def main() -> None:
    if (
        os.environ.get("FLASK_ENV", "").lower() == "production"
        and os.environ.get("SEED_ALLOW_PROD") != "1"
    ):
        raise SystemExit(
            "Refusing to seed in FLASK_ENV=production without "
            "SEED_ALLOW_PROD=1."
        )

    admin_password = _seed_password()
    admin_email = os.environ.get(
        "SEED_ADMIN_EMAIL", "admin@zororo.co.za"
    ).strip()
    tenant_slug = os.environ.get("SEED_TENANT_SLUG", "zororo").strip()
    tenant_name = os.environ.get(
        "SEED_TENANT_NAME", "Zororo Phumulani"
    ).strip()

    app = create_app()
    with app.app_context():
        if Tenant.query.count() == 0:
            tenant = Tenant(
                name=tenant_name,
                slug=tenant_slug,
                plan="enterprise",
                status="active",
            )
            db.session.add(tenant)
            db.session.flush()

            admin = User(
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                tenant_id=tenant.id,
                role="admin",
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Seed complete: {admin_email} created.")
        else:
            tenant = Tenant.query.filter_by(slug=tenant_slug).first()
            if tenant and tenant.status != "active":
                tenant.status = "active"
                db.session.commit()
                print(f"Updated tenant '{tenant_slug}' -> active")
            else:
                print("Already seeded - skipping")


if __name__ == "__main__":
    main()

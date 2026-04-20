"""
Developer helper: force-reset a small set of demo user passwords using bcrypt.

This script previously hardcoded the passwords ('password123', 'Admin1234!',
'test123') in source and in its final print statement. Those values were
committed to git and appeared in seed scripts and the dashboard. This version:

* Reads every password from environment variables.
* Refuses to run unless the operator explicitly opts in via ALLOW_PASSWORD_RESET=1.
* Refuses to run in a production environment (FLASK_ENV=production).
* Never prints the plaintext passwords or writes them to a log.

Usage (local dev only):

    ALLOW_PASSWORD_RESET=1 \
    FIX_ACME_ADMIN_PASSWORD='...' \
    FIX_ZORORO_ADMIN_PASSWORD='...' \
    FIX_TEST_USER_PASSWORD='...' \
    python fix_passwords.py
"""

import os
import sys
import uuid

sys.path.insert(0, ".")

from app import create_app  # noqa: E402
from src.extensions import db  # noqa: E402
from src.models.tenant import Tenant  # noqa: E402
from src.models.user import User  # noqa: E402


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Refusing to run: environment variable {name} is not set. "
            "This script never accepts hardcoded passwords."
        )
    if len(value) < 12:
        raise SystemExit(
            f"Refusing to run: {name} must be at least 12 characters."
        )
    return value


def main() -> None:
    if os.environ.get("ALLOW_PASSWORD_RESET") != "1":
        raise SystemExit(
            "Refusing to run: set ALLOW_PASSWORD_RESET=1 to confirm a "
            "destructive password reset."
        )
    if os.environ.get("FLASK_ENV", "").lower() == "production":
        raise SystemExit(
            "Refusing to run in FLASK_ENV=production. "
            "Rotate passwords through the normal admin flow instead."
        )

    acme_password = _require("FIX_ACME_ADMIN_PASSWORD")
    zororo_password = _require("FIX_ZORORO_ADMIN_PASSWORD")
    test_password = _require("FIX_TEST_USER_PASSWORD")

    app = create_app()
    with app.app_context():
        tenant = Tenant.query.filter_by(subdomain="acme").first()
        if not tenant:
            tenant = Tenant(
                id=uuid.uuid4(),
                name="Acme Insurance",
                subdomain="acme",
                status="active",
            )
            db.session.add(tenant)
            db.session.commit()

        for email, password, role in (
            ("admin@acme.com", acme_password, "admin"),
            ("admin@zororo.co.za", zororo_password, "admin"),
            ("test@acme.com", test_password, "analyst"),
        ):
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    email=email,
                    role=role,
                )
                db.session.add(user)
            user.set_password(password)

        db.session.commit()
        # Intentionally no listing of email->password pairs: the operator
        # already has the values in-process via the env.
        print(
            f"Reset {User.query.count()} user password(s). "
            "Plaintext values were not logged."
        )


if __name__ == "__main__":
    main()

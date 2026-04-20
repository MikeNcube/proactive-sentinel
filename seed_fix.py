"""
Deprecated -- superseded by ``fix_passwords.py``.

This file previously hardcoded bcrypt password resets for demo accounts
('password123' / 'Admin1234!'). Those values leaked into git and are now
treated as compromised.

It is kept as a thin stub so that any automation or runbook that still
invokes it fails loudly with an actionable error instead of silently
re-seeding compromised passwords.
"""

import sys


def main() -> None:
    print(
        "seed_fix.py has been removed. "
        "Use fix_passwords.py with explicit env vars instead:\n"
        "    ALLOW_PASSWORD_RESET=1 "
        "FIX_ACME_ADMIN_PASSWORD=... "
        "FIX_ZORORO_ADMIN_PASSWORD=... "
        "FIX_TEST_USER_PASSWORD=... "
        "python fix_passwords.py",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

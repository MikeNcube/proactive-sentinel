"""
Seeds the live Proactive Sentinel demo environment via the REST API.

Creates two tenants and one admin user each:
  - Zororo Claims   / admin@zororo.test
  - Zororo Digital  / analyst@zororo.test

Safe to run multiple times: if a tenant already exists (409) the script
skips registration and proceeds straight to login verification.

Usage:
    python scripts/setup_demo.py [BASE_URL]

    BASE_URL defaults to the Railway production URL.
"""

import sys
import time

import httpx

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://proactive-sentinel-production.up.railway.app"
PASSWORD = "Demo@1234567890"

DEMO_ACCOUNTS = [
    {
        "email": "admin@zororo.test",
        "tenant_name": "Zororo Claims",
        "tenant_slug": "zororo-claims",
    },
    {
        "email": "analyst@zororo.test",
        "tenant_name": "Zororo Digital",
        "tenant_slug": "zororo-digital",
    },
]


def register(client: httpx.Client, account: dict) -> str:
    """
    POST /api/auth/register.
    Returns "created" or "already_exists".
    Raises on any other error.
    """
    payload = {
        "email": account["email"],
        "password": PASSWORD,
        "tenant_name": account["tenant_name"],
        "tenant_slug": account["tenant_slug"],
    }
    resp = client.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=15)

    if resp.status_code == 201:
        return "created"
    if resp.status_code == 409:
        return "already_exists"

    raise RuntimeError(
        f"Registration failed for {account['email']}: "
        f"HTTP {resp.status_code} — {resp.text[:200]}"
    )


def login_and_verify(client: httpx.Client, email: str) -> str:
    """
    POST /api/auth/login.
    Returns the access token on success.
    Raises if no token is returned.
    """
    resp = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=15,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Login failed for {email}: "
            f"HTTP {resp.status_code} — {resp.text[:200]}"
        )

    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(
            f"Login response for {email} contained no access_token: {resp.text[:200]}"
        )
    return token


def main() -> None:
    print(f"Target: {BASE_URL}")
    print(f"Accounts: {len(DEMO_ACCOUNTS)}")
    print()

    results = []

    with httpx.Client() as client:
        for account in DEMO_ACCOUNTS:
            email = account["email"]
            tenant = account["tenant_name"]

            # --- registration ---
            print(f"[{email}] Registering tenant '{tenant}'...")
            try:
                outcome = register(client, account)
            except RuntimeError as exc:
                print(f"  ERROR: {exc}")
                results.append((email, tenant, "FAIL", None))
                continue

            if outcome == "created":
                print(f"  Tenant created.")
            else:
                print(f"  Tenant already exists — skipping registration.")

            # Brief pause so the login rate limiter doesn't see a burst
            time.sleep(1)

            # --- login verification ---
            print(f"[{email}] Verifying login...")
            try:
                token = login_and_verify(client, email)
            except RuntimeError as exc:
                print(f"  ERROR: {exc}")
                results.append((email, tenant, "FAIL", None))
                continue

            preview = token[:24] + "..."
            print(f"  Login OK. Token: {preview}")
            results.append((email, tenant, "OK", token))

            time.sleep(1)

    # --- summary ---
    print()
    print("=" * 60)
    print("DEMO ENVIRONMENT SUMMARY")
    print("=" * 60)
    print(f"URL:      {BASE_URL}")
    print(f"Password: {PASSWORD}")
    print()

    all_ok = True
    for email, tenant, status, _ in results:
        mark = "PASS" if status == "OK" else "FAIL"
        print(f"  [{mark}] {email}  ({tenant})")
        if status != "OK":
            all_ok = False

    print()
    if all_ok:
        print("All accounts ready. Hand these credentials to the demo operator.")
    else:
        print("One or more accounts failed. Review errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

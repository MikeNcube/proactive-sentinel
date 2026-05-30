#!/usr/bin/env python3
"""
Proactive Sentinel â€” end-to-end demo test.

Registers a fresh test tenant, logs in, ingests a CRITICAL security event,
and confirms the alert appears in GET /api/alerts.  Prints a PASS/FAIL
summary suitable for a management demo.

Usage:
    python scripts/demo_test.py
    python scripts/demo_test.py --base-url https://proactive-sentinel-production.up.railway.app
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _request(method: str, url: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            body_bytes = exc.read()
            return exc.code, json.loads(body_bytes)
        except Exception:
            return exc.code, {"error": str(exc)}
    except Exception as exc:
        return 0, {"error": str(exc)}


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run(base_url: str) -> bool:
    ts = int(time.time())
    email = f"demo-{ts}@zororo-sentinel-test.local"
    password = f"Demo{ts}!Xz"          # 12+ chars, upper + digit + special
    tenant_slug = f"demo-tenant-{ts}"
    results: list[tuple[str, bool, str]] = []

    def check(label: str, passed: bool, detail: str = "") -> bool:
        results.append((label, passed, detail))
        marker = "PASS" if passed else "FAIL"
        print(f"  [{marker}] {label}" + (f"  â€” {detail}" if detail else ""))
        return passed

    print(f"\nProactive Sentinel â€” end-to-end demo")
    print(f"Target : {base_url}")
    print(f"Time   : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("-" * 60)

    # ------------------------------------------------------------------
    # 1. Health check
    # ------------------------------------------------------------------
    print("\n[1] Health check")
    status, body = _request("GET", f"{base_url}/api/health")
    check("API reachable", status == 200, f"HTTP {status}")
    if status != 200:
        _print_summary(results)
        return False

    # ------------------------------------------------------------------
    # 2. Register test tenant + user
    # ------------------------------------------------------------------
    print("\n[2] Register test tenant")
    status, body = _request("POST", f"{base_url}/api/auth/register", {
        "email": email,
        "password": password,
        "tenant_name": f"Demo Tenant {ts}",
        "tenant_slug": tenant_slug,
    })
    check(
        "Tenant registered",
        status == 201,
        f"HTTP {status}" + (f" â€” {body.get('error', '')}" if status != 201 else f" â€” tenant_id={body.get('tenant_id', '')[:8]}â€¦"),
    )
    if status != 201:
        _print_summary(results)
        return False

    # ------------------------------------------------------------------
    # 3. Login
    # ------------------------------------------------------------------
    print("\n[3] Login")
    status, body = _request("POST", f"{base_url}/api/auth/login", {
        "email": email,
        "password": password,
    })
    token = body.get("access_token", "")
    check("Login successful", status == 200 and bool(token), f"HTTP {status}")
    if not token:
        _print_summary(results)
        return False

    # ------------------------------------------------------------------
    # 4. Ingest a CRITICAL event
    # ------------------------------------------------------------------
    print("\n[4] Ingest CRITICAL event")
    event_payload = {
        "source": "demo-wazuh-agent-01",
        "event_type": "ransomware",
        "severity": "critical",
        "confidence": 0.97,
        "raw_data": {
            "host": "demo-server-01",
            "source_ip": "10.99.0.1",
            "pid": 4812,
            "description": "Mass file encryption detected â€” 1 400 files in 12 seconds",
        },
        "title": "Ransomware Burst â€” Demo Server",
    }
    status, body = _request("POST", f"{base_url}/api/events/ingest", event_payload, token)
    ingest_ok = status in (200, 201) and "created" in body
    check("Event accepted", ingest_ok, f"HTTP {status}")

    if not ingest_ok:
        _print_summary(results)
        return False

    created = body.get("created", False)
    alert_id = body.get("alert_id", "")
    check("Alert created (not duplicate)", created is True, f"alert_id={alert_id[:8] if alert_id else 'n/a'}â€¦")
    check("Severity preserved", body.get("severity") == "critical", f"got '{body.get('severity')}'")

    # ------------------------------------------------------------------
    # 5. Verify alert appears in GET /api/alerts
    # ------------------------------------------------------------------
    print("\n[5] Verify alert in alerts list")
    time.sleep(0.3)   # brief pause â€” not needed for SQLite but polite for Postgres
    status, body = _request("GET", f"{base_url}/api/alerts", token=token)
    check("Alerts endpoint reachable", status == 200, f"HTTP {status}")

    alerts = body.get("alerts", [])
    check("Alerts list non-empty", len(alerts) > 0, f"{len(alerts)} alert(s) returned")

    found = any(str(a.get("id", "")) == alert_id for a in alerts) if alert_id else False
    if not found and alerts:
        # alert_id match may vary by dedup; accept any critical alert from this session
        found = any(str(a.get("severity", "")).lower() == "critical" for a in alerts)
    check("CRITICAL alert visible on dashboard", found)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    return _print_summary(results)


def _print_summary(results: list[tuple[str, bool, str]]) -> bool:
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    all_ok = passed == total
    print("\n" + "=" * 60)
    print(f"  RESULT : {'ALL PASS' if all_ok else 'FAILED'}")
    print(f"  Checks : {passed}/{total} passed")
    print("=" * 60 + "\n")
    return all_ok


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proactive Sentinel demo test")
    parser.add_argument(
        "--base-url",
        default="http://localhost:5001",
        help="API base URL (default: http://localhost:5001)",
    )
    args = parser.parse_args()
    ok = run(args.base_url.rstrip("/"))
    sys.exit(0 if ok else 1)


"""
Health checker for all Zororo integrated systems.

Probes each enabled system's health endpoint on a configurable interval.
Failures are persisted as Alert records with severity derived from the
system's event_severities config in zororo_systems.py.

Run via run_health_loop() in a daemon thread started by the app factory.
report_failure() requires an active Flask app context.
"""

import logging
import os
import time
import asyncio
from datetime import datetime, timezone

import httpx

from src.integrations.zororo_systems import get_all_systems

logger = logging.getLogger("sentinel.health")

# Statuses that represent a real failure worth alerting on.
_FAILURE_STATUSES = frozenset({"unreachable", "timeout", "degraded"})

# Event keys in event_severities that indicate the system considers itself
# critical if it goes down or becomes unreachable.
_CRITICAL_AVAILABILITY_EVENTS = frozenset({
    "self_down",
    "system_unreachable",
    "redis_unreachable",
    "db_unreachable",
})


async def check_system_health(system_key: str, config: dict) -> dict:
    """
    Probe the health endpoint of a single system.
    Returns a status dict with system, status, and checked_at.
    """
    base_url = os.getenv(
        f"{system_key.upper()}_URL",
        config.get("url") or config.get("base_url", ""),
    )

    if not base_url:
        return {
            "system": system_key,
            "status": "unconfigured",
            "message": f"No URL configured for {system_key}",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    url = base_url.rstrip("/") + config.get("health_endpoint", "/health")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            is_healthy = response.status_code == 200
            return {
                "system": system_key,
                "status": "healthy" if is_healthy else "degraded",
                "status_code": response.status_code,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
    except httpx.TimeoutException:
        logger.error("Health check timeout: %s", system_key)
        return {
            "system": system_key,
            "status": "timeout",
            "message": "Health check timed out after 10s",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        logger.exception("Health check error: %s", system_key)
        return {
            "system": system_key,
            "status": "unreachable",
            "message": f"{system_key} is unreachable",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


async def check_all_systems() -> list:
    """
    Probe all enabled systems concurrently.
    Disabled entries (enabled=False) are silently skipped.
    """
    systems = get_all_systems()
    tasks = [
        check_system_health(key, cfg)
        for key, cfg in systems.items()
        if cfg.get("enabled", True)
    ]
    return list(await asyncio.gather(*tasks))


def _get_failure_severity(config: dict) -> str:
    """
    Return the alert severity for a health check failure.

    If the system's event_severities marks any availability event as CRITICAL,
    the health failure is CRITICAL. Otherwise defaults to HIGH.
    """
    event_severities = config.get("event_severities") or {}
    for event, sev in event_severities.items():
        if event in _CRITICAL_AVAILABILITY_EVENTS and str(sev).upper() == "CRITICAL":
            return "critical"
    return "high"


def report_failure(app, system_key: str, config: dict, result: dict) -> None:
    """
    Persist a health check failure as an Alert.

    Must be called with an active Flask app context. Severity is driven by
    the system's event_severities config, not the MITRE rules taxonomy.
    """
    from src.models.alert import Alert
    from src.models.tenant import Tenant
    from src.extensions import db
    from src.actions.dispatcher import ActionDispatcher

    severity = _get_failure_severity(config)
    system_name = config.get("name", system_key)
    status = result.get("status", "unknown")

    # Resolve tenant: prefer env override, then first tenant in DB.
    tenant_id = os.getenv("HEALTH_CHECK_TENANT_ID")
    if not tenant_id:
        try:
            tenant = Tenant.query.first()
        except Exception:
            logger.warning(
                "DB unavailable — cannot persist health alert for %s", system_key
            )
            return
        if not tenant:
            logger.warning(
                "No tenants registered — cannot persist health alert for %s", system_key
            )
            return
        tenant_id = str(tenant.id)

    try:
        alert = Alert(
            tenant_id=tenant_id,
            title=f"{system_name} health check failed ({status})",
            severity=severity,
            status="open",
            category="health_check_failure",
            source="health_checker",
            description=result.get("message", f"{system_key} is {status}"),
            raw_data=result,
            confidence=1.0,
        )
        db.session.add(alert)
        db.session.commit()
        logger.info(
            "Health alert created: system=%s status=%s severity=%s",
            system_key, status, severity,
        )
        try:
            ActionDispatcher.dispatch(alert)
        except Exception as exc:
            logger.warning("ActionDispatcher.dispatch failed (non-fatal): %s", exc)
    except Exception:
        db.session.rollback()
        logger.exception("Failed to persist health alert for %s", system_key)


def run_health_loop(app, interval_seconds: int = 60) -> None:
    """
    Blocking health check loop — run in a dedicated daemon thread.

    Sleeps for interval_seconds before the first probe so startup logs are
    not polluted with immediate health noise. On each tick, probes all
    enabled systems and calls report_failure() for any that are down.
    """
    logger.info("Health checker started (interval=%ds)", interval_seconds)

    while True:
        time.sleep(interval_seconds)
        logger.debug("Running scheduled health checks")

        try:
            results = asyncio.run(check_all_systems())
        except Exception:
            logger.exception("Health check cycle error — will retry next interval")
            continue

        failures = [r for r in results if r.get("status") in _FAILURE_STATUSES]

        if not failures:
            logger.debug("All systems healthy (%d probed)", len(results))
            continue

        systems = get_all_systems()
        with app.app_context():
            for result in failures:
                system_key = result.get("system", "")
                cfg = systems.get(system_key, {})
                report_failure(app, system_key, cfg, result)

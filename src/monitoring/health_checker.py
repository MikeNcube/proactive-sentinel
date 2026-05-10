"""
Health checker for all Zororo integrated systems.
Runs on a schedule and reports status to the dashboard.
Alerts are raised when any system goes down or degrades.
"""

import logging
import os
from datetime import datetime, timezone

import httpx

from src.integrations.zororo_systems import get_all_systems

logger = logging.getLogger("sentinel.health")


async def check_system_health(system_key: str, config: dict) -> dict:
    """
    Checks the health of a single integrated system.
    Returns a health status dict with timestamp and details.
    """
    base_url = os.getenv(f"{system_key.upper()}_URL", config.get("base_url", ""))

    if not base_url:
        return {
            "system": system_key,
            "status": "unconfigured",
            "message": f"URL not set for {system_key}",
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
        logger.error("Health check timeout for %s", system_key)
        return {
            "system": system_key,
            "status": "timeout",
            "message": "Health check timed out after 10 seconds",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        logger.exception("Health check failed for %s", system_key)
        return {
            "system": system_key,
            "status": "unreachable",
            "message": "System is unreachable",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


async def check_all_systems() -> list:
    """
    Checks health of all registered Zororo systems.
    Returns list of health status dicts.
    Used by dashboard and alerting engine.
    """
    systems = get_all_systems()
    results = []
    for key, config in systems.items():
        result = await check_system_health(key, config)
        results.append(result)
    return results

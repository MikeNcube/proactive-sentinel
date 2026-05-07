"""
Zororo Systems Integration Registry.
Defines all systems that Proactive Sentinel monitors.
Add new systems here to bring them under protection.
Each system must define its health check endpoint,
authentication method, and alert thresholds.
"""

"""
Static baseline registry. All keys here are built-in and cannot be
overwritten via the runtime API. Runtime additions are stored in the
integrations DB table and merged in by get_all_systems().
"""

ZORORO_SYSTEMS = {
    "zororo_claims": {
        "name": "Zororo Claims System",
        "description": "Funeral claims operations platform",
        "url": "",
        "webhook_secret": "",
        "health_endpoint": "/api/health",
        "auth_type": "bearer",
        "monitor_endpoints": [
            "/api/cases",
            "/api/documents",
            "/api/finance/approved-claims",
        ],
        "alert_thresholds": {
            "response_time_ms": 3000,
            "error_rate_percent": 5,
            "failed_logins_per_hour": 10,
        },
        "pii_fields": [
            "deceasedIdNumber",
            "bankAccount",
            "phoneNumber",
            "email",
        ],
        "compliance_requirements": ["POPIA", "financial_data_protection"],
        "enabled": True,
        "builtin": True,
    },
    "ai_social_agent": {
        "name": "AI Social Agent",
        "description": "LinkedIn and social media automation",
        "url": "",
        "webhook_secret": "",
        "health_endpoint": "/health",
        "auth_type": "api_key",
        "monitor_endpoints": ["/api/v2/drafts", "/api/v2/publish"],
        "alert_thresholds": {
            "response_time_ms": 5000,
            "error_rate_percent": 10,
            "failed_publishes_per_hour": 5,
        },
        "pii_fields": ["linkedin_token", "access_token"],
        "compliance_requirements": ["social_media_policy"],
        "enabled": True,
        "builtin": True,
    },
    "proactive_sentinel": {
        "name": "Proactive Sentinel (self)",
        "description": "Security monitoring platform",
        "url": "",
        "webhook_secret": "",
        "health_endpoint": "/health",
        "auth_type": "internal",
        "monitor_endpoints": [],
        "alert_thresholds": {},
        "pii_fields": [],
        "compliance_requirements": ["cybersecurity_policy"],
        "enabled": True,
        "builtin": True,
    },
}


def get_system(system_key: str) -> dict | None:
    """Return config for a named system (static + DB), or None."""
    if system_key in ZORORO_SYSTEMS:
        return ZORORO_SYSTEMS[system_key]
    try:
        from src.models.integration import Integration
        row = Integration.query.get(system_key)
        return row.to_dict() if row else None
    except Exception:
        return None


def get_all_systems() -> dict:
    """
    Return all registered systems: static built-ins merged with DB entries.
    DB entries do not overwrite built-ins.
    """
    result = dict(ZORORO_SYSTEMS)
    try:
        from src.models.integration import Integration
        for row in Integration.query.filter_by(enabled=True).all():
            if row.key not in result:
                result[row.key] = row.to_dict()
    except Exception:
        pass
    return result

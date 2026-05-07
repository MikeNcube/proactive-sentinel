"""
Zororo Systems Integration Registry.
Defines all systems that Proactive Sentinel monitors.
Add new systems here to bring them under protection.
Each system must define its health check endpoint,
authentication method, and alert thresholds.
"""

ZORORO_SYSTEMS = {
    "zororo_claims": {
        "name": "Zororo Claims System",
        "description": "Funeral claims operations platform",
        "base_url": "",
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
        "compliance_requirements": [
            "POPIA",
            "financial_data_protection",
        ],
    },
    "ai_social_agent": {
        "name": "AI Social Agent",
        "description": "LinkedIn and social media automation",
        "base_url": "",
        "health_endpoint": "/health",
        "auth_type": "api_key",
        "monitor_endpoints": [
            "/api/v2/drafts",
            "/api/v2/publish",
        ],
        "alert_thresholds": {
            "response_time_ms": 5000,
            "error_rate_percent": 10,
            "failed_publishes_per_hour": 5,
        },
        "pii_fields": [
            "linkedin_token",
            "access_token",
        ],
        "compliance_requirements": [
            "social_media_policy",
        ],
    },
    "proactive_sentinel": {
        "name": "Proactive Sentinel (self)",
        "description": "Security monitoring platform",
        "base_url": "",
        "health_endpoint": "/health",
        "auth_type": "internal",
        "monitor_endpoints": [],
        "alert_thresholds": {},
        "pii_fields": [],
        "compliance_requirements": ["cybersecurity_policy"],
    },
}


def get_system(system_key: str) -> dict:
    """
    Returns the integration config for a named system.
    Returns None if system is not registered.
    """
    return ZORORO_SYSTEMS.get(system_key)


def get_all_systems() -> dict:
    """
    Returns all registered systems.
    Used by monitoring scheduler and dashboard.
    """
    return ZORORO_SYSTEMS

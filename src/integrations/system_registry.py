"""
System Integration Registry.

Static baseline registry of all systems that Proactive Sentinel monitors.
Built-in keys defined here cannot be overwritten via the runtime API.
Runtime additions are stored in the integrations DB table and merged in
by get_all_systems().

Schema notes:
  monitor_events   - semantic event names this system is expected to emit.
  event_severities - alert level to assign when a named event is detected.
  status           - "active" (default) or "pending-authority".
  enabled          - False entries appear in the dashboard as planned but
                     inactive; no probes or alerts are generated for them.
"""

import os

BUILTIN_SYSTEMS = {
    # --- AI orchestration platform ---
    "ai_orchestrator": {
        "name": "AI Orchestration Platform",
        "description": "AI-augmented SOC pipeline, MCP gateway, and audit chain",
        "url": os.getenv("AI_ORCHESTRATOR_URL", "http://localhost:8000"),
        "webhook_secret": "",
        "health_endpoint": "/health",
        "auth_type": "bearer",
        "monitor_endpoints": [
            "/api/pipeline/evaluate",
            "/api/audit/records",
        ],
        "monitor_events": [
            "soc_pipeline_event",
            "audit_chain_integrity",
            "mcp_gateway_dispatch",
            "test_failure",
        ],
        "alert_thresholds": {
            "response_time_ms": 2000,
            "error_rate_percent": 5,
        },
        "event_severities": {
            "pipeline_failure": "HIGH",
            "audit_chain_break": "CRITICAL",
            "test_failure": "HIGH",
        },
        "pii_fields": [],
        "compliance_requirements": ["POPIA", "cybersecurity_policy"],
        "status": "active",
        "enabled": True,
        "builtin": True,
    },

    # --- Claims platform ---
    "claims_platform": {
        "name": "Claims Platform",
        "description": "Insurance claims operations platform",
        "url": os.getenv("CLAIMS_PLATFORM_URL", ""),
        "webhook_secret": "",
        "health_endpoint": "/api/health",
        "auth_type": "bearer",
        "monitor_endpoints": [
            "/api/cases",
            "/api/documents",
            "/api/finance/approved-claims",
        ],
        "monitor_events": [
            "claim_submission",
            "claim_override",
            "failed_login",
            "bulk_export",
        ],
        "alert_thresholds": {
            "response_time_ms": 3000,
            "error_rate_percent": 5,
            "failed_logins_per_hour": 10,
            "override_count_per_hour": 5,
            "bulk_export_records_threshold": 100,
        },
        "event_severities": {
            "failed_login": "MEDIUM",
            "override_abuse": "HIGH",
            "claim_submission_anomaly": "HIGH",
            "bulk_export": "CRITICAL",
        },
        "pii_fields": [
            "idNumber",
            "bankAccount",
            "phoneNumber",
            "email",
        ],
        "compliance_requirements": ["POPIA", "financial_data_protection"],
        "status": "active",
        "enabled": True,
        "builtin": True,
    },

    # --- Proactive Sentinel (self) ---
    "proactive_sentinel": {
        "name": "Proactive Sentinel (self)",
        "description": "Security monitoring platform - self-monitoring entry",
        "url": "http://localhost:5000",
        "webhook_secret": "",
        "health_endpoint": "/health",
        "auth_type": "internal",
        "monitor_endpoints": [
            "/health",
        ],
        "monitor_events": [
            "self_health",
            "redis_connectivity",
            "db_connectivity",
        ],
        "alert_thresholds": {
            "response_time_ms": 1000,
            "error_rate_percent": 1,
        },
        "event_severities": {
            "self_down": "CRITICAL",
            "redis_unreachable": "CRITICAL",
            "db_unreachable": "CRITICAL",
        },
        "pii_fields": [],
        "compliance_requirements": ["cybersecurity_policy"],
        "status": "active",
        "enabled": True,
        "builtin": True,
    },

    # --- AI Social Agent ---
    "ai_social_agent": {
        "name": "AI Social Agent",
        "description": "LinkedIn and social media automation",
        "url": "",
        "webhook_secret": "",
        "health_endpoint": "/health",
        "auth_type": "api_key",
        "monitor_endpoints": ["/api/v2/drafts", "/api/v2/publish"],
        "monitor_events": [],
        "alert_thresholds": {
            "response_time_ms": 5000,
            "error_rate_percent": 10,
            "failed_publishes_per_hour": 5,
        },
        "event_severities": {},
        "pii_fields": ["linkedin_token", "access_token"],
        "compliance_requirements": ["social_media_policy"],
        "status": "active",
        "enabled": True,
        "builtin": True,
    },

}


def get_system(system_key: str) -> dict | None:
    """Return config for a named system (static + DB), or None."""
    if system_key in BUILTIN_SYSTEMS:
        return BUILTIN_SYSTEMS[system_key]
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
    result = dict(BUILTIN_SYSTEMS)
    try:
        from src.models.integration import Integration
        for row in Integration.query.filter_by(enabled=True).all():
            if row.key not in result:
                result[row.key] = row.to_dict()
    except Exception:
        pass
    return result


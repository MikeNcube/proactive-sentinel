"""
Zororo Systems Integration Registry.

Static baseline registry of all systems that Proactive Sentinel monitors.
Built-in keys defined here cannot be overwritten via the runtime API.
Runtime additions are stored in the integrations DB table and merged in
by get_all_systems().

Schema notes:
  monitor_events   â€” semantic event names this system is expected to emit.
  event_severities â€” alert level to assign when a named event is detected.
  status           â€” "active" (default) or "pending-authority".
  enabled          â€” False entries appear in the dashboard as planned but
                     inactive; no probes or alerts are generated for them.
"""

ZORORO_SYSTEMS = {
    # â”€â”€ Zororo AI OS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "zororo_ai_os": {
        "name": "Zororo AI OS",
        "description": "AI-augmented SOC pipeline, MCP gateway, and audit chain",
        "url": "http://localhost:8000",
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

    # â”€â”€ Zororo Claims â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "zororo_claims": {
        "name": "Zororo Claims System",
        "description": "Funeral claims operations platform",
        "url": "https://zororo-claims.railway.app",  # confirm URL before go-live
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
            "deceasedIdNumber",
            "bankAccount",
            "phoneNumber",
            "email",
        ],
        "compliance_requirements": ["POPIA", "financial_data_protection"],
        "status": "active",
        "enabled": True,
        "builtin": True,
    },

    # â”€â”€ Proactive Sentinel (self) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "proactive_sentinel": {
        "name": "Proactive Sentinel (self)",
        "description": "Security monitoring platform â€” self-monitoring entry",
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

    # â”€â”€ AI Social Agent â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ IT Manager Systems (placeholder) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Integration designed and reserved. Activation requires IT manager to
    # grant access approval. No probes, webhooks, or alerts are generated
    # while enabled=False.
    "it_manager_systems": {
        "name": "IT Manager Systems",
        "description": "IT manager's systems â€” reserved for future integration",
        "url": "",
        "webhook_secret": "",
        "health_endpoint": "",
        "auth_type": "pending",
        "monitor_endpoints": [],
        "monitor_events": [],
        "alert_thresholds": {},
        "event_severities": {},
        "pii_fields": [],
        "compliance_requirements": [],
        "status": "pending-authority",
        "note": "Integration deferred until IT manager grants access approval",
        "enabled": False,
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


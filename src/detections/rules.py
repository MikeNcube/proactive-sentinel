"""
Severity classification rules for the Proactive Sentinel detection engine.

Severity is determined by event_type, not by the sender's claimed severity.
This prevents severity spoofing by compromised or misconfigured sources.
"""
from typing import Dict, Set

SEVERITY_RULES: Dict[str, Set[str]] = {
    "critical": {
        "credential_exposure",
        "data_exfiltration",
        "ransomware",
        "unauthorized_admin_access",
        "bulk_data_export",
        "api_key_exposed",
    },
    "high": {
        "login_anomaly",
        "override_abuse",
        "suspicious_claim_pattern",
        "rate_limit_breach",
        "failed_auth_burst",
    },
    "medium": {
        "unusual_navigation",
        "slow_response_pattern",
        "single_failed_login",
    },
}


def classify_severity(event_type: str) -> str:
    """
    Map an event_type to its canonical severity.

    Returns "low" for event types not covered by the ruleset.
    The lookup is case-insensitive.
    """
    key = str(event_type or "").lower().strip()
    for severity, event_types in SEVERITY_RULES.items():
        if key in event_types:
            return severity
    return "low"


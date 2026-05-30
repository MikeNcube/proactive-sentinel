"""
Alert correlation and deduplication engine.
"""

from collections import defaultdict
from typing import Dict, List
import hashlib
import json

from src.extensions import get_redis


class CorrelationEngine:
    """Deduplicate and correlate related alerts."""

    def __init__(self, time_window_seconds: int = 300):
        self.time_window = time_window_seconds
        self.redis = get_redis()

    def get_fingerprint(self, alert_data: Dict) -> str:
        """Generate unique fingerprint for alert deduplication."""
        signature_fields = {
            "tenant_id": alert_data.get("tenant_id"),
            "category": alert_data.get("category"),
            "source": alert_data.get("source"),
            "host": alert_data.get("host"),
        }
        signature = {k: v for k, v in signature_fields.items() if v}
        key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
        return f"alert:dedup:{key}"

    def should_alert(self, alert_data: Dict) -> bool:
        """Check if alert should be created or suppressed."""
        fingerprint = self.get_fingerprint(alert_data)
        existing = self.redis.get(fingerprint)

        if existing:
            return False

        pipe = self.redis.pipeline()
        pipe.incr(fingerprint)
        pipe.expire(fingerprint, self.time_window)
        pipe.execute()
        return True

    def correlate_attack_chain(self, alerts: List[Dict]) -> List[Dict]:
        """Group alerts into potential attack chains by source/user."""
        chains = defaultdict(list)

        for alert in alerts:
            key = alert.get("source_ip") or alert.get("user_id")
            if key:
                chains[key].append(alert)

        attack_chains = []
        mitre_sequence = {
            "reconnaissance": ["T1046", "T1592", "T1526"],
            "initial_access": ["T1078", "T1133", "T1199"],
            "execution": ["T1059", "T1204"],
            "persistence": ["T1098", "T1136"],
            "lateral_movement": ["T1021", "T1570"],
            "exfiltration": ["T1020", "T1048"],
        }

        for key, chain_alerts in chains.items():
            if len(chain_alerts) < 3:
                continue

            techniques = set()
            for alert in chain_alerts:
                techniques.update(alert.get("mitre_techniques", []))

            stages_detected = []
            for stage, techs in mitre_sequence.items():
                if any(t in techniques for t in techs):
                    stages_detected.append(stage)

            if len(stages_detected) >= 2:
                attack_chains.append(
                    {
                        "key": key,
                        "stages": stages_detected,
                        "confidence": min(0.95, 0.6 + (len(stages_detected) * 0.1)),
                        "alerts": chain_alerts,
                        "severity": "critical" if len(stages_detected) >= 3 else "high",
                    }
                )

        return attack_chains


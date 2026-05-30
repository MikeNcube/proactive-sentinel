import ipaddress
import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class ThreatDetector:
    """Simple proactive threat detector with in-memory state."""

    def __init__(self):
        self.blocked_ips: set[str] = set()
        self.violations: Dict[str, int] = defaultdict(int)
        self.request_windows: Dict[str, Deque[float]] = defaultdict(deque)
        self.unit_request_windows: Dict[str, Deque[float]] = defaultdict(deque)
        self.quarantined_units: set[str] = set()
        self.known_bad_ips = {
            ip.strip()
            for ip in os.environ.get("KNOWN_BAD_IPS", "").split(",")
            if ip.strip()
        }

    def _normalize_ip(self, ip: str) -> str:
        try:
            return str(ipaddress.ip_address(ip))
        except Exception:
            return ip or "unknown"

    def evaluate_request_velocity(self, ip: str, now: float | None = None) -> dict[str, object]:
        """Block after >20 requests per 10 seconds from one IP."""
        now = now or time.time()
        ip = self._normalize_ip(ip)
        window = self.request_windows[ip]
        window.append(now)
        while window and now - window[0] > 10:
            window.popleft()
        if len(window) > 20:
            return self.register_violation(ip, "velocity_exceeded")
        return {"allowed": True}

    def evaluate_unit_velocity(self, unit_id: str, now: float | None = None) -> dict[str, object]:
        """
        Flag unit compromise if a single unit sends too many events quickly,
        regardless of source IP.
        """
        now = now or time.time()
        if not unit_id:
            return {"allowed": True}

        window = self.unit_request_windows[unit_id]
        window.append(now)
        while window and now - window[0] > 10:
            window.popleft()

        if unit_id in self.quarantined_units:
            return {"allowed": False, "reason": "unit_quarantined", "unit_compromised": True}

        if len(window) > 20:
            self.quarantined_units.add(unit_id)
            return {
                "allowed": False,
                "reason": "unit_compromise_velocity_exceeded",
                "unit_compromised": True,
            }
        return {"allowed": True}

    def evaluate_ip_reputation(self, ip: str) -> dict[str, object]:
        ip = self._normalize_ip(ip)
        if ip in self.known_bad_ips or ip in self.blocked_ips:
            return {"allowed": False, "reason": "blocked_ip"}
        return {"allowed": True}

    def register_violation(self, ip: str, reason: str) -> dict[str, object]:
        ip = self._normalize_ip(ip)
        self.violations[ip] += 1
        if self.violations[ip] >= 3:
            self.blocked_ips.add(ip)
            return {"allowed": False, "reason": f"auto_ban:{reason}", "banned": True}
        return {"allowed": False, "reason": reason, "banned": False}



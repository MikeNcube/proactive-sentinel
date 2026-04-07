from typing import Dict, List


class UXObserver:
    """Detect UX pain points from operational and conversation logs."""

    FRUSTRATION_KEYWORDS = ("human", "help")
    SOCIAL_OUTCRY_THRESHOLD = 3
    LEAD_LEAKAGE_THRESHOLD = 5
    ZENDESK_WAIT_THRESHOLD_MINUTES = 5

    @staticmethod
    def detect_slow_claims(logs: List[Dict]) -> List[Dict]:
        alerts: List[Dict] = []
        for log in logs:
            if not isinstance(log, dict):
                continue
            processing_time = log.get("processing_time")
            if isinstance(processing_time, (int, float)) and processing_time > 2.0:
                user = log.get("user", log.get("user_id", "unknown"))
                alerts.append(
                    {
                        "severity": "MEDIUM",
                        "type": "IMPROVEMENT",
                        "user": user,
                        "status": "Pending Agent Review",
                        "description": (
                            f"Slow Claims detected: processing_time={processing_time:.2f}s "
                            "(threshold > 2.0s)."
                        ),
                    }
                )
        return alerts

    @staticmethod
    def detect_whatsapp_frustration(logs: List[Dict]) -> List[Dict]:
        alerts: List[Dict] = []
        for log in logs:
            if not isinstance(log, dict):
                continue
            channel = str(log.get("channel", "")).lower()
            if channel != "whatsapp":
                continue

            message = str(log.get("message", "")).lower()
            repeats = sum(message.count(keyword) for keyword in UXObserver.FRUSTRATION_KEYWORDS)
            if repeats >= 2:
                user = log.get("user", log.get("user_id", "unknown"))
                alerts.append(
                    {
                        "severity": "HIGH",
                        "type": "IMPROVEMENT",
                        "user": user,
                        "status": "Pending Agent Review",
                        "description": (
                            "WhatsApp Frustration detected: repeated requests for "
                            "'human/help'."
                        ),
                    }
                )
        return alerts

    @staticmethod
    def detect_web_errors(logs: List[Dict]) -> List[Dict]:
        alerts: List[Dict] = []
        for log in logs:
            if not isinstance(log, dict):
                continue
            status_code = log.get("status_code")
            if status_code in (404, 500):
                user = log.get("user", log.get("user_id", "unknown"))
                alerts.append(
                    {
                        "severity": "HIGH" if status_code == 500 else "MEDIUM",
                        "type": "IMPROVEMENT",
                        "user": user,
                        "status": "Pending Agent Review",
                        "description": f"Web Errors detected: HTTP {status_code} observed.",
                    }
                )
        return alerts

    @staticmethod
    def detect_social_outcry(logs: List[Dict]) -> List[Dict]:
        alerts: List[Dict] = []
        negative_count = 0
        monitored_channels = {"facebook", "x"}

        for log in logs:
            if not isinstance(log, dict):
                continue
            channel = str(log.get("channel", "")).lower()
            if channel not in monitored_channels:
                continue

            sentiment = str(log.get("sentiment", "")).lower()
            score = log.get("sentiment_score")
            is_negative = sentiment == "negative" or (
                isinstance(score, (int, float)) and score < 0
            )
            if is_negative:
                negative_count += 1

        if negative_count > UXObserver.SOCIAL_OUTCRY_THRESHOLD:
            alerts.append(
                {
                    "severity": "HIGH",
                    "type": "IMPROVEMENT",
                    "user": "public-channel",
                    "status": "Pending Agent Review",
                    "description": (
                        "Social Outcry detected: negative sentiment on Facebook/X "
                        f"exceeded threshold ({negative_count} > "
                        f"{UXObserver.SOCIAL_OUTCRY_THRESHOLD})."
                    ),
                }
            )
        return alerts

    @staticmethod
    def detect_lead_leakage(crm_logs: List[Dict]) -> List[Dict]:
        alerts: List[Dict] = []
        incomplete_total = 0

        for log in crm_logs:
            if not isinstance(log, dict):
                continue
            if str(log.get("metric", "")).lower() == "incomplete applications":
                value = log.get("count", 0)
                if isinstance(value, int):
                    incomplete_total += value
                elif isinstance(value, float):
                    incomplete_total += int(value)
                else:
                    incomplete_total += 1

        if incomplete_total > UXObserver.LEAD_LEAKAGE_THRESHOLD:
            alerts.append(
                {
                    "severity": "HIGH",
                    "type": "IMPROVEMENT",
                    "user": "crm-funnel",
                    "status": "Pending Agent Review",
                    "description": (
                        "Lead Leakage detected: 'Incomplete Applications' spiked "
                        f"({incomplete_total} > {UXObserver.LEAD_LEAKAGE_THRESHOLD})."
                    ),
                }
            )
        return alerts

    @staticmethod
    def detect_zendesk_latency(logs: List[Dict]) -> List[Dict]:
        alerts: List[Dict] = []
        for log in logs:
            if not isinstance(log, dict):
                continue
            platform = str(log.get("platform", "")).lower()
            if platform != "zendesk":
                continue

            wait_time = log.get("wait_time_minutes")
            if isinstance(wait_time, (int, float)) and wait_time > UXObserver.ZENDESK_WAIT_THRESHOLD_MINUTES:
                user = log.get("user", log.get("user_id", "unknown"))
                alerts.append(
                    {
                        "severity": "MEDIUM",
                        "type": "IMPROVEMENT",
                        "user": user,
                        "status": "Pending Agent Review",
                        "description": (
                            "Zendesk Latency detected: wait time exceeded 5 minutes "
                            f"({wait_time:.1f}m)."
                        ),
                    }
                )
        return alerts

    @staticmethod
    def detect(logs: List[Dict]) -> List[Dict]:
        alerts: List[Dict] = []
        alerts.extend(UXObserver.detect_slow_claims(logs))
        alerts.extend(UXObserver.detect_whatsapp_frustration(logs))
        alerts.extend(UXObserver.detect_web_errors(logs))
        alerts.extend(UXObserver.detect_social_outcry(logs))
        alerts.extend(UXObserver.detect_zendesk_latency(logs))
        alerts.extend(UXObserver.detect_lead_leakage(logs))
        return alerts

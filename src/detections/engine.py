from typing import Dict, Optional

from src.detections.correlation_engine import CorrelationEngine
from src.models.alert import Alert


class DetectionEngine:
    def __init__(self):
        self.correlation = CorrelationEngine()

    def process_alert(self, alert_data: Dict) -> Optional[Dict]:
        # Check deduplication
        if not self.correlation.should_alert(alert_data):
            return None

        # Create alert
        valid_fields = {c.name for c in Alert.__table__.columns}
        clean_data = {k: v for k, v in alert_data.items() if k in valid_fields}
        alert = Alert(**clean_data)
        return alert

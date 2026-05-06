from typing import List, Dict
from utils import VRLFilter, ResponseSimulator

class DetectionEngine:
    def __init__(self):
        self.alerts = []
        self.SPIKE_THRESHOLD = 0

    def detect(self, logs: List[Dict]) -> List[Dict]:
        self.alerts = []
        # Ensure we are working with a list
        if not isinstance(logs, list):
            logs = [logs]
            
        # 1. Mask PII first for compliance
        masked_logs = VRLFilter.mask_pii(logs)
        
        # 2. Run different detection modules
        self.alerts.extend(self._detect_spike(masked_logs))
        
        return self.alerts

    def _detect_spike(self, logs: List[Dict]) -> List[Dict]:
        alerts = []
        access_counts = {}
        
        for log in logs:
            # Defensive check: skip if log isn't a dictionary
            if not isinstance(log, dict): continue
            
            user = log.get('user_id', 'unknown')
            event_type = log.get('event_type', '')
            
            if event_type == 'file_access':
                access_counts[user] = access_counts.get(user, 0) + 1
                
                if access_counts[user] > self.SPIKE_THRESHOLD:
                    alerts.append({
                        'severity': 'HIGH',
                        'type': 'Data Access Spike',
                        'user': user,
                        'description': f'User {user} accessed multiple files rapidly.'
                    })
                    ResponseSimulator.isolate_user(user)
        return alerts

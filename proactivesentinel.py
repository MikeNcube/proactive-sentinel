#!/usr/bin/env python3

from datetime import datetime
import json
import re
from typing import Dict, List
from utils import VRLFilter
from detections.detection_engine import DetectionEngine

class ProactiveSentinel:
    def __init__(self):
        self.logs: List[Dict] = []
        self.detection_engine = DetectionEngine()

    def ingest_logs(self, log_dir: str = "./logs") -> None:
        """Read and process JSON logs from directory with PII masking"""
        for filename in os.listdir(log_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(log_dir, filename)
                with open(filepath, 'r') as f:
                    try:
                        log_data = f.read()
                        log_entry = json.loads(log_data)
                        masked_log = VRLFilter.mask_pii(log_entry)
                        self.logs.append(masked_log)
                    except json.JSONDecodeError as e:
                        print(f'Log parsing error in {filename}: {e}')

    def run_detection(self) -> List[Dict]:
        """Process logs through detection engine"""
        return self.detection_engine.detect(self.logs)
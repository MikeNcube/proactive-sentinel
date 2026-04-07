#!/usr/bin/env python3

from datetime import datetime
import json
from typing import List, Dict
from proactivesentinel import ProactiveSentinel

def display_alerts(alerts: List[Dict]) -> None:
    """Display alerts in CLI format"""
    print(f"\n\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\n{datetime.now().isoformat()}\n\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\n")
    for alert in alerts:
        print(f"Severity: {alert['severity'].upper()}")
        print(f"Type: {alert['type']}")
        print(f"Confidence: {alert['confidence']:.2f}\n")
        print(f"Description: {alert['description']}\n")
    print("\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\n")

if __name__ == "__main__":
    sentinel = ProactiveSentinel()
    alerts = sentinel.run_detection()
    display_alerts(alerts)
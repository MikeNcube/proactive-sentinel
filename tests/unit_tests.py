import unittest
from detections.detection_engine import DetectionEngine
from utils import VRLFilter
from proactivesentinel import ProactiveSentinel
import json

class TestProactiveSentinel(unittest.TestCase):
    def setUp(self):
        self.sentinel = ProactiveSentinel()
        self.engine = DetectionEngine()

    def test_vrl_masking(self):
        """Test PII masking functionality"""
        test_log = {"id": "1234567890123", "phone": "0712345678"}
        masked = VRLFilter.mask_pii(test_log)
        self.assertEqual(masked['id'], 'XXX-XXX-XXX-XXX-XXX')
        self.assertEqual(masked['phone'], 'XXX-XXX-XXX-XXX')

    def test_detection_engine(self):
        """Test detection rules"""
        # Test spike detection
        spike_logs = [{
            'user_id': 'user_001',
            'event_type': 'file_access',
            'file_path': '/documents/report.pdf'
        }] * 6  # Exceeds SPIKE_THRESHOLD=5
        alerts = self.engine.detect(spike_logs)
        self.assertTrue(any(a['type'] == 'Data Access Spike' for a in alerts))

    def test_ai_classification(self):
        """Test AI threat classification"""
        ai_log = {"description": "Potential ransomware activity detected"}
        alerts = self.engine._ai_classify_threat([ai_log])
        self.assertTrue(any(a['type'] == 'AI-Classified Threat' for a in alerts))

    def test_full_pipeline(self):
        """Test complete workflow"""
        # Load sample logs
        with open('logs/sample.json', 'r') as f:
            logs = json.load(f)
        # Run detection
        alerts = self.sentinel.run_detection(logs)
        # Verify alerts
        self.assertTrue(len(alerts) > 0)
        # Check response simulation
        self.assertTrue(any('isolate_user' in str(a) for a in alerts))

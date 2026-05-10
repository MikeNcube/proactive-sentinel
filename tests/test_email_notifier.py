"""
Tests for src/notifications/email_notifier.py

All SMTP calls are mocked — no live mail server required.
"""

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.notifications.email_notifier import _mask_ip, send_alert_email


# ---------------------------------------------------------------------------
# Minimal alert stub — avoids needing a full DB-backed Alert object
# ---------------------------------------------------------------------------

class _FakeAlert:
    def __init__(self, severity="critical", raw_data=None):
        self.id = str(uuid.uuid4())
        self.title = "Test Alert"
        self.severity = severity
        self.category = "ransomware"
        self.status = "open"
        self.raw_data = raw_data or {}


# ---------------------------------------------------------------------------
# IP masking
# ---------------------------------------------------------------------------

class TestMaskIp:
    def test_standard_ipv4(self):
        assert _mask_ip("192.168.1.100") == "192.168.xxx.xxx"

    def test_rfc1918_address(self):
        assert _mask_ip("10.0.0.5") == "10.0.xxx.xxx"

    def test_non_ipv4_returns_generic_mask(self):
        assert _mask_ip("invalid") == "xxx.xxx.xxx.xxx"

    def test_empty_string_returns_generic_mask(self):
        assert _mask_ip("") == "xxx.xxx.xxx.xxx"


# ---------------------------------------------------------------------------
# send_alert_email: configuration guard
# ---------------------------------------------------------------------------

class TestSendAlertEmailConfig:
    def test_skipped_when_smtp_host_not_set(self):
        alert = _FakeAlert()
        env = {k: v for k, v in os.environ.items() if k != "SMTP_HOST"}
        with patch.dict(os.environ, env, clear=True):
            os.environ.pop("SMTP_HOST", None)
            result = send_alert_email(alert)
        assert result is False

    def test_skipped_when_recipients_empty(self):
        alert = _FakeAlert()
        env = {"SMTP_HOST": "smtp.example.com", "ALERT_EMAIL_RECIPIENTS": ""}
        with patch.dict(os.environ, env):
            result = send_alert_email(alert)
        assert result is False

    def test_skipped_when_recipients_not_set(self):
        alert = _FakeAlert()
        with patch.dict(os.environ, {"SMTP_HOST": "smtp.example.com"}, clear=False):
            os.environ.pop("ALERT_EMAIL_RECIPIENTS", None)
            result = send_alert_email(alert)
        assert result is False


# ---------------------------------------------------------------------------
# send_alert_email: successful send
# ---------------------------------------------------------------------------

class TestSendAlertEmailSend:
    _env = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "alert@example.com",
        "SMTP_PASSWORD": "s3cr3t",
        "SMTP_FROM": "alert@example.com",
        "ALERT_EMAIL_RECIPIENTS": "sec@example.com,it@example.com",
    }

    def test_send_succeeds_for_critical_alert(self):
        alert = _FakeAlert(severity="critical", raw_data={"source_ip": "10.1.2.3"})
        with patch.dict(os.environ, self._env):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_server = MagicMock()
                mock_smtp_cls.return_value.__enter__.return_value = mock_server
                result = send_alert_email(alert)
        assert result is True
        mock_server.send_message.assert_called_once()

    def test_send_succeeds_for_high_alert(self):
        alert = _FakeAlert(severity="high")
        with patch.dict(os.environ, self._env):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_server = MagicMock()
                mock_smtp_cls.return_value.__enter__.return_value = mock_server
                result = send_alert_email(alert)
        assert result is True

    def test_subject_contains_severity_and_title(self):
        alert = _FakeAlert(severity="critical")
        captured = {}
        with patch.dict(os.environ, self._env):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_server = MagicMock()
                mock_smtp_cls.return_value.__enter__.return_value = mock_server

                def capture(msg):
                    captured["msg"] = msg

                mock_server.send_message.side_effect = capture
                send_alert_email(alert)
        assert "[CRITICAL]" in captured["msg"]["Subject"]
        assert alert.title in captured["msg"]["Subject"]

    def test_never_crashes_on_smtp_error(self):
        alert = _FakeAlert(severity="critical")
        with patch.dict(os.environ, self._env):
            with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("SMTP down")):
                result = send_alert_email(alert)
        assert result is False

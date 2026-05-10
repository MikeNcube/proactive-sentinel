"""
Unit tests for credential masking in detections/vrl_filter.py.

Verifies that mask_text() detects and masks all seven credential patterns
and that MaskReport.pii_types_found reports them as CRED_* entries.
"""
from __future__ import annotations

import pytest

from detections.vrl_filter import mask_text


# ── AWS Access Key ID ─────────────────────────────────────────────────────

def test_aws_access_key_masked():
    text = "Configured key AKIAIOSFODNN7EXAMPLE here"
    masked, report = mask_text(text)
    assert "[REDACTED_CRED_AWS_ACCESS_KEY]" in masked
    assert "CRED_AWS_ACCESS_KEY" in report.pii_types_found
    assert "AKIAIOSFODNN7EXAMPLE" not in masked


def test_aws_access_key_not_false_positive_on_short_akia():
    # AKIA followed by fewer than 16 uppercase alphanumeric chars — must not match
    text = "AKIA123"
    masked, report = mask_text(text)
    assert "CRED_AWS_ACCESS_KEY" not in report.pii_types_found
    assert masked == "AKIA123"


# ── AWS Secret Access Key ─────────────────────────────────────────────────

def test_aws_secret_key_masked():
    text = "aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"
    masked, report = mask_text(text)
    assert "[REDACTED_CRED_AWS_SECRET_KEY]" in masked
    assert "CRED_AWS_SECRET_KEY" in report.pii_types_found
    assert "wJalrXUtnFEMI" not in masked


def test_aws_secret_key_case_insensitive():
    text = "AWS_SECRET='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"
    masked, report = mask_text(text)
    assert "CRED_AWS_SECRET_KEY" in report.pii_types_found


# ── Generic API Key ───────────────────────────────────────────────────────

def test_api_key_masked():
    text = "api_key=abcdefghij1234567890ABCDEF"
    masked, report = mask_text(text)
    assert "[REDACTED_CRED_API_KEY]" in masked
    assert "CRED_API_KEY" in report.pii_types_found
    assert "abcdefghij1234567890ABCDEF" not in masked


def test_apikey_no_separator_masked():
    text = 'apikey:"sk-prod-abc1234567890abcdef1234"'
    masked, report = mask_text(text)
    assert "CRED_API_KEY" in report.pii_types_found


def test_api_key_too_short_not_masked():
    # Value shorter than 20 chars should not trigger
    text = "api_key=short"
    masked, report = mask_text(text)
    assert "CRED_API_KEY" not in report.pii_types_found


# ── PEM Private Key ───────────────────────────────────────────────────────

def test_private_key_block_masked():
    text = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA2a2rwplBQLF29amygykEMmYz0+Kcj3bKBp29S00000000000\n"
        "-----END RSA PRIVATE KEY-----"
    )
    masked, report = mask_text(text)
    assert "[REDACTED_CRED_PRIVATE_KEY]" in masked
    assert "CRED_PRIVATE_KEY" in report.pii_types_found
    assert "MIIEowIBAAK" not in masked


def test_ec_private_key_block_masked():
    text = (
        "-----BEGIN EC PRIVATE KEY-----\n"
        "MHQCAQEEIOaRsLjI2R3NHSnQy/sVRtHNBgAm4sRBJJJMokRIklcJoAoGCCqGSM49\n"
        "-----END EC PRIVATE KEY-----"
    )
    masked, report = mask_text(text)
    assert "CRED_PRIVATE_KEY" in report.pii_types_found


# ── GitHub Token ──────────────────────────────────────────────────────────

def test_github_pat_masked():
    token = "ghp_" + "A" * 36
    text = f"export GH_TOKEN={token}"
    masked, report = mask_text(text)
    assert "[REDACTED_CRED_GITHUB_TOKEN]" in masked
    assert "CRED_GITHUB_TOKEN" in report.pii_types_found
    assert token not in masked


def test_github_oauth_token_masked():
    token = "gho_" + "b" * 36
    masked, report = mask_text(token)
    assert "CRED_GITHUB_TOKEN" in report.pii_types_found


def test_github_server_token_masked():
    token = "ghs_" + "C" * 30
    masked, report = mask_text(token)
    assert "CRED_GITHUB_TOKEN" in report.pii_types_found


# ── JWT Token ─────────────────────────────────────────────────────────────

def test_jwt_masked():
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiJ1c2VyXzAwMSIsImV4cCI6OTk5OTk5OTk5OX0"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    text = f"Authorization: Bearer {jwt}"
    masked, report = mask_text(text)
    assert "[REDACTED_CRED_JWT]" in masked
    assert "CRED_JWT" in report.pii_types_found
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked


# ── Plaintext Password ────────────────────────────────────────────────────

def test_password_masked():
    text = "password=Sup3rS3cr3tPass!"
    masked, report = mask_text(text)
    assert "[REDACTED_CRED_PASSWORD]" in masked
    assert "CRED_PASSWORD" in report.pii_types_found
    assert "Sup3rS3cr3tPass!" not in masked


def test_passwd_variant_masked():
    text = "passwd:hunter2password"
    masked, report = mask_text(text)
    assert "CRED_PASSWORD" in report.pii_types_found


def test_password_too_short_not_masked():
    # Fewer than 6 chars after separator — should not trigger
    text = "password=abc"
    masked, report = mask_text(text)
    assert "CRED_PASSWORD" not in report.pii_types_found


# ── Multi-credential and replacement count ────────────────────────────────

def test_multiple_credentials_all_masked():
    aws_key = "AKIAIOSFODNN7EXAMPLE"
    gh_token = "ghp_" + "X" * 36
    jwt = (
        "eyJhbGciOiJIUzI1NiJ9"
        ".eyJzdWIiOiJ1c2VyIn0"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    text = f"key={aws_key} token={gh_token} auth={jwt}"
    masked, report = mask_text(text)
    assert aws_key not in masked
    assert gh_token not in masked
    assert "eyJhbGciOiJIUzI1NiJ9" not in masked
    assert "CRED_AWS_ACCESS_KEY" in report.pii_types_found
    assert "CRED_GITHUB_TOKEN" in report.pii_types_found
    assert "CRED_JWT" in report.pii_types_found
    assert report.total_replacements >= 3


def test_clean_text_unchanged():
    text = "This log entry contains no credentials."
    masked, report = mask_text(text)
    assert masked == text
    assert report.total_replacements == 0
    cred_types = [t for t in report.pii_types_found if t.startswith("CRED_")]
    assert cred_types == []


def test_existing_pii_masking_still_works_alongside_credentials():
    sa_id = "9001015009087"
    aws_key = "AKIAIOSFODNN7EXAMPLE"
    text = f"id={sa_id} key={aws_key}"
    masked, report = mask_text(text)
    assert sa_id not in masked
    assert aws_key not in masked
    assert "SA_ID" in report.pii_types_found
    assert "CRED_AWS_ACCESS_KEY" in report.pii_types_found
    assert report.total_replacements >= 2

"""
Input validation helpers for Proactive Sentinel API.
All user input must pass through these validators
before reaching business logic or database.
"""

import re
from typing import Any


MAX_STRING_LENGTH = 1000
SAFE_STRING_PATTERN = re.compile(r"^[\w\s\-\.@]+$")


def validate_string(value: Any, field_name: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """
    Validates a string input field.
    Raises ValueError with a clear message if invalid.
    Returns the cleaned string if valid.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    cleaned = value.strip()
    if len(cleaned) == 0:
        raise ValueError(f"{field_name} cannot be empty")
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length}")
    return cleaned


def validate_email(value: Any) -> str:
    """
    Validates an email address format.
    Returns the cleaned email if valid.
    """
    email = validate_string(value, "email", max_length=254)
    pattern = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    if not pattern.match(email):
        raise ValueError("Invalid email address format")
    return email.lower()


def validate_tenant_id(value: Any) -> str:
    """
    Validates a tenant ID.
    Only alphanumeric and hyphens allowed.
    Prevents tenant isolation bypass attempts.
    """
    tenant_id = validate_string(value, "tenant_id", max_length=64)
    if not re.match(r"^[a-zA-Z0-9\-]+$", tenant_id):
        raise ValueError("Tenant ID contains invalid characters")
    return tenant_id


def validate_uuid_string(value: Any, field_name: str) -> str:
    """Validates UUID-like string format."""
    candidate = validate_string(value, field_name, max_length=64)
    if not re.match(r"^[a-fA-F0-9\-]{8,64}$", candidate):
        raise ValueError(f"{field_name} contains invalid characters")
    return candidate

import re
from typing import Any
from dataclasses import dataclass

# â”€â”€ Credential detection patterns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each pattern targets a self-identifying or labeled credential form.

_CRED_AWS_KEY_RE = re.compile(r"\bAKIA[A-Z0-9]{16}\b")

_CRED_AWS_SECRET_RE = re.compile(
    r"(?i)(?:aws.{0,15}secret|secret.{0,10}access.{0,10}key)\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"
)

_CRED_API_KEY_RE = re.compile(
    r"(?i)(?:api[-_]?key|apikey)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,64}"
)

_CRED_PRIVKEY_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?"
    r"-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
)

_CRED_GITHUB_RE = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")

_CRED_JWT_RE = re.compile(
    r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"
)

_CRED_PASSWORD_RE = re.compile(
    r"(?i)(?:password|passwd|pwd)\s*[=:]\s*[^\s'\"]{6,}"
)


class VRLFilter:
    """Enterprise-grade PII masking utility."""

    PII_MASKING_ENABLED = True

    IDENTITY_KEYS = {
        "id",
        "user_id",
        "identity",
        "identity_number",
        "id_number",
        "national_id",
        "sa_id",
        "passport",
        "passport_no",
        "passport_number",
        "zim_passport",
    }

    SA_ID_RE = re.compile(r"\b\d{13}\b")
    PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}[0-9]{6,9}\b", re.IGNORECASE)

    @staticmethod
    def _partial_mask(value: str) -> str:
        """Mask all characters except the first two and last two."""
        cleaned = re.sub(r"\s+", "", value)
        if len(cleaned) <= 4:
            return "*" * len(cleaned)
        return f"{cleaned[:2]}{'*' * (len(cleaned) - 4)}{cleaned[-2:]}"

    @staticmethod
    def _mask_identity_value(value: Any) -> Any:
        """Apply SA ID and passport masking patterns to a value."""
        if value is None:
            return value
        text = str(value)
        text = VRLFilter.SA_ID_RE.sub(lambda m: VRLFilter._partial_mask(m.group(0)), text)
        text = VRLFilter.PASSPORT_RE.sub(lambda m: VRLFilter._partial_mask(m.group(0)), text)
        return text

    @staticmethod
    def mask_pii(log_entry: Any) -> Any:
        """Recursively mask PII in structured telemetry payloads."""
        if not VRLFilter.PII_MASKING_ENABLED:
            return log_entry

        if isinstance(log_entry, list):
            return [VRLFilter.mask_pii(item) for item in log_entry]

        if not isinstance(log_entry, dict):
            return log_entry

        masked = {}
        for key, value in log_entry.items():
            key_text = str(key).lower()
            if key_text in VRLFilter.IDENTITY_KEYS:
                masked[key] = VRLFilter._mask_identity_value(value)
            elif isinstance(value, (dict, list)):
                masked[key] = VRLFilter.mask_pii(value)
            else:
                masked[key] = value
        return masked


@dataclass
class MaskReport:
    pii_types_found: list[str]
    total_replacements: int


def mask_text(text: str) -> tuple[str, MaskReport]:
    """Mask free-form text for SA IDs, Zimbabwe IDs, and passports."""
    if text is None:
        return "", MaskReport([], 0)

    pii_types: list[str] = []
    replacements = 0
    masked = str(text)

    # SA national ID: 13 digits
    sa_re = re.compile(r"\b\d{13}\b")

    def sa_sub(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        if "SA_ID" not in pii_types:
            pii_types.append("SA_ID")
        value = match.group(0)
        return f"{value[:2]}{'X' * 9}{value[-2:]}"

    masked = sa_re.sub(sa_sub, masked)

    # Zimbabwe ID: NN-NNNNNN[A-Z]NN
    zim_re = re.compile(r"\b(\d{2})-(\d{6}[A-Z])(\d{2})\b")

    def zim_sub(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        if "ZIM_ID" not in pii_types:
            pii_types.append("ZIM_ID")
        prefix, _, suffix = match.group(1), match.group(2), match.group(3)
        return f"{prefix}-XXXXXX{suffix}"

    masked = zim_re.sub(zim_sub, masked)

    # Passport patterns like ZN1234567, SA9876543, BW789012
    pass_re = re.compile(r"\b([A-Z]{1,2})(\d{6,9})\b", re.IGNORECASE)

    def pass_sub(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        if "PASSPORT" not in pii_types:
            pii_types.append("PASSPORT")
        country = match.group(1).upper()
        digits = match.group(2)
        return f"{country}{'X' * (len(digits) - 2)}{digits[-2:]}"

    masked = pass_re.sub(pass_sub, masked)

    # â”€â”€ Credential masking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _cred_sub(cred_type: str):
        tag = f"[REDACTED_{cred_type}]"
        def _sub(match: re.Match[str]) -> str:
            nonlocal replacements
            replacements += 1
            if cred_type not in pii_types:
                pii_types.append(cred_type)
            return tag
        return _sub

    masked = _CRED_AWS_KEY_RE.sub(_cred_sub("CRED_AWS_ACCESS_KEY"), masked)
    masked = _CRED_AWS_SECRET_RE.sub(_cred_sub("CRED_AWS_SECRET_KEY"), masked)
    masked = _CRED_API_KEY_RE.sub(_cred_sub("CRED_API_KEY"), masked)
    masked = _CRED_PRIVKEY_RE.sub(_cred_sub("CRED_PRIVATE_KEY"), masked)
    masked = _CRED_GITHUB_RE.sub(_cred_sub("CRED_GITHUB_TOKEN"), masked)
    masked = _CRED_JWT_RE.sub(_cred_sub("CRED_JWT"), masked)
    masked = _CRED_PASSWORD_RE.sub(_cred_sub("CRED_PASSWORD"), masked)

    return masked, MaskReport(pii_types_found=pii_types, total_replacements=replacements)


class PIIMasker:
    """Backward-compatible text masker used by sentinel tests."""

    def mask(self, text: str) -> tuple[str, MaskReport]:
        return mask_text(text)


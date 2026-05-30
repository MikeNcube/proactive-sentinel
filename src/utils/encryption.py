import base64
import json
import logging
import os
import warnings

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.types import Text, TypeDecorator

logger = logging.getLogger(__name__)


class FieldEncryption:
    """AES-256-GCM encryption helper for PII fields."""

    def __init__(self):
        self._key = None

    @property
    def key(self):
        if self._key is None:
            self._key = self._load_key()
        return self._key

    def _load_key(self) -> bytes:
        key_b64 = os.environ.get("ENCRYPTION_KEY", "")
        if key_b64:
            try:
                key = base64.b64decode(key_b64)
                if len(key) != 32:
                    raise ValueError(f"ENCRYPTION_KEY must be 32 bytes, got {len(key)}")
                logger.info("Encryption key loaded from ENCRYPTION_KEY env var")
                return key
            except Exception as exc:
                raise RuntimeError(f"Invalid ENCRYPTION_KEY: {exc}") from exc

        warnings.warn(
            "ENCRYPTION_KEY not set - generating ephemeral key. "
            "All encrypted data will be lost on restart. "
            "Set ENCRYPTION_KEY in production.",
            RuntimeWarning,
            stacklevel=3,
        )
        return AESGCM.generate_key(bit_length=256)

    def encrypt(self, plaintext):
        if not plaintext:
            return None
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)
        cipher = AESGCM(self.key)
        nonce = os.urandom(12)
        ciphertext = cipher.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, encrypted_text):
        if not encrypted_text:
            return None
        try:
            raw = base64.b64decode(encrypted_text)
            nonce, ciphertext = raw[:12], raw[12:]
            cipher = AESGCM(self.key)
            return cipher.decrypt(nonce, ciphertext, None).decode("utf-8")
        except Exception as exc:
            logger.error("Decryption failed - possible key mismatch or data corruption")
            raise RuntimeError("Decryption failed") from exc


field_encryption = FieldEncryption()


class EncryptedJSON(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that stores JSON as AES-256-GCM encrypted text.

    On INSERT/UPDATE: dict â†’ json.dumps â†’ encrypt â†’ base64 string in DB.
    On SELECT: base64 string â†’ decrypt â†’ json.loads â†’ dict in Python.

    Falls back to plain json.loads if decryption fails, so existing
    unencrypted rows remain readable after adding this column type.
    """

    impl = Text
    cache_ok = False  # key is runtime-generated; must not cache

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        text = json.dumps(value) if not isinstance(value, str) else value
        return field_encryption.encrypt(text)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            decrypted = field_encryption.decrypt(value)
            return json.loads(decrypted)
        except Exception:
            # Fallback: handle unencrypted legacy rows transparently.
            try:
                return json.loads(value)
            except Exception:
                return None


# Role sets that may receive raw_data in alert detail responses.
_DISPLAY_ROLES = {"IT_ADMIN", "SECURITY_ANALYST", "ADMIN"}


def _mask_ip_in_dict(data: dict) -> dict:
    """Return a copy of data with source_ip / ip fields partially masked."""
    masked = dict(data)
    for field in ("source_ip", "ip"):
        if field in masked:
            parts = str(masked[field]).split(".")
            if len(parts) == 4:
                masked[field] = f"{parts[0]}.{parts[1]}.xxx.xxx"
            else:
                masked[field] = "xxx.xxx.xxx.xxx"
    return masked


def decrypt_for_display(alert, role: str) -> dict:
    """
    Return a safe alert dict for API responses.

    raw_data is included only for IT_ADMIN, SECURITY_ANALYST, or admin roles,
    with source_ip always masked. All other roles receive a redacted placeholder.
    """
    authorized = str(role or "").upper() in _DISPLAY_ROLES
    raw = alert.raw_data or {}

    return {
        "id": str(alert.id),
        "title": alert.title,
        "severity": alert.severity,
        "status": alert.status,
        "category": alert.category,
        "source": alert.source,
        "description": alert.description,
        "confidence": alert.confidence,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "raw_data": _mask_ip_in_dict(raw) if authorized else {
            "_note": "raw_data requires IT_ADMIN or SECURITY_ANALYST role"
        },
    }


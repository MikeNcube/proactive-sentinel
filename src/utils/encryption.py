import base64
import logging
import os
import warnings

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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

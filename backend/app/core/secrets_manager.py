import os
import json
import base64
import logging
from typing import Optional
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import keyring
from app.core.config import settings

logger = logging.getLogger("ruby.secrets")
SERVICE_NAME = "ruby_academic_ai"


class SecretsManager:
    """
    Manages sensitive credentials (API keys).
    Primary backend: OS Keyring (Linux Secret Service via freedesktop SecretStorage/jeepney).
    Secondary fallback: AES-256-GCM encrypted local store.
    """

    def __init__(self):
        self._fallback_file = settings.data_dir / ".secrets.enc"
        self._salt_file = settings.data_dir / ".salt"
        self._keyring_available = self._probe_keyring()

    def _probe_keyring(self) -> bool:
        """Check if OS keyring is functioning."""
        try:
            test_key = "__ruby_probe__"
            keyring.set_password(SERVICE_NAME, test_key, "probe_val")
            val = keyring.get_password(SERVICE_NAME, test_key)
            keyring.delete_password(SERVICE_NAME, test_key)
            return val == "probe_val"
        except Exception as e:
            logger.info("OS Keyring unavailable (%s); using AES-GCM encrypted fallback.", e)
            return False

    def _get_encryption_key(self) -> bytes:
        """Derive 256-bit AES key for fallback storage."""
        if not self._salt_file.exists():
            salt = os.urandom(16)
            self._salt_file.write_bytes(salt)
        else:
            salt = self._salt_file.read_bytes()

        passphrase = (settings.encryption_key or "ruby-academic-default-passphrase").encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(passphrase)

    def _read_fallback_store(self) -> dict:
        if not self._fallback_file.exists():
            return {}
        try:
            data = self._fallback_file.read_bytes()
            if len(data) < 12:
                return {}
            nonce = data[:12]
            ciphertext = data[12:]
            aesgcm = AESGCM(self._get_encryption_key())
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            logger.error("Failed to decrypt local fallback secrets store: %s", e)
            return {}

    def _write_fallback_store(self, store: dict) -> None:
        try:
            aesgcm = AESGCM(self._get_encryption_key())
            nonce = os.urandom(12)
            raw = json.dumps(store).encode("utf-8")
            ciphertext = aesgcm.encrypt(nonce, raw, None)
            self._fallback_file.write_bytes(nonce + ciphertext)
        except Exception as e:
            logger.error("Failed to write encrypted fallback secrets store: %s", e)
            raise

    def store_secret(self, key_name: str, secret_value: str) -> str:
        """
        Store secret securely. Returns backend used: 'keyring' or 'encrypted_file'.
        """
        if not secret_value:
            raise ValueError("Secret value cannot be empty.")

        if self._keyring_available:
            try:
                keyring.set_password(SERVICE_NAME, key_name, secret_value)
                return "keyring"
            except Exception as e:
                logger.warning("Keyring set_password failed (%s), falling back to encrypted file.", e)
                self._keyring_available = False

        store = self._read_fallback_store()
        store[key_name] = secret_value
        self._write_fallback_store(store)
        return "encrypted_file"

    def get_secret(self, key_name: str) -> Optional[str]:
        """Retrieve plaintext secret."""
        if self._keyring_available:
            try:
                val = keyring.get_password(SERVICE_NAME, key_name)
                if val is not None:
                    return val
            except Exception as e:
                logger.warning("Keyring get_password failed (%s), trying encrypted file.", e)

        store = self._read_fallback_store()
        return store.get(key_name)

    def delete_secret(self, key_name: str) -> bool:
        """Delete secret from all backends."""
        deleted = False
        if self._keyring_available:
            try:
                keyring.delete_password(SERVICE_NAME, key_name)
                deleted = True
            except Exception:
                pass

        store = self._read_fallback_store()
        if key_name in store:
            del store[key_name]
            self._write_fallback_store(store)
            deleted = True

        return deleted

    @staticmethod
    def mask_secret(secret_value: str) -> str:
        """Mask a secret for UI display (e.g., 'sk-...4a2b'). Never reveals the secret."""
        if not secret_value:
            return ""
        if len(secret_value) <= 8:
            return "••••••••"
        return f"{secret_value[:3]}••••{secret_value[-4:]}"


secrets_manager = SecretsManager()

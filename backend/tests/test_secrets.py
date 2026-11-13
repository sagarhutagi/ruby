import pytest
from app.core.secrets_manager import SecretsManager


def test_secret_masking():
    # Long key
    masked = SecretsManager.mask_secret("sk-proj-1234567890abcdef1234")
    assert masked.startswith("sk-")
    assert masked.endswith("1234")
    assert "••••" in masked
    assert "abcdef" not in masked

    # Short key
    short_masked = SecretsManager.mask_secret("secret12")
    assert short_masked == "••••••••"
    assert "secret" not in short_masked

    # Empty
    assert SecretsManager.mask_secret("") == ""


def test_secrets_store_retrieve_delete():
    sm = SecretsManager()
    key_name = "test_test_secret_alpha"
    secret_value = "super-secret-api-token-987654"

    # Store
    backend = sm.store_secret(key_name, secret_value)
    assert backend in ["keyring", "encrypted_file"]

    # Retrieve
    retrieved = sm.get_secret(key_name)
    assert retrieved == secret_value

    # Delete
    deleted = sm.delete_secret(key_name)
    assert deleted is True

    # Retrieve after deletion
    assert sm.get_secret(key_name) is None

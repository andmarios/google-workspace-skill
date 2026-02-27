"""Tests for the gws.crypto encryption-at-rest module."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from gws.crypto import (
    generate_salt,
    derive_key,
    save_encrypted,
    load_encrypted,
    delete_encrypted,
    _enc_path,
    get_machine_id,
)


# ---------------------------------------------------------------------------
# Salt & key derivation
# ---------------------------------------------------------------------------

def test_generate_salt_length():
    """Salt should be a 64-char hex string."""
    salt = generate_salt()
    assert len(salt) == 64
    assert all(c in "0123456789abcdef" for c in salt)


def test_generate_salt_unique():
    """Two salts should never collide."""
    assert generate_salt() != generate_salt()


def test_derive_key_deterministic():
    """Same inputs must always produce the same key."""
    salt = "a" * 64
    key1 = derive_key(salt, "test-app")
    key2 = derive_key(salt, "test-app")
    assert key1 == key2


def test_derive_key_differs_by_salt():
    """Different salts must produce different keys."""
    k1 = derive_key("a" * 64, "test-app")
    k2 = derive_key("b" * 64, "test-app")
    assert k1 != k2


def test_derive_key_differs_by_app_id():
    """Different app_ids must produce different keys."""
    salt = "c" * 64
    k1 = derive_key(salt, "gws-cli")
    k2 = derive_key(salt, "zd-cli")
    assert k1 != k2


def test_get_machine_id_returns_string():
    """get_machine_id() should return a non-empty string on Linux."""
    mid = get_machine_id()
    assert isinstance(mid, str)
    assert len(mid) > 0  # Linux CI has /etc/machine-id


# ---------------------------------------------------------------------------
# _enc_path
# ---------------------------------------------------------------------------

def test_enc_path():
    p = Path("/some/dir/token.json")
    assert _enc_path(p) == Path("/some/dir/token.json.enc")


# ---------------------------------------------------------------------------
# save / load roundtrip
# ---------------------------------------------------------------------------

@pytest.fixture
def key():
    """A real Fernet key derived from the current machine."""
    return derive_key("test_salt_" + "0" * 54, "test-app")


def test_save_load_encrypted_roundtrip(tmp_path, key):
    """Encrypted save → load roundtrip returns identical data."""
    data = {"access_token": "tok123", "refresh_token": "ref456"}
    base = tmp_path / "token.json"

    save_encrypted(base, data, key)

    # Encrypted file should exist, plaintext should not
    assert _enc_path(base).exists()
    assert not base.exists()

    # Permissions should be 0o600
    mode = _enc_path(base).stat().st_mode & 0o777
    assert mode == 0o600

    loaded = load_encrypted(base, key)
    assert loaded == data


def test_save_load_no_key(tmp_path):
    """With key=None, data is saved as plaintext JSON."""
    data = {"secret": "value"}
    base = tmp_path / "config.json"

    save_encrypted(base, data, None)

    # Plaintext file should exist, no .enc
    assert base.exists()
    assert not _enc_path(base).exists()

    # Should be valid JSON
    with open(base) as f:
        assert json.load(f) == data

    # Permissions should be 0o600
    mode = base.stat().st_mode & 0o777
    assert mode == 0o600

    loaded = load_encrypted(base, None)
    assert loaded == data


def test_auto_migration_plaintext_to_encrypted(tmp_path, key):
    """When loading with a key, plaintext files are auto-migrated to .enc."""
    data = {"token": "migrate_me"}
    base = tmp_path / "token.json"

    # Write plaintext manually
    with open(base, "w") as f:
        json.dump(data, f)

    # Load with key should trigger migration
    loaded = load_encrypted(base, key)
    assert loaded == data

    # Now .enc should exist and plaintext should be gone
    assert _enc_path(base).exists()
    assert not base.exists()

    # Subsequent load should still work
    loaded2 = load_encrypted(base, key)
    assert loaded2 == data


def test_decrypt_failure_returns_none(tmp_path, key):
    """Wrong key returns None instead of crashing."""
    data = {"secret": "value"}
    base = tmp_path / "token.json"

    save_encrypted(base, data, key)

    # Derive a different key
    wrong_key = derive_key("wrong_salt_" + "0" * 53, "test-app")
    assert wrong_key != key

    loaded = load_encrypted(base, wrong_key)
    assert loaded is None


def test_load_missing_file(tmp_path, key):
    """Loading a non-existent file returns None."""
    base = tmp_path / "nonexistent.json"
    assert load_encrypted(base, key) is None
    assert load_encrypted(base, None) is None


def test_save_encrypted_removes_plaintext_leftover(tmp_path, key):
    """Saving encrypted removes any pre-existing plaintext file."""
    base = tmp_path / "token.json"

    # Create a plaintext file first
    with open(base, "w") as f:
        json.dump({"old": "data"}, f)
    assert base.exists()

    # Save encrypted
    save_encrypted(base, {"new": "data"}, key)

    # Plaintext should be gone
    assert not base.exists()
    assert _enc_path(base).exists()


# ---------------------------------------------------------------------------
# delete_encrypted
# ---------------------------------------------------------------------------

def test_delete_encrypted_removes_both(tmp_path, key):
    """delete_encrypted removes both .enc and plaintext versions."""
    base = tmp_path / "token.json"

    # Create both files
    save_encrypted(base, {"data": 1}, key)
    with open(base, "w") as f:
        json.dump({"data": 2}, f)

    assert _enc_path(base).exists()
    assert base.exists()

    result = delete_encrypted(base)
    assert result is True
    assert not _enc_path(base).exists()
    assert not base.exists()


def test_delete_encrypted_nothing_exists(tmp_path):
    """delete_encrypted returns False when neither file exists."""
    base = tmp_path / "nonexistent.json"
    assert delete_encrypted(base) is False


def test_delete_encrypted_only_enc(tmp_path, key):
    """delete_encrypted works when only .enc exists."""
    base = tmp_path / "token.json"
    save_encrypted(base, {"data": 1}, key)
    assert _enc_path(base).exists()
    assert not base.exists()

    assert delete_encrypted(base) is True
    assert not _enc_path(base).exists()


def test_delete_encrypted_only_plaintext(tmp_path):
    """delete_encrypted works when only plaintext exists."""
    base = tmp_path / "token.json"
    with open(base, "w") as f:
        json.dump({"data": 1}, f)

    assert delete_encrypted(base) is True
    assert not base.exists()

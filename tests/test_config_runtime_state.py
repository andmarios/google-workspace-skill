"""Runtime-only Config state must never be persisted to, or read back from, disk.

Config keeps the derived encryption key (and whether it was resolved) as
dataclass fields. If those reach gws_config.json, save() crashes once a key
is derived (bytes aren't JSON), and a stale ``_encryption_key_resolved: true``
silently disables encryption on every later run.
"""

import json

import pytest

from gws.config import Config
from gws.crypto import _enc_path, generate_salt, load_encrypted


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    monkeypatch.delenv("GWS_ENCRYPTION", raising=False)
    return tmp_path


def _saved_keys() -> set[str]:
    return set(json.loads(Config.CONFIG_PATH.read_text()))


def test_save_after_key_derivation_succeeds(config_dir):
    config = Config.load()
    assert config.get_encryption_key() is not None

    config.save()  # used to raise TypeError: bytes is not JSON serializable

    assert not {k for k in _saved_keys() if k.startswith("_")}


def test_encryption_opt_out_is_not_persisted(config_dir, monkeypatch):
    monkeypatch.setenv("GWS_ENCRYPTION", "none")
    config = Config.load()
    assert config.get_encryption_key() is None
    config.save()

    monkeypatch.delenv("GWS_ENCRYPTION")
    assert Config.load().get_encryption_key() is not None


def test_polluted_config_is_healed(config_dir):
    """Config files written by affected versions must not keep encryption off."""
    Config.CONFIG_PATH.write_text(json.dumps({
        "encryption_salt": generate_salt(),
        "_encryption_key_cache": None,
        "_encryption_key_resolved": True,
    }))

    config = Config.load()
    assert config.get_encryption_key() is not None

    config.save()
    assert not {k for k in _saved_keys() if k.startswith("_")}


def test_plaintext_token_from_affected_version_is_reencrypted(config_dir):
    """A token stored in plaintext while encryption was silently off gets migrated."""
    Config.CONFIG_PATH.write_text(json.dumps({
        "encryption_salt": generate_salt(),
        "_encryption_key_resolved": True,
    }))
    token_path = config_dir / "token.json"
    token_path.write_text(json.dumps({"refresh_token": "r"}))

    loaded = load_encrypted(token_path, Config.load().get_encryption_key())

    assert loaded == {"refresh_token": "r"}
    assert _enc_path(token_path).exists()
    assert not token_path.exists()


def test_repr_does_not_expose_derived_key(config_dir):
    config = Config.load()
    key = config.get_encryption_key()
    assert key is not None

    assert key.decode() not in repr(config)
    assert "_encryption_key" not in repr(config)

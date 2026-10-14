"""Tests for multi-account configuration support."""

import json
import sys

import pytest

from gws.config import Config, AccountEntry, AccountsRegistry


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Set up isolated config directory."""
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    return tmp_path


class TestLegacyMode:
    """Legacy mode: no accounts key in config."""

    def test_load_default_has_no_accounts(self, config_dir):
        config = Config.load()
        assert config.accounts is None
        assert not config.is_multi_account

    def test_save_omits_accounts_key(self, config_dir):
        config = Config()
        config.save()
        with open(Config.CONFIG_PATH) as f:
            data = json.load(f)
        assert "accounts" not in data

    def test_load_legacy_config_file(self, config_dir):
        """Loading a config without accounts key works exactly as before."""
        legacy_data = {
            "enabled_services": ["docs", "sheets"],
            "kroki_url": "https://kroki.io",
            "security_enabled": True,
            "allowlisted_documents": [],
            "allowlisted_emails": [],
            "disabled_security_services": [],
            "disabled_security_operations": {},
        }
        with open(Config.CONFIG_PATH, "w") as f:
            json.dump(legacy_data, f)

        config = Config.load()
        assert config.enabled_services == ["docs", "sheets"]
        assert config.accounts is None
        assert not config.is_multi_account


class TestConfigRoundtrip:
    """Config save/load with accounts preserves structure."""

    def test_roundtrip_with_accounts(self, config_dir):
        config = Config()
        config.accounts = AccountsRegistry(
            default_account="work",
            entries={
                "work": AccountEntry(email="work@example.com", created_at="2025-01-01T00:00:00+00:00"),
                "personal": AccountEntry(email="me@gmail.com", created_at="2025-01-02T00:00:00+00:00"),
            },
        )
        config.save()

        loaded = Config.load()
        assert loaded.accounts is not None
        assert loaded.accounts.default_account == "work"
        assert "work" in loaded.accounts.entries
        assert "personal" in loaded.accounts.entries
        assert loaded.accounts.entries["work"].email == "work@example.com"
        assert loaded.is_multi_account

    def test_roundtrip_preserves_other_fields(self, config_dir):
        config = Config()
        config.enabled_services = ["docs", "gmail"]
        config.kroki_url = "http://localhost:8000"
        config.accounts = AccountsRegistry(
            default_account="test",
            entries={"test": AccountEntry(email="test@example.com")},
        )
        config.save()

        loaded = Config.load()
        assert loaded.enabled_services == ["docs", "gmail"]
        assert loaded.kroki_url == "http://localhost:8000"
        assert loaded.accounts is not None


class TestAccountCRUD:
    """Account add/remove/list/default operations."""

    def test_add_first_account_sets_default(self, config_dir):
        config = Config()
        config.add_account("work", email="work@example.com")

        assert config.accounts is not None
        assert config.accounts.default_account == "work"
        assert "work" in config.accounts.entries
        assert config.accounts.entries["work"].email == "work@example.com"
        assert config.is_multi_account

    def test_add_creates_directory(self, config_dir):
        config = Config()
        config.add_account("work")

        account_dir = config_dir / "accounts" / "work"
        assert account_dir.exists()
        assert account_dir.is_dir()

    def test_add_second_account_keeps_first_default(self, config_dir):
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        assert config.accounts.default_account == "work"
        assert len(config.accounts.entries) == 2

    def test_remove_account(self, config_dir):
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        removed = config.remove_account("personal")
        assert removed
        assert "personal" not in config.accounts.entries

    def test_remove_last_account_reverts_to_legacy(self, config_dir):
        config = Config()
        config.add_account("work")
        config.remove_account("work")

        assert config.accounts is None
        assert not config.is_multi_account

    def test_remove_default_reassigns(self, config_dir):
        config = Config()
        config.add_account("work")
        config.add_account("personal")
        config.remove_account("work")

        assert config.accounts.default_account == "personal"

    def test_remove_cleans_up_directory(self, config_dir):
        config = Config()
        config.add_account("work")
        account_dir = config_dir / "accounts" / "work"
        assert account_dir.exists()

        config.remove_account("work")
        assert not account_dir.exists()

    def test_remove_nonexistent_returns_false(self, config_dir):
        config = Config()
        assert not config.remove_account("nonexistent")

    def test_set_default_account(self, config_dir):
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        changed = config.set_default_account("personal")
        assert changed
        assert config.accounts.default_account == "personal"

    def test_set_default_nonexistent_returns_false(self, config_dir):
        config = Config()
        config.add_account("work")
        assert not config.set_default_account("nonexistent")

    def test_list_accounts(self, config_dir):
        config = Config()
        config.add_account("work", email="work@example.com")
        config.add_account("personal", email="me@gmail.com")

        accounts = config.list_accounts()
        assert len(accounts) == 2
        assert accounts["work"]["is_default"] is True
        assert accounts["personal"]["is_default"] is False
        assert accounts["work"]["email"] == "work@example.com"

    def test_list_accounts_empty(self, config_dir):
        config = Config()
        assert config.list_accounts() == {}


class TestAccountResolution:
    """Account resolution priority: explicit > env > default > None."""

    def test_explicit_wins(self, config_dir):
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        assert config.resolve_account("personal") == "personal"

    def test_env_var_fallback(self, config_dir, monkeypatch):
        monkeypatch.setenv("GWS_ACCOUNT", "personal")
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        assert config.resolve_account() == "personal"

    def test_default_fallback(self, config_dir, monkeypatch):
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()
        config.add_account("work")

        assert config.resolve_account() == "work"

    def test_none_when_no_accounts(self, config_dir, monkeypatch):
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()

        assert config.resolve_account() is None

    def test_explicit_overrides_env(self, config_dir, monkeypatch):
        monkeypatch.setenv("GWS_ACCOUNT", "personal")
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        assert config.resolve_account("work") == "work"


class TestEffectiveConfig:
    """Config merge: global + per-account overrides."""

    def test_no_overrides_returns_self(self, config_dir):
        config = Config()
        config.add_account("work")

        effective = config.load_effective_config("work")
        assert effective.enabled_services == config.enabled_services

    def test_override_disables_service(self, config_dir):
        config = Config()
        config.add_account("work")
        config.save_account_config("work", {
            "enabled_services": ["docs", "sheets"],
        })

        effective = config.load_effective_config("work")
        assert effective.enabled_services == ["docs", "sheets"]
        # Original unchanged
        assert len(config.enabled_services) == 8

    def test_override_kroki_url(self, config_dir):
        config = Config()
        config.add_account("work")
        config.save_account_config("work", {
            "kroki_url": "http://localhost:9000",
        })

        effective = config.load_effective_config("work")
        assert effective.kroki_url == "http://localhost:9000"

    def test_none_account_returns_self(self, config_dir):
        config = Config()
        effective = config.load_effective_config(None)
        assert effective is config

    def test_clear_account_config(self, config_dir):
        config = Config()
        config.add_account("work")
        config.save_account_config("work", {"enabled_services": ["docs"]})

        config_path = config.get_account_dir("work") / "config.json"
        assert config_path.exists()

        config.clear_account_config("work")
        assert not config_path.exists()

    def test_load_account_config_empty_when_no_file(self, config_dir):
        config = Config()
        config.add_account("work")
        assert config.load_account_config("work") == {}


class TestGetAccountDir:
    """Account directory paths."""

    def test_account_dir(self, config_dir):
        config = Config()
        path = config.get_account_dir("work")
        assert path == config_dir / "accounts" / "work"


class TestAccountNameValidation:
    """Account names must be safe for filesystem use."""

    def test_valid_names(self):
        for name in ["work", "personal", "my-account", "account_2", "Work123"]:
            Config.validate_account_name(name)  # Should not raise

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="Invalid account name"):
            Config.validate_account_name("../../etc")

    def test_slashes_rejected(self):
        with pytest.raises(ValueError, match="Invalid account name"):
            Config.validate_account_name("foo/bar")

    def test_spaces_rejected(self):
        with pytest.raises(ValueError, match="Invalid account name"):
            Config.validate_account_name("my account")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="Invalid account name"):
            Config.validate_account_name("")

    def test_dots_rejected(self):
        with pytest.raises(ValueError, match="Invalid account name"):
            Config.validate_account_name("..")


class TestEffectiveConfigDoesNotLeak:
    """H2: deriving the key (or any save) on a per-account effective config
    must never write per-account overrides back to the global config."""

    def test_key_derivation_on_effective_config_does_not_clobber_global(
        self, config_dir, monkeypatch
    ):
        # Avoid machine-id dependency for key derivation.
        monkeypatch.setattr("gws.crypto.derive_key", lambda salt, info: b"k" * 44)

        base = Config()
        base.add_account("work")
        base.save()
        base.save_account_config("work", {"enabled_services": ["docs"]})

        effective = Config.load().load_effective_config("work")
        assert effective.enabled_services == ["docs"]
        assert effective.encryption_salt == ""  # empty salt triggers the persist path

        effective.get_encryption_key()

        on_disk = Config.load()
        # Global enabled_services must be untouched by the per-account override.
        assert on_disk.enabled_services == list(Config.ALL_SERVICES)
        # The salt must still have been persisted to the global config.
        assert on_disk.encryption_salt

    def test_effective_config_save_is_rejected(self, config_dir):
        base = Config()
        base.add_account("work")
        base.save()
        base.save_account_config("work", {"enabled_services": ["docs"]})

        effective = Config.load().load_effective_config("work")
        with pytest.raises(RuntimeError):
            effective.save()


class TestAtomicAndCorruptConfig:
    """H3: atomic writes + corrupt-config preservation."""

    def test_write_failure_preserves_existing_file(self, config_dir, monkeypatch):
        import os as _os
        from gws.config import _write_secure_file

        path = config_dir / "gws_config.json"
        _write_secure_file(path, '{"original": true}')

        def boom(*args, **kwargs):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(_os, "replace", boom)
        with pytest.raises(OSError):
            _write_secure_file(path, '{"new": true}')

        # The pre-existing file must be intact (atomic write never truncates it)
        assert path.read_text() == '{"original": true}'
        # No temp/partial files left behind
        leftovers = [p for p in config_dir.iterdir() if ".tmp" in p.name]
        assert not leftovers

    def test_write_works_without_fchmod(self, config_dir, monkeypatch):
        """os.fchmod is POSIX-only; writes must still succeed on Windows."""
        import os as _os

        from gws.config import _write_secure_file

        monkeypatch.delattr(_os, "fchmod", raising=False)
        path = config_dir / "gws_config.json"
        _write_secure_file(path, '{"new": true}')

        assert path.read_text() == '{"new": true}'
        leftovers = [p for p in config_dir.iterdir() if ".tmp" in p.name]
        assert not leftovers

    def test_fchmod_failure_leaves_no_temp_file(self, config_dir, monkeypatch):
        """The temp fd must be closed before cleanup (Windows can't unlink open files)."""
        import os as _os

        from gws.config import _write_secure_file

        def boom(*args, **kwargs):
            raise OSError("simulated fchmod failure")

        monkeypatch.setattr(_os, "fchmod", boom, raising=False)
        with pytest.raises(OSError):
            _write_secure_file(config_dir / "gws_config.json", '{"new": true}')

        leftovers = [p for p in config_dir.iterdir() if ".tmp" in p.name]
        assert not leftovers

    def test_corrupt_config_is_backed_up_not_silently_destroyed(self, config_dir):
        # A config that contains account data but is syntactically broken
        Config.CONFIG_PATH.write_text('{"accounts": {"entries": {"work": {')

        cfg = Config.load()  # must not raise, must not silently drop the data

        backups = list(config_dir.glob("gws_config.json.corrupt*"))
        assert backups, "corrupt config must be preserved as a backup"
        assert "work" in backups[0].read_text(), "backup must retain original bytes"


class TestAccountNameHardening:
    """Security: account name validation must be airtight."""

    def test_trailing_newline_rejected(self):
        # re.match + '$' accepts a trailing newline; fullmatch must not.
        with pytest.raises(ValueError, match="Invalid account name"):
            Config.validate_account_name("work\n")

    def test_overlong_name_rejected(self):
        with pytest.raises(ValueError):
            Config.validate_account_name("a" * 200)


class TestAccountDirPermissions:
    """Security: per-account dirs (holding tokens) must be private (0o700)."""

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits are not enforced on Windows")
    def test_account_dir_is_owner_only(self, config_dir):
        import stat
        config = Config()
        config.add_account("work")
        d = config.get_account_dir("work")
        mode = stat.S_IMODE(d.stat().st_mode)
        assert mode == 0o700, oct(mode)

"""Tests for multi-account configuration support."""

import json
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

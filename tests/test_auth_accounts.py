"""Tests for account-aware authentication."""

import pytest

from gws.auth.oauth import AuthManager
from gws.config import Config
from gws.exceptions import AuthError


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Set up isolated config directory."""
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    return tmp_path


class TestTokenPathResolution:
    """TOKEN_PATH returns correct path for legacy vs account mode."""

    def test_legacy_token_path(self, config_dir):
        config = Config()
        auth = AuthManager(config=config)
        assert auth.TOKEN_PATH == AuthManager._LEGACY_TOKEN_PATH

    def test_account_token_path(self, config_dir):
        config = Config()
        config.add_account("work")

        auth = AuthManager(config=config, account="work")
        expected = config_dir / "accounts" / "work" / "token.json"
        assert auth.TOKEN_PATH == expected

    def test_default_account_token_path(self, config_dir, monkeypatch):
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()
        config.add_account("work")

        auth = AuthManager(config=config)
        expected = config_dir / "accounts" / "work" / "token.json"
        assert auth.TOKEN_PATH == expected

    def test_env_account_token_path(self, config_dir, monkeypatch):
        monkeypatch.setenv("GWS_ACCOUNT", "personal")
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        auth = AuthManager(config=config)
        expected = config_dir / "accounts" / "personal" / "token.json"
        assert auth.TOKEN_PATH == expected


class TestAccountValidation:
    """Explicit account names must exist in registry."""

    def test_valid_account_accepted(self, config_dir):
        config = Config()
        config.add_account("work")
        # Should not raise
        auth = AuthManager(config=config, account="work")
        assert auth.account_name == "work"

    def test_invalid_account_raises(self, config_dir):
        config = Config()
        config.add_account("work")

        with pytest.raises(AuthError, match="Account 'nonexistent' not found"):
            AuthManager(config=config, account="nonexistent")

    def test_no_accounts_no_validation_when_none(self, config_dir, monkeypatch):
        """When no accounts registry exists and no account specified, no error."""
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()
        auth = AuthManager(config=config, account=None)
        assert auth.account_name is None

    def test_account_specified_but_no_registry_raises(self, config_dir, monkeypatch):
        """When account is specified but no registry exists, raises AuthError."""
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()
        with pytest.raises(AuthError, match="no accounts are configured"):
            AuthManager(config=config, account="work")

    def test_env_account_but_no_registry_raises(self, config_dir, monkeypatch):
        """When GWS_ACCOUNT is set but no registry exists, raises AuthError."""
        monkeypatch.setenv("GWS_ACCOUNT", "phantom")
        config = Config()
        with pytest.raises(AuthError, match="no accounts are configured"):
            AuthManager(config=config)

    def test_env_account_nonexistent_raises(self, config_dir, monkeypatch):
        """When GWS_ACCOUNT points to nonexistent account, raises AuthError."""
        monkeypatch.setenv("GWS_ACCOUNT", "nonexistent")
        config = Config()
        config.add_account("work")
        with pytest.raises(AuthError, match="Account 'nonexistent' not found"):
            AuthManager(config=config)


class TestAccountNameProperty:
    """The account_name property reflects resolved account."""

    def test_no_account(self, config_dir, monkeypatch):
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()
        auth = AuthManager(config=config)
        assert auth.account_name is None

    def test_explicit_account(self, config_dir):
        config = Config()
        config.add_account("work")
        auth = AuthManager(config=config, account="work")
        assert auth.account_name == "work"

    def test_resolved_default(self, config_dir, monkeypatch):
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()
        config.add_account("work")
        auth = AuthManager(config=config)
        assert auth.account_name == "work"


class TestEffectiveConfigInAuth:
    """AuthManager loads effective config for account."""

    def test_auth_uses_account_config(self, config_dir):
        config = Config()
        config.add_account("work")
        config.save_account_config("work", {
            "enabled_services": ["docs", "sheets"],
        })

        auth = AuthManager(config=config, account="work")
        assert auth.config.enabled_services == ["docs", "sheets"]

    def test_auth_without_account_uses_global(self, config_dir, monkeypatch):
        monkeypatch.delenv("GWS_ACCOUNT", raising=False)
        config = Config()
        config.enabled_services = ["docs", "gmail"]

        auth = AuthManager(config=config)
        assert auth.config.enabled_services == ["docs", "gmail"]

"""Tests for account CLI commands."""

import json
import pytest
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from gws.cli import app
from gws.config import Config


runner = CliRunner()


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Set up isolated config directory."""
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    monkeypatch.delenv("GWS_ACCOUNT", raising=False)
    return tmp_path


class TestAccountAdd:
    """Tests for 'gws account add'."""

    def test_add_account_success(self, config_dir):
        """Adding an account creates directory and triggers auth."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = "{}"

        with patch("gws.auth.oauth.AuthManager.get_credentials", return_value=mock_creds), \
             patch("gws.auth.oauth.AuthManager.CREDENTIALS_PATH", config_dir / "client_secret.json"):
            result = runner.invoke(app, ["account", "add", "work"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["account"] == "work"
        assert (config_dir / "accounts" / "work").exists()

    def test_add_duplicate_account_fails(self, config_dir):
        """Adding an existing account without --force fails."""
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["account", "add", "work"])
        assert result.exit_code != 0
        output = json.loads(result.stdout)
        assert output["error_code"] == "ACCOUNT_EXISTS"

    def test_add_duplicate_with_force(self, config_dir):
        """Adding an existing account with --force overwrites."""
        config = Config()
        config.add_account("work")

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = "{}"

        with patch("gws.auth.oauth.AuthManager.get_credentials", return_value=mock_creds), \
             patch("gws.auth.oauth.AuthManager.CREDENTIALS_PATH", config_dir / "client_secret.json"):
            result = runner.invoke(app, ["account", "add", "work", "--force"])

        assert result.exit_code == 0


class TestAccountRemove:
    """Tests for 'gws account remove'."""

    def test_remove_existing_account(self, config_dir):
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["account", "remove", "work"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["status"] == "success"

    def test_remove_nonexistent_account(self, config_dir):
        result = runner.invoke(app, ["account", "remove", "nonexistent"])
        assert result.exit_code != 0
        output = json.loads(result.stdout)
        assert output["error_code"] == "NOT_FOUND"


class TestAccountList:
    """Tests for 'gws account list'."""

    def test_list_empty(self, config_dir):
        result = runner.invoke(app, ["account", "list"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["count"] == 0
        assert output["accounts"] == {}

    def test_list_with_accounts(self, config_dir):
        config = Config()
        config.add_account("work", email="work@example.com")
        config.add_account("personal", email="me@gmail.com")

        result = runner.invoke(app, ["account", "list"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["count"] == 2
        assert output["default"] == "work"
        assert output["accounts"]["work"]["is_default"] is True


class TestAccountDefault:
    """Tests for 'gws account default'."""

    def test_set_default(self, config_dir):
        config = Config()
        config.add_account("work")
        config.add_account("personal")

        result = runner.invoke(app, ["account", "default", "personal"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["account"] == "personal"

    def test_set_default_nonexistent(self, config_dir):
        result = runner.invoke(app, ["account", "default", "nonexistent"])
        assert result.exit_code != 0


class TestAccountConfig:
    """Tests for 'gws account config' commands."""

    def test_show_config(self, config_dir):
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["account", "config", "work"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["account"] == "work"
        assert output["has_overrides"] is False

    def test_config_enable_service(self, config_dir):
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["account", "config-enable", "work", "docs"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "docs" in output["enabled_services"]

    def test_config_disable_service(self, config_dir):
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["account", "config-disable", "work", "gmail"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "gmail" not in output["enabled_services"]

    def test_config_reset(self, config_dir):
        config = Config()
        config.add_account("work")
        config.save_account_config("work", {"enabled_services": ["docs"]})

        result = runner.invoke(app, ["account", "config-reset", "work"])
        assert result.exit_code == 0

        # Verify overrides removed
        assert config.load_account_config("work") == {}

    def test_config_nonexistent_account(self, config_dir):
        result = runner.invoke(app, ["account", "config", "nonexistent"])
        assert result.exit_code != 0

    def test_config_enable_invalid_service(self, config_dir):
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["account", "config-enable", "work", "invalid_svc"])
        assert result.exit_code != 0
        output = json.loads(result.stdout)
        assert output["error_code"] == "INVALID_SERVICE"


class TestAuthWithAccount:
    """Tests for auth commands with --account flag."""

    def test_auth_status_with_account(self, config_dir):
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["auth", "status", "--account", "work"])
        # Will be auth error (no token), but should include account info
        output = json.loads(result.stdout)
        assert output["account"] == "work"

    def test_auth_logout_with_account(self, config_dir):
        config = Config()
        config.add_account("work")

        result = runner.invoke(app, ["auth", "logout", "--account", "work"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["operation"] == "auth.logout"

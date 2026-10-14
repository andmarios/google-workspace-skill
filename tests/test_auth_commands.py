"""Tests for the auth CLI headless option."""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gws.cli import app

runner = CliRunner()


def test_auth_headless_is_forwarded_to_provider() -> None:
    provider = MagicMock()
    provider.account_name = None
    provider.TOKEN_PATH = "token.json"
    provider.get_credentials.return_value.valid = True

    with patch("gws.commands.auth.resolve_auth_provider", return_value=provider):
        result = runner.invoke(app, ["auth", "--headless"])

    assert result.exit_code == 0
    provider.get_credentials.assert_called_once_with(force_refresh=False, headless=True)
    payload = json.loads(result.stdout)
    assert payload["operation"] == "auth"


def test_auth_force_headless_account_combination_is_forwarded() -> None:
    provider = MagicMock()
    provider.account_name = "work"
    provider.TOKEN_PATH = "accounts/work/token.json"
    provider.get_credentials.return_value.valid = True

    with patch("gws.commands.auth.resolve_auth_provider", return_value=provider) as resolve:
        result = runner.invoke(app, ["auth", "--force", "--headless", "-a", "work"])

    assert result.exit_code == 0
    resolve.assert_called_once_with(account="work")
    # --force replaces the token only once the new login succeeds; it never deletes up front.
    provider.delete_token.assert_not_called()
    provider.get_credentials.assert_called_once_with(force_refresh=True, headless=True)


def test_auth_help_documents_headless_option() -> None:
    # Rich wraps help text to the terminal width; pin it so the phrase stays on one line.
    result = runner.invoke(app, ["auth", "--help"], env={"COLUMNS": "200"})

    assert result.exit_code == 0
    assert "--headless" in result.stdout
    assert "provider's headless flow" in result.stdout

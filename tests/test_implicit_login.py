"""Implicit logins (triggered by a service command) fail fast without a terminal.

An agent or CI run cannot see a login prompt, so with a revoked token the
command used to wait forever for a browser callback. pytest captures stderr,
so it is not a TTY here unless a test says otherwise.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from gws.auth.oauth import LocalAuthProvider
from gws.auth.server import ServerAuthProvider
from gws.config import Config
from gws.exceptions import AuthError, ExitCode
from gws.services.base import BaseService


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep tests away from the real ~/.config/gws-cli (config, salt, tokens)."""
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    monkeypatch.setattr(Config, "_LEGACY_BASE_DIR", tmp_path / "legacy")
    monkeypatch.setattr(LocalAuthProvider, "_LEGACY_TOKEN_PATH", tmp_path / "token.json")
    for var in ("GWS_ACCOUNT", "GWS_ENCRYPTION", "GWS_HEADLESS"):
        monkeypatch.delenv(var, raising=False)


def _local(account: str | None = None) -> LocalAuthProvider:
    provider = LocalAuthProvider(config=Config())
    provider._account_name = account
    return provider


def _server(account: str | None = None) -> ServerAuthProvider:
    provider = object.__new__(ServerAuthProvider)
    provider.server_url = "https://relay.example.com"
    provider.config = Config()
    provider._account_name = account
    provider._credentials = None
    provider._server_token = None
    return provider


@pytest.mark.parametrize(
    ("account", "command"), [("work", "gws-cli auth --account work"), (None, "gws-cli auth")]
)
def test_local_implicit_login_without_tty_fails_fast(account, command) -> None:
    provider = _local(account)
    with (
        patch("gws.auth.oauth.load_encrypted", return_value=None),
        patch.object(provider, "_run_auth_flow") as run_auth_flow,
        pytest.raises(AuthError, match=r"Not authenticated \(token missing") as exc,
    ):
        provider.get_credentials(implicit=True)

    assert exc.value.details == f"Run '{command}' in your own terminal to authenticate."
    run_auth_flow.assert_not_called()


def test_local_implicit_login_with_tty_or_explicit_runs_flow(monkeypatch) -> None:
    provider = _local("work")
    with (
        patch("gws.auth.oauth.load_encrypted", return_value=None),
        patch.object(provider, "_run_auth_flow") as run_auth_flow,
    ):
        provider.get_credentials()  # explicit (`auth`, `account add`): never blocked
        monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
        provider.get_credentials(implicit=True)

    assert run_auth_flow.call_count == 2


def test_local_silent_refresh_without_tty_still_works() -> None:
    provider = _local("work")
    expired = MagicMock(valid=False, expired=True, refresh_token="refresh")
    with (
        patch("gws.auth.oauth.load_encrypted", return_value={"token": "t"}),
        patch("gws.auth.oauth.Credentials.from_authorized_user_info", return_value=expired),
        patch.object(provider, "_save_credentials"),
        patch.object(provider, "_run_auth_flow") as run_auth_flow,
    ):
        assert provider.get_credentials(implicit=True) is expired

    expired.refresh.assert_called_once()
    run_auth_flow.assert_not_called()


def test_server_implicit_login_without_tty_fails_fast() -> None:
    provider = _server("work")
    with (
        patch.object(provider, "_load_google_token", return_value=None),
        patch.object(provider, "_run_server_auth_flow") as run_server_auth_flow,
        pytest.raises(AuthError, match="Not authenticated") as exc,
    ):
        provider.get_credentials(implicit=True)

    assert "gws-cli auth --account work" in exc.value.details
    run_server_auth_flow.assert_not_called()


def test_server_refresh_without_relay_session_and_tty_fails_fast() -> None:
    """The refresh would auto-start the relay login; that needs a human too."""
    provider = _server("work")
    expired = MagicMock(valid=False, expired=True, refresh_token="refresh")
    with (
        patch.object(provider, "_load_google_token", return_value=expired),
        patch.object(provider, "_load_server_token", return_value=None),
        patch.object(provider, "server_login") as server_login,
        patch.object(provider, "_run_server_auth_flow") as run_server_auth_flow,
        pytest.raises(AuthError, match="Not authenticated"),
    ):
        provider.get_credentials(implicit=True)

    server_login.assert_not_called()
    run_server_auth_flow.assert_not_called()


def test_server_implicit_login_with_tty_runs_flow(monkeypatch) -> None:
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    provider = _server("work")
    with (
        patch.object(provider, "_load_google_token", return_value=None),
        patch.object(provider, "_run_server_auth_flow") as run_server_auth_flow,
    ):
        provider.get_credentials(implicit=True)

    run_server_auth_flow.assert_called_once()


def test_server_silent_refresh_without_tty_still_works() -> None:
    provider = _server("work")
    expired = MagicMock(valid=False, expired=True, refresh_token="refresh")
    with (
        patch.object(provider, "_load_google_token", return_value=expired),
        patch.object(provider, "_load_server_token", return_value={"access_token": "jwt"}),
        patch.object(provider, "_refresh_via_server") as refresh,
        patch.object(provider, "_run_server_auth_flow") as run_server_auth_flow,
    ):
        provider.get_credentials(implicit=True)

    refresh.assert_called_once()
    run_server_auth_flow.assert_not_called()


def test_service_auth_error_exits_with_json(capsys) -> None:
    class _Service(BaseService):
        SERVICE_NAME = "drive"
        VERSION = "v3"

    auth = MagicMock()
    auth.get_credentials.side_effect = AuthError("Not authenticated.", "Run 'gws-cli auth'.")

    with pytest.raises(SystemExit) as exc:
        _Service(auth_manager=auth).service

    assert exc.value.code == ExitCode.AUTH_ERROR
    auth.get_credentials.assert_called_once_with(implicit=True)
    out = json.loads(capsys.readouterr().out)
    assert out["error_code"] == "AUTH_ERROR"
    assert out["message"] == "Not authenticated."
    assert out["details"] == "Run 'gws-cli auth'."

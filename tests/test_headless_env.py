"""GWS_HEADLESS makes implicit logins headless, not just `auth --headless`.

Implicit logins happen when any command finds no token, or when a server-relay
refresh finds no relay session. Without a browser they would wait forever for a
loopback callback; with GWS_HEADLESS set they use the headless flows instead.
The default (unset) keeps the existing browser behavior.
"""

from unittest.mock import MagicMock, patch

import pytest

from gws.auth.oauth import LocalAuthProvider
from gws.auth.provider import headless_requested
from gws.auth.server import ServerAuthProvider
from gws.config import Config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep tests away from the real ~/.config/gws-cli (config, salt, tokens)."""
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    monkeypatch.setattr(Config, "_LEGACY_BASE_DIR", tmp_path / "legacy")
    monkeypatch.setattr(LocalAuthProvider, "_LEGACY_TOKEN_PATH", tmp_path / "token.json")
    monkeypatch.setattr(LocalAuthProvider, "CREDENTIALS_PATH", tmp_path / "client_secret.json")
    for var in ("GWS_ACCOUNT", "GWS_ENCRYPTION", "GWS_HEADLESS"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True), ("true", True), ("TRUE", True), ("yes", True), ("on", True), (" 1 ", True),
        ("0", False), ("false", False), ("no", False), ("off", False), ("", False),
    ],
)
def test_env_values(value: str, expected: bool, monkeypatch) -> None:
    monkeypatch.setenv("GWS_HEADLESS", value)
    assert headless_requested() is expected


def test_unset_env_is_not_headless() -> None:
    assert headless_requested() is False


def test_explicit_flag_is_headless_without_env() -> None:
    assert headless_requested(True) is True


@pytest.mark.parametrize(("env", "expected"), [(None, False), ("1", True)])
def test_local_implicit_login_follows_env(env, expected, monkeypatch) -> None:
    if env is not None:
        monkeypatch.setenv("GWS_HEADLESS", env)
    provider = LocalAuthProvider(config=Config())

    with (
        patch("gws.auth.oauth.load_encrypted", return_value=None),
        patch.object(provider, "_run_auth_flow") as run_auth_flow,
    ):
        provider.get_credentials()  # what every service command does when it needs a token

    assert run_auth_flow.call_args.kwargs["headless"] is expected


def _server_provider() -> ServerAuthProvider:
    provider = object.__new__(ServerAuthProvider)
    provider.server_url = "https://relay.example.com"
    provider.config = Config()
    provider._account_name = None
    provider._credentials = None
    provider._server_token = None
    return provider


@pytest.mark.parametrize(("env", "device_flow"), [(None, False), ("1", True)])
def test_server_refresh_relay_login_follows_env(env, device_flow, monkeypatch) -> None:
    """A Google-token refresh that finds no relay session must log in to the relay
    with device login when headless (the browser login can't complete there)."""
    if env is not None:
        monkeypatch.setenv("GWS_HEADLESS", env)
    provider = _server_provider()
    expired = MagicMock(valid=False, expired=True, refresh_token="refresh")

    with (
        patch.object(provider, "_load_google_token", return_value=expired),
        patch.object(provider, "_load_server_token", return_value=None),
        patch.object(provider, "server_login") as server_login,
        patch.object(provider, "_run_server_auth_flow") as run_server_auth_flow,
    ):
        provider.get_credentials()

    server_login.assert_called_once_with(device_flow=device_flow)
    assert run_server_auth_flow.call_args.kwargs["headless"] is device_flow

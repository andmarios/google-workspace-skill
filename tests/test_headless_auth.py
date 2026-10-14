"""Tests for local OAuth authentication on headless servers."""

import json
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import InvalidGrantError
from requests.exceptions import ConnectionError

from gws.auth.oauth import (
    LocalAuthProvider,
    _fetch_headless_token,
    _validate_headless_redirect,
)
from gws.auth.server import ServerAuthProvider
from gws.config import Config
from gws.exceptions import AuthError


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep tests away from the real ~/.config/gws-cli (config, salt, tokens)."""
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    monkeypatch.setattr(Config, "_LEGACY_BASE_DIR", tmp_path / "legacy")
    monkeypatch.setattr(LocalAuthProvider, "_LEGACY_TOKEN_PATH", tmp_path / "token.json")
    monkeypatch.setattr(LocalAuthProvider, "CREDENTIALS_PATH", tmp_path / "client_secret.json")
    monkeypatch.delenv("GWS_ACCOUNT", raising=False)
    return tmp_path


@pytest.fixture
def provider() -> LocalAuthProvider:
    return LocalAuthProvider(config=Config())


def _mock_flow(state: str = "expected-state") -> MagicMock:
    flow = MagicMock()
    flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?state=expected-state",
        state,
    )
    credentials = MagicMock()
    credentials.valid = True
    flow.credentials = credentials
    return flow


def test_real_installed_app_flow_generates_pkce_s256_challenge() -> None:
    client_config = {
        "installed": {
            "client_id": "test.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=["openid"],
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = "http://127.0.0.1:8080/"

    authorization_url, state = flow.authorization_url()
    query = parse_qs(urlparse(authorization_url).query)

    assert query["state"] == [state]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
    assert flow.code_verifier


def test_real_installed_app_flow_accepts_pasted_http_loopback_response() -> None:
    client_config = {
        "installed": {
            "client_id": "test.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=["openid"],
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = "http://127.0.0.1:8080/"
    _, state = flow.authorization_url()
    redirect = f"http://127.0.0.1:8080/?code=one-time-code&state={state}"
    token = {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch.object(flow.oauth2session, "request") as request:
        response = MagicMock(status_code=200, headers={}, text=json.dumps(token))
        response.request = MagicMock(url="https://oauth2.googleapis.com/token", headers={}, body="")
        request.return_value = response

        _fetch_headless_token(flow, redirect)

    assert flow.credentials.token == "access-token"
    token_request = request.call_args.kwargs["data"]
    assert token_request["redirect_uri"] == "http://127.0.0.1:8080/"
    assert token_request["code"] == "one-time-code"
    assert token_request["code_verifier"] == flow.code_verifier


def test_headless_flow_exchanges_full_redirect_without_local_server(
    provider: LocalAuthProvider,
) -> None:
    flow = _mock_flow()
    redirect = "http://127.0.0.1:8080/?code=one-time-code&state=expected-state"

    with (
        patch("gws.auth.oauth.load_encrypted", return_value={"installed": {}}),
        patch("gws.auth.oauth.InstalledAppFlow.from_client_config", return_value=flow),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", return_value=redirect),
        patch.object(provider, "_save_credentials") as save_credentials,
        patch("gws.auth.oauth.webbrowser.open") as open_browser,
    ):
        credentials = provider.get_credentials(headless=True)

    assert credentials is flow.credentials
    assert flow.redirect_uri == "http://127.0.0.1:8080/"
    flow.fetch_token.assert_called_once_with(
        authorization_response="https://127.0.0.1:8080/?code=one-time-code&state=expected-state"
    )
    flow.run_local_server.assert_not_called()
    open_browser.assert_not_called()
    save_credentials.assert_called_once_with()


def test_default_flow_still_uses_local_server(provider: LocalAuthProvider) -> None:
    flow = _mock_flow()
    flow.run_local_server.return_value = flow.credentials

    with (
        patch("gws.auth.oauth.load_encrypted", return_value={"installed": {}}),
        patch(
            "gws.auth.oauth.InstalledAppFlow.from_client_config", return_value=flow
        ) as from_client_config,
        patch.object(provider, "_find_available_port", return_value=8080),
        patch.object(provider, "_save_credentials"),
    ):
        provider.get_credentials()

    flow.run_local_server.assert_called_once()
    flow.fetch_token.assert_not_called()
    # The browser flow must keep the library's PKCE default, exactly as before headless mode.
    assert "autogenerate_code_verifier" not in from_client_config.call_args.kwargs


def test_headless_flow_requests_pkce_on_real_flow(provider: LocalAuthProvider, capsys) -> None:
    """google-auth-oauthlib < 1.3 only enables PKCE when asked; headless must always ask."""
    client_config = {
        "installed": {
            "client_id": "test.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    def fake_load(path, key):
        return client_config if path == provider.CREDENTIALS_PATH else None

    with (
        patch("gws.auth.oauth.load_encrypted", side_effect=fake_load),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", side_effect=EOFError),
        pytest.raises(AuthError, match="cancelled"),
    ):
        provider.get_credentials(headless=True)

    printed = capsys.readouterr().err.split()
    authorization_url = next(word for word in printed if word.startswith("https://accounts"))
    query = parse_qs(urlparse(authorization_url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == ["http://127.0.0.1:8080/"]


@pytest.mark.parametrize(
    ("redirect_url", "message"),
    [
        ("http://127.0.0.1:8080/?code=x&state=wrong", "state"),
        ("http://127.0.0.1:8080/?state=expected-state", "authorization code"),
        ("https://127.0.0.1:8080/?code=x&state=expected-state", "redirect URI"),
        ("http://localhost:8080/?code=x&state=expected-state", "redirect URI"),
        ("http://127.0.0.1:8081/?code=x&state=expected-state", "redirect URI"),
        ("http://user@127.0.0.1:8080/?code=x&state=expected-state", "redirect URI"),
        ("http://127.0.0.1:bad/?code=x&state=expected-state", "redirect URI"),
        ("http://127.0.0.1:8080/?error=access_denied&state=expected-state", "denied"),
        ("http://127.0.0.1:8080/?error=access_denied&state=wrong", "state"),
        ("http://127.0.0.1:8080/?error=access_denied", "state"),
        (
            "http://127.0.0.1:8080/?error=access_denied&state=expected-state&state=other",
            "state",
        ),
        ("http://127.0.0.1:8080/?code=x&code=y&state=expected-state", "exactly one"),
        ("http://127.0.0.1:8080/?code=x&state=expected-state#fragment", "fragment"),
    ],
)
def test_headless_redirect_rejects_invalid_input(redirect_url: str, message: str) -> None:
    with pytest.raises(AuthError, match=message):
        _validate_headless_redirect(
            redirect_url,
            expected_redirect_uri="http://127.0.0.1:8080/",
            expected_state="expected-state",
        )


def test_headless_redirect_accepts_expected_loopback_url() -> None:
    _validate_headless_redirect(
        "http://127.0.0.1:8080/?code=one-time-code&state=expected-state",
        expected_redirect_uri="http://127.0.0.1:8080/",
        expected_state="expected-state",
    )


def test_headless_flow_does_not_echo_pasted_redirect(provider: LocalAuthProvider, capsys) -> None:
    flow = _mock_flow()
    secret_redirect = (
        "http://127.0.0.1:8080/?code=SECRET-AUTHORIZATION-CODE&state=expected-state"
    )

    with (
        patch("gws.auth.oauth.load_encrypted", return_value={"installed": {}}),
        patch("gws.auth.oauth.InstalledAppFlow.from_client_config", return_value=flow),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", return_value=secret_redirect),
        patch.object(provider, "_save_credentials"),
    ):
        provider.get_credentials(headless=True)

    captured = capsys.readouterr()
    assert "SECRET-AUTHORIZATION-CODE" not in captured.out
    assert "SECRET-AUTHORIZATION-CODE" not in captured.err


def test_headless_flow_treats_eof_as_cancellation(provider: LocalAuthProvider) -> None:
    flow = _mock_flow()

    with (
        patch("gws.auth.oauth.load_encrypted", return_value={"installed": {}}),
        patch("gws.auth.oauth.InstalledAppFlow.from_client_config", return_value=flow),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", side_effect=EOFError),
        pytest.raises(AuthError, match="cancelled"),
    ):
        provider.get_credentials(headless=True)

    flow.fetch_token.assert_not_called()


def test_headless_flow_wraps_token_exchange_network_error(provider: LocalAuthProvider) -> None:
    flow = _mock_flow()
    flow.fetch_token.side_effect = ConnectionError("network unavailable")
    redirect = "http://127.0.0.1:8080/?code=one-time-code&state=expected-state"

    with (
        patch("gws.auth.oauth.load_encrypted", return_value={"installed": {}}),
        patch("gws.auth.oauth.InstalledAppFlow.from_client_config", return_value=flow),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", return_value=redirect),
        pytest.raises(AuthError, match="exchange"),
    ):
        provider.get_credentials(headless=True)


def test_headless_flow_wraps_oauth_protocol_error_without_leaking_code(
    provider: LocalAuthProvider,
    capsys,
) -> None:
    flow = _mock_flow()
    flow.fetch_token.side_effect = InvalidGrantError()
    redirect = "http://127.0.0.1:8080/?code=SECRET-CODE&state=expected-state"

    with (
        patch("gws.auth.oauth.load_encrypted", return_value={"installed": {}}),
        patch("gws.auth.oauth.InstalledAppFlow.from_client_config", return_value=flow),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", return_value=redirect),
        pytest.raises(AuthError, match="exchange"),
    ):
        provider.get_credentials(headless=True)

    captured = capsys.readouterr()
    assert "SECRET-CODE" not in captured.out
    assert "SECRET-CODE" not in captured.err


def test_server_headless_bootstrap_uses_device_flow() -> None:
    provider = object.__new__(ServerAuthProvider)
    provider._server_token = None

    with (
        patch.object(
            provider,
            "_load_server_token",
            side_effect=[None, {"access_token": "server"}],
        ),
        patch.object(provider, "server_login") as server_login,
    ):
        token = provider._ensure_server_token(headless=True)

    assert token == {"access_token": "server"}
    server_login.assert_called_once_with(device_flow=True)


def test_server_headless_flow_does_not_open_browser() -> None:
    provider = object.__new__(ServerAuthProvider)
    provider.server_url = "https://relay.example.com"
    provider.config = Config()
    provider._account_name = None
    provider._credentials = None
    provider._server_token = None

    responses = [
        MagicMock(
            status_code=200,
            json=lambda: {
                "auth_url": "https://accounts.google.com/o/oauth2/auth",
                "session_id": "session-1",
            },
        ),
        MagicMock(
            status_code=200,
            json=lambda: {"access_token": "access", "expires_in": 3600},
        ),
    ]

    with (
        patch.object(provider, "_ensure_server_token", return_value={"access_token": "server"}),
        patch.object(provider, "_discover_relay_provider", return_value="google"),
        patch.object(provider, "_server_request", side_effect=responses),
        patch.object(provider, "_save_google_token") as save_token,
        patch("gws.auth.server.webbrowser.get", return_value=MagicMock()),
        patch("gws.auth.server.webbrowser.open") as open_browser,
        patch("gws.auth.server.time.sleep"),
    ):
        provider._run_server_auth_flow(headless=True)

    open_browser.assert_not_called()
    save_token.assert_called_once_with({"access_token": "access", "expires_in": 3600})

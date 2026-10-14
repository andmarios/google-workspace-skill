"""`auth --force` keeps the existing token until the new login succeeds.

The old token is no longer revoked or deleted up front, so a cancelled or
failed re-login leaves the user logged in. Because the old grant is kept, a
forced local login asks Google for prompt=consent, which guarantees a fresh
refresh token (Google may omit it when re-authorizing an existing grant).
"""

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from google.oauth2.credentials import Credentials
from typer.testing import CliRunner

from gws.auth.oauth import LocalAuthProvider
from gws.cli import app
from gws.config import Config
from gws.crypto import load_encrypted, save_encrypted
from gws.exceptions import AuthError, ExitCode

runner = CliRunner()

CLIENT_CONFIG = {
    "installed": {
        "client_id": "test.apps.googleusercontent.com",
        "client_secret": "test-secret",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
OLD_TOKEN = {
    "token": "old-access",
    "refresh_token": "old-refresh",
    "client_id": "test.apps.googleusercontent.com",
    "client_secret": "test-secret",
}


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


@pytest.fixture
def stored_token() -> bytes | None:
    """Store a client config and an existing token with real encryption."""
    key = Config.load().get_encryption_key()
    save_encrypted(LocalAuthProvider.CREDENTIALS_PATH, CLIENT_CONFIG, key)
    save_encrypted(LocalAuthProvider._LEGACY_TOKEN_PATH, OLD_TOKEN, key)
    return key


def test_cancelled_force_login_keeps_existing_token(stored_token) -> None:
    with (
        patch.object(LocalAuthProvider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", side_effect=EOFError),
        patch.object(LocalAuthProvider, "_revoke_token_best_effort") as revoke,
    ):
        result = runner.invoke(app, ["auth", "--force", "--headless"])

    assert result.exit_code == ExitCode.AUTH_ERROR
    revoke.assert_not_called()
    assert load_encrypted(LocalAuthProvider._LEGACY_TOKEN_PATH, stored_token) == OLD_TOKEN


def test_successful_force_login_replaces_token(stored_token) -> None:
    new_credentials = Credentials(
        token="new-access",
        refresh_token="new-refresh",
        client_id="test.apps.googleusercontent.com",
        client_secret="test-secret",
        token_uri="https://oauth2.googleapis.com/token",
    )

    def fake_headless_flow(self, *args, **kwargs):
        self._credentials = new_credentials

    with (
        patch.object(LocalAuthProvider, "_find_available_port", return_value=8080),
        patch.object(LocalAuthProvider, "_run_headless_auth_flow", fake_headless_flow),
        patch.object(LocalAuthProvider, "_revoke_token_best_effort") as revoke,
    ):
        result = runner.invoke(app, ["auth", "--force", "--headless"])

    assert result.exit_code == 0, result.output
    revoke.assert_not_called()
    saved = load_encrypted(LocalAuthProvider._LEGACY_TOKEN_PATH, stored_token)
    assert saved is not None
    assert saved["refresh_token"] == "new-refresh"


def _client_config_only(path, key):
    return CLIENT_CONFIG if path == LocalAuthProvider.CREDENTIALS_PATH else None


@pytest.mark.parametrize("force", [False, True])
def test_browser_flow_requests_consent_only_when_forced(force: bool) -> None:
    provider = LocalAuthProvider(config=Config())
    flow = MagicMock()
    flow.run_local_server.return_value = MagicMock(valid=True)

    with (
        patch("gws.auth.oauth.load_encrypted", side_effect=_client_config_only),
        patch("gws.auth.oauth.InstalledAppFlow.from_client_config", return_value=flow),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch.object(provider, "_save_credentials"),
    ):
        provider.get_credentials(force_refresh=force)

    kwargs = flow.run_local_server.call_args.kwargs
    if force:
        assert kwargs["prompt"] == "consent"
    else:
        assert "prompt" not in kwargs  # normal login: call unchanged


@pytest.mark.parametrize("force", [False, True])
def test_headless_flow_requests_consent_only_when_forced(force: bool, capsys) -> None:
    provider = LocalAuthProvider(config=Config())

    with (
        patch("gws.auth.oauth.load_encrypted", side_effect=_client_config_only),
        patch.object(provider, "_find_available_port", return_value=8080),
        patch("gws.auth.oauth.getpass", side_effect=EOFError),
        pytest.raises(AuthError, match="cancelled"),
    ):
        provider.get_credentials(force_refresh=force, headless=True)

    printed = capsys.readouterr().err.split()
    authorization_url = next(word for word in printed if word.startswith("https://accounts"))
    query = parse_qs(urlparse(authorization_url).query)
    assert query.get("prompt") == (["consent"] if force else None)

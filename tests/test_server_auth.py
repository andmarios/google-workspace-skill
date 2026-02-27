"""Tests for ServerAuthProvider token loading and saving."""

import json
import stat
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, PropertyMock

import pytest
from google.oauth2.credentials import Credentials

from gws.auth.server import ServerAuthProvider
from gws.config import Config


class TestServerAuthTokenHandling:
    """Tests for server token load/save methods."""

    @pytest.fixture
    def provider(self, tmp_path):
        """Create a ServerAuthProvider with mocked paths, bypassing __init__."""
        with patch.object(ServerAuthProvider, "__init__", lambda self, *a, **kw: None):
            p = ServerAuthProvider("unused")

        # Set internal state that __init__ would normally set
        p.config = Config()
        p._account_name = None
        p._credentials = None
        p._server_token = None

        # Override the path properties to use tmp_path
        p._LEGACY_TOKEN_PATH = tmp_path / "token.json"

        # Store tmp_path for property patching in individual tests
        p._test_tmp_path = tmp_path

        return p

    @pytest.fixture
    def provider_with_paths(self, provider, tmp_path):
        """Provider with both path properties patched to tmp_path."""
        # We patch the properties at the class level for the duration of the test
        server_token_path = tmp_path / "server_token.json"
        token_path = tmp_path / "token.json"

        # Since _server_token_path and TOKEN_PATH are properties, we need
        # to patch them on the class.  We return context managers that tests
        # can use, or we can create a helper.
        provider._patched_server_token_path = server_token_path
        provider._patched_token_path = token_path
        return provider

    # ── _load_server_token tests ──────────────────────────────────────

    def test_load_server_token_valid(self, provider, tmp_path):
        """Valid server token JSON loads correctly."""
        server_token_path = tmp_path / "server_token.json"
        token_data = {"access_token": "abc123", "refresh_token": "xyz789"}
        server_token_path.write_text(json.dumps(token_data))

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            result = provider._load_server_token()

        assert result is not None
        assert result["access_token"] == "abc123"
        assert result["refresh_token"] == "xyz789"

    def test_load_server_token_corrupt_json(self, provider, tmp_path):
        """Corrupt JSON returns None (with stderr warning)."""
        server_token_path = tmp_path / "server_token.json"
        server_token_path.write_text("not valid json {{{")

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            result = provider._load_server_token()

        assert result is None

    def test_load_server_token_missing_file(self, provider, tmp_path):
        """Missing file returns None."""
        server_token_path = tmp_path / "nonexistent_server_token.json"

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            result = provider._load_server_token()

        assert result is None

    def test_load_server_token_caches_result(self, provider, tmp_path):
        """Loading a valid token caches it in self._server_token."""
        server_token_path = tmp_path / "server_token.json"
        token_data = {"access_token": "cached", "refresh_token": "also-cached"}
        server_token_path.write_text(json.dumps(token_data))

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            provider._load_server_token()

        assert provider._server_token is not None
        assert provider._server_token["access_token"] == "cached"

    def test_load_server_token_returns_cached(self, provider):
        """If _server_token is already set, returns it without reading disk."""
        provider._server_token = {"access_token": "from-cache"}

        result = provider._load_server_token()

        assert result is not None
        assert result["access_token"] == "from-cache"

    # ── _save_server_token tests ──────────────────────────────────────

    def test_save_server_token_creates_file(self, provider, tmp_path):
        """Saving server token creates the file."""
        server_token_path = tmp_path / "server_token.json"
        token_data = {"access_token": "secret", "refresh_token": "also-secret"}

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            provider._save_server_token(token_data)

        assert server_token_path.exists()

    def test_save_server_token_permissions(self, provider, tmp_path):
        """Saved server token file should have 0o600 permissions."""
        server_token_path = tmp_path / "server_token.json"
        token_data = {"access_token": "secret", "refresh_token": "also-secret"}

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            provider._save_server_token(token_data)

        mode = stat.S_IMODE(server_token_path.stat().st_mode)
        assert mode == 0o600

    def test_save_server_token_content(self, provider, tmp_path):
        """Saved server token should be valid JSON with correct content."""
        server_token_path = tmp_path / "server_token.json"
        token_data = {"access_token": "abc", "refresh_token": "xyz"}

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            provider._save_server_token(token_data)

        loaded = json.loads(server_token_path.read_text())
        assert loaded["access_token"] == "abc"
        assert loaded["refresh_token"] == "xyz"

    def test_save_server_token_updates_cache(self, provider, tmp_path):
        """Saving server token also updates the in-memory cache."""
        server_token_path = tmp_path / "server_token.json"
        token_data = {"access_token": "new-value"}

        with patch.object(
            ServerAuthProvider, "_server_token_path", new_callable=PropertyMock, return_value=server_token_path
        ):
            provider._save_server_token(token_data)

        assert provider._server_token == token_data

    # ── _load_google_token tests ──────────────────────────────────────

    def test_load_google_token_missing_file(self, provider, tmp_path):
        """Missing Google token file returns None."""
        token_path = tmp_path / "token.json"

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            result = provider._load_google_token()

        assert result is None

    def test_load_google_token_corrupt_json(self, provider, tmp_path):
        """Corrupt Google token file returns None."""
        token_path = tmp_path / "token.json"
        token_path.write_text("{{corrupt}}")

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            result = provider._load_google_token()

        assert result is None

    def test_load_google_token_no_token_field(self, provider, tmp_path):
        """Token file without 'token' field returns None."""
        token_path = tmp_path / "token.json"
        token_path.write_text(json.dumps({"refresh_token": "abc"}))

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            result = provider._load_google_token()

        assert result is None

    def test_load_google_token_valid_with_expiry(self, provider, tmp_path):
        """Valid token with future expiry loads correctly."""
        token_path = tmp_path / "token.json"
        future_expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        token_data = {
            "token": "access-token-123",
            "refresh_token": "refresh-123",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "client-id",
            "client_secret": "",
            "expiry": future_expiry,
        }
        token_path.write_text(json.dumps(token_data))

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            creds = provider._load_google_token()

        assert creds is not None
        assert isinstance(creds, Credentials)
        assert creds.token == "access-token-123"
        assert creds.refresh_token == "refresh-123"

    def test_load_google_token_strips_tzinfo(self, provider, tmp_path):
        """Loaded token expiry should have tzinfo stripped (google-auth uses naive UTC)."""
        token_path = tmp_path / "token.json"
        future_expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        token_data = {
            "token": "tok",
            "refresh_token": "ref",
            "expiry": future_expiry,
        }
        token_path.write_text(json.dumps(token_data))

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            creds = provider._load_google_token()

        assert creds is not None
        assert creds.expiry.tzinfo is None

    def test_load_google_token_no_expiry_field(self, provider, tmp_path):
        """Token without expiry field gets a past expiry (treated as expired)."""
        token_path = tmp_path / "token.json"
        token_data = {
            "token": "tok",
            "refresh_token": "ref",
        }
        token_path.write_text(json.dumps(token_data))

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            creds = provider._load_google_token()

        assert creds is not None
        # Should be set to year 2000, which is in the past
        assert creds.expiry.year == 2000

    def test_load_google_token_invalid_expiry_string(self, provider, tmp_path):
        """Invalid expiry string defaults to year 2000 (expired)."""
        token_path = tmp_path / "token.json"
        token_data = {
            "token": "tok",
            "refresh_token": "ref",
            "expiry": "not-a-date",
        }
        token_path.write_text(json.dumps(token_data))

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            creds = provider._load_google_token()

        assert creds is not None
        assert creds.expiry.year == 2000

    def test_load_google_token_uses_default_token_uri(self, provider, tmp_path):
        """Missing token_uri defaults to Google's OAuth endpoint."""
        token_path = tmp_path / "token.json"
        token_data = {"token": "tok", "refresh_token": "ref"}
        token_path.write_text(json.dumps(token_data))

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            creds = provider._load_google_token()

        assert creds is not None
        assert creds.token_uri == "https://oauth2.googleapis.com/token"

    # ── _save_google_token tests ──────────────────────────────────────

    def test_save_google_token_creates_file(self, provider, tmp_path):
        """Saving Google token creates the file on disk."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "abc", "expires_in": 3600}

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data)

        assert token_path.exists()

    def test_save_google_token_permissions(self, provider, tmp_path):
        """Saved Google token should have 0o600 permissions."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "abc", "expires_in": 3600}

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data)

        mode = stat.S_IMODE(token_path.stat().st_mode)
        assert mode == 0o600

    def test_save_google_token_content(self, provider, tmp_path):
        """Saved Google token should contain access_token as 'token' key."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "my-access-token", "expires_in": 3600}

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data)

        loaded = json.loads(token_path.read_text())
        assert loaded["token"] == "my-access-token"
        assert loaded["token_uri"] == "https://oauth2.googleapis.com/token"
        assert "expiry" in loaded

    def test_save_google_token_sets_credentials(self, provider, tmp_path):
        """Saving Google token should update internal _credentials."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "new-token", "expires_in": 3600}

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data, refresh_token="refresh-123")

        assert provider._credentials is not None
        assert isinstance(provider._credentials, Credentials)
        assert provider._credentials.token == "new-token"
        assert provider._credentials.refresh_token == "refresh-123"

    def test_save_google_token_uses_refresh_from_token_data(self, provider, tmp_path):
        """refresh_token from token_data takes precedence over the argument."""
        token_path = tmp_path / "token.json"
        token_data = {
            "access_token": "tok",
            "expires_in": 3600,
            "refresh_token": "from-data",
        }

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data, refresh_token="from-arg")

        # token_data's refresh_token should win (it's first in the get() chain)
        assert provider._credentials.refresh_token == "from-data"
        loaded = json.loads(token_path.read_text())
        assert loaded["refresh_token"] == "from-data"

    def test_save_google_token_falls_back_to_arg_refresh(self, provider, tmp_path):
        """When token_data lacks refresh_token, falls back to the argument."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "tok", "expires_in": 3600}

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data, refresh_token="fallback-ref")

        assert provider._credentials.refresh_token == "fallback-ref"
        loaded = json.loads(token_path.read_text())
        assert loaded["refresh_token"] == "fallback-ref"

    def test_save_google_token_expiry_is_future(self, provider, tmp_path):
        """Saved expiry should be approximately now + expires_in seconds."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "tok", "expires_in": 7200}

        before = datetime.now(timezone.utc)

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data)

        after = datetime.now(timezone.utc)

        loaded = json.loads(token_path.read_text())
        saved_expiry = datetime.fromisoformat(loaded["expiry"])
        # The saved expiry (naive UTC) should be within the expected range
        expected_min = (before + timedelta(seconds=7200)).replace(tzinfo=None)
        expected_max = (after + timedelta(seconds=7200)).replace(tzinfo=None)
        assert expected_min <= saved_expiry <= expected_max

    def test_save_google_token_default_expires_in(self, provider, tmp_path):
        """When expires_in is missing, defaults to 3600 seconds."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "tok"}

        before = datetime.now(timezone.utc)

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data)

        after = datetime.now(timezone.utc)

        loaded = json.loads(token_path.read_text())
        saved_expiry = datetime.fromisoformat(loaded["expiry"])
        expected_min = (before + timedelta(seconds=3600)).replace(tzinfo=None)
        expected_max = (after + timedelta(seconds=3600)).replace(tzinfo=None)
        assert expected_min <= saved_expiry <= expected_max

    def test_save_google_token_client_id_from_data(self, provider, tmp_path):
        """client_id from token_data is preserved in the saved file."""
        token_path = tmp_path / "token.json"
        token_data = {
            "access_token": "tok",
            "expires_in": 3600,
            "client_id": "my-client-id",
        }

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data)

        loaded = json.loads(token_path.read_text())
        assert loaded["client_id"] == "my-client-id"

    def test_save_google_token_default_client_id(self, provider, tmp_path):
        """When client_id is missing, defaults to 'server-managed'."""
        token_path = tmp_path / "token.json"
        token_data = {"access_token": "tok", "expires_in": 3600}

        with patch.object(
            ServerAuthProvider, "TOKEN_PATH", new_callable=PropertyMock, return_value=token_path
        ):
            provider._save_google_token(token_data)

        loaded = json.loads(token_path.read_text())
        assert loaded["client_id"] == "server-managed"

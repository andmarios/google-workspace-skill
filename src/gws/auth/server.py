"""Server auth provider — delegates authentication to an oauth-token-relay server."""

from __future__ import annotations

import hashlib
import json
import secrets
import base64
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from google.oauth2.credentials import Credentials

from gws.config import Config, _write_secure_file
from gws.exceptions import AuthError


class ServerAuthProvider:
    """Auth provider that delegates OAuth to an oauth-token-relay server.

    The server handles:
    - OAuth 2.1 authentication of the CLI user (PKCE or device flow)
    - Provider resolution (which Google OAuth app to use)
    - Token exchange with Google (using server-held client_secret)
    - Token refresh via the server

    The CLI holds:
    - A server JWT (for authenticating to the relay server)
    - Google API tokens (obtained through the relay, stored locally)
    """

    _LEGACY_TOKEN_PATH = Path.home() / ".config" / "gws-cli" / "token.json"
    _SERVER_TOKEN_FILENAME = "server_token.json"

    def __init__(
        self,
        server_url: str,
        account: str | None = None,
        config: Config | None = None,
    ):
        self.server_url = server_url.rstrip("/")
        from gws.auth.provider import _validate_server_url
        _validate_server_url(self.server_url)
        self.config = config or Config.load()
        self._account_name = self.config.resolve_account(account)

        # Validate account if specified
        if self._account_name and self.config.accounts:
            if self._account_name not in self.config.accounts.entries:
                raise AuthError(
                    f"Account '{self._account_name}' not found",
                    f"Available accounts: {', '.join(self.config.accounts.entries.keys())}",
                )
        elif self._account_name and not self.config.accounts:
            raise AuthError(
                f"Account '{self._account_name}' specified but no accounts are configured",
                "Use 'gws-cli account add <name>' to set up multi-account mode.",
            )

        # Load effective config for this account
        if self._account_name:
            self.config = self.config.load_effective_config(self._account_name)

        self._credentials: Credentials | None = None
        self._server_token: dict[str, Any] | None = None

    @property
    def account_name(self) -> str | None:
        """The resolved account name, or None for legacy mode."""
        return self._account_name

    @property
    def TOKEN_PATH(self) -> Path:  # noqa: N802
        """Path to the Google API token file (same layout as local mode)."""
        if self._account_name:
            return self.config.get_account_dir(self._account_name) / "token.json"
        return self._LEGACY_TOKEN_PATH

    @property
    def _server_token_path(self) -> Path:
        """Path to the server JWT file."""
        if self._account_name:
            return self.config.get_account_dir(self._account_name) / self._SERVER_TOKEN_FILENAME
        return Path.home() / ".config" / "gws-cli" / self._SERVER_TOKEN_FILENAME

    # ── AuthProvider protocol methods ─────────────────────────────────

    def get_credentials(self, force_refresh: bool = False) -> Credentials:
        """Get valid Google API credentials via the server relay.

        Flow:
        1. Load cached credentials from local token file
        2. If valid and not force_refresh, return them
        3. If expired, refresh via server (POST /auth/tokens/refresh)
        4. If no credentials, initiate full flow via server
        5. Save credentials locally
        """
        if self._credentials and self._credentials.valid and not force_refresh:
            return self._credentials

        # Try loading existing Google token (with expiry)
        if self.TOKEN_PATH.exists() and not force_refresh:
            self._credentials = self._load_google_token()

        # Refresh if expired
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._refresh_via_server(self._credentials.refresh_token)
                return self._credentials  # Set by _refresh_via_server
            except Exception:
                self._credentials = None

        # Full flow: start → browser → complete
        if not self._credentials or not self._credentials.valid:
            self._run_server_auth_flow()

        return self._credentials  # type: ignore[return-value]

    def delete_token(self) -> bool:
        """Delete the Google API token file."""
        if self.TOKEN_PATH.exists():
            self.TOKEN_PATH.unlink()
            return True
        return False

    def check_credentials(self) -> tuple[bool, str, Credentials | None]:
        """Check credentials without triggering interactive auth."""
        # Check server connection first
        server_token = self._load_server_token()
        if not server_token:
            return False, "no_server_token", None

        if not self.TOKEN_PATH.exists():
            return False, "no_token", None

        credentials = self._load_google_token()
        if not credentials:
            return False, "invalid_token", None

        if credentials.valid:
            return True, "valid", credentials

        if credentials.expired and credentials.refresh_token:
            try:
                self._refresh_via_server(credentials.refresh_token)
                return True, "refreshed", self._credentials
            except Exception as e:
                return False, f"refresh_failed: {e}", None

        return False, "expired_no_refresh", credentials

    # ── Server authentication (CLI user → relay server) ───────────────

    def server_login(self, device_flow: bool = False) -> None:
        """Authenticate the CLI user to the relay server.

        Uses OAuth 2.1 PKCE flow (default) or device flow (for headless).
        Stores the server JWT locally.
        """
        if device_flow:
            self._server_device_flow()
        else:
            self._server_pkce_flow()

    def server_logout(self) -> None:
        """Revoke server token and delete local server_token.json."""
        server_token = self._load_server_token()
        if server_token:
            # Best-effort revoke on server
            try:
                self._server_request(
                    "POST",
                    "/oauth/revoke",
                    json_data={"token": server_token.get("refresh_token", "")},
                )
            except Exception:
                pass  # Server might be unreachable; still clean up locally

        if self._server_token_path.exists():
            self._server_token_path.unlink()
        self._server_token = None

    def server_status(self) -> dict[str, Any]:
        """Check server connection and authentication status."""
        result: dict[str, Any] = {"server_url": self.server_url}

        # Check server health
        try:
            resp = httpx.get(f"{self.server_url}/health", timeout=10)
            health = resp.json()
            result["server_reachable"] = True
            result["server_status"] = health.get("status", "unknown")
            result["providers"] = health.get("providers", [])
        except Exception as e:
            result["server_reachable"] = False
            result["server_error"] = str(e)
            return result

        # Check local server token
        server_token = self._load_server_token()
        if server_token:
            result["authenticated"] = True
            result["server_token_path"] = str(self._server_token_path)
        else:
            result["authenticated"] = False
            result["hint"] = "Run 'gws-cli auth server-login' to authenticate."

        return result

    # ── Private: server PKCE flow ─────────────────────────────────────

    def _server_pkce_flow(self) -> None:
        """OAuth 2.1 PKCE authorization code flow against the relay server."""
        # Generate PKCE verifier + challenge
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()

        state = secrets.token_urlsafe(32)

        # Build authorize URL
        redirect_uri = f"{self.server_url}/oauth/cli-callback"
        params = {
            "response_type": "code",
            "client_id": "cli",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "redirect_uri": redirect_uri,
        }
        auth_url = f"{self.server_url}/oauth/authorize?{urlencode(params)}"

        print("\n" + "=" * 60, file=sys.stderr)
        print("OAuth Token Relay Server Authentication Required", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # Try to open browser
        try:
            can_open = webbrowser.get() is not None
        except webbrowser.Error:
            can_open = False

        if can_open:
            print(f"\nOpening browser to:\n{auth_url}\n", file=sys.stderr)
            webbrowser.open(auth_url)
        else:
            print(f"\nOpen this URL in your browser:\n{auth_url}\n", file=sys.stderr)

        # Poll for authorization code (server stores it when browser callback arrives)
        print("Waiting for authorization...\n", file=sys.stderr)

        code = None
        deadline = time.monotonic() + 600  # 10 minute timeout
        while time.monotonic() < deadline:
            time.sleep(2)

            try:
                poll_resp = httpx.get(
                    f"{self.server_url}/oauth/cli-poll",
                    params={"state": state},
                    timeout=10,
                )
            except httpx.RequestError:
                continue  # Network hiccup, retry

            if poll_resp.status_code == 200:
                code = poll_resp.json().get("code")
                break
            elif poll_resp.status_code == 202:
                continue  # Still pending
            else:
                raise AuthError(
                    "Server authentication failed",
                    f"Poll error: {poll_resp.status_code} {poll_resp.text}",
                )

        if not code:
            raise AuthError("Authorization timed out. Please try again.")

        # Exchange code for tokens
        resp = httpx.post(
            f"{self.server_url}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "cli",
                "code_verifier": verifier,
                "redirect_uri": redirect_uri,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            raise AuthError(
                "Server authentication failed",
                f"Status {resp.status_code}: {resp.text}",
            )

        token_data = resp.json()
        self._save_server_token(token_data)
        print("\nServer authentication successful!\n", file=sys.stderr)

    # ── Private: server device flow ───────────────────────────────────

    def _server_device_flow(self) -> None:
        """OAuth 2.1 device authorization flow (for headless/SSH)."""
        # Initiate device flow
        resp = httpx.post(f"{self.server_url}/oauth/device", timeout=30)

        if resp.status_code != 200:
            raise AuthError(
                "Device flow initiation failed",
                f"Status {resp.status_code}: {resp.text}",
            )

        device_data = resp.json()
        user_code = device_data["user_code"]
        verification_uri = device_data["verification_uri"]
        device_code = device_data["device_code"]
        interval = device_data.get("interval", 5)
        expires_in = device_data.get("expires_in", 300)

        print("\n" + "=" * 60, file=sys.stderr)
        print("Server Authentication (Device Flow)", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"\nGo to: {verification_uri}", file=sys.stderr)
        print(f"Enter code: {user_code}\n", file=sys.stderr)
        print("Waiting for authorization...", file=sys.stderr)

        # Poll for completion
        deadline = time.monotonic() + expires_in
        while time.monotonic() < deadline:
            time.sleep(interval)

            resp = httpx.post(
                f"{self.server_url}/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                },
                timeout=30,
            )

            if resp.status_code == 200:
                token_data = resp.json()
                self._save_server_token(token_data)
                print("\nServer authentication successful!\n", file=sys.stderr)
                return

            error = resp.json().get("error", "")
            if error == "authorization_pending":
                continue
            elif error == "slow_down":
                interval += 5
                continue
            else:
                raise AuthError(
                    "Device flow failed",
                    f"Error: {error} — {resp.json().get('error_description', '')}",
                )

        raise AuthError("Device flow timed out. Please try again.")

    # ── Private: Google token relay ───────────────────────────────────

    def _run_server_auth_flow(self) -> None:
        """Initiate upstream OAuth via the server relay.

        The CLI sends full scope URLs directly — the server is scope-agnostic
        and passes them through to the upstream provider as-is.
        """
        from gws.auth.scopes import get_scopes_for_services

        server_token = self._ensure_server_token()
        scopes = get_scopes_for_services(self.config.enabled_services)

        # Discover relay provider from server health endpoint
        provider = self._discover_relay_provider()

        # Start the flow — send full scope URLs, server passes them through
        resp = self._server_request(
            "POST",
            "/auth/tokens/start",
            json_data={"scopes": scopes, "provider": provider},
            bearer_token=server_token["access_token"],
        )

        if resp.status_code != 200:
            raise AuthError(
                "Failed to start token relay",
                f"Status {resp.status_code}: {resp.text}",
            )

        start_data = resp.json()
        auth_url = start_data["auth_url"]
        session_id = start_data["session_id"]

        print("\n" + "=" * 60, file=sys.stderr)
        account_label = f" (account: {self._account_name})" if self._account_name else ""
        print(f"Google OAuth Authorization Required for gws-cli{account_label}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        try:
            can_open = webbrowser.get() is not None
        except webbrowser.Error:
            can_open = False

        if can_open:
            print(f"\nOpening browser to:\n{auth_url}\n", file=sys.stderr)
            webbrowser.open(auth_url)
        else:
            print(f"\nOpen this URL in your browser:\n{auth_url}\n", file=sys.stderr)

        print("Waiting for authorization...\n", file=sys.stderr)

        # Poll for completion (server holds tokens for ~5min)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            time.sleep(3)

            resp = self._server_request(
                "POST",
                "/auth/tokens/complete",
                json_data={"session_id": session_id},
                bearer_token=server_token["access_token"],
            )

            if resp.status_code == 200:
                token_data = resp.json()
                self._save_google_token(token_data)
                print("Authorization successful! Token saved.\n", file=sys.stderr)
                return
            elif resp.status_code == 202:
                # Still pending
                continue
            else:
                raise AuthError(
                    "Token relay failed",
                    f"Status {resp.status_code}: {resp.text}",
                )

        raise AuthError("Authorization timed out. Please try again.")

    def _refresh_via_server(self, refresh_token: str) -> None:
        """Refresh Google API token via the server relay."""
        server_token = self._ensure_server_token()

        resp = self._server_request(
            "POST",
            "/auth/tokens/refresh",
            json_data={
                "refresh_token": refresh_token,
                "provider": self._discover_relay_provider(),
            },
            bearer_token=server_token["access_token"],
        )

        if resp.status_code != 200:
            raise AuthError(
                "Token refresh via server failed",
                f"Status {resp.status_code}: {resp.text}",
            )

        token_data = resp.json()
        self._save_google_token(token_data, refresh_token=refresh_token)

    # ── Private: helpers ──────────────────────────────────────────────

    def _discover_relay_provider(self) -> str:
        """Resolve which relay provider to use.

        Priority:
        1. Explicit config (server_provider in gws_config.json)
        2. Auto-discover from /health if exactly one provider exists
        3. Error with available options
        """
        # Check explicit config first
        if self.config.server_provider:
            return self.config.server_provider

        # Auto-discover from server
        try:
            resp = httpx.get(f"{self.server_url}/health", timeout=10)
            health = resp.json()
            providers = health.get("providers", [])
        except Exception as e:
            raise AuthError(
                "Cannot discover relay providers",
                f"Server health check failed: {e}",
            )

        if not providers:
            raise AuthError("No relay providers configured on the server.")

        if len(providers) == 1:
            return providers[0]

        raise AuthError(
            "Multiple relay providers available",
            f"Available: {', '.join(providers)}. "
            "Set one with: gws-cli config set-mode server --url <url> --provider <name>",
        )

    def _server_request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        bearer_token: str | None = None,
    ) -> httpx.Response:
        """Make an authenticated request to the relay server.

        Automatically refreshes the server JWT on 401 and retries once.
        """
        headers: dict[str, str] = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        resp = httpx.request(
            method,
            f"{self.server_url}{path}",
            json=json_data,
            headers=headers,
            timeout=30,
        )

        if resp.status_code == 401 and bearer_token:
            new_token = self._refresh_server_token()
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                resp = httpx.request(
                    method,
                    f"{self.server_url}{path}",
                    json=json_data,
                    headers=headers,
                    timeout=30,
                )

        return resp

    def _refresh_server_token(self) -> str | None:
        """Refresh the server JWT using the refresh_token.

        Returns the new access_token, or None if refresh failed.
        """
        server_token = self._load_server_token()
        if not server_token or not server_token.get("refresh_token"):
            return None

        try:
            resp = httpx.post(
                f"{self.server_url}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": server_token["refresh_token"],
                    "client_id": "cli",
                },
                timeout=30,
            )
        except httpx.RequestError:
            return None

        if resp.status_code != 200:
            return None

        new_token_data = resp.json()
        # Preserve the refresh_token if the server didn't issue a new one
        if "refresh_token" not in new_token_data:
            new_token_data["refresh_token"] = server_token["refresh_token"]
        self._save_server_token(new_token_data)
        return new_token_data.get("access_token")

    def _load_server_token(self) -> dict[str, Any] | None:
        """Load the server JWT from disk."""
        if self._server_token:
            return self._server_token

        if not self._server_token_path.exists():
            return None

        try:
            with open(self._server_token_path) as f:
                self._server_token = json.load(f)
            return self._server_token
        except (json.JSONDecodeError, TypeError):
            return None

    def _save_server_token(self, token_data: dict[str, Any]) -> None:
        """Save server JWT to disk."""
        _write_secure_file(self._server_token_path, json.dumps(token_data, indent=2))
        self._server_token = token_data

    def _ensure_server_token(self, auto_login: bool = True) -> dict[str, Any]:
        """Load server token, auto-triggering login if needed.

        When auto_login is True (the default), missing server tokens trigger
        the PKCE login flow automatically so the user never needs to run
        'gws-cli auth server-login' as a separate step.
        """
        token = self._load_server_token()
        if token:
            return token

        if not auto_login:
            raise AuthError(
                "Not authenticated to the server",
                "Run 'gws-cli auth server-login' first.",
            )

        # Auto-trigger server login — one fewer manual step for the user
        print("No server token found — starting server authentication...\n", file=sys.stderr)
        self.server_login()

        token = self._load_server_token()
        if not token:
            raise AuthError(
                "Server login completed but no token was saved.",
                "Try again with 'gws-cli auth server-login'.",
            )
        return token

    def _load_google_token(self) -> Credentials | None:
        """Load Google API credentials from disk with expiry support.

        We don't use Credentials.from_authorized_user_file() because it doesn't
        restore the expiry field, causing tokens to appear perpetually valid even
        when the access token has actually expired. Instead, we read the JSON
        directly and construct Credentials with the saved expiry.
        """
        from datetime import datetime

        if not self.TOKEN_PATH.exists():
            return None

        try:
            with open(self.TOKEN_PATH) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        token = data.get("token")
        if not token:
            return None

        expiry = None
        if data.get("expiry"):
            try:
                expiry = datetime.fromisoformat(data["expiry"])
            except (ValueError, TypeError):
                pass
        if expiry is None:
            # No saved expiry — treat as expired so refresh logic kicks in.
            # This handles tokens saved before expiry tracking was added.
            expiry = datetime(2000, 1, 1)
        # google-auth uses naive UTC datetimes internally (datetime.utcnow()),
        # so we must strip tzinfo to avoid comparison errors.
        if expiry.tzinfo is not None:
            expiry = expiry.replace(tzinfo=None)

        return Credentials(
            token=token,
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            expiry=expiry,
        )

    def _save_google_token(
        self,
        token_data: dict[str, Any],
        refresh_token: str | None = None,
    ) -> None:
        """Save Google API tokens with expiry as a JSON file."""
        from datetime import datetime, timedelta

        client_id = token_data.get("client_id", "server-managed")
        resolved_refresh = token_data.get("refresh_token", refresh_token)
        expires_in = token_data.get("expires_in", 3600)
        # Use naive UTC to match google-auth's internal convention
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        cred_data = {
            "token": token_data["access_token"],
            "refresh_token": resolved_refresh,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": client_id,
            "client_secret": "",  # Held by relay server, not needed locally
            "scopes": token_data.get("scopes", []),
            "expiry": expiry.isoformat(),
        }
        # Omit fields that are None (but keep expiry even if token_data had no expires_in)
        cred_data = {k: v for k, v in cred_data.items() if v is not None}

        _write_secure_file(self.TOKEN_PATH, json.dumps(cred_data, indent=2))

        self._credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=resolved_refresh,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret="",
            expiry=expiry,
        )


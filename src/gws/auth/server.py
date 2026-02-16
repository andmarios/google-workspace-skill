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

from gws.config import Config
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

    _LEGACY_TOKEN_PATH = Path.home() / ".claude" / ".google-workspace" / "token.json"
    _SERVER_TOKEN_FILENAME = "server_token.json"

    def __init__(
        self,
        server_url: str,
        account: str | None = None,
        config: Config | None = None,
    ):
        self.server_url = server_url.rstrip("/")
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
                "Use 'gws account add <name>' to set up multi-account mode.",
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
        return Path.home() / ".claude" / ".google-workspace" / self._SERVER_TOKEN_FILENAME

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

        # Try loading existing Google token
        if self.TOKEN_PATH.exists() and not force_refresh:
            try:
                self._credentials = Credentials.from_authorized_user_file(str(self.TOKEN_PATH))
            except Exception:
                self._credentials = None

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

        try:
            credentials = Credentials.from_authorized_user_file(str(self.TOKEN_PATH))
        except Exception as e:
            return False, f"invalid_token: {e}", None

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
            result["hint"] = "Run 'gws auth server-login' to authenticate."

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
        params = {
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "redirect_uri": "http://127.0.0.1:0/callback",  # Server will provide actual redirect
        }
        auth_url = f"{self.server_url}/oauth/authorize?{urlencode(params)}"

        print("\n" + "=" * 60, file=sys.stderr)
        print("Server Authentication Required", file=sys.stderr)
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

        # Wait for user to complete browser auth, then exchange code
        print("Paste the authorization code here: ", file=sys.stderr, end="")
        code = input().strip()

        if not code:
            raise AuthError("No authorization code provided.")

        # Exchange code for tokens
        resp = httpx.post(
            f"{self.server_url}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": "http://127.0.0.1:0/callback",
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

        # Start the flow — send full scope URLs, server passes them through
        resp = self._server_request(
            "POST",
            "/auth/tokens/start",
            json_data={"scopes": scopes},
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
        print(f"Google OAuth Authorization Required{account_label}", file=sys.stderr)
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
            json_data={"refresh_token": refresh_token},
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

    def _server_request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        bearer_token: str | None = None,
    ) -> httpx.Response:
        """Make an authenticated request to the relay server."""
        headers: dict[str, str] = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        return httpx.request(
            method,
            f"{self.server_url}{path}",
            json=json_data,
            headers=headers,
            timeout=30,
        )

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
        self._server_token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._server_token_path, "w") as f:
            json.dump(token_data, f, indent=2)
        self._server_token = token_data

    def _ensure_server_token(self) -> dict[str, Any]:
        """Load server token or raise if not authenticated."""
        token = self._load_server_token()
        if not token:
            raise AuthError(
                "Not authenticated to the server",
                "Run 'gws auth server-login' first.",
            )
        return token

    def _save_google_token(
        self,
        token_data: dict[str, Any],
        refresh_token: str | None = None,
    ) -> None:
        """Save Google API tokens as a Credentials-compatible JSON file."""
        cred_data = {
            "token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", refresh_token),
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": token_data.get("scopes", []),
        }
        # Omit fields that are None
        cred_data = {k: v for k, v in cred_data.items() if v is not None}

        self.TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.TOKEN_PATH, "w") as f:
            json.dump(cred_data, f, indent=2)

        # Reload as Credentials object
        self._credentials = Credentials.from_authorized_user_file(str(self.TOKEN_PATH))


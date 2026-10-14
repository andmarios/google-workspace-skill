"""OAuth authentication with loopback redirect flow."""

import json
import secrets
import socket
import webbrowser
from getpass import getpass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import OAuth2Error
from requests.exceptions import RequestException

from gws.auth.provider import headless_requested
from gws.auth.scopes import get_scopes_for_services
from gws.config import Config
from gws.crypto import delete_encrypted, load_encrypted, save_encrypted
from gws.exceptions import AuthError


def _validate_headless_redirect(
    redirect_url: str,
    expected_redirect_uri: str,
    expected_state: str,
) -> None:
    """Validate a pasted loopback OAuth redirect before exchanging its code."""
    if not redirect_url.strip():
        raise AuthError("Headless authentication cancelled: no redirect URL was provided.")

    try:
        parsed = urlparse(redirect_url.strip())
        expected = urlparse(expected_redirect_uri)
        redirect_matches = (
            parsed.scheme == expected.scheme
            and parsed.hostname == expected.hostname
            and parsed.port == expected.port
            and parsed.path == expected.path
            and parsed.params == expected.params
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError as exc:
        raise AuthError("Invalid OAuth redirect URI") from exc
    if not redirect_matches:
        raise AuthError(
            "Invalid OAuth redirect URI",
            "Paste the complete loopback URL from the browser address bar.",
        )
    if parsed.fragment:
        raise AuthError("Invalid OAuth redirect: URL fragments are not accepted.")

    query = parse_qs(parsed.query, keep_blank_values=True)
    states = query.get("state", [])
    if len(states) != 1 or not secrets.compare_digest(states[0], expected_state):
        raise AuthError("OAuth state validation failed.")

    if "error" in query:
        error = query["error"][0]
        if error == "access_denied":
            raise AuthError("Google authorization was denied.")
        raise AuthError("Google authorization failed.")

    codes = query.get("code", [])
    if len(codes) != 1 or not codes[0]:
        if len(codes) > 1:
            raise AuthError("OAuth redirect must contain exactly one authorization code.")
        raise AuthError("OAuth redirect is missing the authorization code.")


def _fetch_headless_token(flow: InstalledAppFlow, redirect_url: str) -> None:
    """Exchange a validated loopback response without weakening OAuthlib globally.

    OAuthlib rejects plain-HTTP authorization responses even for native-app
    loopback redirects. ``InstalledAppFlow.run_local_server`` works around this
    by changing only the response URL used for parsing to HTTPS while retaining
    the original HTTP redirect URI in the token request. Mirror that behavior
    for the manually pasted headless response.
    """
    parsed = urlparse(redirect_url.strip())
    authorization_response = parsed._replace(scheme="https").geturl()
    flow.fetch_token(authorization_response=authorization_response)


class LocalAuthProvider:
    """Local OAuth authentication provider using client_secret.json.

    Handles the loopback OAuth flow for users who manage their own
    Google OAuth credentials locally.
    """

    CREDENTIALS_PATH = Path.home() / ".config" / "gws-cli" / "client_secret.json"
    _LEGACY_TOKEN_PATH = Path.home() / ".config" / "gws-cli" / "token.json"
    LOOPBACK_IP = "127.0.0.1"
    PORT_RANGE = range(8080, 8100)

    def __init__(self, config: Config | None = None, account: str | None = None):
        self.config = config or Config.load()
        self._account_name = self.config.resolve_account(account)

        # Validate resolved account name exists in registry
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

    @property
    def account_name(self) -> str | None:
        """The resolved account name, or None for legacy mode."""
        return self._account_name

    @property
    def TOKEN_PATH(self) -> Path:  # noqa: N802 — kept uppercase for backward compatibility
        """Return account-specific or legacy token path."""
        if self._account_name:
            return self.config.get_account_dir(self._account_name) / "token.json"
        return self._LEGACY_TOKEN_PATH

    def get_credentials(
        self,
        force_refresh: bool = False,
        headless: bool = False,
    ) -> Credentials:
        """Get valid credentials, triggering auth flow if needed."""
        headless = headless_requested(headless)
        if self._credentials and self._credentials.valid and not force_refresh:
            return self._credentials

        scopes = self._get_required_scopes()

        # Try loading existing token (encrypted or plaintext)
        if not force_refresh:
            try:
                token_data = load_encrypted(self.TOKEN_PATH, self.config.get_encryption_key())
                if token_data:
                    self._credentials = Credentials.from_authorized_user_info(
                        token_data,
                        scopes=scopes,
                    )
            except (ValueError, KeyError) as e:
                import sys
                print(f"[gws-cli] Warning: failed to load token: {e}", file=sys.stderr)
                self._credentials = None

        # Refresh if expired
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_credentials()
                return self._credentials
            except (
                google.auth.exceptions.RefreshError,
                google.auth.exceptions.TransportError,
                OSError,
            ) as e:
                import sys
                print(f"[gws-cli] Warning: token refresh failed: {e}", file=sys.stderr)
                self._credentials = None

        # Run auth flow if no valid credentials
        if not self._credentials or not self._credentials.valid:
            self._run_auth_flow(scopes, headless=headless)

        return self._credentials  # type: ignore

    def _get_required_scopes(self) -> list[str]:
        """Get OAuth scopes for enabled services."""
        return get_scopes_for_services(
            self.config.enabled_services,
            read_only=self.config.read_only,
        )

    def _find_available_port(self) -> int:
        """Find an available port for OAuth callback."""
        for port in self.PORT_RANGE:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.LOOPBACK_IP, port))
                    return port
            except OSError:
                continue
        raise AuthError("No available ports in range 8080-8099 for OAuth callback")

    def _run_auth_flow(self, scopes: list[str], headless: bool = False) -> None:
        """Run the OAuth loopback authentication flow."""
        import sys

        key = self.config.get_encryption_key()
        client_config = load_encrypted(self.CREDENTIALS_PATH, key)
        if not client_config:
            raise AuthError(
                "Credentials file not found",
                "Import with: gws-cli auth import-credentials <path-to-client_secret.json>",
            )

        port = self._find_available_port()

        if headless:
            # PKCE is what protects the pasted code. google-auth-oauthlib < 1.3
            # only enables it when asked, so request it explicitly here; the
            # browser flow below keeps the library default, as before.
            flow = InstalledAppFlow.from_client_config(
                client_config,
                scopes=scopes,
                autogenerate_code_verifier=True,
            )
            self._run_headless_auth_flow(flow, port)
            self._save_credentials()
            return

        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=scopes,
        )

        try:
            can_open_browser = webbrowser.get() is not None
        except webbrowser.Error:
            can_open_browser = False

        print("\n" + "=" * 60, file=sys.stderr)
        account_label = f" (account: {self._account_name})" if self._account_name else ""
        print(f"Google OAuth Authorization Required for gws-cli{account_label}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        self._credentials = flow.run_local_server(
            host=self.LOOPBACK_IP,
            port=port,
            open_browser=can_open_browser,
            authorization_prompt_message=(
                "\n{url}\n\n" + "=" * 60 + "\nWaiting for authorization...\n"
            ),
            success_message="Authorization successful! You can close this window.",
        )

        print("\n✓ Authorization successful! Token saved.\n", file=sys.stderr)
        self._save_credentials()

    def _run_headless_auth_flow(self, flow: InstalledAppFlow, port: int) -> None:
        """Complete local OAuth without a browser or callback HTTP server."""
        import sys

        redirect_uri = f"http://{self.LOOPBACK_IP}:{port}/"
        flow.redirect_uri = redirect_uri
        authorization_url, state = flow.authorization_url()

        print("\n" + "=" * 60, file=sys.stderr)
        account_label = f" (account: {self._account_name})" if self._account_name else ""
        print(f"Google OAuth Headless Authorization for gws-cli{account_label}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("\n1. Open this URL in a browser on another computer:\n", file=sys.stderr)
        print(authorization_url, file=sys.stderr)
        print(
            "\n2. Complete Google sign-in and consent. The final loopback page may fail to load."
            "\n3. Copy the ENTIRE URL from the browser address bar and paste it below."
            "\n   Treat that URL as a one-time secret; do not share or log it.\n",
            file=sys.stderr,
        )

        try:
            redirect_url = getpass("Full redirect URL (input hidden): ", stream=sys.stderr).strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise AuthError("Headless authentication cancelled.") from exc

        _validate_headless_redirect(redirect_url, redirect_uri, state)
        try:
            _fetch_headless_token(flow, redirect_url)
        except (OAuth2Error, ValueError, OSError, RequestException) as exc:
            raise AuthError(
                "Failed to exchange the OAuth authorization code.",
                "The code may be expired or already used. Run the command again.",
            ) from exc

        self._credentials = flow.credentials
        if not self._credentials or not self._credentials.valid:
            raise AuthError("Google returned invalid OAuth credentials.")
        print("\nAuthorization successful! Token saved.\n", file=sys.stderr)

    def _save_credentials(self) -> None:
        """Save credentials to token file (encrypted if enabled)."""
        if self._credentials:
            data = json.loads(self._credentials.to_json())
            save_encrypted(self.TOKEN_PATH, data, self.config.get_encryption_key())

    def delete_token(self) -> bool:
        """Delete the token file (encrypted and/or plaintext).

        Best-effort revokes the token upstream at Google first, so that logging
        out actually invalidates access rather than only removing the local
        copy. A failed revoke never blocks the local deletion.
        """
        self._revoke_token_best_effort()
        return delete_encrypted(self.TOKEN_PATH)

    def _revoke_token_best_effort(self) -> None:
        """Revoke the stored Google token at Google's revoke endpoint.

        Never raises — logout must succeed even if the network call fails.
        """
        try:
            token_data = load_encrypted(self.TOKEN_PATH, self.config.get_encryption_key())
        except Exception:
            return
        if not token_data:
            return
        # Revoking a refresh token invalidates the whole grant; fall back to the
        # access token if that is all we have.
        token = token_data.get("refresh_token") or token_data.get("token")
        if not token:
            return
        try:
            import httpx

            httpx.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": token},
                timeout=5.0,
            )
        except Exception:
            # Best-effort only — a revoke failure must not break logout.
            pass

    def check_credentials(self) -> tuple[bool, str, Credentials | None]:
        """Check credentials without triggering auth flow.

        Returns:
            Tuple of (is_valid, status_message, credentials_or_none)
        """
        scopes = self._get_required_scopes()

        try:
            token_data = load_encrypted(self.TOKEN_PATH, self.config.get_encryption_key())
            if not token_data:
                return False, "no_token", None
            credentials = Credentials.from_authorized_user_info(
                token_data,
                scopes=scopes,
            )
        except Exception as e:
            return False, f"invalid_token: {e}", None

        if credentials.valid:
            return True, "valid", credentials

        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                self._credentials = credentials
                self._save_credentials()
                return True, "refreshed", credentials
            except Exception as e:
                return False, f"refresh_failed: {e}", None

        return False, "expired_no_refresh", credentials


# Backward-compatibility alias — existing code that imports AuthManager keeps working.
AuthManager = LocalAuthProvider

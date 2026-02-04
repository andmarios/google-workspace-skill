"""OAuth authentication with loopback redirect flow."""

import socket
import webbrowser
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from gws.auth.scopes import get_scopes_for_services
from gws.config import Config
from gws.exceptions import AuthError


class AuthManager:
    """Manages OAuth authentication for all Google services."""

    CREDENTIALS_PATH = Path.home() / ".claude" / ".google-workspace" / "client_secret.json"
    _LEGACY_TOKEN_PATH = Path.home() / ".claude" / ".google-workspace" / "token.json"
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
                "Use 'gws account add <name>' to set up multi-account mode.",
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

    def get_credentials(self, force_refresh: bool = False) -> Credentials:
        """Get valid credentials, triggering auth flow if needed."""
        if self._credentials and self._credentials.valid and not force_refresh:
            return self._credentials

        scopes = self._get_required_scopes()

        # Try loading existing token
        if self.TOKEN_PATH.exists() and not force_refresh:
            try:
                self._credentials = Credentials.from_authorized_user_file(
                    str(self.TOKEN_PATH),
                    scopes=scopes,
                )
            except Exception:
                self._credentials = None

        # Refresh if expired
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_credentials()
                return self._credentials
            except Exception:
                # Refresh failed, need new auth
                self._credentials = None

        # Run auth flow if no valid credentials
        if not self._credentials or not self._credentials.valid:
            self._run_auth_flow(scopes)

        return self._credentials  # type: ignore

    def _get_required_scopes(self) -> list[str]:
        """Get OAuth scopes for enabled services."""
        return get_scopes_for_services(self.config.enabled_services)

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

    def _run_auth_flow(self, scopes: list[str]) -> None:
        """Run the OAuth loopback authentication flow."""
        import sys

        if not self.CREDENTIALS_PATH.exists():
            raise AuthError(
                "Credentials file not found",
                f"Please save your OAuth credentials to {self.CREDENTIALS_PATH}",
            )

        port = self._find_available_port()

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.CREDENTIALS_PATH),
            scopes=scopes,
        )

        # Try to open browser
        try:
            can_open_browser = webbrowser.get() is not None
        except webbrowser.Error:
            can_open_browser = False

        # Print header
        print("\n" + "=" * 60, file=sys.stderr)
        account_label = f" (account: {self._account_name})" if self._account_name else ""
        print(f"Google OAuth Authorization Required{account_label}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # Let run_local_server handle everything including URL generation
        # The authorization_prompt_message will print the URL
        self._credentials = flow.run_local_server(
            host=self.LOOPBACK_IP,
            port=port,
            open_browser=can_open_browser,
            authorization_prompt_message="\n{url}\n\n" + "=" * 60 + "\nWaiting for authorization...\n",
            success_message="Authorization successful! You can close this window.",
        )

        print("\n✓ Authorization successful! Token saved.\n", file=sys.stderr)
        self._save_credentials()

    def _save_credentials(self) -> None:
        """Save credentials to token file."""
        if self._credentials:
            self.TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.TOKEN_PATH, "w") as f:
                f.write(self._credentials.to_json())

    def delete_token(self) -> bool:
        """Delete the token file for re-authentication."""
        if self.TOKEN_PATH.exists():
            self.TOKEN_PATH.unlink()
            return True
        return False

    def check_credentials(self) -> tuple[bool, str, Credentials | None]:
        """Check credentials without triggering auth flow.

        Returns:
            Tuple of (is_valid, status_message, credentials_or_none)
        """
        if not self.TOKEN_PATH.exists():
            return False, "no_token", None

        scopes = self._get_required_scopes()

        try:
            credentials = Credentials.from_authorized_user_file(
                str(self.TOKEN_PATH),
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

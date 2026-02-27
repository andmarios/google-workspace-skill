"""Auth provider protocol for pluggable authentication backends."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from google.oauth2.credentials import Credentials


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers.

    LocalAuthProvider: handles OAuth locally with client_secret.json.
    ServerAuthProvider: delegates to an oauth-token-relay server.
    """

    def get_credentials(self, force_refresh: bool = False) -> Credentials:
        """Get valid Google API credentials, triggering auth if needed."""
        ...

    def delete_token(self) -> bool:
        """Delete stored token(s). Returns True if a token was deleted."""
        ...

    def check_credentials(self) -> tuple[bool, str, Credentials | None]:
        """Check credentials without triggering interactive auth.

        Returns:
            Tuple of (is_valid, status_message, credentials_or_none)
        """
        ...


def resolve_auth_provider(
    account: str | None = None,
    config: Any | None = None,
) -> AuthProvider:
    """Factory: return the appropriate auth provider based on config.

    Each account can have its own auth mode (local or server) via per-account
    config overrides. Resolution:
        1. Load global config
        2. Resolve account name (explicit > env > default)
        3. Apply per-account overrides (mode, server_url, server_provider)
        4. GWS_SERVER_URL env var overrides per-account server_url
        5. Create the appropriate provider
    """
    import os

    from gws.config import Config

    cfg = config or Config.load()
    resolved_account = account or cfg.resolve_account()

    # Apply per-account overrides (mode, server_url, server_provider, etc.)
    effective = cfg.load_effective_config(resolved_account)

    server_url = os.environ.get("GWS_SERVER_URL") or effective.server_url

    if effective.mode == "server" and server_url:
        from gws.auth.server import ServerAuthProvider

        return ServerAuthProvider(
            server_url=server_url, account=resolved_account, config=effective,
        )

    from gws.auth.oauth import LocalAuthProvider

    return LocalAuthProvider(config=effective, account=resolved_account)

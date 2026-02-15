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

    Resolution order for server mode:
        1. GWS_SERVER_URL environment variable
        2. config.server_url from gws_config.json
    Falls back to LocalAuthProvider when no server URL is set.
    """
    import os

    from gws.config import Config

    cfg = config or Config.load()
    server_url = os.environ.get("GWS_SERVER_URL") or cfg.server_url

    if server_url:
        from gws.auth.server import ServerAuthProvider

        return ServerAuthProvider(server_url=server_url, account=account)

    from gws.auth.oauth import LocalAuthProvider

    return LocalAuthProvider(config=cfg, account=account)

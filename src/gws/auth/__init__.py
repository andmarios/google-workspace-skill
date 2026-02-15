"""Authentication module for GWS CLI."""

from gws.auth.oauth import AuthManager, LocalAuthProvider
from gws.auth.provider import AuthProvider, resolve_auth_provider
from gws.auth.scopes import SCOPES, get_scopes_for_services

__all__ = [
    "AuthManager",
    "AuthProvider",
    "LocalAuthProvider",
    "SCOPES",
    "get_scopes_for_services",
    "resolve_auth_provider",
]

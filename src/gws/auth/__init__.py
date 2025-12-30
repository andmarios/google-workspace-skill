"""Authentication module for GWS CLI."""

from gws.auth.oauth import AuthManager
from gws.auth.scopes import SCOPES, get_scopes_for_services

__all__ = ["AuthManager", "SCOPES", "get_scopes_for_services"]

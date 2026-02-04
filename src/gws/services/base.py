"""Base service class for Google API services."""

from abc import ABC
from typing import Any

from googleapiclient.discovery import build, Resource

from gws.auth.oauth import AuthManager
from gws.context import get_active_account
from gws.utils.retry import execute_with_retry


class BaseService(ABC):
    """Base class for Google API services."""

    SERVICE_NAME: str = ""
    VERSION: str = ""

    def __init__(self, auth_manager: AuthManager | None = None, account: str | None = None):
        resolved_account = account or get_active_account()
        self.auth_manager = auth_manager or AuthManager(account=resolved_account)
        self._service: Resource | None = None
        self._drive_service: Resource | None = None

    @property
    def service(self) -> Resource:
        """Lazy-load the Google API service."""
        if self._service is None:
            credentials = self.auth_manager.get_credentials()
            self._service = build(
                self.SERVICE_NAME,
                self.VERSION,
                credentials=credentials,
            )
        return self._service

    def execute(self, request: Any) -> Any:
        """Execute a Google API request with automatic retry on transient errors."""
        return execute_with_retry(request)

    @property
    def drive_service(self) -> Resource:
        """Lazy-load Drive service (used by multiple services)."""
        if self._drive_service is None:
            credentials = self.auth_manager.get_credentials()
            self._drive_service = build("drive", "v3", credentials=credentials)
        return self._drive_service

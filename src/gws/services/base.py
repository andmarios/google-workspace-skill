"""Base service class for Google API services."""

from abc import ABC

from googleapiclient.discovery import build, Resource

from gws.auth.oauth import AuthManager


class BaseService(ABC):
    """Base class for Google API services."""

    SERVICE_NAME: str = ""
    VERSION: str = ""

    def __init__(self, auth_manager: AuthManager | None = None):
        self.auth_manager = auth_manager or AuthManager()
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

    @property
    def drive_service(self) -> Resource:
        """Lazy-load Drive service (used by multiple services)."""
        if self._drive_service is None:
            credentials = self.auth_manager.get_credentials()
            self._drive_service = build("drive", "v3", credentials=credentials)
        return self._drive_service

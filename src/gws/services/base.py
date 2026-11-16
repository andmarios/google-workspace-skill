"""Base service class for Google API services."""

from abc import ABC
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource

from gws.auth.provider import AuthProvider, resolve_auth_provider
from gws.context import get_active_account
from gws.exceptions import AuthError, ExitCode
from gws.output import output_error
from gws.utils.retry import execute_with_retry


class BaseService(ABC):
    """Base class for Google API services."""

    SERVICE_NAME: str = ""
    VERSION: str = ""

    def __init__(self, auth_manager: AuthProvider | None = None, account: str | None = None):
        resolved_account = account or get_active_account()
        self.auth_manager = auth_manager or resolve_auth_provider(account=resolved_account)
        self._service: Resource | None = None
        self._drive_service: Resource | None = None

    def _get_credentials(self) -> Credentials:
        """Get credentials for a service command; auth errors exit with JSON, not a traceback."""
        try:
            return self.auth_manager.get_credentials(implicit=True)
        except AuthError as e:
            output_error(
                error_code="AUTH_ERROR",
                operation="auth",
                message=str(e),
                details=e.details,
            )
            raise SystemExit(ExitCode.AUTH_ERROR)

    @property
    def service(self) -> Resource:
        """Lazy-load the Google API service."""
        if self._service is None:
            credentials = self._get_credentials()
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
            credentials = self._get_credentials()
            self._drive_service = build("drive", "v3", credentials=credentials)
        return self._drive_service

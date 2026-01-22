"""Custom exceptions and exit codes for GWS CLI."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Exit codes for GWS CLI.

    Exit codes:
    - 0: Success
    - 1: Authentication error
    - 2: API error
    - 3: Invalid arguments
    - 4: Not found
    """

    SUCCESS = 0
    AUTH_ERROR = 1
    API_ERROR = 2
    INVALID_ARGS = 3
    NOT_FOUND = 4
    # Legacy alias for backwards compatibility
    OPERATION_FAILED = 1


class GWSError(Exception):
    """Base exception for GWS CLI."""

    exit_code = ExitCode.OPERATION_FAILED

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class AuthError(GWSError):
    """Authentication error."""

    exit_code = ExitCode.AUTH_ERROR


class APIError(GWSError):
    """Google API error."""

    exit_code = ExitCode.API_ERROR


class InvalidArgsError(GWSError):
    """Invalid arguments error."""

    exit_code = ExitCode.INVALID_ARGS


class ConfigError(GWSError):
    """Configuration error."""

    exit_code = ExitCode.OPERATION_FAILED

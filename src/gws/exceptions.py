"""Custom exceptions and exit codes for GWS CLI."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Exit codes matching Ruby implementation."""

    SUCCESS = 0
    OPERATION_FAILED = 1
    AUTH_ERROR = 2
    API_ERROR = 3
    INVALID_ARGS = 4


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

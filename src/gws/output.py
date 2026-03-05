"""JSON output formatting for GWS CLI."""

import json
import sys
from typing import Any

from prompt_security import output_external_content as _output_external_content
from prompt_security import load_config as load_security_config
from prompt_security import generate_markers

from gws.config import Config

# Session-scoped security markers — generated once at import time.
# For CLI tools the human controls the pipeline, so these are defense-in-depth.
_SESSION_START, _SESSION_END = generate_markers()


def _get_session_markers() -> tuple[str, str]:
    """Return the module-level session markers."""
    return _SESSION_START, _SESSION_END


def output_json(data: dict[str, Any]) -> None:
    """Output JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def output_success(operation: str, **kwargs: Any) -> None:
    """Output success response."""
    response = {"status": "success", "operation": operation, **kwargs}
    output_json(response)


def output_error(
    error_code: str,
    operation: str,
    message: str,
    details: Any = None,
) -> None:
    """Output error response to stdout."""
    response: dict[str, Any] = {
        "status": "error",
        "error_code": error_code,
        "operation": operation,
        "message": message,
    }
    if details is not None:
        response["details"] = details
    output_json(response)


def output_external_content(
    operation: str,
    source_type: str,
    source_id: str,
    content_fields: dict[str, str],
    **kwargs: Any,
) -> None:
    """
    Output response with wrapped external content.

    Security is skipped if:
    - security_enabled=False in GWS config
    - The operation is in disabled_security_operations
    - The source is in the allowlist

    Args:
        operation: Operation name (e.g., "gmail.read")
        source_type: Type of source ("email", "document", "spreadsheet", "slide")
        source_id: Unique identifier (document ID, message ID, etc.)
        content_fields: Dict mapping field names to content to wrap
        **kwargs: Additional fields to include in response
    """
    from gws.context import get_active_account

    gws_config = Config.load()
    account = get_active_account()
    if account:
        gws_config = gws_config.load_effective_config(account)

    # Determine if we should skip wrapping
    skip_wrapping = (
        not gws_config.security_enabled
        or not gws_config.is_security_enabled_for_operation(operation)
        or gws_config.is_allowlisted(source_type, source_id)
    )

    if skip_wrapping:
        # Output without security wrapping
        response = {
            "status": "success",
            "operation": operation,
            "source_id": source_id,
            **content_fields,
            **kwargs,
        }
        output_json(response)
        return

    # Security enabled - wrap content with session markers
    start, end = _get_session_markers()
    security_config = load_security_config()
    response = _output_external_content(
        operation=operation,
        source_type=source_type,
        source_id=source_id,
        content_fields=content_fields,
        start_marker=start,
        end_marker=end,
        config=security_config,
        **kwargs,
    )
    output_json(response)


def read_json_stdin() -> dict[str, Any]:
    """Read JSON from stdin."""
    from gws.exceptions import ExitCode

    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        output_error("INVALID_JSON", "stdin", f"Invalid JSON input: {e}")
        raise SystemExit(ExitCode.INVALID_ARGS)

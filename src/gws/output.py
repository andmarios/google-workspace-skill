"""JSON output formatting for GWS CLI."""

import json
import sys
from typing import Any

from prompt_security import output_external_content as _output_external_content
from prompt_security import load_config as load_security_config

from gws.config import Config


def output_json(data: dict[str, Any]) -> None:
    """Output JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def is_security_enabled() -> bool:
    """Check if security wrapping is enabled in gws config."""
    gws_config = Config.load()
    return gws_config.security_enabled


def output_success(operation: str, **kwargs: Any) -> None:
    """Output success response."""
    response = {"status": "success", "operation": operation, **kwargs}
    output_json(response)


def output_error(
    error_code: str,
    operation: str,
    message: str,
    details: str | None = None,
) -> None:
    """Output error response to stdout."""
    response: dict[str, Any] = {
        "status": "error",
        "error_code": error_code,
        "operation": operation,
        "message": message,
    }
    if details:
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

    If security is disabled in gws config, outputs without wrapping.

    Args:
        operation: Operation name (e.g., "gmail.read")
        source_type: Type of source ("email", "document", "spreadsheet", "slide")
        source_id: Unique identifier (document ID, message ID, etc.)
        content_fields: Dict mapping field names to content to wrap
        **kwargs: Additional fields to include in response
    """
    # Check if security is enabled in gws config
    if not is_security_enabled():
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

    # Security enabled - wrap content with markers
    config = load_security_config()
    response = _output_external_content(
        operation=operation,
        source_type=source_type,
        source_id=source_id,
        content_fields=content_fields,
        config=config,
        **kwargs,
    )
    output_json(response)


def read_json_stdin() -> dict[str, Any]:
    """Read JSON from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        output_error("INVALID_JSON", "stdin", f"Invalid JSON input: {e}")
        sys.exit(4)

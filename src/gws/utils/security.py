"""Security utilities for GWS - thin wrapper around mcp-security-utils."""

from mcp_security import (
    wrap_untrusted_content,
    wrap_field,
    wrap_fields,
    output_external_content,
    detect_suspicious_content,
    screen_content,
    load_config,
    SecurityConfig,
)

__all__ = [
    "wrap_untrusted_content",
    "wrap_field",
    "wrap_fields",
    "output_external_content",
    "detect_suspicious_content",
    "screen_content",
    "load_config",
    "SecurityConfig",
]

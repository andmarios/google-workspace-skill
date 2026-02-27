"""Color parsing utilities."""


def parse_hex_color(color_str: str) -> dict[str, float]:
    """Parse hex color to RGB float values (0.0-1.0).

    Args:
        color_str: Hex color string like "#FF0000", "FF0000", "#F00", or "F00"

    Returns:
        Dict with red, green, blue keys (0.0-1.0 range)

    Raises:
        ValueError: If color string is not a valid 3 or 6 character hex color.
    """
    hex_color = color_str.lstrip("#")
    if len(hex_color) == 3:
        hex_color = hex_color[0] * 2 + hex_color[1] * 2 + hex_color[2] * 2
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {color_str!r} (expected 3 or 6 hex digits)")
    return {
        "red": int(hex_color[0:2], 16) / 255.0,
        "green": int(hex_color[2:4], 16) / 255.0,
        "blue": int(hex_color[4:6], 16) / 255.0,
    }

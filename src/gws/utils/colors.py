"""Color parsing utilities."""


def parse_hex_color(color_str: str) -> dict[str, float]:
    """Parse hex color to RGB float values (0.0-1.0).

    Args:
        color_str: Hex color string like "#FF0000" or "FF0000"

    Returns:
        Dict with red, green, blue keys (0.0-1.0 range)
    """
    hex_color = color_str.lstrip("#")
    if len(hex_color) == 6:
        return {
            "red": int(hex_color[0:2], 16) / 255.0,
            "green": int(hex_color[2:4], 16) / 255.0,
            "blue": int(hex_color[4:6], 16) / 255.0,
        }
    return {"red": 0.0, "green": 0.0, "blue": 0.0}

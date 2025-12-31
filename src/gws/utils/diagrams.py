"""Diagram rendering via Kroki API."""

import base64
import os
import re
import zlib
from pathlib import Path
from typing import Any

import httpx


# Supported diagram types and their Kroki identifiers
DIAGRAM_TYPES = {
    "mermaid": "mermaid",
    "plantuml": "plantuml",
    "graphviz": "graphviz",
    "dot": "graphviz",
    "d2": "d2",
    "excalidraw": "excalidraw",
    "ditaa": "ditaa",
    "blockdiag": "blockdiag",
    "seqdiag": "seqdiag",
    "actdiag": "actdiag",
    "nwdiag": "nwdiag",
    "packetdiag": "packetdiag",
    "rackdiag": "rackdiag",
    "erd": "erd",
    "nomnoml": "nomnoml",
    "pikchr": "pikchr",
    "structurizr": "structurizr",
    "svgbob": "svgbob",
    "vega": "vega",
    "vegalite": "vegalite",
    "wavedrom": "wavedrom",
}

def get_kroki_url() -> str:
    """Get the Kroki server URL.

    Priority:
    1. GWS_KROKI_URL environment variable (for testing/override)
    2. kroki_url from gws_config.json
    3. Default: https://kroki.io
    """
    # Environment variable takes precedence (useful for testing)
    env_url = os.environ.get("GWS_KROKI_URL")
    if env_url:
        return env_url.rstrip("/")

    # Load from config file
    from gws.config import Config
    config = Config.load()
    return config.kroki_url.rstrip("/")


def encode_diagram(source: str) -> str:
    """Encode diagram source for Kroki API URL."""
    compressed = zlib.compress(source.encode("utf-8"), level=9)
    return base64.urlsafe_b64encode(compressed).decode("utf-8")


def render_diagram(
    diagram_type: str,
    source: str,
    output_format: str = "png",
    timeout: float = 30.0,
    mermaid_theme: str = "neutral",
) -> bytes:
    """Render a diagram using Kroki API.

    Args:
        diagram_type: Type of diagram (mermaid, plantuml, graphviz, etc.)
        source: The diagram source code
        output_format: Output format (png, svg, pdf)
        timeout: Request timeout in seconds
        mermaid_theme: Theme for Mermaid diagrams (neutral, default, dark, forest)

    Returns:
        Rendered diagram as bytes

    Raises:
        ValueError: If diagram type is not supported
        httpx.HTTPError: If API request fails
    """
    kroki_type = DIAGRAM_TYPES.get(diagram_type.lower())
    if not kroki_type:
        raise ValueError(
            f"Unsupported diagram type: {diagram_type}. "
            f"Supported: {', '.join(DIAGRAM_TYPES.keys())}"
        )

    # Inject theme for Mermaid diagrams if not already specified
    processed_source = source
    if kroki_type == "mermaid" and "%%{init:" not in source:
        theme_directive = f"%%{{init: {{'theme': '{mermaid_theme}'}}}}%%\n"
        processed_source = theme_directive + source

    encoded = encode_diagram(processed_source)
    kroki_url = get_kroki_url()
    url = f"{kroki_url}/{kroki_type}/{output_format}/{encoded}"

    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def render_diagram_to_file(
    diagram_type: str,
    source: str,
    output_path: str | Path,
    output_format: str = "png",
) -> Path:
    """Render a diagram and save to file.

    Args:
        diagram_type: Type of diagram
        source: The diagram source code
        output_path: Path to save the rendered diagram
        output_format: Output format (png, svg, pdf)

    Returns:
        Path to the saved file
    """
    content = render_diagram(diagram_type, source, output_format)
    path = Path(output_path)
    path.write_bytes(content)
    return path


def find_diagram_blocks(markdown: str) -> list[dict[str, Any]]:
    """Find all diagram code blocks in markdown.

    Args:
        markdown: Markdown content

    Returns:
        List of dicts with 'type', 'source', 'start', 'end' keys
    """
    # Pattern to match fenced code blocks with diagram types
    pattern = r"```(" + "|".join(DIAGRAM_TYPES.keys()) + r")\s*\n(.*?)```"

    blocks = []
    for match in re.finditer(pattern, markdown, re.DOTALL | re.IGNORECASE):
        blocks.append({
            "type": match.group(1).lower(),
            "source": match.group(2).strip(),
            "start": match.start(),
            "end": match.end(),
            "full_match": match.group(0),
        })

    return blocks


def render_diagrams_in_markdown(
    markdown: str,
    output_dir: str | Path,
    output_format: str = "png",
) -> tuple[str, list[Path]]:
    """Render all diagrams in markdown and replace with image references.

    Args:
        markdown: Markdown content with diagram code blocks
        output_dir: Directory to save rendered diagrams
        output_format: Output format for diagrams (png, svg)

    Returns:
        Tuple of (modified markdown, list of rendered image paths)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    blocks = find_diagram_blocks(markdown)
    if not blocks:
        return markdown, []

    rendered_paths = []
    # Process in reverse order to preserve string positions
    for i, block in enumerate(reversed(blocks)):
        try:
            # Generate unique filename
            filename = f"diagram_{len(blocks) - i - 1}.{output_format}"
            output_path = output_dir / filename

            # Render diagram
            render_diagram_to_file(
                block["type"],
                block["source"],
                output_path,
                output_format,
            )
            rendered_paths.insert(0, output_path)

            # Replace code block with image reference
            # Use absolute path for local files
            image_ref = f"![{block['type']} diagram]({output_path.absolute()})"
            markdown = (
                markdown[:block["start"]] +
                image_ref +
                markdown[block["end"]:]
            )
        except Exception as e:
            # Keep original code block on error, add error comment
            error_msg = f"\n\n<!-- Diagram rendering failed: {e} -->\n\n"
            markdown = (
                markdown[:block["end"]] +
                error_msg +
                markdown[block["end"]:]
            )

    return markdown, rendered_paths

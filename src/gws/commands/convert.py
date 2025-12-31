"""Document conversion CLI commands."""

import typer
from typing import Annotated, Optional

from gws.services.convert import ConvertService

app = typer.Typer(
    name="convert",
    help="Document conversion (Markdown to Google formats).",
    no_args_is_help=True,
)


@app.command("md-to-doc")
def md_to_doc(
    input_path: Annotated[str, typer.Argument(help="Path to Markdown file.")],
    title: Annotated[
        Optional[str],
        typer.Option("--title", "-t", help="Document title (default: filename)."),
    ] = None,
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Folder ID to create document in."),
    ] = None,
    render_diagrams: Annotated[
        bool,
        typer.Option("--render-diagrams", "-d", help="Render Mermaid/PlantUML diagrams via Kroki API."),
    ] = False,
) -> None:
    """Convert Markdown file to Google Doc.

    Uses Google's native Markdown import for high-fidelity conversion.
    Supports headers, lists, code blocks, links, and basic formatting.

    With --render-diagrams, Mermaid, PlantUML, GraphViz and other diagram
    types are rendered to images via Kroki API and embedded in the document.
    """
    service = ConvertService()
    service.md_to_doc(
        input_path=input_path,
        title=title,
        folder_id=folder_id,
        render_diagrams=render_diagrams,
    )


@app.command("md-to-pdf")
def md_to_pdf(
    input_path: Annotated[str, typer.Argument(help="Path to Markdown file.")],
    output_path: Annotated[str, typer.Argument(help="Path for output PDF file.")],
    title: Annotated[
        Optional[str],
        typer.Option("--title", "-t", help="Temporary doc title."),
    ] = None,
    render_diagrams: Annotated[
        bool,
        typer.Option("--render-diagrams", "-d", help="Render Mermaid/PlantUML diagrams via Kroki API."),
    ] = False,
) -> None:
    """Convert Markdown file to PDF.

    Creates a temporary Google Doc, exports as PDF, then deletes the doc.

    With --render-diagrams, Mermaid, PlantUML, GraphViz and other diagram
    types are rendered to images via Kroki API and embedded in the PDF.
    """
    service = ConvertService()
    service.md_to_pdf(
        input_path=input_path,
        output_path=output_path,
        title=title,
        render_diagrams=render_diagrams,
    )


@app.command("md-to-slides")
def md_to_slides(
    input_path: Annotated[str, typer.Argument(help="Path to Markdown file.")],
    title: Annotated[
        Optional[str],
        typer.Option("--title", "-t", help="Presentation title (default: filename)."),
    ] = None,
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Folder ID to create presentation in."),
    ] = None,
) -> None:
    """Convert Markdown file to Google Slides.

    Parsing rules:
    - # Heading → New slide with title
    - ## Subheading → Subtitle
    - Bullet lists (- or *) → Slide bullet points
    - --- → Force slide break
    """
    service = ConvertService()
    service.md_to_slides(
        input_path=input_path,
        title=title,
        folder_id=folder_id,
    )

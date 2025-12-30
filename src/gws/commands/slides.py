"""Slides CLI commands."""

import typer
from typing import Annotated, Optional

from gws.services.slides import SlidesService

app = typer.Typer(
    name="slides",
    help="Google Slides presentation operations.",
    no_args_is_help=True,
)


@app.command("metadata")
def get_metadata(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
) -> None:
    """Get presentation metadata."""
    service = SlidesService()
    service.metadata(presentation_id=presentation_id)


@app.command("read")
def read_presentation(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    page_id: Annotated[
        Optional[str],
        typer.Option("--page", "-p", help="Specific page/slide object ID to read."),
    ] = None,
) -> None:
    """Read presentation content."""
    service = SlidesService()
    service.read(presentation_id=presentation_id, page_object_id=page_id)


@app.command("create")
def create_presentation(
    title: Annotated[str, typer.Argument(help="Presentation title.")],
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Folder ID to create presentation in."),
    ] = None,
) -> None:
    """Create a new presentation."""
    service = SlidesService()
    service.create(title=title, folder_id=folder_id)


@app.command("add-slide")
def add_slide(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    layout: Annotated[
        str,
        typer.Option(
            "--layout",
            "-l",
            help="Layout: BLANK, TITLE, TITLE_AND_BODY, TITLE_ONLY, etc.",
        ),
    ] = "BLANK",
    index: Annotated[
        Optional[int],
        typer.Option("--index", "-i", help="Index to insert slide at."),
    ] = None,
) -> None:
    """Add a new slide."""
    service = SlidesService()
    service.add_slide(
        presentation_id=presentation_id,
        layout=layout,
        insertion_index=index,
    )


@app.command("delete-slide")
def delete_slide(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    slide_id: Annotated[str, typer.Argument(help="Slide object ID to delete.")],
) -> None:
    """Delete a slide."""
    service = SlidesService()
    service.delete_slide(presentation_id=presentation_id, slide_id=slide_id)


@app.command("duplicate-slide")
def duplicate_slide(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    slide_id: Annotated[str, typer.Argument(help="Slide object ID to duplicate.")],
) -> None:
    """Duplicate a slide."""
    service = SlidesService()
    service.duplicate_slide(presentation_id=presentation_id, slide_id=slide_id)


@app.command("insert-text")
def insert_text(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Shape object ID.")],
    text: Annotated[str, typer.Argument(help="Text to insert.")],
    index: Annotated[
        int,
        typer.Option("--index", "-i", help="Character index to insert at."),
    ] = 0,
) -> None:
    """Insert text into a shape."""
    service = SlidesService()
    service.insert_text(
        presentation_id=presentation_id,
        object_id=object_id,
        text=text,
        insertion_index=index,
    )


@app.command("replace-text")
def replace_text(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    find: Annotated[str, typer.Argument(help="Text to find.")],
    replace_with: Annotated[str, typer.Argument(help="Replacement text.")],
    match_case: Annotated[
        bool,
        typer.Option("--match-case", "-m", help="Case-sensitive matching."),
    ] = False,
) -> None:
    """Replace text throughout the presentation."""
    service = SlidesService()
    service.replace_text(
        presentation_id=presentation_id,
        find=find,
        replace_with=replace_with,
        match_case=match_case,
    )


@app.command("create-textbox")
def create_textbox(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    page_id: Annotated[str, typer.Argument(help="Page/slide object ID.")],
    text: Annotated[str, typer.Argument(help="Text content.")],
    x: Annotated[float, typer.Option("--x", help="X position in points.")],
    y: Annotated[float, typer.Option("--y", help="Y position in points.")],
    width: Annotated[float, typer.Option("--width", "-w", help="Width in points.")],
    height: Annotated[float, typer.Option("--height", "-h", help="Height in points.")],
) -> None:
    """Create a text box on a slide."""
    service = SlidesService()
    service.create_textbox(
        presentation_id=presentation_id,
        page_object_id=page_id,
        text=text,
        x=x,
        y=y,
        width=width,
        height=height,
    )


@app.command("insert-image")
def insert_image(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    page_id: Annotated[str, typer.Argument(help="Page/slide object ID.")],
    image_url: Annotated[str, typer.Argument(help="Image URL (publicly accessible).")],
    x: Annotated[float, typer.Option("--x", help="X position in points.")] = 0,
    y: Annotated[float, typer.Option("--y", help="Y position in points.")] = 0,
    width: Annotated[
        Optional[float],
        typer.Option("--width", "-w", help="Width in points."),
    ] = None,
    height: Annotated[
        Optional[float],
        typer.Option("--height", "-h", help="Height in points."),
    ] = None,
) -> None:
    """Insert an image on a slide."""
    service = SlidesService()
    service.insert_image(
        presentation_id=presentation_id,
        page_object_id=page_id,
        image_url=image_url,
        x=x,
        y=y,
        width=width,
        height=height,
    )


@app.command("delete-element")
def delete_element(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Element object ID to delete.")],
) -> None:
    """Delete an element from a slide."""
    service = SlidesService()
    service.delete_element(presentation_id=presentation_id, object_id=object_id)


@app.command("format-text")
def format_text(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Shape object ID.")],
    bold: Annotated[
        Optional[bool],
        typer.Option("--bold/--no-bold", "-b", help="Bold formatting."),
    ] = None,
    italic: Annotated[
        Optional[bool],
        typer.Option("--italic/--no-italic", "-i", help="Italic formatting."),
    ] = None,
    underline: Annotated[
        Optional[bool],
        typer.Option("--underline/--no-underline", "-u", help="Underline formatting."),
    ] = None,
    font_size: Annotated[
        Optional[int],
        typer.Option("--font-size", "-s", help="Font size in points."),
    ] = None,
    color: Annotated[
        Optional[str],
        typer.Option("--color", help="Text color (hex, e.g., #FF0000)."),
    ] = None,
) -> None:
    """Apply formatting to text in an element."""
    service = SlidesService()
    service.format_text(
        presentation_id=presentation_id,
        object_id=object_id,
        bold=bold,
        italic=italic,
        underline=underline,
        font_size=font_size,
        foreground_color=color,
    )

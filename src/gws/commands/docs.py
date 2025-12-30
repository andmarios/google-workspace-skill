"""Docs CLI commands."""

import sys
import typer
from typing import Annotated, Optional

from gws.services.docs import DocsService
from gws.output import read_json_stdin

app = typer.Typer(
    name="docs",
    help="Google Docs document operations.",
    no_args_is_help=True,
)


@app.command("read")
def read_document(
    document_id: Annotated[str, typer.Argument(help="Document ID to read.")],
) -> None:
    """Read document content as plain text."""
    service = DocsService()
    service.read(document_id=document_id)


@app.command("structure")
def get_structure(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
) -> None:
    """Get document heading structure."""
    service = DocsService()
    service.structure(document_id=document_id)


@app.command("create")
def create_document(
    title: Annotated[str, typer.Argument(help="Document title.")],
    content: Annotated[
        Optional[str],
        typer.Option("--content", "-c", help="Initial content."),
    ] = None,
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Folder ID to create document in."),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read content from stdin."),
    ] = False,
) -> None:
    """Create a new document."""
    if stdin:
        content = sys.stdin.read()

    service = DocsService()
    service.create(title=title, content=content, folder_id=folder_id)


@app.command("insert")
def insert_text(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    text: Annotated[str, typer.Argument(help="Text to insert.")],
    index: Annotated[
        int,
        typer.Option("--index", "-i", help="Index to insert at (default: 1)."),
    ] = 1,
) -> None:
    """Insert text at a specific index."""
    service = DocsService()
    service.insert(document_id=document_id, text=text, index=index)


@app.command("append")
def append_text(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    text: Annotated[
        Optional[str],
        typer.Argument(help="Text to append."),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read text from stdin."),
    ] = False,
) -> None:
    """Append text to the end of the document."""
    if stdin:
        text = sys.stdin.read()
    elif text is None:
        typer.echo("Error: Either provide text argument or use --stdin", err=True)
        raise typer.Exit(1)

    service = DocsService()
    service.append(document_id=document_id, text=text)


@app.command("replace")
def replace_text(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    find: Annotated[str, typer.Argument(help="Text to find.")],
    replace_with: Annotated[str, typer.Argument(help="Replacement text.")],
    match_case: Annotated[
        bool,
        typer.Option("--match-case", "-m", help="Case-sensitive matching."),
    ] = False,
) -> None:
    """Replace text throughout the document."""
    service = DocsService()
    service.replace(
        document_id=document_id,
        find=find,
        replace_with=replace_with,
        match_case=match_case,
    )


@app.command("format")
def format_text(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index.")],
    end_index: Annotated[int, typer.Argument(help="End index.")],
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
    """Apply formatting to a text range."""
    service = DocsService()
    service.format_text(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        bold=bold,
        italic=italic,
        underline=underline,
        font_size=font_size,
        foreground_color=color,
    )


@app.command("delete")
def delete_content(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index.")],
    end_index: Annotated[int, typer.Argument(help="End index.")],
) -> None:
    """Delete content in a range."""
    service = DocsService()
    service.delete_content(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
    )


@app.command("page-break")
def insert_page_break(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    index: Annotated[int, typer.Argument(help="Index to insert page break.")],
) -> None:
    """Insert a page break at the specified index."""
    service = DocsService()
    service.insert_page_break(document_id=document_id, index=index)


@app.command("insert-image")
def insert_image(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    image_url: Annotated[str, typer.Argument(help="Image URL (must be publicly accessible).")],
    index: Annotated[
        Optional[int],
        typer.Option("--index", "-i", help="Index to insert at (default: end)."),
    ] = None,
    width: Annotated[
        Optional[float],
        typer.Option("--width", "-w", help="Width in points."),
    ] = None,
    height: Annotated[
        Optional[float],
        typer.Option("--height", "-h", help="Height in points."),
    ] = None,
) -> None:
    """Insert an image from a URL."""
    service = DocsService()
    service.insert_image(
        document_id=document_id,
        image_url=image_url,
        index=index,
        width=width,
        height=height,
    )

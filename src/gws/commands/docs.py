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


# =============================================================================
# TABLE COMMANDS
# =============================================================================


@app.command("list-tables")
def list_tables(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
) -> None:
    """List all tables in the document."""
    service = DocsService()
    service.list_tables(document_id=document_id)


@app.command("insert-table")
def insert_table(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    rows: Annotated[int, typer.Argument(help="Number of rows.")],
    columns: Annotated[int, typer.Argument(help="Number of columns.")],
    index: Annotated[
        Optional[int],
        typer.Option("--index", "-i", help="Insert position (default: end)."),
    ] = None,
) -> None:
    """Insert a table into the document."""
    service = DocsService()
    service.insert_table(
        document_id=document_id,
        rows=rows,
        columns=columns,
        index=index,
    )


@app.command("insert-table-row")
def insert_table_row(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    row_index: Annotated[int, typer.Argument(help="Row index to insert at.")],
    above: Annotated[
        bool,
        typer.Option("--above", help="Insert above instead of below."),
    ] = False,
) -> None:
    """Insert a row into a table."""
    service = DocsService()
    service.insert_table_row(
        document_id=document_id,
        table_index=table_index,
        row_index=row_index,
        insert_below=not above,
    )


@app.command("insert-table-column")
def insert_table_column(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    column_index: Annotated[int, typer.Argument(help="Column index to insert at.")],
    left: Annotated[
        bool,
        typer.Option("--left", help="Insert left instead of right."),
    ] = False,
) -> None:
    """Insert a column into a table."""
    service = DocsService()
    service.insert_table_column(
        document_id=document_id,
        table_index=table_index,
        column_index=column_index,
        insert_right=not left,
    )


@app.command("delete-table-row")
def delete_table_row(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    row_index: Annotated[int, typer.Argument(help="Row index to delete.")],
) -> None:
    """Delete a row from a table."""
    service = DocsService()
    service.delete_table_row(
        document_id=document_id,
        table_index=table_index,
        row_index=row_index,
    )


@app.command("delete-table-column")
def delete_table_column(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    column_index: Annotated[int, typer.Argument(help="Column index to delete.")],
) -> None:
    """Delete a column from a table."""
    service = DocsService()
    service.delete_table_column(
        document_id=document_id,
        table_index=table_index,
        column_index=column_index,
    )


@app.command("merge-cells")
def merge_cells(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    start_row: Annotated[int, typer.Argument(help="Start row index.")],
    start_column: Annotated[int, typer.Argument(help="Start column index.")],
    end_row: Annotated[int, typer.Argument(help="End row index.")],
    end_column: Annotated[int, typer.Argument(help="End column index.")],
) -> None:
    """Merge cells in a table."""
    service = DocsService()
    service.merge_table_cells(
        document_id=document_id,
        table_index=table_index,
        start_row=start_row,
        start_column=start_column,
        end_row=end_row,
        end_column=end_column,
    )


@app.command("unmerge-cells")
def unmerge_cells(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    start_row: Annotated[int, typer.Argument(help="Start row index.")],
    start_column: Annotated[int, typer.Argument(help="Start column index.")],
    end_row: Annotated[int, typer.Argument(help="End row index.")],
    end_column: Annotated[int, typer.Argument(help="End column index.")],
) -> None:
    """Unmerge previously merged cells in a table."""
    service = DocsService()
    service.unmerge_table_cells(
        document_id=document_id,
        table_index=table_index,
        start_row=start_row,
        start_column=start_column,
        end_row=end_row,
        end_column=end_column,
    )


@app.command("style-table-cell")
def style_table_cell(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    start_row: Annotated[int, typer.Argument(help="Start row index.")],
    start_column: Annotated[int, typer.Argument(help="Start column index.")],
    end_row: Annotated[
        Optional[int],
        typer.Option("--end-row", help="End row index (default: same as start)."),
    ] = None,
    end_column: Annotated[
        Optional[int],
        typer.Option("--end-column", help="End column index (default: same as start)."),
    ] = None,
    bg_color: Annotated[
        Optional[str],
        typer.Option("--bg-color", help="Background color (hex, e.g., #FFFF00)."),
    ] = None,
    border_color: Annotated[
        Optional[str],
        typer.Option("--border-color", help="Border color (hex)."),
    ] = None,
    border_width: Annotated[
        Optional[float],
        typer.Option("--border-width", help="Border width in points."),
    ] = None,
    padding: Annotated[
        Optional[float],
        typer.Option("--padding", help="Padding for all sides in points."),
    ] = None,
) -> None:
    """Style table cells (background, borders, padding)."""
    service = DocsService()
    service.style_table_cell(
        document_id=document_id,
        table_index=table_index,
        start_row=start_row,
        start_column=start_column,
        end_row=end_row,
        end_column=end_column,
        background_color=bg_color,
        border_color=border_color,
        border_width=border_width,
        padding_top=padding,
        padding_bottom=padding,
        padding_left=padding,
        padding_right=padding,
    )


@app.command("set-column-width")
def set_column_width(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    column_index: Annotated[int, typer.Argument(help="Column index.")],
    width: Annotated[float, typer.Argument(help="Width in points.")],
) -> None:
    """Set the width of a table column."""
    service = DocsService()
    service.set_column_width(
        document_id=document_id,
        table_index=table_index,
        column_index=column_index,
        width=width,
    )


@app.command("pin-table-header")
def pin_table_header(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    table_index: Annotated[int, typer.Argument(help="Table index (0-based).")],
    rows: Annotated[
        int,
        typer.Option("--rows", "-r", help="Number of rows to pin as header."),
    ] = 1,
) -> None:
    """Pin header rows in a table (they repeat on each page)."""
    service = DocsService()
    service.pin_table_header(
        document_id=document_id,
        table_index=table_index,
        rows_to_pin=rows,
    )


# =============================================================================
# PARAGRAPH STYLE COMMANDS
# =============================================================================


@app.command("format-paragraph")
def format_paragraph(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index.")],
    end_index: Annotated[int, typer.Argument(help="End index.")],
    alignment: Annotated[
        Optional[str],
        typer.Option("--align", "-a", help="Alignment: START, CENTER, END, JUSTIFIED."),
    ] = None,
    style: Annotated[
        Optional[str],
        typer.Option("--style", "-s", help="Named style: TITLE, HEADING_1, etc."),
    ] = None,
    line_spacing: Annotated[
        Optional[float],
        typer.Option("--line-spacing", help="Line spacing (100=single, 200=double)."),
    ] = None,
    space_above: Annotated[
        Optional[float],
        typer.Option("--space-above", help="Space above paragraph in points."),
    ] = None,
    space_below: Annotated[
        Optional[float],
        typer.Option("--space-below", help="Space below paragraph in points."),
    ] = None,
    indent_first: Annotated[
        Optional[float],
        typer.Option("--indent-first", help="First line indent in points."),
    ] = None,
    indent_left: Annotated[
        Optional[float],
        typer.Option("--indent-left", help="Left indent in points."),
    ] = None,
    indent_right: Annotated[
        Optional[float],
        typer.Option("--indent-right", help="Right indent in points."),
    ] = None,
    shading: Annotated[
        Optional[str],
        typer.Option("--shading", help="Background color (hex, e.g., #FFFFCC)."),
    ] = None,
    keep_together: Annotated[
        Optional[bool],
        typer.Option("--keep-together/--no-keep-together", help="Keep lines together."),
    ] = None,
    keep_with_next: Annotated[
        Optional[bool],
        typer.Option("--keep-with-next/--no-keep-with-next", help="Keep with next paragraph."),
    ] = None,
) -> None:
    """Apply paragraph formatting (alignment, spacing, indentation, style)."""
    service = DocsService()
    service.format_paragraph(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        alignment=alignment,
        named_style=style,
        line_spacing=line_spacing,
        space_above=space_above,
        space_below=space_below,
        indent_first_line=indent_first,
        indent_start=indent_left,
        indent_end=indent_right,
        keep_lines_together=keep_together,
        keep_with_next=keep_with_next,
        shading_color=shading,
    )


@app.command("paragraph-border")
def paragraph_border(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index.")],
    end_index: Annotated[int, typer.Argument(help="End index.")],
    color: Annotated[
        str,
        typer.Option("--color", "-c", help="Border color (hex)."),
    ] = "#000000",
    width: Annotated[
        float,
        typer.Option("--width", "-w", help="Border width in points."),
    ] = 1.0,
    top: Annotated[bool, typer.Option("--top", help="Add top border.")] = False,
    bottom: Annotated[bool, typer.Option("--bottom", help="Add bottom border.")] = False,
    left: Annotated[bool, typer.Option("--left", help="Add left border.")] = False,
    right: Annotated[bool, typer.Option("--right", help="Add right border.")] = False,
    between: Annotated[bool, typer.Option("--between", help="Add border between paragraphs.")] = False,
    all_sides: Annotated[bool, typer.Option("--all", help="Add borders on all sides.")] = False,
) -> None:
    """Add borders to paragraphs."""
    service = DocsService()
    service.set_paragraph_border(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        color=color,
        width=width,
        top=top or all_sides,
        bottom=bottom or all_sides,
        left=left or all_sides,
        right=right or all_sides,
        between=between,
    )


# =============================================================================
# EXTENDED TEXT STYLE COMMANDS (Phase 3)
# =============================================================================


@app.command("format-text-extended")
def format_text_extended(
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
        typer.Option("--underline/--no-underline", "-u", help="Underline."),
    ] = None,
    strikethrough: Annotated[
        Optional[bool],
        typer.Option("--strikethrough/--no-strikethrough", help="Strikethrough."),
    ] = None,
    small_caps: Annotated[
        Optional[bool],
        typer.Option("--small-caps/--no-small-caps", help="Small caps."),
    ] = None,
    font: Annotated[
        Optional[str],
        typer.Option("--font", "-f", help="Font family (e.g., 'Arial', 'Times New Roman')."),
    ] = None,
    weight: Annotated[
        Optional[int],
        typer.Option("--weight", help="Font weight (100-900, 400=normal, 700=bold)."),
    ] = None,
    size: Annotated[
        Optional[int],
        typer.Option("--size", "-s", help="Font size in points."),
    ] = None,
    color: Annotated[
        Optional[str],
        typer.Option("--color", "-c", help="Text color (hex, e.g., #FF0000)."),
    ] = None,
    bg_color: Annotated[
        Optional[str],
        typer.Option("--bg-color", help="Background/highlight color (hex)."),
    ] = None,
    superscript: Annotated[
        bool,
        typer.Option("--superscript", help="Apply superscript."),
    ] = False,
    subscript: Annotated[
        bool,
        typer.Option("--subscript", help="Apply subscript."),
    ] = False,
    link: Annotated[
        Optional[str],
        typer.Option("--link", help="Add hyperlink URL."),
    ] = None,
) -> None:
    """Apply extended text formatting (fonts, colors, effects)."""
    baseline = None
    if superscript:
        baseline = "SUPERSCRIPT"
    elif subscript:
        baseline = "SUBSCRIPT"

    service = DocsService()
    service.format_text_extended(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        bold=bold,
        italic=italic,
        underline=underline,
        strikethrough=strikethrough,
        small_caps=small_caps,
        font_family=font,
        font_weight=weight,
        font_size=size,
        foreground_color=color,
        background_color=bg_color,
        baseline_offset=baseline,
        link_url=link,
    )


@app.command("insert-link")
def insert_link(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index of text to link.")],
    end_index: Annotated[int, typer.Argument(help="End index of text to link.")],
    url: Annotated[str, typer.Argument(help="URL to link to.")],
) -> None:
    """Add a hyperlink to existing text."""
    service = DocsService()
    service.insert_link(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        url=url,
    )


# =============================================================================
# HEADER/FOOTER COMMANDS (Phase 4)
# =============================================================================


@app.command("create-header")
def create_header(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    header_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Header type: DEFAULT or FIRST_PAGE_HEADER."),
    ] = "DEFAULT",
) -> None:
    """Create a document header."""
    service = DocsService()
    service.create_header(document_id=document_id, header_type=header_type)


@app.command("create-footer")
def create_footer(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    footer_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Footer type: DEFAULT or FIRST_PAGE_FOOTER."),
    ] = "DEFAULT",
) -> None:
    """Create a document footer."""
    service = DocsService()
    service.create_footer(document_id=document_id, footer_type=footer_type)


@app.command("delete-header")
def delete_header(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    header_id: Annotated[str, typer.Argument(help="Header ID to delete.")],
) -> None:
    """Delete a document header."""
    service = DocsService()
    service.delete_header(document_id=document_id, header_id=header_id)


@app.command("delete-footer")
def delete_footer(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    footer_id: Annotated[str, typer.Argument(help="Footer ID to delete.")],
) -> None:
    """Delete a document footer."""
    service = DocsService()
    service.delete_footer(document_id=document_id, footer_id=footer_id)


@app.command("list-headers-footers")
def list_headers_footers(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
) -> None:
    """List all headers and footers in the document."""
    service = DocsService()
    service.get_headers_footers(document_id=document_id)


@app.command("insert-segment-text")
def insert_segment_text(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    segment_id: Annotated[str, typer.Argument(help="Header or footer segment ID.")],
    text: Annotated[str, typer.Argument(help="Text to insert.")],
    index: Annotated[
        int,
        typer.Option("--index", "-i", help="Insert position within segment."),
    ] = 0,
) -> None:
    """Insert text into a header or footer."""
    service = DocsService()
    service.insert_text_in_segment(
        document_id=document_id,
        segment_id=segment_id,
        text=text,
        index=index,
    )


# =============================================================================
# LIST/BULLET COMMANDS (Phase 5)
# =============================================================================


@app.command("create-bullets")
def create_bullets(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index.")],
    end_index: Annotated[int, typer.Argument(help="End index.")],
    preset: Annotated[
        str,
        typer.Option("--preset", "-p", help="Bullet style preset."),
    ] = "BULLET_DISC_CIRCLE_SQUARE",
) -> None:
    """Create a bulleted list from paragraphs.

    Presets: BULLET_DISC_CIRCLE_SQUARE, BULLET_DIAMONDX_ARROW3D_SQUARE,
    BULLET_CHECKBOX, BULLET_ARROW_DIAMOND_DISC, BULLET_STAR_CIRCLE_SQUARE
    """
    service = DocsService()
    service.create_bullets(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        preset=preset,
    )


@app.command("create-numbered")
def create_numbered_list(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index.")],
    end_index: Annotated[int, typer.Argument(help="End index.")],
    preset: Annotated[
        str,
        typer.Option("--preset", "-p", help="Numbering style preset."),
    ] = "NUMBERED_DECIMAL_NESTED",
) -> None:
    """Create a numbered list from paragraphs.

    Presets: NUMBERED_DECIMAL_NESTED, NUMBERED_DECIMAL_ALPHA_ROMAN,
    NUMBERED_UPPERALPHA_ALPHA_ROMAN, NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL
    """
    service = DocsService()
    service.create_numbered_list(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        preset=preset,
    )


@app.command("remove-bullets")
def remove_bullets(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    start_index: Annotated[int, typer.Argument(help="Start index.")],
    end_index: Annotated[int, typer.Argument(help="End index.")],
) -> None:
    """Remove bullets or numbering from paragraphs."""
    service = DocsService()
    service.remove_bullets(
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
    )


# =============================================================================
# SECTION AND DOCUMENT STYLE COMMANDS (Phase 6)
# =============================================================================


@app.command("insert-section-break")
def insert_section_break(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    index: Annotated[int, typer.Argument(help="Index to insert break.")],
    break_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Break type: NEXT_PAGE or CONTINUOUS."),
    ] = "NEXT_PAGE",
) -> None:
    """Insert a section break."""
    service = DocsService()
    service.insert_section_break(
        document_id=document_id,
        index=index,
        break_type=break_type,
    )


@app.command("document-style")
def document_style(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    margin_top: Annotated[
        Optional[float],
        typer.Option("--margin-top", help="Top margin in points."),
    ] = None,
    margin_bottom: Annotated[
        Optional[float],
        typer.Option("--margin-bottom", help="Bottom margin in points."),
    ] = None,
    margin_left: Annotated[
        Optional[float],
        typer.Option("--margin-left", help="Left margin in points."),
    ] = None,
    margin_right: Annotated[
        Optional[float],
        typer.Option("--margin-right", help="Right margin in points."),
    ] = None,
    page_width: Annotated[
        Optional[float],
        typer.Option("--page-width", help="Page width in points (612=Letter, 595=A4)."),
    ] = None,
    page_height: Annotated[
        Optional[float],
        typer.Option("--page-height", help="Page height in points (792=Letter, 842=A4)."),
    ] = None,
    use_first_page_header_footer: Annotated[
        Optional[bool],
        typer.Option("--first-page-diff/--no-first-page-diff",
                     help="Use different header/footer on first page."),
    ] = None,
) -> None:
    """Update document-level style (margins, page size).

    Measurements in points (72 points = 1 inch).
    Letter: 612x792 points, A4: 595x842 points.
    """
    service = DocsService()
    service.update_document_style(
        document_id=document_id,
        margin_top=margin_top,
        margin_bottom=margin_bottom,
        margin_left=margin_left,
        margin_right=margin_right,
        page_width=page_width,
        page_height=page_height,
        use_first_page_header_footer=use_first_page_header_footer,
    )


# =============================================================================
# NAMED RANGE COMMANDS (Phase 7)
# =============================================================================


@app.command("create-named-range")
def create_named_range(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    name: Annotated[str, typer.Argument(help="Name for the range (must be unique).")],
    start_index: Annotated[int, typer.Argument(help="Start character index.")],
    end_index: Annotated[int, typer.Argument(help="End character index.")],
) -> None:
    """Create a named range (bookmark) in the document."""
    service = DocsService()
    service.create_named_range(
        document_id=document_id,
        name=name,
        start_index=start_index,
        end_index=end_index,
    )


@app.command("delete-named-range")
def delete_named_range(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Name of the range to delete."),
    ] = None,
    range_id: Annotated[
        Optional[str],
        typer.Option("--id", "-i", help="ID of the range to delete."),
    ] = None,
) -> None:
    """Delete a named range by name or ID."""
    service = DocsService()
    service.delete_named_range(
        document_id=document_id,
        name=name,
        named_range_id=range_id,
    )


@app.command("list-named-ranges")
def list_named_ranges(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
) -> None:
    """List all named ranges (bookmarks) in the document."""
    service = DocsService()
    service.list_named_ranges(document_id=document_id)


# =============================================================================
# FOOTNOTE COMMANDS (Phase 7)
# =============================================================================


@app.command("insert-footnote")
def insert_footnote(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    index: Annotated[int, typer.Argument(help="Character index to insert footnote reference.")],
) -> None:
    """Insert a footnote reference at the specified index.

    After creation, use insert-segment-text with the footnote ID to add footnote content.
    """
    service = DocsService()
    service.insert_footnote(document_id=document_id, index=index)


@app.command("list-footnotes")
def list_footnotes(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
) -> None:
    """List all footnotes in the document."""
    service = DocsService()
    service.list_footnotes(document_id=document_id)


# =============================================================================
# SUGGESTION COMMANDS (Phase 8)
# =============================================================================


@app.command("suggestions")
def get_suggestions(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
) -> None:
    """Get all pending suggestions (tracked changes) in the document.

    Returns suggestions including insertions, deletions, and style changes
    made while in "Suggesting" mode in Google Docs.

    Note: The Docs API can read suggestions but cannot accept/reject them
    programmatically. Use the Google Docs UI to accept or reject.
    """
    service = DocsService()
    service.get_suggestions(document_id=document_id)


@app.command("document-mode")
def get_document_mode(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
) -> None:
    """Check if document has pending suggestions.

    Returns information about whether the document has pending tracked changes
    and a count of unique suggestions.
    """
    service = DocsService()
    service.get_document_mode(document_id=document_id)

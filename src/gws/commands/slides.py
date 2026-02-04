"""Slides CLI commands."""

import typer
from typing import Annotated, Optional

from gws.commands._account import account_callback
from gws.services.slides import SlidesService

app = typer.Typer(
    name="slides",
    help="Google Slides presentation operations.",
    no_args_is_help=True,
    callback=account_callback,
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


@app.command("format-text-extended")
def format_text_extended(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Shape object ID.")],
    start_index: Annotated[
        Optional[int],
        typer.Option("--start", help="Start character index (0-based)."),
    ] = None,
    end_index: Annotated[
        Optional[int],
        typer.Option("--end", help="End character index (exclusive)."),
    ] = None,
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
    strikethrough: Annotated[
        Optional[bool],
        typer.Option("--strikethrough/--no-strikethrough", help="Strikethrough."),
    ] = None,
    small_caps: Annotated[
        Optional[bool],
        typer.Option("--small-caps/--no-small-caps", help="Small caps."),
    ] = None,
    font_family: Annotated[
        Optional[str],
        typer.Option("--font", "-f", help="Font family (e.g., Arial, Roboto)."),
    ] = None,
    font_weight: Annotated[
        Optional[int],
        typer.Option("--weight", "-w", help="Font weight (100-900)."),
    ] = None,
    font_size: Annotated[
        Optional[int],
        typer.Option("--size", "-s", help="Font size in points."),
    ] = None,
    foreground_color: Annotated[
        Optional[str],
        typer.Option("--color", help="Text color (hex, e.g., #FF0000)."),
    ] = None,
    background_color: Annotated[
        Optional[str],
        typer.Option("--bg-color", help="Background/highlight color (hex)."),
    ] = None,
    baseline_offset: Annotated[
        Optional[str],
        typer.Option("--baseline", help="Baseline offset (SUPERSCRIPT, SUBSCRIPT)."),
    ] = None,
    link_url: Annotated[
        Optional[str],
        typer.Option("--link", help="URL to link the text to."),
    ] = None,
) -> None:
    """Apply extended formatting to text with all options."""
    service = SlidesService()
    service.format_text_extended(
        presentation_id=presentation_id,
        object_id=object_id,
        start_index=start_index,
        end_index=end_index,
        bold=bold,
        italic=italic,
        underline=underline,
        strikethrough=strikethrough,
        small_caps=small_caps,
        font_family=font_family,
        font_weight=font_weight,
        font_size=font_size,
        foreground_color=foreground_color,
        background_color=background_color,
        baseline_offset=baseline_offset,
        link_url=link_url,
    )


@app.command("format-paragraph")
def format_paragraph(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Shape object ID.")],
    start_index: Annotated[
        Optional[int],
        typer.Option("--start", help="Start character index (0-based)."),
    ] = None,
    end_index: Annotated[
        Optional[int],
        typer.Option("--end", help="End character index (exclusive)."),
    ] = None,
    alignment: Annotated[
        Optional[str],
        typer.Option("--align", "-a", help="Alignment (START, CENTER, END, JUSTIFIED)."),
    ] = None,
    line_spacing: Annotated[
        Optional[float],
        typer.Option("--line-spacing", help="Line spacing as percentage (100=single)."),
    ] = None,
    space_above: Annotated[
        Optional[float],
        typer.Option("--space-above", help="Space above paragraph in points."),
    ] = None,
    space_below: Annotated[
        Optional[float],
        typer.Option("--space-below", help="Space below paragraph in points."),
    ] = None,
    indent_first_line: Annotated[
        Optional[float],
        typer.Option("--indent-first", help="First line indent in points."),
    ] = None,
    indent_start: Annotated[
        Optional[float],
        typer.Option("--indent-start", help="Start (left) indent in points."),
    ] = None,
    indent_end: Annotated[
        Optional[float],
        typer.Option("--indent-end", help="End (right) indent in points."),
    ] = None,
) -> None:
    """Apply paragraph formatting (alignment, spacing, indentation)."""
    service = SlidesService()
    service.format_paragraph(
        presentation_id=presentation_id,
        object_id=object_id,
        start_index=start_index,
        end_index=end_index,
        alignment=alignment,
        line_spacing=line_spacing,
        space_above=space_above,
        space_below=space_below,
        indent_first_line=indent_first_line,
        indent_start=indent_start,
        indent_end=indent_end,
    )


@app.command("create-shape")
def create_shape(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    page_id: Annotated[str, typer.Argument(help="Page/slide object ID.")],
    shape_type: Annotated[
        str, typer.Argument(help="Shape type (RECTANGLE, ELLIPSE, etc.).")
    ],
    x: Annotated[float, typer.Option("--x", help="X position in points.")],
    y: Annotated[float, typer.Option("--y", help="Y position in points.")],
    width: Annotated[float, typer.Option("--width", "-w", help="Width in points.")],
    height: Annotated[float, typer.Option("--height", "-h", help="Height in points.")],
) -> None:
    """Create a shape on a slide."""
    service = SlidesService()
    service.create_shape(
        presentation_id=presentation_id,
        page_object_id=page_id,
        shape_type=shape_type,
        x=x,
        y=y,
        width=width,
        height=height,
    )


@app.command("format-shape")
def format_shape(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Shape object ID.")],
    fill_color: Annotated[
        Optional[str],
        typer.Option("--fill", help="Fill color (hex, e.g., #FF0000)."),
    ] = None,
    outline_color: Annotated[
        Optional[str],
        typer.Option("--outline-color", help="Outline color (hex)."),
    ] = None,
    outline_weight: Annotated[
        Optional[float],
        typer.Option("--outline-weight", help="Outline weight in points."),
    ] = None,
    outline_dash_style: Annotated[
        Optional[str],
        typer.Option("--outline-style", help="Dash style (SOLID, DOT, DASH, etc.)."),
    ] = None,
) -> None:
    """Format a shape's fill and outline."""
    service = SlidesService()
    service.format_shape(
        presentation_id=presentation_id,
        object_id=object_id,
        fill_color=fill_color,
        outline_color=outline_color,
        outline_weight=outline_weight,
        outline_dash_style=outline_dash_style,
    )


@app.command("insert-table")
def insert_table(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    page_id: Annotated[str, typer.Argument(help="Page/slide object ID.")],
    rows: Annotated[int, typer.Argument(help="Number of rows.")],
    columns: Annotated[int, typer.Argument(help="Number of columns.")],
    x: Annotated[float, typer.Option("--x", help="X position in points.")],
    y: Annotated[float, typer.Option("--y", help="Y position in points.")],
    width: Annotated[float, typer.Option("--width", "-w", help="Width in points.")],
    height: Annotated[float, typer.Option("--height", "-h", help="Height in points.")],
) -> None:
    """Insert a table on a slide."""
    service = SlidesService()
    service.insert_table(
        presentation_id=presentation_id,
        page_object_id=page_id,
        rows=rows,
        columns=columns,
        x=x,
        y=y,
        width=width,
        height=height,
    )


@app.command("insert-table-row")
def insert_table_row(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    row_index: Annotated[int, typer.Argument(help="Row index to insert at.")],
    below: Annotated[
        bool,
        typer.Option("--below/--above", help="Insert below (default) or above."),
    ] = True,
) -> None:
    """Insert a row in a table."""
    service = SlidesService()
    service.insert_table_row(
        presentation_id=presentation_id,
        table_id=table_id,
        row_index=row_index,
        insert_below=below,
    )


@app.command("insert-table-column")
def insert_table_column(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    column_index: Annotated[int, typer.Argument(help="Column index to insert at.")],
    right: Annotated[
        bool,
        typer.Option("--right/--left", help="Insert right (default) or left."),
    ] = True,
) -> None:
    """Insert a column in a table."""
    service = SlidesService()
    service.insert_table_column(
        presentation_id=presentation_id,
        table_id=table_id,
        column_index=column_index,
        insert_right=right,
    )


@app.command("delete-table-row")
def delete_table_row(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    row_index: Annotated[int, typer.Argument(help="Row index to delete.")],
) -> None:
    """Delete a row from a table."""
    service = SlidesService()
    service.delete_table_row(
        presentation_id=presentation_id,
        table_id=table_id,
        row_index=row_index,
    )


@app.command("delete-table-column")
def delete_table_column(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    column_index: Annotated[int, typer.Argument(help="Column index to delete.")],
) -> None:
    """Delete a column from a table."""
    service = SlidesService()
    service.delete_table_column(
        presentation_id=presentation_id,
        table_id=table_id,
        column_index=column_index,
    )


@app.command("style-table-cell")
def style_table_cell(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    row_index: Annotated[int, typer.Argument(help="Starting row index.")],
    column_index: Annotated[int, typer.Argument(help="Starting column index.")],
    background_color: Annotated[
        Optional[str],
        typer.Option("--bg-color", help="Background color (hex)."),
    ] = None,
    end_row_index: Annotated[
        Optional[int],
        typer.Option("--end-row", help="Ending row index (exclusive)."),
    ] = None,
    end_column_index: Annotated[
        Optional[int],
        typer.Option("--end-col", help="Ending column index (exclusive)."),
    ] = None,
) -> None:
    """Style table cells (background color)."""
    service = SlidesService()
    service.style_table_cell(
        presentation_id=presentation_id,
        table_id=table_id,
        row_index=row_index,
        column_index=column_index,
        background_color=background_color,
        end_row_index=end_row_index,
        end_column_index=end_column_index,
    )


@app.command("insert-table-text")
def insert_table_text(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    row_index: Annotated[int, typer.Argument(help="Row index.")],
    column_index: Annotated[int, typer.Argument(help="Column index.")],
    text: Annotated[str, typer.Argument(help="Text to insert.")],
) -> None:
    """Insert text into a table cell."""
    service = SlidesService()
    service.insert_text_in_table_cell(
        presentation_id=presentation_id,
        table_id=table_id,
        row_index=row_index,
        column_index=column_index,
        text=text,
    )


# ===== Phase 6: Slides Enhancements =====


@app.command("set-background")
def set_background(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    slide_id: Annotated[str, typer.Argument(help="Slide object ID.")],
    color: Annotated[
        Optional[str],
        typer.Option("--color", "-c", help="Background color (hex, e.g., #FFFFFF)."),
    ] = None,
    image_url: Annotated[
        Optional[str],
        typer.Option("--image", "-i", help="Background image URL."),
    ] = None,
) -> None:
    """Set slide background to a color or image."""
    service = SlidesService()
    service.set_slide_background(
        presentation_id=presentation_id,
        slide_id=slide_id,
        color=color,
        image_url=image_url,
    )


@app.command("create-bullets")
def create_bullets(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Shape/text box object ID.")],
    bullet_preset: Annotated[
        str,
        typer.Option(
            "--preset", "-p",
            help="Bullet preset (BULLET_DISC_CIRCLE_SQUARE, NUMBERED_DIGIT_ALPHA_ROMAN, etc.).",
        ),
    ] = "BULLET_DISC_CIRCLE_SQUARE",
    start_index: Annotated[
        Optional[int],
        typer.Option("--start", help="Start character index (0-based)."),
    ] = None,
    end_index: Annotated[
        Optional[int],
        typer.Option("--end", help="End character index (exclusive)."),
    ] = None,
) -> None:
    """Add bullet list formatting to text."""
    service = SlidesService()
    service.create_bullets(
        presentation_id=presentation_id,
        object_id=object_id,
        bullet_preset=bullet_preset,
        start_index=start_index,
        end_index=end_index,
    )


@app.command("remove-bullets")
def remove_bullets(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    object_id: Annotated[str, typer.Argument(help="Shape/text box object ID.")],
    start_index: Annotated[
        Optional[int],
        typer.Option("--start", help="Start character index (0-based)."),
    ] = None,
    end_index: Annotated[
        Optional[int],
        typer.Option("--end", help="End character index (exclusive)."),
    ] = None,
) -> None:
    """Remove bullet list formatting from text."""
    service = SlidesService()
    service.remove_bullets(
        presentation_id=presentation_id,
        object_id=object_id,
        start_index=start_index,
        end_index=end_index,
    )


@app.command("style-table-borders")
def style_table_borders(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    row_index: Annotated[int, typer.Argument(help="Starting row index.")],
    column_index: Annotated[int, typer.Argument(help="Starting column index.")],
    row_span: Annotated[
        int,
        typer.Option("--rows", "-r", help="Number of rows to style."),
    ] = 1,
    column_span: Annotated[
        int,
        typer.Option("--cols", "-c", help="Number of columns to style."),
    ] = 1,
    color: Annotated[
        str,
        typer.Option("--color", help="Border color (hex)."),
    ] = "#000000",
    weight: Annotated[
        float,
        typer.Option("--weight", "-w", help="Border weight in points."),
    ] = 1.0,
    dash_style: Annotated[
        str,
        typer.Option("--style", "-s", help="Dash style (SOLID, DOT, DASH, etc.)."),
    ] = "SOLID",
    border_position: Annotated[
        str,
        typer.Option("--position", "-p", help="Border position (ALL, INNER, OUTER, etc.)."),
    ] = "ALL",
) -> None:
    """Style table cell borders."""
    service = SlidesService()
    service.style_table_borders(
        presentation_id=presentation_id,
        table_id=table_id,
        row_index=row_index,
        column_index=column_index,
        row_span=row_span,
        column_span=column_span,
        color=color,
        weight=weight,
        dash_style=dash_style,
        border_position=border_position,
    )


@app.command("merge-table-cells")
def merge_table_cells(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    row_index: Annotated[int, typer.Argument(help="Starting row index.")],
    column_index: Annotated[int, typer.Argument(help="Starting column index.")],
    row_span: Annotated[int, typer.Argument(help="Number of rows to merge.")],
    column_span: Annotated[int, typer.Argument(help="Number of columns to merge.")],
) -> None:
    """Merge table cells into one."""
    service = SlidesService()
    service.merge_table_cells(
        presentation_id=presentation_id,
        table_id=table_id,
        row_index=row_index,
        column_index=column_index,
        row_span=row_span,
        column_span=column_span,
    )


@app.command("unmerge-table-cells")
def unmerge_table_cells(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    table_id: Annotated[str, typer.Argument(help="Table object ID.")],
    row_index: Annotated[int, typer.Argument(help="Starting row index.")],
    column_index: Annotated[int, typer.Argument(help="Starting column index.")],
    row_span: Annotated[int, typer.Argument(help="Number of rows in merged region.")],
    column_span: Annotated[int, typer.Argument(help="Number of columns in merged region.")],
) -> None:
    """Unmerge previously merged table cells."""
    service = SlidesService()
    service.unmerge_table_cells(
        presentation_id=presentation_id,
        table_id=table_id,
        row_index=row_index,
        column_index=column_index,
        row_span=row_span,
        column_span=column_span,
    )


@app.command("create-line")
def create_line(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    page_id: Annotated[str, typer.Argument(help="Page/slide object ID.")],
    start_x: Annotated[float, typer.Option("--start-x", help="Start X position in points.")],
    start_y: Annotated[float, typer.Option("--start-y", help="Start Y position in points.")],
    end_x: Annotated[float, typer.Option("--end-x", help="End X position in points.")],
    end_y: Annotated[float, typer.Option("--end-y", help="End Y position in points.")],
    line_category: Annotated[
        str,
        typer.Option("--category", "-c", help="Line category (STRAIGHT, BENT, CURVED)."),
    ] = "STRAIGHT",
    color: Annotated[
        str,
        typer.Option("--color", help="Line color (hex)."),
    ] = "#000000",
    weight: Annotated[
        float,
        typer.Option("--weight", "-w", help="Line weight in points."),
    ] = 1.0,
    dash_style: Annotated[
        str,
        typer.Option("--style", "-s", help="Dash style (SOLID, DOT, DASH, etc.)."),
    ] = "SOLID",
    start_arrow: Annotated[
        Optional[str],
        typer.Option("--start-arrow", help="Start arrow type (FILL_ARROW, OPEN_ARROW, etc.)."),
    ] = None,
    end_arrow: Annotated[
        Optional[str],
        typer.Option("--end-arrow", help="End arrow type (FILL_ARROW, OPEN_ARROW, etc.)."),
    ] = None,
) -> None:
    """Create a line or arrow on a slide."""
    service = SlidesService()
    service.create_line(
        presentation_id=presentation_id,
        page_object_id=page_id,
        start_x=start_x,
        start_y=start_y,
        end_x=end_x,
        end_y=end_y,
        line_category=line_category,
        color=color,
        weight=weight,
        dash_style=dash_style,
        start_arrow=start_arrow,
        end_arrow=end_arrow,
    )


@app.command("reorder-slides")
def reorder_slides(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    slide_ids: Annotated[str, typer.Argument(help="Comma-separated slide object IDs to move.")],
    insertion_index: Annotated[int, typer.Argument(help="Target index (0-based).")],
) -> None:
    """Move slides to a new position."""
    slide_id_list = [s.strip() for s in slide_ids.split(",")]

    service = SlidesService()
    service.reorder_slides(
        presentation_id=presentation_id,
        slide_ids=slide_id_list,
        insertion_index=insertion_index,
    )


# ===== Speaker Notes =====


@app.command("get-speaker-notes")
def get_speaker_notes(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    slide_id: Annotated[str, typer.Argument(help="Slide object ID.")],
) -> None:
    """Get speaker notes for a slide."""
    service = SlidesService()
    service.get_speaker_notes(
        presentation_id=presentation_id,
        slide_id=slide_id,
    )


@app.command("set-speaker-notes")
def set_speaker_notes(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    slide_id: Annotated[str, typer.Argument(help="Slide object ID.")],
    notes_text: Annotated[str, typer.Argument(help="Speaker notes text content.")],
) -> None:
    """Set speaker notes for a slide."""
    service = SlidesService()
    service.set_speaker_notes(
        presentation_id=presentation_id,
        slide_id=slide_id,
        notes_text=notes_text,
    )


# ===== Video =====


@app.command("insert-video")
def insert_video(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    page_id: Annotated[str, typer.Argument(help="Slide/page object ID.")],
    video_url: Annotated[str, typer.Argument(help="YouTube video URL.")],
    x: Annotated[float, typer.Argument(help="X position in points.")],
    y: Annotated[float, typer.Argument(help="Y position in points.")],
    width: Annotated[float, typer.Argument(help="Width in points.")],
    height: Annotated[float, typer.Argument(help="Height in points.")],
) -> None:
    """Insert a YouTube video on a slide."""
    service = SlidesService()
    service.insert_video(
        presentation_id=presentation_id,
        page_object_id=page_id,
        video_url=video_url,
        x=x,
        y=y,
        width=width,
        height=height,
    )


@app.command("update-video-properties")
def update_video_properties(
    presentation_id: Annotated[str, typer.Argument(help="Presentation ID.")],
    video_object_id: Annotated[str, typer.Argument(help="Video object ID.")],
    autoplay: Annotated[
        Optional[bool],
        typer.Option("--autoplay", help="Autoplay when presenting."),
    ] = None,
    start_time: Annotated[
        Optional[int],
        typer.Option("--start", "-s", help="Start time in seconds."),
    ] = None,
    end_time: Annotated[
        Optional[int],
        typer.Option("--end", "-e", help="End time in seconds."),
    ] = None,
    mute: Annotated[
        Optional[bool],
        typer.Option("--mute", "-m", help="Mute video."),
    ] = None,
) -> None:
    """Update video playback properties."""
    service = SlidesService()
    service.update_video_properties(
        presentation_id=presentation_id,
        video_object_id=video_object_id,
        autoplay=autoplay,
        start_time=start_time,
        end_time=end_time,
        mute=mute,
    )

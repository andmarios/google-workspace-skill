"""Sheets CLI commands."""

import json
import sys
import typer
from typing import Annotated, Optional

from gws.services.sheets import SheetsService
from gws.output import output_error
from gws.exceptions import ExitCode

app = typer.Typer(
    name="sheets",
    help="Google Sheets spreadsheet operations.",
    no_args_is_help=True,
)


@app.command("metadata")
def get_metadata(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
) -> None:
    """Get spreadsheet metadata and sheet list."""
    service = SheetsService()
    service.metadata(spreadsheet_id=spreadsheet_id)


@app.command("read")
def read_values(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    range_notation: Annotated[
        Optional[str],
        typer.Argument(help="A1 notation range (e.g., 'Sheet1!A1:C10')."),
    ] = None,
) -> None:
    """Read values from a spreadsheet range."""
    service = SheetsService()
    service.read(spreadsheet_id=spreadsheet_id, range_notation=range_notation)


@app.command("create")
def create_spreadsheet(
    title: Annotated[str, typer.Argument(help="Spreadsheet title.")],
    sheets: Annotated[
        Optional[str],
        typer.Option("--sheets", "-s", help="Comma-separated sheet names."),
    ] = None,
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Folder ID to create spreadsheet in."),
    ] = None,
) -> None:
    """Create a new spreadsheet."""
    sheet_titles = sheets.split(",") if sheets else None

    service = SheetsService()
    service.create(title=title, sheet_titles=sheet_titles, folder_id=folder_id)


@app.command("write")
def write_values(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    range_notation: Annotated[str, typer.Argument(help="A1 notation range.")],
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read values as JSON from stdin."),
    ] = False,
    values: Annotated[
        Optional[str],
        typer.Option("--values", "-v", help="JSON array of rows."),
    ] = None,
) -> None:
    """Write values to a spreadsheet range.

    Values should be a JSON array of arrays, e.g., '[["A1", "B1"], ["A2", "B2"]]'
    """
    if stdin:
        data = json.loads(sys.stdin.read())
        if isinstance(data, list):
            values_list = data
        else:
            values_list = data.get("values", [])
    elif values:
        values_list = json.loads(values)
    else:
        output_error(
            error_code="INVALID_ARGS",
            operation="sheets.write",
            message="Either --stdin or --values required",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    service = SheetsService()
    service.write(
        spreadsheet_id=spreadsheet_id,
        range_notation=range_notation,
        values=values_list,
    )


@app.command("append")
def append_values(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    range_notation: Annotated[str, typer.Argument(help="A1 notation range to append to.")],
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read values as JSON from stdin."),
    ] = False,
    values: Annotated[
        Optional[str],
        typer.Option("--values", "-v", help="JSON array of rows."),
    ] = None,
) -> None:
    """Append values to a spreadsheet."""
    if stdin:
        data = json.loads(sys.stdin.read())
        if isinstance(data, list):
            values_list = data
        else:
            values_list = data.get("values", [])
    elif values:
        values_list = json.loads(values)
    else:
        output_error(
            error_code="INVALID_ARGS",
            operation="sheets.append",
            message="Either --stdin or --values required",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    service = SheetsService()
    service.append(
        spreadsheet_id=spreadsheet_id,
        range_notation=range_notation,
        values=values_list,
    )


@app.command("clear")
def clear_values(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    range_notation: Annotated[str, typer.Argument(help="A1 notation range to clear.")],
) -> None:
    """Clear values from a range."""
    service = SheetsService()
    service.clear(spreadsheet_id=spreadsheet_id, range_notation=range_notation)


@app.command("add-sheet")
def add_sheet(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    title: Annotated[str, typer.Argument(help="New sheet title.")],
) -> None:
    """Add a new sheet to the spreadsheet."""
    service = SheetsService()
    service.add_sheet(spreadsheet_id=spreadsheet_id, title=title)


@app.command("delete-sheet")
def delete_sheet(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric) to delete.")],
) -> None:
    """Delete a sheet from the spreadsheet."""
    service = SheetsService()
    service.delete_sheet(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)


@app.command("rename-sheet")
def rename_sheet(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    new_title: Annotated[str, typer.Argument(help="New title for the sheet.")],
) -> None:
    """Rename a sheet."""
    service = SheetsService()
    service.rename_sheet(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        new_title=new_title,
    )


@app.command("format")
def format_cells(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive, 0-indexed).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive, 0-indexed).")],
    bold: Annotated[
        Optional[bool],
        typer.Option("--bold/--no-bold", "-b", help="Bold formatting."),
    ] = None,
    italic: Annotated[
        Optional[bool],
        typer.Option("--italic/--no-italic", "-i", help="Italic formatting."),
    ] = None,
    font_size: Annotated[
        Optional[int],
        typer.Option("--font-size", "-s", help="Font size in points."),
    ] = None,
    background_color: Annotated[
        Optional[str],
        typer.Option("--bg-color", help="Background color (hex, e.g., #FFFF00)."),
    ] = None,
    foreground_color: Annotated[
        Optional[str],
        typer.Option("--fg-color", help="Text color (hex, e.g., #FF0000)."),
    ] = None,
) -> None:
    """Apply formatting to a cell range."""
    service = SheetsService()
    service.format_cells(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        bold=bold,
        italic=italic,
        font_size=font_size,
        background_color=background_color,
        foreground_color=foreground_color,
    )


@app.command("batch-get")
def batch_get(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    ranges: Annotated[str, typer.Argument(help="Comma-separated A1 notation ranges.")],
) -> None:
    """Read multiple ranges at once."""
    range_list = [r.strip() for r in ranges.split(",")]

    service = SheetsService()
    service.batch_get(spreadsheet_id=spreadsheet_id, ranges=range_list)


@app.command("format-extended")
def format_cells_extended(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
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
    font_family: Annotated[
        Optional[str],
        typer.Option("--font", "-f", help="Font family name."),
    ] = None,
    font_size: Annotated[
        Optional[int],
        typer.Option("--size", "-s", help="Font size in points."),
    ] = None,
    foreground_color: Annotated[
        Optional[str],
        typer.Option("--fg-color", help="Text color (hex)."),
    ] = None,
    background_color: Annotated[
        Optional[str],
        typer.Option("--bg-color", help="Background color (hex)."),
    ] = None,
    horizontal_alignment: Annotated[
        Optional[str],
        typer.Option("--h-align", help="Horizontal alignment (LEFT, CENTER, RIGHT)."),
    ] = None,
    vertical_alignment: Annotated[
        Optional[str],
        typer.Option("--v-align", help="Vertical alignment (TOP, MIDDLE, BOTTOM)."),
    ] = None,
    text_wrap: Annotated[
        Optional[str],
        typer.Option("--wrap", help="Text wrap (OVERFLOW_CELL, CLIP, WRAP)."),
    ] = None,
    number_format: Annotated[
        Optional[str],
        typer.Option("--number-format", help="Number format pattern (e.g., '#,##0.00')."),
    ] = None,
) -> None:
    """Apply extended formatting to a cell range."""
    service = SheetsService()
    service.format_cells_extended(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        bold=bold,
        italic=italic,
        underline=underline,
        strikethrough=strikethrough,
        font_family=font_family,
        font_size=font_size,
        foreground_color=foreground_color,
        background_color=background_color,
        horizontal_alignment=horizontal_alignment,
        vertical_alignment=vertical_alignment,
        text_wrap=text_wrap,
        number_format=number_format,
    )


@app.command("set-borders")
def set_borders(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
    top: Annotated[bool, typer.Option("--top", help="Apply top border.")] = False,
    bottom: Annotated[bool, typer.Option("--bottom", help="Apply bottom border.")] = False,
    left: Annotated[bool, typer.Option("--left", help="Apply left border.")] = False,
    right: Annotated[bool, typer.Option("--right", help="Apply right border.")] = False,
    inner_horizontal: Annotated[
        bool, typer.Option("--inner-h", help="Apply inner horizontal borders.")
    ] = False,
    inner_vertical: Annotated[
        bool, typer.Option("--inner-v", help="Apply inner vertical borders.")
    ] = False,
    all_borders: Annotated[
        bool, typer.Option("--all", "-a", help="Apply all borders (outer + inner).")
    ] = False,
    color: Annotated[
        str, typer.Option("--color", "-c", help="Border color (hex).")
    ] = "#000000",
    style: Annotated[
        str, typer.Option("--style", help="Border style (SOLID, DOTTED, DASHED, etc.).")
    ] = "SOLID",
    width: Annotated[
        int, typer.Option("--width", "-w", help="Border width (1, 2, or 3).")
    ] = 1,
) -> None:
    """Set borders on a cell range."""
    if all_borders:
        top = bottom = left = right = inner_horizontal = inner_vertical = True

    service = SheetsService()
    service.set_borders(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        top=top,
        bottom=bottom,
        left=left,
        right=right,
        inner_horizontal=inner_horizontal,
        inner_vertical=inner_vertical,
        color=color,
        style=style,
        width=width,
    )


@app.command("merge-cells")
def merge_cells(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
    merge_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Merge type (MERGE_ALL, MERGE_COLUMNS, MERGE_ROWS)."),
    ] = "MERGE_ALL",
) -> None:
    """Merge cells in a range."""
    service = SheetsService()
    service.merge_cells(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        merge_type=merge_type,
    )


@app.command("unmerge-cells")
def unmerge_cells(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
) -> None:
    """Unmerge cells in a range."""
    service = SheetsService()
    service.unmerge_cells(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
    )


@app.command("set-column-width")
def set_column_width(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_column: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_column: Annotated[int, typer.Argument(help="End column (exclusive).")],
    width: Annotated[int, typer.Argument(help="Width in pixels.")],
) -> None:
    """Set column width."""
    service = SheetsService()
    service.set_column_width(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_column=start_column,
        end_column=end_column,
        width=width,
    )


@app.command("set-row-height")
def set_row_height(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    height: Annotated[int, typer.Argument(help="Height in pixels.")],
) -> None:
    """Set row height."""
    service = SheetsService()
    service.set_row_height(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        height=height,
    )


@app.command("auto-resize-columns")
def auto_resize_columns(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_column: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_column: Annotated[int, typer.Argument(help="End column (exclusive).")],
) -> None:
    """Auto-resize columns to fit content."""
    service = SheetsService()
    service.auto_resize_columns(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_column=start_column,
        end_column=end_column,
    )


@app.command("freeze-rows")
def freeze_rows(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    num_rows: Annotated[int, typer.Argument(help="Number of rows to freeze (0 to unfreeze).")],
) -> None:
    """Freeze rows at the top of the sheet."""
    service = SheetsService()
    service.freeze_rows(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        num_rows=num_rows,
    )


@app.command("freeze-columns")
def freeze_columns(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    num_columns: Annotated[int, typer.Argument(help="Number of columns to freeze (0 to unfreeze).")],
) -> None:
    """Freeze columns at the left of the sheet."""
    service = SheetsService()
    service.freeze_columns(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        num_columns=num_columns,
    )


@app.command("add-conditional-format")
def add_conditional_format(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
    condition_type: Annotated[
        str,
        typer.Option("--condition", "-c", help="Condition type (NUMBER_GREATER, TEXT_CONTAINS, etc.)."),
    ],
    condition_values: Annotated[
        str,
        typer.Option("--values", "-v", help="Comma-separated condition values."),
    ] = "",
    background_color: Annotated[
        Optional[str],
        typer.Option("--bg-color", help="Background color when condition met (hex)."),
    ] = None,
    foreground_color: Annotated[
        Optional[str],
        typer.Option("--fg-color", help="Text color when condition met (hex)."),
    ] = None,
    bold: Annotated[
        Optional[bool],
        typer.Option("--bold/--no-bold", "-b", help="Bold when condition met."),
    ] = None,
) -> None:
    """Add a conditional formatting rule."""
    values_list = [v.strip() for v in condition_values.split(",") if v.strip()]

    service = SheetsService()
    service.add_conditional_format(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        condition_type=condition_type,
        condition_values=values_list,
        background_color=background_color,
        foreground_color=foreground_color,
        bold=bold,
    )


@app.command("add-color-scale")
def add_color_scale(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
    min_color: Annotated[
        str, typer.Option("--min-color", help="Color for minimum values (hex).")
    ],
    max_color: Annotated[
        str, typer.Option("--max-color", help="Color for maximum values (hex).")
    ],
    mid_color: Annotated[
        Optional[str],
        typer.Option("--mid-color", help="Color for midpoint values (hex, optional)."),
    ] = None,
) -> None:
    """Add a color scale conditional formatting rule."""
    service = SheetsService()
    service.add_color_scale(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        min_color=min_color,
        max_color=max_color,
        mid_color=mid_color,
    )


@app.command("clear-conditional-formats")
def clear_conditional_formats(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
) -> None:
    """Clear all conditional formatting rules from a sheet."""
    service = SheetsService()
    service.clear_conditional_formats(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
    )


@app.command("insert-rows")
def insert_rows(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_index: Annotated[int, typer.Argument(help="Row index to insert at (0-indexed).")],
    count: Annotated[int, typer.Argument(help="Number of rows to insert.")],
    inherit_from_before: Annotated[
        bool,
        typer.Option("--inherit-before/--inherit-after", help="Inherit formatting from row before (default) or after."),
    ] = True,
) -> None:
    """Insert rows at a specific index."""
    service = SheetsService()
    service.insert_rows(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_index=start_index,
        count=count,
        inherit_from_before=inherit_from_before,
    )


@app.command("insert-columns")
def insert_columns(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_index: Annotated[int, typer.Argument(help="Column index to insert at (0-indexed).")],
    count: Annotated[int, typer.Argument(help="Number of columns to insert.")],
    inherit_from_before: Annotated[
        bool,
        typer.Option("--inherit-before/--inherit-after", help="Inherit formatting from column before (default) or after."),
    ] = True,
) -> None:
    """Insert columns at a specific index."""
    service = SheetsService()
    service.insert_columns(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_index=start_index,
        count=count,
        inherit_from_before=inherit_from_before,
    )


@app.command("delete-rows")
def delete_rows(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_index: Annotated[int, typer.Argument(help="Start row index (0-indexed, inclusive).")],
    end_index: Annotated[int, typer.Argument(help="End row index (0-indexed, exclusive).")],
) -> None:
    """Delete rows in a range."""
    service = SheetsService()
    service.delete_rows(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_index=start_index,
        end_index=end_index,
    )


@app.command("delete-columns")
def delete_columns(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_index: Annotated[int, typer.Argument(help="Start column index (0-indexed, inclusive).")],
    end_index: Annotated[int, typer.Argument(help="End column index (0-indexed, exclusive).")],
) -> None:
    """Delete columns in a range."""
    service = SheetsService()
    service.delete_columns(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_index=start_index,
        end_index=end_index,
    )


@app.command("sort")
def sort_range(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
    sort_column: Annotated[int, typer.Argument(help="Column index to sort by (0-indexed).")],
    descending: Annotated[
        bool,
        typer.Option("--desc", "-d", help="Sort in descending order."),
    ] = False,
) -> None:
    """Sort a range by a column."""
    service = SheetsService()
    service.sort_range(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        sort_column=sort_column,
        ascending=not descending,
    )


@app.command("find-replace")
def find_replace(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    find: Annotated[str, typer.Argument(help="Text to find.")],
    replace: Annotated[str, typer.Argument(help="Replacement text.")],
    sheet_id: Annotated[
        Optional[int],
        typer.Option("--sheet-id", "-s", help="Limit to specific sheet ID."),
    ] = None,
    all_sheets: Annotated[
        bool,
        typer.Option("--all-sheets", "-a", help="Search all sheets."),
    ] = False,
    match_case: Annotated[
        bool,
        typer.Option("--match-case", "-c", help="Case-sensitive matching."),
    ] = False,
    match_entire_cell: Annotated[
        bool,
        typer.Option("--entire-cell", "-e", help="Match entire cell contents."),
    ] = False,
    use_regex: Annotated[
        bool,
        typer.Option("--regex", "-r", help="Use regular expression."),
    ] = False,
) -> None:
    """Find and replace text in a spreadsheet."""
    service = SheetsService()
    service.find_replace(
        spreadsheet_id=spreadsheet_id,
        find=find,
        replace=replace,
        sheet_id=sheet_id,
        all_sheets=all_sheets,
        match_case=match_case,
        match_entire_cell=match_entire_cell,
        use_regex=use_regex,
    )


@app.command("duplicate-sheet")
def duplicate_sheet(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID to duplicate.")],
    new_name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Name for the new sheet."),
    ] = None,
    insert_index: Annotated[
        Optional[int],
        typer.Option("--index", "-i", help="Position to insert the new sheet."),
    ] = None,
) -> None:
    """Duplicate a sheet within the spreadsheet."""
    service = SheetsService()
    service.duplicate_sheet(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        new_name=new_name,
        insert_index=insert_index,
    )


@app.command("set-validation")
def set_validation(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
    validation_type: Annotated[
        str,
        typer.Option(
            "--type", "-t",
            help="Validation type (ONE_OF_LIST, NUMBER_GREATER, TEXT_CONTAINS, etc.).",
        ),
    ],
    values: Annotated[
        Optional[str],
        typer.Option("--values", "-v", help="Comma-separated values for list or conditions."),
    ] = None,
    formula: Annotated[
        Optional[str],
        typer.Option("--formula", "-f", help="Custom formula for CUSTOM_FORMULA type."),
    ] = None,
    allow_invalid: Annotated[
        bool,
        typer.Option("--allow-invalid", help="Allow invalid input with warning."),
    ] = False,
    no_dropdown: Annotated[
        bool,
        typer.Option("--no-dropdown", help="Hide dropdown for list validation."),
    ] = False,
) -> None:
    """Set data validation on a cell range.

    Validation types: ONE_OF_LIST, NUMBER_GREATER, NUMBER_LESS, NUMBER_BETWEEN,
    TEXT_CONTAINS, TEXT_IS_EMAIL, DATE_BEFORE, CUSTOM_FORMULA, etc.
    """
    values_list = [v.strip() for v in values.split(",")] if values else None

    service = SheetsService()
    service.set_data_validation(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        validation_type=validation_type,
        values=values_list,
        formula=formula,
        strict=not allow_invalid,
        show_dropdown=not no_dropdown,
    )


@app.command("clear-validation")
def clear_validation(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
) -> None:
    """Clear data validation from a cell range."""
    service = SheetsService()
    service.clear_data_validation(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
    )


@app.command("add-chart")
def add_chart(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    chart_type: Annotated[
        str, typer.Argument(help="Chart type (LINE, COLUMN, BAR, PIE, SCATTER, AREA).")
    ],
    data_start_row: Annotated[int, typer.Argument(help="Data range start row (0-indexed).")],
    data_end_row: Annotated[int, typer.Argument(help="Data range end row (exclusive).")],
    data_start_col: Annotated[int, typer.Argument(help="Data range start column (0-indexed).")],
    data_end_col: Annotated[int, typer.Argument(help="Data range end column (exclusive).")],
    anchor_row: Annotated[int, typer.Option("--anchor-row", "-r", help="Anchor row (0-indexed).")] = 0,
    anchor_col: Annotated[int, typer.Option("--anchor-col", "-c", help="Anchor column (0-indexed).")] = 5,
    title: Annotated[
        Optional[str],
        typer.Option("--title", "-t", help="Chart title."),
    ] = None,
    legend: Annotated[
        str,
        typer.Option("--legend", "-l", help="Legend position (BOTTOM_LEGEND, NO_LEGEND, etc.)."),
    ] = "BOTTOM_LEGEND",
) -> None:
    """Add a chart to a sheet."""
    service = SheetsService()
    service.add_chart(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        chart_type=chart_type,
        data_range_start_row=data_start_row,
        data_range_end_row=data_end_row,
        data_range_start_col=data_start_col,
        data_range_end_col=data_end_col,
        anchor_row=anchor_row,
        anchor_col=anchor_col,
        title=title,
        legend_position=legend,
    )


@app.command("delete-chart")
def delete_chart(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    chart_id: Annotated[int, typer.Argument(help="Chart ID to delete.")],
) -> None:
    """Delete a chart from a spreadsheet."""
    service = SheetsService()
    service.delete_chart(
        spreadsheet_id=spreadsheet_id,
        chart_id=chart_id,
    )


@app.command("add-banding")
def add_banding(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    sheet_id: Annotated[int, typer.Argument(help="Sheet ID (numeric).")],
    start_row: Annotated[int, typer.Argument(help="Start row (0-indexed).")],
    end_row: Annotated[int, typer.Argument(help="End row (exclusive).")],
    start_col: Annotated[int, typer.Argument(help="Start column (0-indexed).")],
    end_col: Annotated[int, typer.Argument(help="End column (exclusive).")],
    header_color: Annotated[
        Optional[str],
        typer.Option("--header-color", help="Header row color (hex, e.g., #4285F4)."),
    ] = None,
    first_color: Annotated[
        Optional[str],
        typer.Option("--first-color", help="First alternating color (hex)."),
    ] = None,
    second_color: Annotated[
        Optional[str],
        typer.Option("--second-color", help="Second alternating color (hex)."),
    ] = None,
) -> None:
    """Add alternating row colors (banding) to a range."""
    service = SheetsService()
    service.add_banding(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row=start_row,
        end_row=end_row,
        start_col=start_col,
        end_col=end_col,
        header_color=header_color,
        first_color=first_color,
        second_color=second_color,
    )


@app.command("delete-banding")
def delete_banding(
    spreadsheet_id: Annotated[str, typer.Argument(help="Spreadsheet ID.")],
    banded_range_id: Annotated[int, typer.Argument(help="Banded range ID to delete.")],
) -> None:
    """Delete a banded range (alternating colors) from a spreadsheet."""
    service = SheetsService()
    service.delete_banding(
        spreadsheet_id=spreadsheet_id,
        banded_range_id=banded_range_id,
    )

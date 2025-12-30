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

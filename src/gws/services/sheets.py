"""Google Sheets service operations."""

from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode


class SheetsService(BaseService):
    """Google Sheets operations."""

    SERVICE_NAME = "sheets"
    VERSION = "v4"

    def metadata(self, spreadsheet_id: str) -> dict[str, Any]:
        """Get spreadsheet metadata."""
        try:
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )

            sheets = [
                {
                    "title": sheet["properties"]["title"],
                    "sheet_id": sheet["properties"]["sheetId"],
                    "index": sheet["properties"]["index"],
                    "row_count": sheet["properties"]["gridProperties"]["rowCount"],
                    "column_count": sheet["properties"]["gridProperties"]["columnCount"],
                }
                for sheet in spreadsheet.get("sheets", [])
            ]

            output_success(
                operation="sheets.metadata",
                spreadsheet_id=spreadsheet_id,
                title=spreadsheet.get("properties", {}).get("title", ""),
                sheets=sheets,
                sheet_count=len(sheets),
            )
            return spreadsheet
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.metadata",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def read(
        self,
        spreadsheet_id: str,
        range_notation: str | None = None,
    ) -> dict[str, Any]:
        """Read values from a spreadsheet."""
        try:
            if range_notation:
                result = (
                    self.service.spreadsheets()
                    .values()
                    .get(spreadsheetId=spreadsheet_id, range=range_notation)
                    .execute()
                )
            else:
                # Get all data from first sheet
                spreadsheet = (
                    self.service.spreadsheets()
                    .get(spreadsheetId=spreadsheet_id)
                    .execute()
                )
                first_sheet = spreadsheet["sheets"][0]["properties"]["title"]
                result = (
                    self.service.spreadsheets()
                    .values()
                    .get(spreadsheetId=spreadsheet_id, range=first_sheet)
                    .execute()
                )

            values = result.get("values", [])
            output_success(
                operation="sheets.read",
                spreadsheet_id=spreadsheet_id,
                range=result.get("range", range_notation),
                row_count=len(values),
                values=values,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.read",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create(
        self,
        title: str,
        sheet_titles: list[str] | None = None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new spreadsheet."""
        try:
            body: dict[str, Any] = {"properties": {"title": title}}

            if sheet_titles:
                body["sheets"] = [
                    {"properties": {"title": sheet_title}}
                    for sheet_title in sheet_titles
                ]

            spreadsheet = (
                self.service.spreadsheets().create(body=body).execute()
            )
            spreadsheet_id = spreadsheet["spreadsheetId"]

            # Move to folder if specified
            if folder_id:
                file = self.drive_service.files().get(
                    fileId=spreadsheet_id, fields="parents"
                ).execute()
                previous_parents = ",".join(file.get("parents", []))

                self.drive_service.files().update(
                    fileId=spreadsheet_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields="id, parents",
                ).execute()

            output_success(
                operation="sheets.create",
                spreadsheet_id=spreadsheet_id,
                title=title,
                web_view_link=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
            )
            return spreadsheet
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.create",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def write(
        self,
        spreadsheet_id: str,
        range_notation: str,
        values: list[list[Any]],
        input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Write values to a spreadsheet."""
        try:
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_notation,
                    valueInputOption=input_option,
                    body=body,
                )
                .execute()
            )

            output_success(
                operation="sheets.write",
                spreadsheet_id=spreadsheet_id,
                range=result.get("updatedRange"),
                updated_rows=result.get("updatedRows", 0),
                updated_columns=result.get("updatedColumns", 0),
                updated_cells=result.get("updatedCells", 0),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.write",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def append(
        self,
        spreadsheet_id: str,
        range_notation: str,
        values: list[list[Any]],
        input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Append values to a spreadsheet."""
        try:
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_notation,
                    valueInputOption=input_option,
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
                .execute()
            )

            updates = result.get("updates", {})
            output_success(
                operation="sheets.append",
                spreadsheet_id=spreadsheet_id,
                range=updates.get("updatedRange"),
                updated_rows=updates.get("updatedRows", 0),
                updated_cells=updates.get("updatedCells", 0),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.append",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def clear(
        self,
        spreadsheet_id: str,
        range_notation: str,
    ) -> dict[str, Any]:
        """Clear values from a range."""
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .clear(spreadsheetId=spreadsheet_id, range=range_notation, body={})
                .execute()
            )

            output_success(
                operation="sheets.clear",
                spreadsheet_id=spreadsheet_id,
                cleared_range=result.get("clearedRange"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.clear",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_sheet(
        self,
        spreadsheet_id: str,
        title: str,
    ) -> dict[str, Any]:
        """Add a new sheet to the spreadsheet."""
        try:
            requests = [
                {
                    "addSheet": {
                        "properties": {
                            "title": title,
                        }
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            reply = result.get("replies", [{}])[0]
            sheet_id = reply.get("addSheet", {}).get("properties", {}).get("sheetId")

            output_success(
                operation="sheets.add_sheet",
                spreadsheet_id=spreadsheet_id,
                sheet_title=title,
                sheet_id=sheet_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.add_sheet",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_sheet(
        self,
        spreadsheet_id: str,
        sheet_id: int,
    ) -> dict[str, Any]:
        """Delete a sheet from the spreadsheet."""
        try:
            requests = [{"deleteSheet": {"sheetId": sheet_id}}]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.delete_sheet",
                spreadsheet_id=spreadsheet_id,
                deleted_sheet_id=sheet_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.delete_sheet",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def rename_sheet(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        new_title: str,
    ) -> dict[str, Any]:
        """Rename a sheet."""
        try:
            requests = [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "title": new_title,
                        },
                        "fields": "title",
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.rename_sheet",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                new_title=new_title,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.rename_sheet",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def format_cells(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        bold: bool | None = None,
        italic: bool | None = None,
        font_size: int | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> dict[str, Any]:
        """Apply formatting to a cell range."""
        try:
            cell_format: dict[str, Any] = {}
            fields = []

            if bold is not None or italic is not None or font_size is not None:
                text_format: dict[str, Any] = {}
                if bold is not None:
                    text_format["bold"] = bold
                    fields.append("userEnteredFormat.textFormat.bold")
                if italic is not None:
                    text_format["italic"] = italic
                    fields.append("userEnteredFormat.textFormat.italic")
                if font_size is not None:
                    text_format["fontSize"] = font_size
                    fields.append("userEnteredFormat.textFormat.fontSize")
                cell_format["textFormat"] = text_format

            if background_color is not None:
                from gws.utils.colors import parse_hex_color
                rgb = parse_hex_color(background_color)
                cell_format["backgroundColor"] = rgb
                fields.append("userEnteredFormat.backgroundColor")

            if foreground_color is not None:
                from gws.utils.colors import parse_hex_color
                rgb = parse_hex_color(foreground_color)
                if "textFormat" not in cell_format:
                    cell_format["textFormat"] = {}
                cell_format["textFormat"]["foregroundColor"] = rgb
                fields.append("userEnteredFormat.textFormat.foregroundColor")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.format",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        },
                        "cell": {"userEnteredFormat": cell_format},
                        "fields": ",".join(fields),
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.format",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.format",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def batch_get(
        self,
        spreadsheet_id: str,
        ranges: list[str],
    ) -> dict[str, Any]:
        """Read multiple ranges at once."""
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
                .execute()
            )

            value_ranges = result.get("valueRanges", [])
            output_data = [
                {
                    "range": vr.get("range"),
                    "values": vr.get("values", []),
                }
                for vr in value_ranges
            ]

            output_success(
                operation="sheets.batch_get",
                spreadsheet_id=spreadsheet_id,
                ranges_requested=len(ranges),
                ranges_returned=len(value_ranges),
                data=output_data,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.batch_get",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def format_cells_extended(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        strikethrough: bool | None = None,
        font_family: str | None = None,
        font_size: int | None = None,
        foreground_color: str | None = None,
        background_color: str | None = None,
        horizontal_alignment: str | None = None,
        vertical_alignment: str | None = None,
        text_wrap: str | None = None,
        number_format: str | None = None,
    ) -> dict[str, Any]:
        """Apply extended formatting to a cell range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            bold: Bold text.
            italic: Italic text.
            underline: Underline text.
            strikethrough: Strikethrough text.
            font_family: Font family name.
            font_size: Font size in points.
            foreground_color: Text color (hex).
            background_color: Cell background color (hex).
            horizontal_alignment: Alignment (LEFT, CENTER, RIGHT).
            vertical_alignment: Vertical alignment (TOP, MIDDLE, BOTTOM).
            text_wrap: Wrap strategy (OVERFLOW_CELL, CLIP, WRAP).
            number_format: Number format pattern (e.g., "#,##0.00", "0%").
        """
        try:
            from gws.utils.colors import parse_hex_color

            cell_format: dict[str, Any] = {}
            fields = []

            # Text formatting
            text_format: dict[str, Any] = {}
            if bold is not None:
                text_format["bold"] = bold
                fields.append("userEnteredFormat.textFormat.bold")
            if italic is not None:
                text_format["italic"] = italic
                fields.append("userEnteredFormat.textFormat.italic")
            if underline is not None:
                text_format["underline"] = underline
                fields.append("userEnteredFormat.textFormat.underline")
            if strikethrough is not None:
                text_format["strikethrough"] = strikethrough
                fields.append("userEnteredFormat.textFormat.strikethrough")
            if font_family is not None:
                text_format["fontFamily"] = font_family
                fields.append("userEnteredFormat.textFormat.fontFamily")
            if font_size is not None:
                text_format["fontSize"] = font_size
                fields.append("userEnteredFormat.textFormat.fontSize")
            if foreground_color is not None:
                rgb = parse_hex_color(foreground_color)
                text_format["foregroundColor"] = rgb
                fields.append("userEnteredFormat.textFormat.foregroundColor")
            if text_format:
                cell_format["textFormat"] = text_format

            # Background color
            if background_color is not None:
                rgb = parse_hex_color(background_color)
                cell_format["backgroundColor"] = rgb
                fields.append("userEnteredFormat.backgroundColor")

            # Alignment
            if horizontal_alignment is not None:
                valid = {"LEFT", "CENTER", "RIGHT"}
                if horizontal_alignment.upper() not in valid:
                    output_error(
                        error_code="INVALID_ARGS",
                        operation="sheets.format_extended",
                        message=f"horizontal_alignment must be one of: {valid}",
                    )
                    raise SystemExit(ExitCode.INVALID_ARGS)
                cell_format["horizontalAlignment"] = horizontal_alignment.upper()
                fields.append("userEnteredFormat.horizontalAlignment")

            if vertical_alignment is not None:
                valid = {"TOP", "MIDDLE", "BOTTOM"}
                if vertical_alignment.upper() not in valid:
                    output_error(
                        error_code="INVALID_ARGS",
                        operation="sheets.format_extended",
                        message=f"vertical_alignment must be one of: {valid}",
                    )
                    raise SystemExit(ExitCode.INVALID_ARGS)
                cell_format["verticalAlignment"] = vertical_alignment.upper()
                fields.append("userEnteredFormat.verticalAlignment")

            # Text wrap
            if text_wrap is not None:
                valid = {"OVERFLOW_CELL", "CLIP", "WRAP"}
                if text_wrap.upper() not in valid:
                    output_error(
                        error_code="INVALID_ARGS",
                        operation="sheets.format_extended",
                        message=f"text_wrap must be one of: {valid}",
                    )
                    raise SystemExit(ExitCode.INVALID_ARGS)
                cell_format["wrapStrategy"] = text_wrap.upper()
                fields.append("userEnteredFormat.wrapStrategy")

            # Number format
            if number_format is not None:
                cell_format["numberFormat"] = {
                    "type": "NUMBER",
                    "pattern": number_format,
                }
                fields.append("userEnteredFormat.numberFormat")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.format_extended",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        },
                        "cell": {"userEnteredFormat": cell_format},
                        "fields": ",".join(fields),
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.format_extended",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.format_extended",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_borders(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        top: bool = False,
        bottom: bool = False,
        left: bool = False,
        right: bool = False,
        inner_horizontal: bool = False,
        inner_vertical: bool = False,
        color: str = "#000000",
        style: str = "SOLID",
        width: int = 1,
    ) -> dict[str, Any]:
        """Set borders on a cell range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            top: Apply top border.
            bottom: Apply bottom border.
            left: Apply left border.
            right: Apply right border.
            inner_horizontal: Apply horizontal borders between rows.
            inner_vertical: Apply vertical borders between columns.
            color: Border color (hex).
            style: Border style (SOLID, DOTTED, DASHED, SOLID_MEDIUM, SOLID_THICK, DOUBLE).
            width: Border width (1, 2, or 3).
        """
        try:
            from gws.utils.colors import parse_hex_color

            valid_styles = {
                "SOLID",
                "DOTTED",
                "DASHED",
                "SOLID_MEDIUM",
                "SOLID_THICK",
                "DOUBLE",
            }
            if style.upper() not in valid_styles:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.set_borders",
                    message=f"style must be one of: {valid_styles}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            rgb = parse_hex_color(color)
            border_style = {
                "style": style.upper(),
                "width": width,
                "color": rgb,
            }

            update_borders: dict[str, Any] = {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                },
            }

            if top:
                update_borders["top"] = border_style
            if bottom:
                update_borders["bottom"] = border_style
            if left:
                update_borders["left"] = border_style
            if right:
                update_borders["right"] = border_style
            if inner_horizontal:
                update_borders["innerHorizontal"] = border_style
            if inner_vertical:
                update_borders["innerVertical"] = border_style

            if not any([top, bottom, left, right, inner_horizontal, inner_vertical]):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.set_borders",
                    message="At least one border side required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{"updateBorders": update_borders}]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.set_borders",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.set_borders",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def merge_cells(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        merge_type: str = "MERGE_ALL",
    ) -> dict[str, Any]:
        """Merge cells in a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            merge_type: Type of merge (MERGE_ALL, MERGE_COLUMNS, MERGE_ROWS).
        """
        try:
            valid_types = {"MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"}
            if merge_type.upper() not in valid_types:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.merge_cells",
                    message=f"merge_type must be one of: {valid_types}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        },
                        "mergeType": merge_type.upper(),
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.merge_cells",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
                merge_type=merge_type.upper(),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.merge_cells",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def unmerge_cells(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
    ) -> dict[str, Any]:
        """Unmerge cells in a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
        """
        try:
            requests = [
                {
                    "unmergeCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        },
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.unmerge_cells",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.unmerge_cells",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_column_width(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_column: int,
        end_column: int,
        width: int,
    ) -> dict[str, Any]:
        """Set column width.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_column: Start column index (0-based).
            end_column: End column index (exclusive).
            width: Width in pixels.
        """
        try:
            requests = [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_column,
                            "endIndex": end_column,
                        },
                        "properties": {"pixelSize": width},
                        "fields": "pixelSize",
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.set_column_width",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                columns=f"{start_column}-{end_column}",
                width=width,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.set_column_width",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_row_height(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        height: int,
    ) -> dict[str, Any]:
        """Set row height.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            height: Height in pixels.
        """
        try:
            requests = [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_row,
                            "endIndex": end_row,
                        },
                        "properties": {"pixelSize": height},
                        "fields": "pixelSize",
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.set_row_height",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                rows=f"{start_row}-{end_row}",
                height=height,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.set_row_height",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def auto_resize_columns(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_column: int,
        end_column: int,
    ) -> dict[str, Any]:
        """Auto-resize columns to fit content.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_column: Start column index (0-based).
            end_column: End column index (exclusive).
        """
        try:
            requests = [
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_column,
                            "endIndex": end_column,
                        },
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.auto_resize_columns",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                columns=f"{start_column}-{end_column}",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.auto_resize_columns",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def freeze_rows(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        num_rows: int,
    ) -> dict[str, Any]:
        """Freeze rows at the top of the sheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            num_rows: Number of rows to freeze (0 to unfreeze).
        """
        try:
            requests = [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"frozenRowCount": num_rows},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.freeze_rows",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                frozen_rows=num_rows,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.freeze_rows",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def freeze_columns(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        num_columns: int,
    ) -> dict[str, Any]:
        """Freeze columns at the left of the sheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            num_columns: Number of columns to freeze (0 to unfreeze).
        """
        try:
            requests = [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"frozenColumnCount": num_columns},
                        },
                        "fields": "gridProperties.frozenColumnCount",
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.freeze_columns",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                frozen_columns=num_columns,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.freeze_columns",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_conditional_format(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        condition_type: str,
        condition_values: list[str],
        background_color: str | None = None,
        foreground_color: str | None = None,
        bold: bool | None = None,
    ) -> dict[str, Any]:
        """Add a conditional formatting rule.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            condition_type: Condition type (NUMBER_GREATER, NUMBER_LESS, NUMBER_EQ,
                TEXT_CONTAINS, TEXT_STARTS_WITH, BLANK, NOT_BLANK, etc.).
            condition_values: List of values for the condition.
            background_color: Cell background color when condition is met (hex).
            foreground_color: Text color when condition is met (hex).
            bold: Bold text when condition is met.
        """
        try:
            from gws.utils.colors import parse_hex_color

            valid_types = {
                "NUMBER_GREATER",
                "NUMBER_GREATER_THAN_EQ",
                "NUMBER_LESS",
                "NUMBER_LESS_THAN_EQ",
                "NUMBER_EQ",
                "NUMBER_NOT_EQ",
                "NUMBER_BETWEEN",
                "NUMBER_NOT_BETWEEN",
                "TEXT_CONTAINS",
                "TEXT_NOT_CONTAINS",
                "TEXT_STARTS_WITH",
                "TEXT_ENDS_WITH",
                "TEXT_EQ",
                "BLANK",
                "NOT_BLANK",
                "CUSTOM_FORMULA",
            }
            if condition_type.upper() not in valid_types:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.add_conditional_format",
                    message=f"condition_type must be one of: {valid_types}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Build format
            cell_format: dict[str, Any] = {}
            if background_color is not None:
                rgb = parse_hex_color(background_color)
                cell_format["backgroundColor"] = rgb
            if foreground_color is not None or bold is not None:
                text_format: dict[str, Any] = {}
                if foreground_color is not None:
                    rgb = parse_hex_color(foreground_color)
                    text_format["foregroundColor"] = rgb
                if bold is not None:
                    text_format["bold"] = bold
                cell_format["textFormat"] = text_format

            if not cell_format:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.add_conditional_format",
                    message="At least one format option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Build condition values
            condition_value_objs = [
                {"userEnteredValue": v} for v in condition_values
            ]

            requests = [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": sheet_id,
                                    "startRowIndex": start_row,
                                    "endRowIndex": end_row,
                                    "startColumnIndex": start_col,
                                    "endColumnIndex": end_col,
                                }
                            ],
                            "booleanRule": {
                                "condition": {
                                    "type": condition_type.upper(),
                                    "values": condition_value_objs,
                                },
                                "format": cell_format,
                            },
                        },
                        "index": 0,
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.add_conditional_format",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                condition_type=condition_type.upper(),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.add_conditional_format",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_color_scale(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        min_color: str,
        max_color: str,
        mid_color: str | None = None,
    ) -> dict[str, Any]:
        """Add a color scale conditional formatting rule.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            min_color: Color for minimum values (hex).
            max_color: Color for maximum values (hex).
            mid_color: Color for midpoint values (hex, optional).
        """
        try:
            from gws.utils.colors import parse_hex_color

            gradient_rule: dict[str, Any] = {
                "minpoint": {
                    "type": "MIN",
                    "color": parse_hex_color(min_color),
                },
                "maxpoint": {
                    "type": "MAX",
                    "color": parse_hex_color(max_color),
                },
            }

            if mid_color is not None:
                gradient_rule["midpoint"] = {
                    "type": "PERCENTILE",
                    "value": "50",
                    "color": parse_hex_color(mid_color),
                }

            requests = [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [
                                {
                                    "sheetId": sheet_id,
                                    "startRowIndex": start_row,
                                    "endRowIndex": end_row,
                                    "startColumnIndex": start_col,
                                    "endColumnIndex": end_col,
                                }
                            ],
                            "gradientRule": gradient_rule,
                        },
                        "index": 0,
                    }
                }
            ]

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.add_color_scale",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                min_color=min_color,
                max_color=max_color,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.add_color_scale",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def clear_conditional_formats(
        self,
        spreadsheet_id: str,
        sheet_id: int,
    ) -> dict[str, Any]:
        """Clear all conditional formatting rules from a sheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
        """
        try:
            # First, get the spreadsheet to find all conditional format rules
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )

            # Find the sheet
            sheet = None
            for s in spreadsheet.get("sheets", []):
                if s["properties"]["sheetId"] == sheet_id:
                    sheet = s
                    break

            if sheet is None:
                output_error(
                    error_code="NOT_FOUND",
                    operation="sheets.clear_conditional_formats",
                    message=f"Sheet with ID {sheet_id} not found",
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            conditional_formats = sheet.get("conditionalFormats", [])
            if not conditional_formats:
                output_success(
                    operation="sheets.clear_conditional_formats",
                    spreadsheet_id=spreadsheet_id,
                    sheet_id=sheet_id,
                    rules_cleared=0,
                )
                return {"cleared": 0}

            # Delete rules from highest index to lowest
            requests = []
            for i in range(len(conditional_formats) - 1, -1, -1):
                requests.append(
                    {
                        "deleteConditionalFormatRule": {
                            "sheetId": sheet_id,
                            "index": i,
                        }
                    }
                )

            result = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="sheets.clear_conditional_formats",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                rules_cleared=len(conditional_formats),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.clear_conditional_formats",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

"""Google Sheets service operations."""

from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
import json
from gws.output import output_success, output_error, output_external_content
from gws.exceptions import ExitCode
from gws.utils.colors import parse_hex_color


class SheetsService(BaseService):
    """Google Sheets operations."""

    SERVICE_NAME = "sheets"
    VERSION = "v4"

    def _unescape_text(self, text: str) -> str:
        """Remove unnecessary escape sequences from text.

        This handles cases where shell environments escape special characters
        like exclamation marks (\\! -> !).
        """
        return text.replace("\\!", "!")

    def metadata(self, spreadsheet_id: str) -> dict[str, Any]:
        """Get spreadsheet metadata."""
        try:
            spreadsheet = self.execute(
                self.service.spreadsheets()
                .get(
                    spreadsheetId=spreadsheet_id,
                    fields="spreadsheetId,properties,sheets(properties)",
                )
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
        value_render_option: str = "FORMATTED_VALUE",
    ) -> dict[str, Any]:
        """Read values from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            range_notation: A1 notation range (e.g., 'Sheet1!A1:C10').
            value_render_option: How values should be rendered:
                - FORMATTED_VALUE (default): Values as displayed in the UI
                - UNFORMATTED_VALUE: Raw values without formatting
                - FORMULA: The formulas in cells (not computed values)
        """
        try:
            # Unescape shell-escaped characters in range
            if range_notation:
                range_notation = self._unescape_text(range_notation)
            if range_notation:
                result = self.execute(
                    self.service.spreadsheets()
                    .values()
                    .get(
                        spreadsheetId=spreadsheet_id,
                        range=range_notation,
                        valueRenderOption=value_render_option,
                    )
                )
            else:
                # Get all data from first sheet
                spreadsheet = self.execute(
                    self.service.spreadsheets()
                    .get(
                        spreadsheetId=spreadsheet_id,
                        fields="sheets(properties(title))",
                    )
                )
                first_sheet = spreadsheet["sheets"][0]["properties"]["title"]
                result = self.execute(
                    self.service.spreadsheets()
                    .values()
                    .get(
                        spreadsheetId=spreadsheet_id,
                        range=first_sheet,
                        valueRenderOption=value_render_option,
                    )
                )

            values = result.get("values", [])
            # Wrap cell values as JSON string for security scanning
            output_external_content(
                operation="sheets.read",
                source_type="spreadsheet",
                source_id=spreadsheet_id,
                content_fields={
                    "values": json.dumps(values),
                },
                spreadsheet_id=spreadsheet_id,
                range=result.get("range", range_notation),
                row_count=len(values),
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

            spreadsheet = self.execute(
                self.service.spreadsheets().create(body=body)
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
            # Unescape shell-escaped characters in range
            range_notation = self._unescape_text(range_notation)
            body = {"values": values}
            result = self.execute(
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_notation,
                    valueInputOption=input_option,
                    body=body,
                )
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
            # Unescape shell-escaped characters in range
            range_notation = self._unescape_text(range_notation)
            body = {"values": values}
            result = self.execute(
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_notation,
                    valueInputOption=input_option,
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
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
            # Unescape shell-escaped characters in range
            range_notation = self._unescape_text(range_notation)
            result = self.execute(
                self.service.spreadsheets()
                .values()
                .clear(spreadsheetId=spreadsheet_id, range=range_notation, body={})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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
                rgb = parse_hex_color(background_color)
                cell_format["backgroundColor"] = rgb
                fields.append("userEnteredFormat.backgroundColor")

            if foreground_color is not None:
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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
            # Unescape shell-escaped characters in all ranges
            ranges = [self._unescape_text(r) for r in ranges]
            result = self.execute(
                self.service.spreadsheets()
                .values()
                .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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
            spreadsheet = self.execute(
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
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

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
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

    def insert_rows(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_index: int,
        count: int,
        inherit_from_before: bool = True,
    ) -> dict[str, Any]:
        """Insert rows at a specific index.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_index: Row index to insert at (0-based).
            count: Number of rows to insert.
            inherit_from_before: If True, new rows inherit formatting from row above.
        """
        try:
            requests = [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_index,
                            "endIndex": start_index + count,
                        },
                        "inheritFromBefore": inherit_from_before,
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.insert_rows",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                start_index=start_index,
                count=count,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.insert_rows",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_columns(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_index: int,
        count: int,
        inherit_from_before: bool = True,
    ) -> dict[str, Any]:
        """Insert columns at a specific index.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_index: Column index to insert at (0-based).
            count: Number of columns to insert.
            inherit_from_before: If True, new columns inherit formatting from column to the left.
        """
        try:
            requests = [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_index,
                            "endIndex": start_index + count,
                        },
                        "inheritFromBefore": inherit_from_before,
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.insert_columns",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                start_index=start_index,
                count=count,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.insert_columns",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_rows(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_index: int,
        end_index: int,
    ) -> dict[str, Any]:
        """Delete rows in a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_index: Start row index (0-based).
            end_index: End row index (exclusive).
        """
        try:
            requests = [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_index,
                            "endIndex": end_index,
                        },
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.delete_rows",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                start_index=start_index,
                end_index=end_index,
                deleted_count=end_index - start_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.delete_rows",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_columns(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_index: int,
        end_index: int,
    ) -> dict[str, Any]:
        """Delete columns in a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_index: Start column index (0-based).
            end_index: End column index (exclusive).
        """
        try:
            requests = [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_index,
                            "endIndex": end_index,
                        },
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.delete_columns",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                start_index=start_index,
                end_index=end_index,
                deleted_count=end_index - start_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.delete_columns",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def sort_range(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        sort_column: int,
        ascending: bool = True,
    ) -> dict[str, Any]:
        """Sort a range by a column.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            sort_column: Column index to sort by (0-based).
            ascending: Sort ascending if True, descending if False.
        """
        try:
            requests = [
                {
                    "sortRange": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        },
                        "sortSpecs": [
                            {
                                "dimensionIndex": sort_column,
                                "sortOrder": "ASCENDING" if ascending else "DESCENDING",
                            }
                        ],
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.sort_range",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
                sort_column=sort_column,
                ascending=ascending,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.sort_range",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def find_replace(
        self,
        spreadsheet_id: str,
        find: str,
        replace: str,
        sheet_id: int | None = None,
        all_sheets: bool = False,
        match_case: bool = False,
        match_entire_cell: bool = False,
        use_regex: bool = False,
    ) -> dict[str, Any]:
        """Find and replace text in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            find: Text to find.
            replace: Replacement text.
            sheet_id: Sheet ID to search in (optional, omit for all_sheets).
            all_sheets: If True, search all sheets.
            match_case: Case-sensitive search.
            match_entire_cell: Match entire cell content only.
            use_regex: Treat find as a regular expression.
        """
        try:
            find_replace_request: dict[str, Any] = {
                "find": find,
                "replacement": replace,
                "matchCase": match_case,
                "matchEntireCell": match_entire_cell,
                "searchByRegex": use_regex,
            }

            if all_sheets:
                find_replace_request["allSheets"] = True
            elif sheet_id is not None:
                find_replace_request["sheetId"] = sheet_id
            else:
                find_replace_request["allSheets"] = True

            requests = [{"findReplace": find_replace_request}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            # Extract replacement count from response
            replies = result.get("replies", [{}])
            find_replace_response = replies[0].get("findReplace", {})
            occurrences_changed = find_replace_response.get("occurrencesChanged", 0)
            values_changed = find_replace_response.get("valuesChanged", 0)
            sheets_changed = find_replace_response.get("sheetsChanged", 0)

            output_success(
                operation="sheets.find_replace",
                spreadsheet_id=spreadsheet_id,
                find=find,
                replace=replace,
                occurrences_changed=occurrences_changed,
                values_changed=values_changed,
                sheets_changed=sheets_changed,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.find_replace",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def duplicate_sheet(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        new_name: str | None = None,
        insert_index: int | None = None,
    ) -> dict[str, Any]:
        """Duplicate a sheet within the spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID to duplicate.
            new_name: Name for the new sheet (optional).
            insert_index: Position to insert the new sheet (optional).
        """
        try:
            duplicate_request: dict[str, Any] = {
                "sourceSheetId": sheet_id,
            }

            if new_name is not None:
                duplicate_request["newSheetName"] = new_name
            if insert_index is not None:
                duplicate_request["insertSheetIndex"] = insert_index

            requests = [{"duplicateSheet": duplicate_request}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            # Extract new sheet info from response
            replies = result.get("replies", [{}])
            duplicate_response = replies[0].get("duplicateSheet", {}).get("properties", {})
            new_sheet_id = duplicate_response.get("sheetId")
            new_sheet_title = duplicate_response.get("title")

            output_success(
                operation="sheets.duplicate_sheet",
                spreadsheet_id=spreadsheet_id,
                source_sheet_id=sheet_id,
                new_sheet_id=new_sheet_id,
                new_sheet_title=new_sheet_title,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.duplicate_sheet",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_data_validation(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        validation_type: str,
        values: list[str] | None = None,
        formula: str | None = None,
        strict: bool = True,
        show_dropdown: bool = True,
    ) -> dict[str, Any]:
        """Set data validation on a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            validation_type: Type of validation (ONE_OF_LIST, NUMBER_GREATER,
                NUMBER_LESS, NUMBER_BETWEEN, TEXT_CONTAINS, CUSTOM_FORMULA, etc.).
            values: List of values for ONE_OF_LIST or condition values.
            formula: Custom formula for CUSTOM_FORMULA type.
            strict: If True, reject invalid input; if False, show warning.
            show_dropdown: Show dropdown for list validation.
        """
        try:
            valid_types = {
                "ONE_OF_LIST",
                "NUMBER_GREATER",
                "NUMBER_LESS",
                "NUMBER_EQUAL",
                "NUMBER_NOT_EQUAL",
                "NUMBER_GREATER_THAN_EQ",
                "NUMBER_LESS_THAN_EQ",
                "NUMBER_BETWEEN",
                "NUMBER_NOT_BETWEEN",
                "TEXT_CONTAINS",
                "TEXT_NOT_CONTAINS",
                "TEXT_STARTS_WITH",
                "TEXT_ENDS_WITH",
                "TEXT_EQ",
                "TEXT_IS_EMAIL",
                "TEXT_IS_URL",
                "DATE_EQ",
                "DATE_BEFORE",
                "DATE_AFTER",
                "DATE_ON_OR_BEFORE",
                "DATE_ON_OR_AFTER",
                "DATE_BETWEEN",
                "DATE_NOT_BETWEEN",
                "DATE_IS_VALID",
                "CUSTOM_FORMULA",
                "BOOLEAN",
            }
            if validation_type.upper() not in valid_types:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.set_data_validation",
                    message=f"validation_type must be one of: {sorted(valid_types)}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Build condition based on type
            condition: dict[str, Any] = {"type": validation_type.upper()}

            if validation_type.upper() == "ONE_OF_LIST" and values:
                condition["values"] = [{"userEnteredValue": v} for v in values]
            elif validation_type.upper() == "CUSTOM_FORMULA" and formula:
                condition["values"] = [{"userEnteredValue": formula}]
            elif values:
                condition["values"] = [{"userEnteredValue": v} for v in values]

            validation_rule: dict[str, Any] = {
                "condition": condition,
                "strict": strict,
            }

            if validation_type.upper() == "ONE_OF_LIST":
                validation_rule["showCustomUi"] = show_dropdown

            requests = [
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        },
                        "rule": validation_rule,
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.set_data_validation",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
                validation_type=validation_type.upper(),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.set_data_validation",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def clear_data_validation(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
    ) -> dict[str, Any]:
        """Clear data validation from a range.

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
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        },
                        # Omitting 'rule' clears validation
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.clear_data_validation",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.clear_data_validation",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_chart(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        chart_type: str,
        data_range_start_row: int,
        data_range_end_row: int,
        data_range_start_col: int,
        data_range_end_col: int,
        anchor_row: int,
        anchor_col: int,
        title: str | None = None,
        legend_position: str = "BOTTOM_LEGEND",
    ) -> dict[str, Any]:
        """Add a chart to a sheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            chart_type: Type of chart (LINE, COLUMN, BAR, PIE, SCATTER, AREA).
            data_range_start_row: Start row of data range (0-based).
            data_range_end_row: End row of data range (exclusive).
            data_range_start_col: Start column of data range (0-based).
            data_range_end_col: End column of data range (exclusive).
            anchor_row: Row to anchor chart (0-based).
            anchor_col: Column to anchor chart (0-based).
            title: Chart title (optional).
            legend_position: Legend position (BOTTOM_LEGEND, LEFT_LEGEND,
                RIGHT_LEGEND, TOP_LEGEND, NO_LEGEND).
        """
        try:
            valid_types = {"LINE", "COLUMN", "BAR", "PIE", "SCATTER", "AREA"}
            if chart_type.upper() not in valid_types:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="sheets.add_chart",
                    message=f"chart_type must be one of: {valid_types}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Build data range
            data_range = {
                "sheetId": sheet_id,
                "startRowIndex": data_range_start_row,
                "endRowIndex": data_range_end_row,
                "startColumnIndex": data_range_start_col,
                "endColumnIndex": data_range_end_col,
            }

            # Build chart spec based on type
            chart_spec: dict[str, Any] = {
                "title": title or "",
                "basicChart": {
                    "chartType": chart_type.upper(),
                    "legendPosition": legend_position.upper(),
                    "domains": [{"domain": {"sourceRange": {"sources": [data_range]}}}],
                    "series": [{"series": {"sourceRange": {"sources": [data_range]}}}],
                },
            }

            requests = [
                {
                    "addChart": {
                        "chart": {
                            "spec": chart_spec,
                            "position": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": sheet_id,
                                        "rowIndex": anchor_row,
                                        "columnIndex": anchor_col,
                                    },
                                    "widthPixels": 600,
                                    "heightPixels": 400,
                                }
                            },
                        }
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            # Extract chart ID from response
            replies = result.get("replies", [{}])
            chart_id = replies[0].get("addChart", {}).get("chart", {}).get("chartId")

            output_success(
                operation="sheets.add_chart",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                chart_id=chart_id,
                chart_type=chart_type.upper(),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.add_chart",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_chart(
        self,
        spreadsheet_id: str,
        chart_id: int,
    ) -> dict[str, Any]:
        """Delete a chart from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            chart_id: The chart ID to delete.
        """
        try:
            requests = [{"deleteEmbeddedObject": {"objectId": chart_id}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.delete_chart",
                spreadsheet_id=spreadsheet_id,
                chart_id=chart_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.delete_chart",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_banding(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        header_color: str | None = None,
        first_color: str | None = None,
        second_color: str | None = None,
    ) -> dict[str, Any]:
        """Add alternating row colors (banding) to a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            start_col: Start column index (0-based).
            end_col: End column index (exclusive).
            header_color: Header row color (hex, e.g., '#4285F4').
            first_color: First alternating color (hex, e.g., '#FFFFFF').
            second_color: Second alternating color (hex, e.g., '#F3F3F3').
        """
        try:
            row_properties: dict[str, Any] = {}

            if header_color:
                row_properties["headerColor"] = parse_hex_color(header_color)
            if first_color:
                row_properties["firstBandColor"] = parse_hex_color(first_color)
            if second_color:
                row_properties["secondBandColor"] = parse_hex_color(second_color)

            # Use defaults if no colors provided
            if not row_properties:
                row_properties = {
                    "headerColor": {"red": 0.26, "green": 0.52, "blue": 0.96},
                    "firstBandColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "secondBandColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
                }

            requests = [
                {
                    "addBanding": {
                        "bandedRange": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": start_row,
                                "endRowIndex": end_row,
                                "startColumnIndex": start_col,
                                "endColumnIndex": end_col,
                            },
                            "rowProperties": row_properties,
                        }
                    }
                }
            ]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            # Extract banded range ID from response
            replies = result.get("replies", [{}])
            banded_range_id = (
                replies[0].get("addBanding", {}).get("bandedRange", {}).get("bandedRangeId")
            )

            output_success(
                operation="sheets.add_banding",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
                banded_range_id=banded_range_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.add_banding",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_banding(
        self,
        spreadsheet_id: str,
        banded_range_id: int,
    ) -> dict[str, Any]:
        """Delete a banded range (alternating colors) from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            banded_range_id: The banded range ID to delete.
        """
        try:
            requests = [{"deleteBanding": {"bandedRangeId": banded_range_id}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.delete_banding",
                spreadsheet_id=spreadsheet_id,
                banded_range_id=banded_range_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.delete_banding",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # FILTER OPERATIONS
    # =========================================================================

    def set_basic_filter(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
    ) -> dict[str, Any]:
        """Set a basic filter on a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID.
            start_row: Starting row index (0-indexed).
            end_row: Ending row index (exclusive).
            start_col: Starting column index (0-indexed).
            end_col: Ending column index (exclusive).
        """
        try:
            requests = [{
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        }
                    }
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.set_basic_filter",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.set_basic_filter",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def clear_basic_filter(
        self,
        spreadsheet_id: str,
        sheet_id: int,
    ) -> dict[str, Any]:
        """Clear the basic filter from a sheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID.
        """
        try:
            requests = [{"clearBasicFilter": {"sheetId": sheet_id}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.clear_basic_filter",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.clear_basic_filter",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_filter_view(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        title: str,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
    ) -> dict[str, Any]:
        """Create a named filter view.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID.
            title: Name for the filter view.
            start_row: Starting row index (0-indexed).
            end_row: Ending row index (exclusive).
            start_col: Starting column index (0-indexed).
            end_col: Ending column index (exclusive).
        """
        try:
            requests = [{
                "addFilterView": {
                    "filter": {
                        "title": title,
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        }
                    }
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            filter_view_id = (
                result.get("replies", [{}])[0]
                .get("addFilterView", {})
                .get("filter", {})
                .get("filterViewId")
            )

            output_success(
                operation="sheets.create_filter_view",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                title=title,
                filter_view_id=filter_view_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.create_filter_view",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_filter_views(
        self,
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """List all filter views in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
        """
        try:
            spreadsheet = self.execute(
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
            )

            filter_views = []
            for sheet in spreadsheet.get("sheets", []):
                sheet_title = sheet["properties"]["title"]
                sheet_id = sheet["properties"]["sheetId"]
                for fv in sheet.get("filterViews", []):
                    filter_views.append({
                        "filter_view_id": fv.get("filterViewId"),
                        "title": fv.get("title"),
                        "sheet_id": sheet_id,
                        "sheet_title": sheet_title,
                        "range": fv.get("range"),
                    })

            output_success(
                operation="sheets.list_filter_views",
                spreadsheet_id=spreadsheet_id,
                count=len(filter_views),
                filter_views=filter_views,
            )
            return {"filter_views": filter_views}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.list_filter_views",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_filter_view(
        self,
        spreadsheet_id: str,
        filter_view_id: int,
    ) -> dict[str, Any]:
        """Delete a filter view.

        Args:
            spreadsheet_id: The spreadsheet ID.
            filter_view_id: The filter view ID to delete.
        """
        try:
            requests = [{"deleteFilterView": {"filterId": filter_view_id}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.delete_filter_view",
                spreadsheet_id=spreadsheet_id,
                filter_view_id=filter_view_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.delete_filter_view",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # PIVOT TABLE OPERATIONS
    # =========================================================================

    def create_pivot_table(
        self,
        spreadsheet_id: str,
        source_sheet_id: int,
        source_start_row: int,
        source_end_row: int,
        source_start_col: int,
        source_end_col: int,
        target_sheet_id: int,
        target_row: int,
        target_col: int,
        row_source_columns: list[int],
        value_source_columns: list[int],
        value_functions: list[str] | None = None,
        column_source_columns: list[int] | None = None,
    ) -> dict[str, Any]:
        """Create a pivot table.

        Args:
            spreadsheet_id: The spreadsheet ID.
            source_sheet_id: Sheet ID containing source data.
            source_start_row: Source data start row (0-indexed).
            source_end_row: Source data end row (exclusive).
            source_start_col: Source data start column (0-indexed).
            source_end_col: Source data end column (exclusive).
            target_sheet_id: Sheet ID for pivot table output.
            target_row: Target row for pivot table (0-indexed).
            target_col: Target column for pivot table (0-indexed).
            row_source_columns: List of column indices to use as row groups.
            value_source_columns: List of column indices to aggregate.
            value_functions: Aggregation functions (SUM, AVERAGE, COUNT, MAX, MIN, etc.).
            column_source_columns: Optional column indices for column groups.
        """
        try:
            if value_functions is None:
                value_functions = ["SUM"] * len(value_source_columns)

            # Build row groups
            rows = []
            for col_idx in row_source_columns:
                rows.append({
                    "sourceColumnOffset": col_idx,
                    "showTotals": True,
                    "sortOrder": "ASCENDING",
                })

            # Build values
            values = []
            for i, col_idx in enumerate(value_source_columns):
                func = value_functions[i] if i < len(value_functions) else "SUM"
                values.append({
                    "sourceColumnOffset": col_idx,
                    "summarizeFunction": func.upper(),
                })

            # Build columns (optional)
            columns = []
            if column_source_columns:
                for col_idx in column_source_columns:
                    columns.append({
                        "sourceColumnOffset": col_idx,
                        "showTotals": True,
                        "sortOrder": "ASCENDING",
                    })

            pivot_table: dict[str, Any] = {
                "source": {
                    "sheetId": source_sheet_id,
                    "startRowIndex": source_start_row,
                    "endRowIndex": source_end_row,
                    "startColumnIndex": source_start_col,
                    "endColumnIndex": source_end_col,
                },
                "rows": rows,
                "values": values,
            }
            if columns:
                pivot_table["columns"] = columns

            requests = [{
                "updateCells": {
                    "rows": [{
                        "values": [{
                            "pivotTable": pivot_table
                        }]
                    }],
                    "start": {
                        "sheetId": target_sheet_id,
                        "rowIndex": target_row,
                        "columnIndex": target_col,
                    },
                    "fields": "pivotTable",
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.create_pivot_table",
                spreadsheet_id=spreadsheet_id,
                source_sheet_id=source_sheet_id,
                target_sheet_id=target_sheet_id,
                target_location=f"R{target_row}C{target_col}",
                row_groups=len(row_source_columns),
                values=len(value_source_columns),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.create_pivot_table",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_pivot_tables(
        self,
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """List all pivot tables in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
        """
        try:
            spreadsheet = self.execute(
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id, includeGridData=False)
            )

            pivot_tables = []
            for sheet in spreadsheet.get("sheets", []):
                sheet_title = sheet["properties"]["title"]
                sheet_id = sheet["properties"]["sheetId"]
                for pt in sheet.get("data", [{}])[0].get("rowData", []) if sheet.get("data") else []:
                    for cell in pt.get("values", []):
                        if "pivotTable" in cell:
                            pivot_tables.append({
                                "sheet_id": sheet_id,
                                "sheet_title": sheet_title,
                                "source": cell["pivotTable"].get("source"),
                            })

            # Alternative: check the sheets structure for pivot tables
            for sheet in spreadsheet.get("sheets", []):
                sheet_title = sheet["properties"]["title"]
                sheet_id = sheet["properties"]["sheetId"]
                for pivot in sheet.get("pivotTables", []):
                    pivot_tables.append({
                        "sheet_id": sheet_id,
                        "sheet_title": sheet_title,
                        "source": pivot.get("source"),
                        "rows": len(pivot.get("rows", [])),
                        "columns": len(pivot.get("columns", [])),
                        "values": len(pivot.get("values", [])),
                    })

            output_success(
                operation="sheets.list_pivot_tables",
                spreadsheet_id=spreadsheet_id,
                count=len(pivot_tables),
                pivot_tables=pivot_tables,
            )
            return {"pivot_tables": pivot_tables}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.list_pivot_tables",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # PROTECTED RANGES
    # =========================================================================

    def protect_range(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        description: str | None = None,
        warning_only: bool = False,
        editors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Protect a range from editing.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID.
            start_row: Start row index (0-indexed).
            end_row: End row index (exclusive).
            start_col: Start column index (0-indexed).
            end_col: End column index (exclusive).
            description: Description of the protected range.
            warning_only: If True, shows warning but allows editing.
            editors: List of email addresses that can edit.
        """
        try:
            protected_range: dict[str, Any] = {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                },
                "warningOnly": warning_only,
            }

            if description:
                protected_range["description"] = description

            if editors:
                protected_range["editors"] = {"users": editors}

            requests = [{"addProtectedRange": {"protectedRange": protected_range}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            protected_range_id = (
                result.get("replies", [{}])[0]
                .get("addProtectedRange", {})
                .get("protectedRange", {})
                .get("protectedRangeId")
            )

            output_success(
                operation="sheets.protect_range",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                protected_range_id=protected_range_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
                warning_only=warning_only,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.protect_range",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def protect_sheet(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        description: str | None = None,
        warning_only: bool = False,
        editors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Protect an entire sheet from editing.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID.
            description: Description of the protection.
            warning_only: If True, shows warning but allows editing.
            editors: List of email addresses that can edit.
        """
        try:
            protected_range: dict[str, Any] = {
                "range": {"sheetId": sheet_id},
                "warningOnly": warning_only,
            }

            if description:
                protected_range["description"] = description

            if editors:
                protected_range["editors"] = {"users": editors}

            requests = [{"addProtectedRange": {"protectedRange": protected_range}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            protected_range_id = (
                result.get("replies", [{}])[0]
                .get("addProtectedRange", {})
                .get("protectedRange", {})
                .get("protectedRangeId")
            )

            output_success(
                operation="sheets.protect_sheet",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                protected_range_id=protected_range_id,
                warning_only=warning_only,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.protect_sheet",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_protected_ranges(
        self,
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """List all protected ranges in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
        """
        try:
            spreadsheet = self.execute(
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
            )

            protected_ranges = []
            for sheet in spreadsheet.get("sheets", []):
                sheet_title = sheet["properties"]["title"]
                sheet_id = sheet["properties"]["sheetId"]
                for pr in sheet.get("protectedRanges", []):
                    protected_ranges.append({
                        "protected_range_id": pr.get("protectedRangeId"),
                        "description": pr.get("description"),
                        "sheet_id": sheet_id,
                        "sheet_title": sheet_title,
                        "range": pr.get("range"),
                        "warning_only": pr.get("warningOnly", False),
                        "editors": pr.get("editors", {}).get("users", []),
                    })

            output_success(
                operation="sheets.list_protected_ranges",
                spreadsheet_id=spreadsheet_id,
                count=len(protected_ranges),
                protected_ranges=protected_ranges,
            )
            return {"protected_ranges": protected_ranges}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.list_protected_ranges",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def unprotect_range(
        self,
        spreadsheet_id: str,
        protected_range_id: int,
    ) -> dict[str, Any]:
        """Remove protection from a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            protected_range_id: The protected range ID to remove.
        """
        try:
            requests = [{"deleteProtectedRange": {"protectedRangeId": protected_range_id}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.unprotect_range",
                spreadsheet_id=spreadsheet_id,
                protected_range_id=protected_range_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.unprotect_range",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # NAMED RANGES
    # =========================================================================

    def create_named_range(
        self,
        spreadsheet_id: str,
        name: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
    ) -> dict[str, Any]:
        """Create a named range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            name: Name for the range (must be valid identifier).
            sheet_id: The sheet ID.
            start_row: Start row index (0-indexed).
            end_row: End row index (exclusive).
            start_col: Start column index (0-indexed).
            end_col: End column index (exclusive).
        """
        try:
            requests = [{
                "addNamedRange": {
                    "namedRange": {
                        "name": name,
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
                        }
                    }
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            named_range_id = (
                result.get("replies", [{}])[0]
                .get("addNamedRange", {})
                .get("namedRange", {})
                .get("namedRangeId")
            )

            output_success(
                operation="sheets.create_named_range",
                spreadsheet_id=spreadsheet_id,
                name=name,
                named_range_id=named_range_id,
                range=f"R{start_row}C{start_col}:R{end_row}C{end_col}",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.create_named_range",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_named_ranges(
        self,
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """List all named ranges in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID.
        """
        try:
            spreadsheet = self.execute(
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
            )

            named_ranges = []
            for nr in spreadsheet.get("namedRanges", []):
                range_info = nr.get("range", {})
                named_ranges.append({
                    "named_range_id": nr.get("namedRangeId"),
                    "name": nr.get("name"),
                    "sheet_id": range_info.get("sheetId"),
                    "start_row": range_info.get("startRowIndex"),
                    "end_row": range_info.get("endRowIndex"),
                    "start_col": range_info.get("startColumnIndex"),
                    "end_col": range_info.get("endColumnIndex"),
                })

            output_success(
                operation="sheets.list_named_ranges",
                spreadsheet_id=spreadsheet_id,
                count=len(named_ranges),
                named_ranges=named_ranges,
            )
            return {"named_ranges": named_ranges}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.list_named_ranges",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_named_range(
        self,
        spreadsheet_id: str,
        named_range_id: str,
    ) -> dict[str, Any]:
        """Delete a named range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            named_range_id: The named range ID to delete.
        """
        try:
            requests = [{"deleteNamedRange": {"namedRangeId": named_range_id}}]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.delete_named_range",
                spreadsheet_id=spreadsheet_id,
                named_range_id=named_range_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.delete_named_range",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # CHART UPDATES
    # =========================================================================

    def update_chart(
        self,
        spreadsheet_id: str,
        chart_id: int,
        title: str | None = None,
        chart_type: str | None = None,
        legend_position: str | None = None,
    ) -> dict[str, Any]:
        """Update a chart's specification.

        Args:
            spreadsheet_id: The spreadsheet ID.
            chart_id: The chart ID to update.
            title: New chart title.
            chart_type: Chart type (LINE, BAR, COLUMN, AREA, SCATTER, PIE, etc.).
            legend_position: Legend position (TOP, BOTTOM, LEFT, RIGHT, NONE).
        """
        try:
            # Build the chart spec update
            spec: dict[str, Any] = {}
            fields = []

            if title is not None:
                spec["title"] = title
                fields.append("title")

            if chart_type is not None:
                # Most chart types use basicChart
                spec["basicChart"] = {"chartType": chart_type}
                fields.append("basicChart.chartType")

            if legend_position is not None:
                if "basicChart" not in spec:
                    spec["basicChart"] = {}
                spec["basicChart"]["legendPosition"] = legend_position
                fields.append("basicChart.legendPosition")

            if not fields:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="sheets.update_chart",
                    message="At least one update field required (title, chart_type, legend_position)",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateChartSpec": {
                    "chartId": chart_id,
                    "spec": spec,
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.update_chart",
                spreadsheet_id=spreadsheet_id,
                chart_id=chart_id,
                updated_fields=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.update_chart",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # ROW/COLUMN MOVEMENT
    # =========================================================================

    def move_rows(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        source_start: int,
        source_end: int,
        destination_index: int,
    ) -> dict[str, Any]:
        """Move rows to a new position.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            source_start: Starting row index (0-based).
            source_end: Ending row index (exclusive).
            destination_index: Where to move the rows (0-based).
        """
        try:
            requests = [{
                "moveDimension": {
                    "source": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": source_start,
                        "endIndex": source_end,
                    },
                    "destinationIndex": destination_index,
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.move_rows",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                source_range=f"{source_start}:{source_end}",
                destination_index=destination_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.move_rows",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def move_columns(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        source_start: int,
        source_end: int,
        destination_index: int,
    ) -> dict[str, Any]:
        """Move columns to a new position.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            source_start: Starting column index (0-based).
            source_end: Ending column index (exclusive).
            destination_index: Where to move the columns (0-based).
        """
        try:
            requests = [{
                "moveDimension": {
                    "source": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": source_start,
                        "endIndex": source_end,
                    },
                    "destinationIndex": destination_index,
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.move_columns",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                source_range=f"{source_start}:{source_end}",
                destination_index=destination_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.move_columns",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # COPY/PASTE & AUTO-FILL
    # =========================================================================

    def copy_paste(
        self,
        spreadsheet_id: str,
        source_sheet_id: int,
        source_start_row: int,
        source_end_row: int,
        source_start_col: int,
        source_end_col: int,
        dest_sheet_id: int,
        dest_start_row: int,
        dest_start_col: int,
        paste_type: str = "PASTE_NORMAL",
    ) -> dict[str, Any]:
        """Copy a range and paste it to another location.

        Args:
            spreadsheet_id: The spreadsheet ID.
            source_sheet_id: Source sheet ID (numeric).
            source_start_row: Source start row (0-based).
            source_end_row: Source end row (exclusive).
            source_start_col: Source start column (0-based).
            source_end_col: Source end column (exclusive).
            dest_sheet_id: Destination sheet ID (numeric).
            dest_start_row: Destination start row (0-based).
            dest_start_col: Destination start column (0-based).
            paste_type: What to paste (PASTE_NORMAL, PASTE_VALUES, PASTE_FORMAT,
                       PASTE_NO_BORDERS, PASTE_FORMULA, PASTE_DATA_VALIDATION,
                       PASTE_CONDITIONAL_FORMATTING).
        """
        try:
            requests = [{
                "copyPaste": {
                    "source": {
                        "sheetId": source_sheet_id,
                        "startRowIndex": source_start_row,
                        "endRowIndex": source_end_row,
                        "startColumnIndex": source_start_col,
                        "endColumnIndex": source_end_col,
                    },
                    "destination": {
                        "sheetId": dest_sheet_id,
                        "startRowIndex": dest_start_row,
                        "endRowIndex": dest_start_row + (source_end_row - source_start_row),
                        "startColumnIndex": dest_start_col,
                        "endColumnIndex": dest_start_col + (source_end_col - source_start_col),
                    },
                    "pasteType": paste_type,
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.copy_paste",
                spreadsheet_id=spreadsheet_id,
                paste_type=paste_type,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.copy_paste",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def auto_fill(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        source_start_row: int,
        source_end_row: int,
        source_start_col: int,
        source_end_col: int,
        fill_start_row: int,
        fill_end_row: int,
        fill_start_col: int,
        fill_end_col: int,
        use_alternate_series: bool = False,
    ) -> dict[str, Any]:
        """Auto-fill a range based on source data.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            source_start_row: Source range start row (0-based).
            source_end_row: Source range end row (exclusive).
            source_start_col: Source range start column (0-based).
            source_end_col: Source range end column (exclusive).
            fill_start_row: Fill range start row (0-based).
            fill_end_row: Fill range end row (exclusive).
            fill_start_col: Fill range start column (0-based).
            fill_end_col: Fill range end column (exclusive).
            use_alternate_series: Use alternate series for auto-fill.
        """
        try:
            requests = [{
                "autoFill": {
                    "useAlternateSeries": use_alternate_series,
                    "sourceAndDestination": {
                        "source": {
                            "sheetId": sheet_id,
                            "startRowIndex": source_start_row,
                            "endRowIndex": source_end_row,
                            "startColumnIndex": source_start_col,
                            "endColumnIndex": source_end_col,
                        },
                        "dimension": "ROWS" if fill_end_row > source_end_row else "COLUMNS",
                        "fillLength": max(
                            fill_end_row - source_end_row,
                            fill_end_col - source_end_col
                        ),
                    },
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.auto_fill",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.auto_fill",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # DATA CLEANUP
    # =========================================================================

    def trim_whitespace(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int = 0,
        end_row: int | None = None,
        start_col: int = 0,
        end_col: int | None = None,
    ) -> dict[str, Any]:
        """Trim leading and trailing whitespace from cells.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive), None for entire sheet.
            start_col: Start column index (0-based).
            end_col: End column index (exclusive), None for entire sheet.
        """
        try:
            range_spec: dict[str, Any] = {"sheetId": sheet_id}
            if start_row > 0:
                range_spec["startRowIndex"] = start_row
            if end_row is not None:
                range_spec["endRowIndex"] = end_row
            if start_col > 0:
                range_spec["startColumnIndex"] = start_col
            if end_col is not None:
                range_spec["endColumnIndex"] = end_col

            requests = [{
                "trimWhitespace": {
                    "range": range_spec,
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.trim_whitespace",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.trim_whitespace",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def text_to_columns(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        source_column: int,
        delimiter_type: str = "COMMA",
        custom_delimiter: str | None = None,
    ) -> dict[str, Any]:
        """Split text in a column into multiple columns.

        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_id: The sheet ID (numeric).
            start_row: Start row index (0-based).
            end_row: End row index (exclusive).
            source_column: Column index to split (0-based).
            delimiter_type: Type of delimiter (COMMA, SEMICOLON, PERIOD, SPACE, CUSTOM, AUTODETECT).
            custom_delimiter: Custom delimiter string (required if delimiter_type is CUSTOM).
        """
        try:
            request: dict[str, Any] = {
                "textToColumns": {
                    "source": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": source_column,
                        "endColumnIndex": source_column + 1,
                    },
                    "delimiterType": delimiter_type,
                }
            }

            if delimiter_type == "CUSTOM" and custom_delimiter:
                request["textToColumns"]["delimiter"] = custom_delimiter

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [request]})
            )

            output_success(
                operation="sheets.text_to_columns",
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                delimiter_type=delimiter_type,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.text_to_columns",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # BANDING & FILTER VIEW UPDATES
    # =========================================================================

    def update_banding(
        self,
        spreadsheet_id: str,
        banded_range_id: int,
        header_color: str | None = None,
        first_band_color: str | None = None,
        second_band_color: str | None = None,
        footer_color: str | None = None,
    ) -> dict[str, Any]:
        """Update banding colors on a range.

        Args:
            spreadsheet_id: The spreadsheet ID.
            banded_range_id: The banded range ID to update.
            header_color: Header row color (hex, e.g., '#4285F4').
            first_band_color: First alternating color (hex).
            second_band_color: Second alternating color (hex).
            footer_color: Footer row color (hex).
        """
        try:
            properties: dict[str, Any] = {"bandedRangeId": banded_range_id}
            fields = ["bandedRangeId"]

            if header_color:
                properties["rowProperties"] = properties.get("rowProperties", {})
                properties["rowProperties"]["headerColor"] = parse_hex_color(header_color)
                fields.append("rowProperties.headerColor")

            if first_band_color:
                properties["rowProperties"] = properties.get("rowProperties", {})
                properties["rowProperties"]["firstBandColor"] = parse_hex_color(first_band_color)
                fields.append("rowProperties.firstBandColor")

            if second_band_color:
                properties["rowProperties"] = properties.get("rowProperties", {})
                properties["rowProperties"]["secondBandColor"] = parse_hex_color(second_band_color)
                fields.append("rowProperties.secondBandColor")

            if footer_color:
                properties["rowProperties"] = properties.get("rowProperties", {})
                properties["rowProperties"]["footerColor"] = parse_hex_color(footer_color)
                fields.append("rowProperties.footerColor")

            if len(fields) == 1:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="sheets.update_banding",
                    message="At least one color parameter required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateBanding": {
                    "bandedRange": properties,
                    "fields": ",".join(fields),
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.update_banding",
                spreadsheet_id=spreadsheet_id,
                banded_range_id=banded_range_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.update_banding",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_filter_view(
        self,
        spreadsheet_id: str,
        filter_view_id: int,
        title: str | None = None,
        start_row: int | None = None,
        end_row: int | None = None,
        start_col: int | None = None,
        end_col: int | None = None,
    ) -> dict[str, Any]:
        """Update a filter view's properties.

        Args:
            spreadsheet_id: The spreadsheet ID.
            filter_view_id: The filter view ID to update.
            title: New title for the filter view.
            start_row: New start row index (0-based).
            end_row: New end row index (exclusive).
            start_col: New start column index (0-based).
            end_col: New end column index (exclusive).
        """
        try:
            filter_view: dict[str, Any] = {"filterViewId": filter_view_id}
            fields = []

            if title is not None:
                filter_view["title"] = title
                fields.append("title")

            if any(x is not None for x in [start_row, end_row, start_col, end_col]):
                filter_view["range"] = {}
                if start_row is not None:
                    filter_view["range"]["startRowIndex"] = start_row
                if end_row is not None:
                    filter_view["range"]["endRowIndex"] = end_row
                if start_col is not None:
                    filter_view["range"]["startColumnIndex"] = start_col
                if end_col is not None:
                    filter_view["range"]["endColumnIndex"] = end_col
                fields.append("range")

            if not fields:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="sheets.update_filter_view",
                    message="At least one update field required (title or range bounds)",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateFilterView": {
                    "filter": filter_view,
                    "fields": ",".join(fields),
                }
            }]

            result = self.execute(
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            )

            output_success(
                operation="sheets.update_filter_view",
                spreadsheet_id=spreadsheet_id,
                filter_view_id=filter_view_id,
                updated_fields=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="sheets.update_filter_view",
                message=f"Google Sheets API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

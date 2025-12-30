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

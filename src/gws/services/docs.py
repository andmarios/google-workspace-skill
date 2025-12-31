"""Google Docs service operations."""

from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_json, output_success, output_error
from gws.exceptions import ExitCode


class DocsService(BaseService):
    """Google Docs operations."""

    SERVICE_NAME = "docs"
    VERSION = "v1"

    def _extract_text(self, content: list[dict]) -> str:
        """Extract plain text from document content."""
        text_parts = []
        for element in content:
            if "paragraph" in element:
                for elem in element["paragraph"].get("elements", []):
                    if "textRun" in elem:
                        text_parts.append(elem["textRun"].get("content", ""))
            elif "table" in element:
                for row in element["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        cell_text = self._extract_text(cell.get("content", []))
                        text_parts.append(cell_text)
        return "".join(text_parts)

    def _extract_structure(self, content: list[dict]) -> list[dict]:
        """Extract heading structure from document content."""
        headings = []
        for element in content:
            if "paragraph" in element:
                para = element["paragraph"]
                style = para.get("paragraphStyle", {}).get("namedStyleType", "")
                if style.startswith("HEADING_"):
                    level = int(style.replace("HEADING_", ""))
                    text = ""
                    for elem in para.get("elements", []):
                        if "textRun" in elem:
                            text += elem["textRun"].get("content", "")
                    headings.append({
                        "level": level,
                        "text": text.strip(),
                        "style": style,
                    })
        return headings

    def read(self, document_id: str) -> dict[str, Any]:
        """Read document content as plain text."""
        try:
            doc = self.service.documents().get(documentId=document_id).execute()

            content = doc.get("body", {}).get("content", [])
            text = self._extract_text(content)

            output_success(
                operation="docs.read",
                document_id=document_id,
                title=doc.get("title", ""),
                content=text,
                revision_id=doc.get("revisionId"),
            )
            return doc
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.read",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def structure(self, document_id: str) -> dict[str, Any]:
        """Get document heading structure."""
        try:
            doc = self.service.documents().get(documentId=document_id).execute()

            content = doc.get("body", {}).get("content", [])
            headings = self._extract_structure(content)

            output_success(
                operation="docs.structure",
                document_id=document_id,
                title=doc.get("title", ""),
                headings=headings,
                heading_count=len(headings),
            )
            return {"headings": headings}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.structure",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create(
        self,
        title: str,
        content: str | None = None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new document."""
        try:
            # Create the document
            doc = self.service.documents().create(body={"title": title}).execute()
            document_id = doc["documentId"]

            # Add initial content if provided
            if content:
                requests = [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content,
                        }
                    }
                ]
                self.service.documents().batchUpdate(
                    documentId=document_id, body={"requests": requests}
                ).execute()

            # Move to folder if specified
            if folder_id:
                # Get current parents
                file = self.drive_service.files().get(
                    fileId=document_id, fields="parents"
                ).execute()
                previous_parents = ",".join(file.get("parents", []))

                self.drive_service.files().update(
                    fileId=document_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields="id, parents",
                ).execute()

            output_success(
                operation="docs.create",
                document_id=document_id,
                title=title,
                web_view_link=f"https://docs.google.com/document/d/{document_id}/edit",
            )
            return doc
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.create",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert(
        self,
        document_id: str,
        text: str,
        index: int = 1,
    ) -> dict[str, Any]:
        """Insert text at a specific index."""
        try:
            requests = [
                {
                    "insertText": {
                        "location": {"index": index},
                        "text": text,
                    }
                }
            ]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="docs.insert",
                document_id=document_id,
                index=index,
                text_length=len(text),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def append(self, document_id: str, text: str) -> dict[str, Any]:
        """Append text to the end of the document."""
        try:
            # Get document to find end index
            doc = self.service.documents().get(documentId=document_id).execute()
            content = doc.get("body", {}).get("content", [])

            # Find the end index (last element's endIndex - 1)
            end_index = 1
            if content:
                last_element = content[-1]
                end_index = last_element.get("endIndex", 1) - 1

            requests = [
                {
                    "insertText": {
                        "location": {"index": end_index},
                        "text": text,
                    }
                }
            ]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="docs.append",
                document_id=document_id,
                index=end_index,
                text_length=len(text),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.append",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def replace(
        self,
        document_id: str,
        find: str,
        replace_with: str,
        match_case: bool = False,
    ) -> dict[str, Any]:
        """Replace text throughout the document."""
        try:
            requests = [
                {
                    "replaceAllText": {
                        "containsText": {
                            "text": find,
                            "matchCase": match_case,
                        },
                        "replaceText": replace_with,
                    }
                }
            ]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            # Get replacement count from response
            replies = result.get("replies", [{}])
            occurrences = replies[0].get("replaceAllText", {}).get(
                "occurrencesChanged", 0
            )

            output_success(
                operation="docs.replace",
                document_id=document_id,
                find=find,
                replace_with=replace_with,
                occurrences_changed=occurrences,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.replace",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def format_text(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        font_size: int | None = None,
        foreground_color: str | None = None,
    ) -> dict[str, Any]:
        """Apply formatting to a text range."""
        try:
            text_style: dict[str, Any] = {}
            fields = []

            if bold is not None:
                text_style["bold"] = bold
                fields.append("bold")
            if italic is not None:
                text_style["italic"] = italic
                fields.append("italic")
            if underline is not None:
                text_style["underline"] = underline
                fields.append("underline")
            if font_size is not None:
                text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
                fields.append("fontSize")
            if foreground_color is not None:
                # Parse hex color
                from gws.utils.colors import parse_hex_color
                rgb = parse_hex_color(foreground_color)
                text_style["foregroundColor"] = {"color": {"rgbColor": rgb}}
                fields.append("foregroundColor")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.format",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [
                {
                    "updateTextStyle": {
                        "range": {
                            "startIndex": start_index,
                            "endIndex": end_index,
                        },
                        "textStyle": text_style,
                        "fields": ",".join(fields),
                    }
                }
            ]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="docs.format",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.format",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_content(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
    ) -> dict[str, Any]:
        """Delete content in a range."""
        try:
            requests = [
                {
                    "deleteContentRange": {
                        "range": {
                            "startIndex": start_index,
                            "endIndex": end_index,
                        }
                    }
                }
            ]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="docs.delete",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                deleted_length=end_index - start_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_page_break(
        self,
        document_id: str,
        index: int,
    ) -> dict[str, Any]:
        """Insert a page break at the specified index."""
        try:
            requests = [
                {
                    "insertPageBreak": {
                        "location": {"index": index},
                    }
                }
            ]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="docs.page_break",
                document_id=document_id,
                index=index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.page_break",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_image(
        self,
        document_id: str,
        image_url: str,
        index: int | None = None,
        width: float | None = None,
        height: float | None = None,
    ) -> dict[str, Any]:
        """Insert an image from a URL."""
        try:
            # If no index specified, append at end
            if index is None:
                doc = self.service.documents().get(documentId=document_id).execute()
                content = doc.get("body", {}).get("content", [])
                if content:
                    index = content[-1].get("endIndex", 1) - 1
                else:
                    index = 1

            insert_inline_image: dict[str, Any] = {
                "location": {"index": index},
                "uri": image_url,
            }

            # Add size if specified
            if width is not None or height is not None:
                object_size: dict[str, Any] = {}
                if width is not None:
                    object_size["width"] = {"magnitude": width, "unit": "PT"}
                if height is not None:
                    object_size["height"] = {"magnitude": height, "unit": "PT"}
                insert_inline_image["objectSize"] = object_size

            requests = [{"insertInlineImage": insert_inline_image}]

            result = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            output_success(
                operation="docs.insert_image",
                document_id=document_id,
                index=index,
                image_url=image_url,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_image",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # TABLE OPERATIONS
    # =========================================================================

    def _get_tables(self, document_id: str) -> list[dict]:
        """Get all tables from document with their start indices."""
        doc = self.service.documents().get(documentId=document_id).execute()
        content = doc.get("body", {}).get("content", [])
        tables = []
        for element in content:
            if "table" in element:
                tables.append({
                    "startIndex": element.get("startIndex"),
                    "endIndex": element.get("endIndex"),
                    "rows": len(element["table"].get("tableRows", [])),
                    "columns": len(
                        element["table"]
                        .get("tableRows", [{}])[0]
                        .get("tableCells", [])
                    ) if element["table"].get("tableRows") else 0,
                    "table": element["table"],
                })
        return tables

    def _get_end_index(self, document_id: str) -> int:
        """Get the end index of the document body."""
        doc = self.service.documents().get(documentId=document_id).execute()
        content = doc.get("body", {}).get("content", [])
        if content:
            return content[-1].get("endIndex", 1) - 1
        return 1

    def insert_table(
        self,
        document_id: str,
        rows: int,
        columns: int,
        index: int | None = None,
    ) -> dict[str, Any]:
        """Insert a table at the specified index."""
        try:
            if index is None:
                index = self._get_end_index(document_id)

            requests = [{
                "insertTable": {
                    "location": {"index": index},
                    "rows": rows,
                    "columns": columns,
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.insert_table",
                document_id=document_id,
                rows=rows,
                columns=columns,
                index=index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_table",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_table_row(
        self,
        document_id: str,
        table_index: int,
        row_index: int,
        insert_below: bool = True,
    ) -> dict[str, Any]:
        """Insert a row into a table."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.insert_table_row",
                    message=f"Table index {table_index} not found (document has {len(tables)} tables)",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "insertTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table["startIndex"]},
                        "rowIndex": row_index,
                        "columnIndex": 0,
                    },
                    "insertBelow": insert_below,
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.insert_table_row",
                document_id=document_id,
                table_index=table_index,
                row_index=row_index,
                insert_below=insert_below,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_table_row",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_table_column(
        self,
        document_id: str,
        table_index: int,
        column_index: int,
        insert_right: bool = True,
    ) -> dict[str, Any]:
        """Insert a column into a table."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.insert_table_column",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "insertTableColumn": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table["startIndex"]},
                        "rowIndex": 0,
                        "columnIndex": column_index,
                    },
                    "insertRight": insert_right,
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.insert_table_column",
                document_id=document_id,
                table_index=table_index,
                column_index=column_index,
                insert_right=insert_right,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_table_column",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_table_row(
        self,
        document_id: str,
        table_index: int,
        row_index: int,
    ) -> dict[str, Any]:
        """Delete a row from a table."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.delete_table_row",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "deleteTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table["startIndex"]},
                        "rowIndex": row_index,
                        "columnIndex": 0,
                    },
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.delete_table_row",
                document_id=document_id,
                table_index=table_index,
                row_index=row_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete_table_row",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_table_column(
        self,
        document_id: str,
        table_index: int,
        column_index: int,
    ) -> dict[str, Any]:
        """Delete a column from a table."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.delete_table_column",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "deleteTableColumn": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table["startIndex"]},
                        "rowIndex": 0,
                        "columnIndex": column_index,
                    },
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.delete_table_column",
                document_id=document_id,
                table_index=table_index,
                column_index=column_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete_table_column",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def merge_table_cells(
        self,
        document_id: str,
        table_index: int,
        start_row: int,
        start_column: int,
        end_row: int,
        end_column: int,
    ) -> dict[str, Any]:
        """Merge cells in a table."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.merge_table_cells",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "mergeTableCells": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": table["startIndex"]},
                            "rowIndex": start_row,
                            "columnIndex": start_column,
                        },
                        "rowSpan": end_row - start_row + 1,
                        "columnSpan": end_column - start_column + 1,
                    },
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.merge_table_cells",
                document_id=document_id,
                table_index=table_index,
                range=f"({start_row},{start_column})-({end_row},{end_column})",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.merge_table_cells",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def unmerge_table_cells(
        self,
        document_id: str,
        table_index: int,
        start_row: int,
        start_column: int,
        end_row: int,
        end_column: int,
    ) -> dict[str, Any]:
        """Unmerge previously merged cells in a table."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.unmerge_table_cells",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "unmergeTableCells": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": table["startIndex"]},
                            "rowIndex": start_row,
                            "columnIndex": start_column,
                        },
                        "rowSpan": end_row - start_row + 1,
                        "columnSpan": end_column - start_column + 1,
                    },
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.unmerge_table_cells",
                document_id=document_id,
                table_index=table_index,
                range=f"({start_row},{start_column})-({end_row},{end_column})",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.unmerge_table_cells",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def style_table_cell(
        self,
        document_id: str,
        table_index: int,
        start_row: int,
        start_column: int,
        end_row: int | None = None,
        end_column: int | None = None,
        background_color: str | None = None,
        border_color: str | None = None,
        border_width: float | None = None,
        padding_top: float | None = None,
        padding_bottom: float | None = None,
        padding_left: float | None = None,
        padding_right: float | None = None,
    ) -> dict[str, Any]:
        """Style table cells (background, borders, padding)."""
        try:
            from gws.utils.colors import parse_hex_color

            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.style_table_cell",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Default to single cell if end not specified
            if end_row is None:
                end_row = start_row
            if end_column is None:
                end_column = start_column

            table = tables[table_index]
            cell_style: dict[str, Any] = {}
            fields = []

            if background_color is not None:
                rgb = parse_hex_color(background_color)
                cell_style["backgroundColor"] = {"color": {"rgbColor": rgb}}
                fields.append("backgroundColor")

            if border_color is not None or border_width is not None:
                border_style: dict[str, Any] = {}
                if border_color is not None:
                    rgb = parse_hex_color(border_color)
                    border_style["color"] = {"color": {"rgbColor": rgb}}
                if border_width is not None:
                    border_style["width"] = {"magnitude": border_width, "unit": "PT"}
                    border_style["dashStyle"] = "SOLID"

                for side in ["borderTop", "borderBottom", "borderLeft", "borderRight"]:
                    cell_style[side] = border_style
                    fields.append(side)

            for pad_name, pad_val in [
                ("paddingTop", padding_top),
                ("paddingBottom", padding_bottom),
                ("paddingLeft", padding_left),
                ("paddingRight", padding_right),
            ]:
                if pad_val is not None:
                    cell_style[pad_name] = {"magnitude": pad_val, "unit": "PT"}
                    fields.append(pad_name)

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.style_table_cell",
                    message="At least one styling option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateTableCellStyle": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": table["startIndex"]},
                            "rowIndex": start_row,
                            "columnIndex": start_column,
                        },
                        "rowSpan": end_row - start_row + 1,
                        "columnSpan": end_column - start_column + 1,
                    },
                    "tableCellStyle": cell_style,
                    "fields": ",".join(fields),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.style_table_cell",
                document_id=document_id,
                table_index=table_index,
                range=f"({start_row},{start_column})-({end_row},{end_column})",
                styling=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.style_table_cell",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_column_width(
        self,
        document_id: str,
        table_index: int,
        column_index: int,
        width: float,
    ) -> dict[str, Any]:
        """Set the width of a table column."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.set_column_width",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "updateTableColumnProperties": {
                    "tableStartLocation": {"index": table["startIndex"]},
                    "columnIndices": [column_index],
                    "tableColumnProperties": {
                        "width": {"magnitude": width, "unit": "PT"},
                        "widthType": "FIXED_WIDTH",
                    },
                    "fields": "width,widthType",
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.set_column_width",
                document_id=document_id,
                table_index=table_index,
                column_index=column_index,
                width=width,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.set_column_width",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def pin_table_header(
        self,
        document_id: str,
        table_index: int,
        rows_to_pin: int = 1,
    ) -> dict[str, Any]:
        """Pin header rows in a table (they repeat on each page)."""
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.pin_table_header",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]
            requests = [{
                "pinTableHeaderRows": {
                    "tableStartLocation": {"index": table["startIndex"]},
                    "pinnedHeaderRowsCount": rows_to_pin,
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.pin_table_header",
                document_id=document_id,
                table_index=table_index,
                rows_pinned=rows_to_pin,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.pin_table_header",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_tables(self, document_id: str) -> dict[str, Any]:
        """List all tables in the document with their properties."""
        try:
            tables = self._get_tables(document_id)
            table_info = []
            for i, t in enumerate(tables):
                table_info.append({
                    "index": i,
                    "rows": t["rows"],
                    "columns": t["columns"],
                    "startIndex": t["startIndex"],
                    "endIndex": t["endIndex"],
                })

            output_success(
                operation="docs.list_tables",
                document_id=document_id,
                table_count=len(tables),
                tables=table_info,
            )
            return {"tables": table_info}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.list_tables",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # PARAGRAPH STYLE OPERATIONS
    # =========================================================================

    def format_paragraph(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        alignment: str | None = None,
        named_style: str | None = None,
        line_spacing: float | None = None,
        space_above: float | None = None,
        space_below: float | None = None,
        indent_first_line: float | None = None,
        indent_start: float | None = None,
        indent_end: float | None = None,
        keep_lines_together: bool | None = None,
        keep_with_next: bool | None = None,
        shading_color: str | None = None,
    ) -> dict[str, Any]:
        """Apply paragraph formatting to a range.

        Args:
            alignment: START, CENTER, END, or JUSTIFIED
            named_style: NORMAL_TEXT, TITLE, SUBTITLE, HEADING_1 through HEADING_6
            line_spacing: Line spacing as percentage (e.g., 100 for single, 200 for double)
            space_above/below: Space in points
            indent_*: Indentation in points
            shading_color: Background color for paragraph (hex)
        """
        try:
            from gws.utils.colors import parse_hex_color

            paragraph_style: dict[str, Any] = {}
            fields = []

            if alignment is not None:
                paragraph_style["alignment"] = alignment.upper()
                fields.append("alignment")

            if named_style is not None:
                paragraph_style["namedStyleType"] = named_style.upper()
                fields.append("namedStyleType")

            if line_spacing is not None:
                paragraph_style["lineSpacing"] = line_spacing
                fields.append("lineSpacing")

            if space_above is not None:
                paragraph_style["spaceAbove"] = {"magnitude": space_above, "unit": "PT"}
                fields.append("spaceAbove")

            if space_below is not None:
                paragraph_style["spaceBelow"] = {"magnitude": space_below, "unit": "PT"}
                fields.append("spaceBelow")

            if indent_first_line is not None:
                paragraph_style["indentFirstLine"] = {"magnitude": indent_first_line, "unit": "PT"}
                fields.append("indentFirstLine")

            if indent_start is not None:
                paragraph_style["indentStart"] = {"magnitude": indent_start, "unit": "PT"}
                fields.append("indentStart")

            if indent_end is not None:
                paragraph_style["indentEnd"] = {"magnitude": indent_end, "unit": "PT"}
                fields.append("indentEnd")

            if keep_lines_together is not None:
                paragraph_style["keepLinesTogether"] = keep_lines_together
                fields.append("keepLinesTogether")

            if keep_with_next is not None:
                paragraph_style["keepWithNext"] = keep_with_next
                fields.append("keepWithNext")

            if shading_color is not None:
                rgb = parse_hex_color(shading_color)
                paragraph_style["shading"] = {"backgroundColor": {"color": {"rgbColor": rgb}}}
                fields.append("shading")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.format_paragraph",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "paragraphStyle": paragraph_style,
                    "fields": ",".join(fields),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.format_paragraph",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.format_paragraph",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_paragraph_border(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        color: str = "#000000",
        width: float = 1.0,
        top: bool = False,
        bottom: bool = False,
        left: bool = False,
        right: bool = False,
        between: bool = False,
    ) -> dict[str, Any]:
        """Add borders to paragraphs."""
        try:
            from gws.utils.colors import parse_hex_color

            rgb = parse_hex_color(color)
            border_style = {
                "color": {"color": {"rgbColor": rgb}},
                "width": {"magnitude": width, "unit": "PT"},
                "dashStyle": "SOLID",
            }

            paragraph_style: dict[str, Any] = {}
            fields = []

            if top:
                paragraph_style["borderTop"] = border_style
                fields.append("borderTop")
            if bottom:
                paragraph_style["borderBottom"] = border_style
                fields.append("borderBottom")
            if left:
                paragraph_style["borderLeft"] = border_style
                fields.append("borderLeft")
            if right:
                paragraph_style["borderRight"] = border_style
                fields.append("borderRight")
            if between:
                paragraph_style["borderBetween"] = border_style
                fields.append("borderBetween")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.set_paragraph_border",
                    message="At least one border side must be specified",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "paragraphStyle": paragraph_style,
                    "fields": ",".join(fields),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.set_paragraph_border",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                borders=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.set_paragraph_border",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # EXTENDED TEXT STYLE OPERATIONS (Phase 3)
    # =========================================================================

    def format_text_extended(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        strikethrough: bool | None = None,
        small_caps: bool | None = None,
        font_family: str | None = None,
        font_weight: int | None = None,
        font_size: int | None = None,
        foreground_color: str | None = None,
        background_color: str | None = None,
        baseline_offset: str | None = None,
        link_url: str | None = None,
    ) -> dict[str, Any]:
        """Apply extended text formatting.

        Args:
            baseline_offset: NONE, SUPERSCRIPT, or SUBSCRIPT
            font_weight: 100-900 in increments of 100 (400=normal, 700=bold)
        """
        try:
            from gws.utils.colors import parse_hex_color

            text_style: dict[str, Any] = {}
            fields = []

            if bold is not None:
                text_style["bold"] = bold
                fields.append("bold")
            if italic is not None:
                text_style["italic"] = italic
                fields.append("italic")
            if underline is not None:
                text_style["underline"] = underline
                fields.append("underline")
            if strikethrough is not None:
                text_style["strikethrough"] = strikethrough
                fields.append("strikethrough")
            if small_caps is not None:
                text_style["smallCaps"] = small_caps
                fields.append("smallCaps")

            if font_family is not None or font_weight is not None:
                weighted_font: dict[str, Any] = {}
                if font_family is not None:
                    weighted_font["fontFamily"] = font_family
                if font_weight is not None:
                    weighted_font["weight"] = font_weight
                text_style["weightedFontFamily"] = weighted_font
                fields.append("weightedFontFamily")

            if font_size is not None:
                text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
                fields.append("fontSize")

            if foreground_color is not None:
                rgb = parse_hex_color(foreground_color)
                text_style["foregroundColor"] = {"color": {"rgbColor": rgb}}
                fields.append("foregroundColor")

            if background_color is not None:
                rgb = parse_hex_color(background_color)
                text_style["backgroundColor"] = {"color": {"rgbColor": rgb}}
                fields.append("backgroundColor")

            if baseline_offset is not None:
                text_style["baselineOffset"] = baseline_offset.upper()
                fields.append("baselineOffset")

            if link_url is not None:
                text_style["link"] = {"url": link_url}
                fields.append("link")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.format_text_extended",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateTextStyle": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "textStyle": text_style,
                    "fields": ",".join(fields),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.format_text_extended",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.format_text_extended",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_link(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        url: str,
    ) -> dict[str, Any]:
        """Add a hyperlink to existing text."""
        try:
            requests = [{
                "updateTextStyle": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "textStyle": {"link": {"url": url}},
                    "fields": "link",
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.insert_link",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                url=url,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_link",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # HEADER/FOOTER OPERATIONS (Phase 4)
    # =========================================================================

    def create_header(
        self,
        document_id: str,
        header_type: str = "DEFAULT",
    ) -> dict[str, Any]:
        """Create a document header.

        Args:
            header_type: DEFAULT or FIRST_PAGE_HEADER
        """
        try:
            requests = [{
                "createHeader": {
                    "type": header_type.upper(),
                    "sectionBreakLocation": {"index": 0},
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            header_id = result.get("replies", [{}])[0].get("createHeader", {}).get("headerId")

            output_success(
                operation="docs.create_header",
                document_id=document_id,
                header_id=header_id,
                header_type=header_type,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.create_header",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_footer(
        self,
        document_id: str,
        footer_type: str = "DEFAULT",
    ) -> dict[str, Any]:
        """Create a document footer.

        Args:
            footer_type: DEFAULT or FIRST_PAGE_FOOTER
        """
        try:
            requests = [{
                "createFooter": {
                    "type": footer_type.upper(),
                    "sectionBreakLocation": {"index": 0},
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            footer_id = result.get("replies", [{}])[0].get("createFooter", {}).get("footerId")

            output_success(
                operation="docs.create_footer",
                document_id=document_id,
                footer_id=footer_id,
                footer_type=footer_type,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.create_footer",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_header(self, document_id: str, header_id: str) -> dict[str, Any]:
        """Delete a document header."""
        try:
            requests = [{"deleteHeader": {"headerId": header_id}}]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.delete_header",
                document_id=document_id,
                header_id=header_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete_header",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_footer(self, document_id: str, footer_id: str) -> dict[str, Any]:
        """Delete a document footer."""
        try:
            requests = [{"deleteFooter": {"footerId": footer_id}}]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.delete_footer",
                document_id=document_id,
                footer_id=footer_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete_footer",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_headers_footers(self, document_id: str) -> dict[str, Any]:
        """Get all headers and footers in the document."""
        try:
            doc = self.service.documents().get(documentId=document_id).execute()
            headers = doc.get("headers", {})
            footers = doc.get("footers", {})

            header_info = []
            for hid, header in headers.items():
                content = self._extract_text(header.get("content", []))
                header_info.append({
                    "id": hid,
                    "content": content[:200] if content else "",
                })

            footer_info = []
            for fid, footer in footers.items():
                content = self._extract_text(footer.get("content", []))
                footer_info.append({
                    "id": fid,
                    "content": content[:200] if content else "",
                })

            output_success(
                operation="docs.get_headers_footers",
                document_id=document_id,
                headers=header_info,
                footers=footer_info,
            )
            return {"headers": header_info, "footers": footer_info}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.get_headers_footers",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_text_in_segment(
        self,
        document_id: str,
        segment_id: str,
        text: str,
        index: int = 0,
    ) -> dict[str, Any]:
        """Insert text into a header or footer segment."""
        try:
            requests = [{
                "insertText": {
                    "location": {
                        "segmentId": segment_id,
                        "index": index,
                    },
                    "text": text,
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.insert_text_in_segment",
                document_id=document_id,
                segment_id=segment_id,
                index=index,
                text_length=len(text),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_text_in_segment",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # LIST/BULLET OPERATIONS (Phase 5)
    # =========================================================================

    def create_bullets(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        preset: str = "BULLET_DISC_CIRCLE_SQUARE",
    ) -> dict[str, Any]:
        """Create a bulleted list.

        Presets: BULLET_DISC_CIRCLE_SQUARE, BULLET_DIAMONDX_ARROW3D_SQUARE,
                 BULLET_CHECKBOX, BULLET_ARROW_DIAMOND_DISC,
                 BULLET_STAR_CIRCLE_SQUARE, BULLET_ARROW3D_CIRCLE_SQUARE,
                 BULLET_LEFTTRIANGLE_DIAMOND_DISC
        """
        try:
            requests = [{
                "createParagraphBullets": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "bulletPreset": preset.upper(),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.create_bullets",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                preset=preset,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.create_bullets",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_numbered_list(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        preset: str = "NUMBERED_DECIMAL_NESTED",
    ) -> dict[str, Any]:
        """Create a numbered list.

        Presets: NUMBERED_DECIMAL_NESTED, NUMBERED_DECIMAL_ALPHA_ROMAN,
                 NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS, NUMBERED_DECIMAL_PARENTHESIS,
                 NUMBERED_UPPERALPHA_ALPHA_ROMAN, NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL,
                 NUMBERED_ZERODECIMAL_ALPHA_ROMAN
        """
        try:
            requests = [{
                "createParagraphBullets": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "bulletPreset": preset.upper(),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.create_numbered_list",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                preset=preset,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.create_numbered_list",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def remove_bullets(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
    ) -> dict[str, Any]:
        """Remove bullets/numbering from paragraphs."""
        try:
            requests = [{
                "deleteParagraphBullets": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.remove_bullets",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.remove_bullets",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # SECTION AND DOCUMENT STYLE OPERATIONS (Phase 6)
    # =========================================================================

    def insert_section_break(
        self,
        document_id: str,
        index: int,
        break_type: str = "NEXT_PAGE",
    ) -> dict[str, Any]:
        """Insert a section break.

        Args:
            break_type: NEXT_PAGE or CONTINUOUS
        """
        try:
            requests = [{
                "insertSectionBreak": {
                    "location": {"index": index},
                    "sectionType": break_type.upper(),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.insert_section_break",
                document_id=document_id,
                index=index,
                break_type=break_type,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_section_break",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_document_style(
        self,
        document_id: str,
        margin_top: float | None = None,
        margin_bottom: float | None = None,
        margin_left: float | None = None,
        margin_right: float | None = None,
        page_width: float | None = None,
        page_height: float | None = None,
        use_first_page_header_footer: bool | None = None,
    ) -> dict[str, Any]:
        """Update document-level style (margins, page size).

        All measurements in points (72 points = 1 inch).
        Default US Letter: 612 x 792 points.
        """
        try:
            doc_style: dict[str, Any] = {}
            fields = []

            if margin_top is not None:
                doc_style["marginTop"] = {"magnitude": margin_top, "unit": "PT"}
                fields.append("marginTop")
            if margin_bottom is not None:
                doc_style["marginBottom"] = {"magnitude": margin_bottom, "unit": "PT"}
                fields.append("marginBottom")
            if margin_left is not None:
                doc_style["marginLeft"] = {"magnitude": margin_left, "unit": "PT"}
                fields.append("marginLeft")
            if margin_right is not None:
                doc_style["marginRight"] = {"magnitude": margin_right, "unit": "PT"}
                fields.append("marginRight")

            if page_width is not None or page_height is not None:
                page_size: dict[str, Any] = {}
                if page_width is not None:
                    page_size["width"] = {"magnitude": page_width, "unit": "PT"}
                if page_height is not None:
                    page_size["height"] = {"magnitude": page_height, "unit": "PT"}
                doc_style["pageSize"] = page_size
                fields.append("pageSize")

            if use_first_page_header_footer is not None:
                doc_style["useFirstPageHeaderFooter"] = use_first_page_header_footer
                fields.append("useFirstPageHeaderFooter")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.update_document_style",
                    message="At least one style option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            requests = [{
                "updateDocumentStyle": {
                    "documentStyle": doc_style,
                    "fields": ",".join(fields),
                }
            }]

            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            output_success(
                operation="docs.update_document_style",
                document_id=document_id,
                updated_fields=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.update_document_style",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

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

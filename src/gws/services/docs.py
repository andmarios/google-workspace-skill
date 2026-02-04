"""Google Docs service operations."""

from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error, output_external_content
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

    def _get_tab_content(self, doc: dict, tab_id: str | None = None) -> list[dict]:
        """Get content from a specific tab or the default (first) tab.

        Args:
            doc: The document response from the API.
            tab_id: Optional tab ID. If None, returns content from the first tab
                   or falls back to the legacy body.content.

        Returns:
            List of content elements from the specified tab.

        Raises:
            ValueError: If tab_id is specified but not found.
        """
        tabs = doc.get("tabs", [])

        if tab_id:
            # Search for specific tab (including nested tabs)
            tab = self._find_tab_by_id(tabs, tab_id)
            if tab:
                return tab.get("documentTab", {}).get("body", {}).get("content", [])
            raise ValueError(f"Tab not found: {tab_id}")

        # Default: use first tab if available, otherwise legacy body
        if tabs:
            first_tab = tabs[0]
            return first_tab.get("documentTab", {}).get("body", {}).get("content", [])
        return doc.get("body", {}).get("content", [])

    def _find_tab_by_id(self, tabs: list[dict], tab_id: str) -> dict | None:
        """Recursively find a tab by ID (tabs can be nested)."""
        for tab in tabs:
            props = tab.get("tabProperties", {})
            if props.get("tabId") == tab_id:
                return tab
            # Check child tabs
            child_tabs = tab.get("childTabs", [])
            if child_tabs:
                found = self._find_tab_by_id(child_tabs, tab_id)
                if found:
                    return found
        return None

    def _extract_tabs_info(self, tabs: list[dict], parent_index: int | None = None) -> list[dict]:
        """Extract tab information from tabs array (recursive for child tabs)."""
        result = []
        for i, tab in enumerate(tabs):
            props = tab.get("tabProperties", {})
            doc_tab = tab.get("documentTab", {})

            # Get content length for info
            body_content = doc_tab.get("body", {}).get("content", [])
            content_length = len(body_content)

            tab_info = {
                "tab_id": props.get("tabId"),
                "title": props.get("title", ""),
                "index": props.get("index", i),
                "parent_index": parent_index,
                "content_elements": content_length,
            }
            result.append(tab_info)

            # Process child tabs
            child_tabs = tab.get("childTabs", [])
            if child_tabs:
                result.extend(self._extract_tabs_info(child_tabs, parent_index=i))

        return result

    def list_tabs(self, document_id: str) -> dict[str, Any]:
        """List all tabs in a document.

        Returns tab IDs, titles, and positions.
        """
        try:
            # Include tabs content to get full tab structure
            doc = self.execute(self.service.documents().get(
                documentId=document_id,
                includeTabsContent=True,
            ))

            tabs = doc.get("tabs", [])
            tabs_info = self._extract_tabs_info(tabs)

            output_success(
                operation="docs.list_tabs",
                document_id=document_id,
                title=doc.get("title", ""),
                tab_count=len(tabs_info),
                tabs=tabs_info,
            )
            return {"tabs": tabs_info}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.list_tabs",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_tab(
        self,
        document_id: str,
        title: str,
        index: int | None = None,
    ) -> dict[str, Any]:
        """Create a new tab in the document.

        Args:
            document_id: The document ID.
            title: Title for the new tab.
            index: Optional position (0-based). If None, appends to end.
        """
        try:
            tab_properties: dict[str, Any] = {"title": title}
            if index is not None:
                tab_properties["index"] = index

            requests = [{"addDocumentTab": {"tabProperties": tab_properties}}]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            # Extract the created tab ID from response
            replies = result.get("replies", [{}])
            created_tab = replies[0].get("addDocumentTab", {})
            new_tab_id = created_tab.get("tabProperties", {}).get("tabId")

            output_success(
                operation="docs.create_tab",
                document_id=document_id,
                tab_id=new_tab_id,
                title=title,
                index=index,
            )
            return {"tab_id": new_tab_id, "title": title}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.create_tab",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_tab(self, document_id: str, tab_id: str) -> dict[str, Any]:
        """Delete a tab from the document.

        Args:
            document_id: The document ID.
            tab_id: The tab ID to delete.

        Note: Cannot delete the last remaining tab.
        """
        try:
            requests = [{"deleteTab": {"tabId": tab_id}}]

            self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            output_success(
                operation="docs.delete_tab",
                document_id=document_id,
                tab_id=tab_id,
            )
            return {"deleted": True, "tab_id": tab_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete_tab",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def rename_tab(
        self,
        document_id: str,
        tab_id: str,
        title: str,
    ) -> dict[str, Any]:
        """Rename a tab.

        Args:
            document_id: The document ID.
            tab_id: The tab ID to rename.
            title: New title for the tab.
        """
        try:
            requests = [
                {
                    "updateDocumentTabProperties": {
                        "tabId": tab_id,
                        "tabProperties": {"title": title},
                        "fields": "title",
                    }
                }
            ]

            self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            output_success(
                operation="docs.rename_tab",
                document_id=document_id,
                tab_id=tab_id,
                new_title=title,
            )
            return {"tab_id": tab_id, "title": title}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.rename_tab",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def reorder_tab(
        self,
        document_id: str,
        tab_id: str,
        new_index: int,
    ) -> dict[str, Any]:
        """Move a tab to a new position.

        Args:
            document_id: The document ID.
            tab_id: The tab ID to move.
            new_index: New position (0-based).
        """
        try:
            requests = [
                {
                    "updateDocumentTabProperties": {
                        "tabId": tab_id,
                        "tabProperties": {"index": new_index},
                        "fields": "index",
                    }
                }
            ]

            self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            output_success(
                operation="docs.reorder_tab",
                document_id=document_id,
                tab_id=tab_id,
                new_index=new_index,
            )
            return {"tab_id": tab_id, "index": new_index}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.reorder_tab",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def read(self, document_id: str, tab_id: str | None = None) -> dict[str, Any]:
        """Read document content as plain text.

        Args:
            document_id: The document ID.
            tab_id: Optional tab ID to read from. If None, reads the first tab.
        """
        try:
            # Include tabs content when tab_id specified or to use new API structure
            doc = self.execute(self.service.documents().get(
                documentId=document_id,
                includeTabsContent=True,
            ))

            try:
                content = self._get_tab_content(doc, tab_id)
            except ValueError as e:
                output_error(
                    error_code="NOT_FOUND",
                    operation="docs.read",
                    message=str(e),
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            text = self._extract_text(content)

            output_external_content(
                operation="docs.read",
                source_type="document",
                source_id=document_id,
                content_fields={
                    "content": text,
                },
                document_id=document_id,
                title=doc.get("title", ""),
                tab_id=tab_id,
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

    def structure(self, document_id: str, tab_id: str | None = None) -> dict[str, Any]:
        """Get document heading structure.

        Args:
            document_id: The document ID.
            tab_id: Optional tab ID to get structure from. If None, uses the first tab.
        """
        try:
            doc = self.execute(self.service.documents().get(
                documentId=document_id,
                includeTabsContent=True,
            ))

            try:
                content = self._get_tab_content(doc, tab_id)
            except ValueError as e:
                output_error(
                    error_code="NOT_FOUND",
                    operation="docs.structure",
                    message=str(e),
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            headings = self._extract_structure(content)

            output_success(
                operation="docs.structure",
                document_id=document_id,
                title=doc.get("title", ""),
                tab_id=tab_id,
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
            doc = self.execute(self.service.documents().create(body={"title": title}))
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
                self.execute(self.service.documents().batchUpdate(
                    documentId=document_id, body={"requests": requests}
                ))

            # Move to folder if specified
            if folder_id:
                # Get current parents
                file = self.execute(self.drive_service.files().get(
                    fileId=document_id, fields="parents"
                ))
                previous_parents = ",".join(file.get("parents", []))

                self.execute(self.drive_service.files().update(
                    fileId=document_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields="id, parents",
                ))

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
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert text at a specific index.

        Args:
            document_id: The document ID.
            text: Text to insert.
            index: Character index to insert at (default: 1, start of document).
            tab_id: Optional tab ID to insert into.
        """
        try:
            location: dict[str, Any] = {"index": index}
            if tab_id:
                location["tabId"] = tab_id

            requests = [
                {
                    "insertText": {
                        "location": location,
                        "text": text,
                    }
                }
            ]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.insert",
                document_id=document_id,
                index=index,
                tab_id=tab_id,
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

    def append(
        self,
        document_id: str,
        text: str,
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Append text to the end of the document (or tab).

        Args:
            document_id: The document ID.
            text: Text to append.
            tab_id: Optional tab ID to append to.
        """
        try:
            # Get document to find end index
            doc = self.execute(self.service.documents().get(
                documentId=document_id,
                includeTabsContent=True,
            ))

            try:
                content = self._get_tab_content(doc, tab_id)
            except ValueError as e:
                output_error(
                    error_code="NOT_FOUND",
                    operation="docs.append",
                    message=str(e),
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            # Find the end index (last element's endIndex - 1)
            end_index = 1
            if content:
                last_element = content[-1]
                end_index = last_element.get("endIndex", 1) - 1

            location: dict[str, Any] = {"index": end_index}
            if tab_id:
                location["tabId"] = tab_id

            requests = [
                {
                    "insertText": {
                        "location": location,
                        "text": text,
                    }
                }
            ]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.append",
                document_id=document_id,
                index=end_index,
                tab_id=tab_id,
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
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Replace text throughout the document (or specific tab).

        Args:
            document_id: The document ID.
            find: Text to find.
            replace_with: Replacement text.
            match_case: Case-sensitive matching.
            tab_id: Optional tab ID to restrict replacement to.
        """
        try:
            replace_request: dict[str, Any] = {
                "containsText": {
                    "text": find,
                    "matchCase": match_case,
                },
                "replaceText": replace_with,
            }

            # Restrict to specific tab if provided
            if tab_id:
                replace_request["tabsCriteria"] = {"tabIds": [tab_id]}

            requests = [{"replaceAllText": replace_request}]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
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
                tab_id=tab_id,
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
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Apply formatting to a text range.

        Args:
            document_id: The document ID.
            start_index: Start index of range.
            end_index: End index of range.
            bold: Bold formatting.
            italic: Italic formatting.
            underline: Underline formatting.
            font_size: Font size in points.
            foreground_color: Text color (hex).
            tab_id: Optional tab ID.
        """
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

            range_obj: dict[str, Any] = {
                "startIndex": start_index,
                "endIndex": end_index,
            }
            if tab_id:
                range_obj["tabId"] = tab_id

            requests = [
                {
                    "updateTextStyle": {
                        "range": range_obj,
                        "textStyle": text_style,
                        "fields": ",".join(fields),
                    }
                }
            ]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.format",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                tab_id=tab_id,
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
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Delete content in a range.

        Args:
            document_id: The document ID.
            start_index: Start index of range.
            end_index: End index of range.
            tab_id: Optional tab ID.
        """
        try:
            range_obj: dict[str, Any] = {
                "startIndex": start_index,
                "endIndex": end_index,
            }
            if tab_id:
                range_obj["tabId"] = tab_id

            requests = [{"deleteContentRange": {"range": range_obj}}]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.delete",
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                tab_id=tab_id,
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
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert a page break at the specified index.

        Args:
            document_id: The document ID.
            index: Character index to insert page break.
            tab_id: Optional tab ID.
        """
        try:
            location: dict[str, Any] = {"index": index}
            if tab_id:
                location["tabId"] = tab_id

            requests = [{"insertPageBreak": {"location": location}}]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.page_break",
                document_id=document_id,
                index=index,
                tab_id=tab_id,
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
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert an image from a URL.

        Args:
            document_id: The document ID.
            image_url: URL of the image to insert.
            index: Character index (default: end of document).
            width: Image width in points.
            height: Image height in points.
            tab_id: Optional tab ID.
        """
        try:
            # If no index specified, append at end
            if index is None:
                doc = self.execute(self.service.documents().get(
                    documentId=document_id,
                    includeTabsContent=True,
                ))
                try:
                    content = self._get_tab_content(doc, tab_id)
                except ValueError as e:
                    output_error(
                        error_code="NOT_FOUND",
                        operation="docs.insert_image",
                        message=str(e),
                    )
                    raise SystemExit(ExitCode.NOT_FOUND)
                if content:
                    index = content[-1].get("endIndex", 1) - 1
                else:
                    index = 1

            location: dict[str, Any] = {"index": index}
            if tab_id:
                location["tabId"] = tab_id

            insert_inline_image: dict[str, Any] = {
                "location": location,
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

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.insert_image",
                document_id=document_id,
                index=index,
                tab_id=tab_id,
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
        doc = self.execute(self.service.documents().get(documentId=document_id))
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
        doc = self.execute(self.service.documents().get(documentId=document_id))
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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

    def set_table_column_widths(
        self,
        document_id: str,
        table_index: int,
        column_widths: dict[int, float],
    ) -> dict[str, Any]:
        """Set widths for multiple columns in a table with a single API call.

        Args:
            document_id: The document ID.
            table_index: The table index (0-based).
            column_widths: Dict mapping column index to width in points.
                           Example: {0: 70, 1: 90, 2: 170}
        """
        try:
            tables = self._get_tables(document_id)
            if table_index >= len(tables):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.set_table_column_widths",
                    message=f"Table index {table_index} not found",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            if not column_widths:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.set_table_column_widths",
                    message="No column widths provided",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            table = tables[table_index]

            # Build one request per column, all in single batch
            requests = []
            for col_index, width in column_widths.items():
                requests.append({
                    "updateTableColumnProperties": {
                        "tableStartLocation": {"index": table["startIndex"]},
                        "columnIndices": [col_index],
                        "tableColumnProperties": {
                            "width": {"magnitude": width, "unit": "PT"},
                            "widthType": "FIXED_WIDTH",
                        },
                        "fields": "width,widthType",
                    }
                })

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            output_success(
                operation="docs.set_table_column_widths",
                document_id=document_id,
                table_index=table_index,
                columns_updated=len(column_widths),
                column_widths=column_widths,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.set_table_column_widths",
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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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
            doc = self.execute(self.service.documents().get(documentId=document_id))
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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

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

    def get_page_format(self, document_id: str) -> dict[str, Any]:
        """Get the document's page format (PAGES or PAGELESS).

        Args:
            document_id: The document ID.

        Returns:
            Dict with page_format and related info.
        """
        try:
            doc = self.execute(self.service.documents().get(documentId=document_id))
            doc_style = doc.get("documentStyle", {})
            doc_format = doc_style.get("documentFormat", {})
            mode = doc_format.get("documentMode", "PAGES")

            result = {
                "document_id": document_id,
                "page_format": mode,
                "is_pageless": mode == "PAGELESS",
            }

            output_success(operation="docs.get_page_format", **result)
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.get_page_format",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_page_format(
        self,
        document_id: str,
        mode: str,
    ) -> dict[str, Any]:
        """Set the document's page format to PAGES or PAGELESS.

        Args:
            document_id: The document ID.
            mode: Either "PAGES" or "PAGELESS".

        Note:
            Switching to PAGELESS will disable headers, footers, page numbers,
            and other page-specific features. Content remains but these elements
            become invisible.
        """
        mode = mode.upper()
        if mode not in ("PAGES", "PAGELESS"):
            output_error(
                error_code="INVALID_ARGS",
                operation="docs.set_page_format",
                message=f"Invalid mode '{mode}'. Must be 'PAGES' or 'PAGELESS'.",
            )
            raise SystemExit(ExitCode.INVALID_ARGS)

        try:
            requests = [{
                "updateDocumentStyle": {
                    "documentStyle": {
                        "documentFormat": {
                            "documentMode": mode,
                        }
                    },
                    "fields": "documentFormat",
                }
            }]

            self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            result = {
                "document_id": document_id,
                "page_format": mode,
                "is_pageless": mode == "PAGELESS",
            }

            output_success(operation="docs.set_page_format", **result)
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.set_page_format",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # NAMED RANGE OPERATIONS (Phase 7)
    # =========================================================================

    def create_named_range(
        self,
        document_id: str,
        name: str,
        start_index: int,
        end_index: int,
    ) -> dict[str, Any]:
        """Create a named range (bookmark) in the document.

        Args:
            document_id: The document ID.
            name: Name for the range (must be unique).
            start_index: Start character index.
            end_index: End character index.
        """
        try:
            requests = [{
                "createNamedRange": {
                    "name": name,
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                }
            }]

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            named_range_id = (
                result.get("replies", [{}])[0]
                .get("createNamedRange", {})
                .get("namedRangeId")
            )

            output_success(
                operation="docs.create_named_range",
                document_id=document_id,
                name=name,
                named_range_id=named_range_id,
                start_index=start_index,
                end_index=end_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.create_named_range",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_named_range(
        self,
        document_id: str,
        name: str | None = None,
        named_range_id: str | None = None,
    ) -> dict[str, Any]:
        """Delete a named range by name or ID.

        Args:
            document_id: The document ID.
            name: Name of the range to delete.
            named_range_id: ID of the range to delete.
        """
        try:
            if not name and not named_range_id:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.delete_named_range",
                    message="Either name or named_range_id must be provided",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request: dict[str, Any] = {"deleteNamedRange": {}}
            if name:
                request["deleteNamedRange"]["name"] = name
            else:
                request["deleteNamedRange"]["namedRangeId"] = named_range_id

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": [request]}
            ))

            output_success(
                operation="docs.delete_named_range",
                document_id=document_id,
                name=name,
                named_range_id=named_range_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete_named_range",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_named_ranges(self, document_id: str) -> dict[str, Any]:
        """List all named ranges in the document."""
        try:
            doc = self.execute(self.service.documents().get(documentId=document_id))
            named_ranges = doc.get("namedRanges", {})

            range_info = []
            for name, data in named_ranges.items():
                for nr in data.get("namedRanges", []):
                    ranges = nr.get("ranges", [])
                    for r in ranges:
                        range_info.append({
                            "name": name,
                            "id": nr.get("namedRangeId"),
                            "start_index": r.get("startIndex"),
                            "end_index": r.get("endIndex"),
                        })

            output_success(
                operation="docs.list_named_ranges",
                document_id=document_id,
                count=len(range_info),
                named_ranges=range_info,
            )
            return {"named_ranges": range_info}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.list_named_ranges",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # FOOTNOTE OPERATIONS (Phase 7)
    # =========================================================================

    def insert_footnote(
        self,
        document_id: str,
        index: int,
    ) -> dict[str, Any]:
        """Insert a footnote reference at the specified index.

        Args:
            document_id: The document ID.
            index: Character index where to insert the footnote reference.
        """
        try:
            requests = [{
                "createFootnote": {
                    "location": {"index": index},
                }
            }]

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            footnote_id = (
                result.get("replies", [{}])[0]
                .get("createFootnote", {})
                .get("footnoteId")
            )

            output_success(
                operation="docs.insert_footnote",
                document_id=document_id,
                index=index,
                footnote_id=footnote_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_footnote",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_footnotes(self, document_id: str) -> dict[str, Any]:
        """List all footnotes in the document."""
        try:
            doc = self.execute(self.service.documents().get(documentId=document_id))
            footnotes = doc.get("footnotes", {})

            footnote_info = []
            for fid, footnote in footnotes.items():
                content = self._extract_text(footnote.get("content", []))
                footnote_info.append({
                    "id": fid,
                    "content": content[:500] if content else "",
                })

            output_success(
                operation="docs.list_footnotes",
                document_id=document_id,
                count=len(footnote_info),
                footnotes=footnote_info,
            )
            return {"footnotes": footnote_info}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.list_footnotes",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_footnote_content(
        self,
        document_id: str,
        footnote_id: str,
        start_index: int,
        end_index: int,
    ) -> dict[str, Any]:
        """Delete content from a footnote.

        Note: Footnotes cannot be entirely deleted, only their content can be modified.
        """
        try:
            requests = [{
                "deleteContentRange": {
                    "range": {
                        "segmentId": footnote_id,
                        "startIndex": start_index,
                        "endIndex": end_index,
                    }
                }
            }]

            result = self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            output_success(
                operation="docs.delete_footnote_content",
                document_id=document_id,
                footnote_id=footnote_id,
                start_index=start_index,
                end_index=end_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.delete_footnote_content",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # SUGGESTION OPERATIONS (Phase 8)
    # =========================================================================

    def _extract_suggestions_from_content(
        self, content: list[dict], suggestions: list[dict]
    ) -> None:
        """Recursively extract suggestions from document content."""
        for element in content:
            if "paragraph" in element:
                for elem in element["paragraph"].get("elements", []):
                    if "textRun" in elem:
                        text_run = elem["textRun"]
                        text = text_run.get("content", "")

                        # Check for suggested insertions
                        insertion_ids = text_run.get("suggestedInsertionIds", [])
                        for sid in insertion_ids:
                            suggestions.append({
                                "type": "insertion",
                                "suggestion_id": sid,
                                "text": text,
                                "start_index": elem.get("startIndex"),
                                "end_index": elem.get("endIndex"),
                            })

                        # Check for suggested deletions
                        deletion_ids = text_run.get("suggestedDeletionIds", [])
                        for sid in deletion_ids:
                            suggestions.append({
                                "type": "deletion",
                                "suggestion_id": sid,
                                "text": text,
                                "start_index": elem.get("startIndex"),
                                "end_index": elem.get("endIndex"),
                            })

                        # Check for suggested text style changes
                        style_changes = text_run.get("suggestedTextStyleChanges", {})
                        for sid, change in style_changes.items():
                            suggestions.append({
                                "type": "style_change",
                                "suggestion_id": sid,
                                "text": text,
                                "start_index": elem.get("startIndex"),
                                "end_index": elem.get("endIndex"),
                                "style_change": change.get("textStyle", {}),
                            })

            elif "table" in element:
                for row in element["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        self._extract_suggestions_from_content(
                            cell.get("content", []), suggestions
                        )

    def get_suggestions(self, document_id: str) -> dict[str, Any]:
        """Get all pending suggestions (tracked changes) in the document.

        Returns suggestions including insertions, deletions, and style changes
        made while in "Suggesting" mode.
        """
        try:
            doc = self.execute(self.service.documents().get(
                documentId=document_id,
                suggestionsViewMode="PREVIEW_SUGGESTIONS_ACCEPTED"
            ))

            # Also get with suggestions visible to see what's pending
            doc_with_suggestions = self.execute(self.service.documents().get(
                documentId=document_id,
                suggestionsViewMode="SUGGESTIONS_INLINE"
            ))

            content = doc_with_suggestions.get("body", {}).get("content", [])
            suggestions: list[dict] = []
            self._extract_suggestions_from_content(content, suggestions)

            # Group by suggestion ID to consolidate fragments
            grouped: dict[str, dict] = {}
            for s in suggestions:
                sid = s["suggestion_id"]
                if sid not in grouped:
                    grouped[sid] = {
                        "suggestion_id": sid,
                        "type": s["type"],
                        "fragments": [],
                    }
                grouped[sid]["fragments"].append({
                    "text": s["text"],
                    "start_index": s["start_index"],
                    "end_index": s["end_index"],
                    "style_change": s.get("style_change"),
                })

            suggestion_list = list(grouped.values())

            output_success(
                operation="docs.get_suggestions",
                document_id=document_id,
                suggestion_count=len(suggestion_list),
                suggestions=suggestion_list,
            )
            return {"suggestions": suggestion_list}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.get_suggestions",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_document_mode(self, document_id: str) -> dict[str, Any]:
        """Get document's current revision mode and suggestion state.

        Returns information about whether the document has pending suggestions
        and metadata about the document state.
        """
        try:
            doc = self.execute(self.service.documents().get(documentId=document_id))

            # Check for any suggestions in the document
            content = doc.get("body", {}).get("content", [])
            suggestions: list[dict] = []
            self._extract_suggestions_from_content(content, suggestions)

            has_suggestions = len(suggestions) > 0
            suggestion_ids = list(set(s["suggestion_id"] for s in suggestions))

            output_success(
                operation="docs.get_document_mode",
                document_id=document_id,
                title=doc.get("title", ""),
                revision_id=doc.get("revisionId"),
                has_pending_suggestions=has_suggestions,
                pending_suggestion_count=len(suggestion_ids),
                suggestion_ids=suggestion_ids[:10],  # Limit output
            )
            return {
                "has_suggestions": has_suggestions,
                "suggestion_count": len(suggestion_ids),
            }
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.get_document_mode",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def accept_suggestion(
        self,
        document_id: str,
        suggestion_id: str,
    ) -> dict[str, Any]:
        """Accept a suggestion (tracked change) in the document.

        Args:
            document_id: The document ID.
            suggestion_id: The suggestion ID to accept.
        """
        try:
            requests = [
                {
                    "acceptSuggestion": {
                        "suggestionId": suggestion_id,
                    }
                }
            ]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.accept_suggestion",
                document_id=document_id,
                suggestion_id=suggestion_id,
                accepted=True,
            )
            return result
        except HttpError as e:
            if "not found" in str(e.reason).lower():
                output_error(
                    error_code="NOT_FOUND",
                    operation="docs.accept_suggestion",
                    message=f"Suggestion not found: {suggestion_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="docs.accept_suggestion",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def reject_suggestion(
        self,
        document_id: str,
        suggestion_id: str,
    ) -> dict[str, Any]:
        """Reject a suggestion (tracked change) in the document.

        Args:
            document_id: The document ID.
            suggestion_id: The suggestion ID to reject.
        """
        try:
            requests = [
                {
                    "rejectSuggestion": {
                        "suggestionId": suggestion_id,
                    }
                }
            ]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.reject_suggestion",
                document_id=document_id,
                suggestion_id=suggestion_id,
                rejected=True,
            )
            return result
        except HttpError as e:
            if "not found" in str(e.reason).lower():
                output_error(
                    error_code="NOT_FOUND",
                    operation="docs.reject_suggestion",
                    message=f"Suggestion not found: {suggestion_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="docs.reject_suggestion",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def accept_all_suggestions(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        """Accept all pending suggestions in the document.

        Args:
            document_id: The document ID.
        """
        try:
            # First get all suggestions
            suggestions_result = self.get_suggestions(document_id)
            suggestions = suggestions_result.get("suggestions", [])

            if not suggestions:
                output_success(
                    operation="docs.accept_all_suggestions",
                    document_id=document_id,
                    accepted_count=0,
                    message="No pending suggestions to accept",
                )
                return {"accepted_count": 0}

            # Build batch request
            requests = [
                {"acceptSuggestion": {"suggestionId": s["suggestion_id"]}}
                for s in suggestions
            ]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.accept_all_suggestions",
                document_id=document_id,
                accepted_count=len(suggestions),
            )
            return {"accepted_count": len(suggestions)}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.accept_all_suggestions",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def reject_all_suggestions(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        """Reject all pending suggestions in the document.

        Args:
            document_id: The document ID.
        """
        try:
            # First get all suggestions
            suggestions_result = self.get_suggestions(document_id)
            suggestions = suggestions_result.get("suggestions", [])

            if not suggestions:
                output_success(
                    operation="docs.reject_all_suggestions",
                    document_id=document_id,
                    rejected_count=0,
                    message="No pending suggestions to reject",
                )
                return {"rejected_count": 0}

            # Build batch request
            requests = [
                {"rejectSuggestion": {"suggestionId": s["suggestion_id"]}}
                for s in suggestions
            ]

            result = self.execute(
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
            )

            output_success(
                operation="docs.reject_all_suggestions",
                document_id=document_id,
                rejected_count=len(suggestions),
            )
            return {"rejected_count": len(suggestions)}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.reject_all_suggestions",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # MARKDOWN INSERTION OPERATIONS
    # =========================================================================

    def insert_markdown(
        self,
        document_id: str,
        markdown_content: str,
        index: int = 1,
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert markdown content into an existing document.

        Leverages Google's native markdown parsing by:
        1. Creating a temporary document from the markdown
        2. Reading its formatted content
        3. Inserting the content (with formatting) at the specified position
        4. Deleting the temporary document

        Args:
            document_id: The target document ID.
            markdown_content: Markdown text to insert.
            index: Character index where to insert (default: 1, start of document).
            tab_id: Optional tab ID for documents with multiple tabs.

        Returns:
            Dict with insertion details.
        """
        from googleapiclient.http import MediaIoBaseUpload
        import io

        temp_doc_id = None

        try:
            # Step 1: Create a temporary Google Doc from the markdown
            markdown_bytes = markdown_content.encode("utf-8")
            media = MediaIoBaseUpload(
                io.BytesIO(markdown_bytes),
                mimetype="text/markdown",
                resumable=True,
            )

            temp_file = self.execute(
                self.drive_service.files()
                .create(
                    body={
                        "name": "_temp_markdown_insert",
                        "mimeType": "application/vnd.google-apps.document",
                    },
                    media_body=media,
                    fields="id",
                )
            )
            temp_doc_id = temp_file["id"]

            # Step 2: Read the structured content from the temp doc
            temp_doc = self.execute(
                self.service.documents()
                .get(documentId=temp_doc_id, includeTabsContent=True)
            )

            # Get the body content from the temp doc
            temp_content = self._get_tab_content(temp_doc, None)

            # Step 3: Build insert requests from the temp doc content
            requests = self._build_insert_requests_from_content(
                temp_content, index, tab_id
            )

            if not requests:
                output_error(
                    error_code="EMPTY_CONTENT",
                    operation="docs.insert_markdown",
                    message="No content to insert from markdown.",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Step 4: Execute the insert requests on the target document
            self.execute(self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ))

            # Calculate inserted length for reporting
            inserted_text = self._extract_text_from_content(temp_content)
            inserted_length = len(inserted_text)

            result = {
                "document_id": document_id,
                "inserted_at_index": index,
                "inserted_length": inserted_length,
            }
            if tab_id:
                result["tab_id"] = tab_id

            output_success(operation="docs.insert_markdown", **result)
            return result

        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.insert_markdown",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)
        finally:
            # Step 5: Clean up - delete the temporary document
            if temp_doc_id:
                try:
                    self.execute(self.drive_service.files().delete(fileId=temp_doc_id))
                except Exception:
                    pass  # Ignore cleanup errors

    def _build_insert_requests_from_content(
        self,
        content: list[dict],
        target_index: int,
        tab_id: str | None = None,
    ) -> list[dict]:
        """Build batchUpdate requests to insert content at a target position.

        Processes content elements and generates insertText and formatting requests.
        """
        requests: list[dict] = []

        # Extract all text and formatting info
        text_parts: list[dict] = []

        for element in content:
            if "paragraph" not in element:
                continue

            para = element["paragraph"]
            para_elements = para.get("elements", [])

            for pe in para_elements:
                if "textRun" not in pe:
                    continue

                text_run = pe["textRun"]
                text = text_run.get("content", "")
                style = text_run.get("textStyle", {})

                if text:
                    text_parts.append({
                        "text": text,
                        "style": style,
                    })

        if not text_parts:
            return []

        # Combine all text for a single insert
        full_text = "".join(tp["text"] for tp in text_parts)

        # Don't insert if it's just a single newline (empty doc)
        if full_text.strip() == "":
            return []

        # Build the insert location
        location: dict[str, Any] = {"index": target_index}
        if tab_id:
            location["tabId"] = tab_id

        # Insert all the text at once
        requests.append({
            "insertText": {
                "location": location,
                "text": full_text,
            }
        })

        # Now apply formatting for each text part
        current_index = target_index
        for tp in text_parts:
            text = tp["text"]
            style = tp["style"]
            text_len = len(text)

            if text_len == 0:
                continue

            # Build text style update if there's any formatting
            style_updates: dict[str, Any] = {}
            fields: list[str] = []

            if style.get("bold"):
                style_updates["bold"] = True
                fields.append("bold")

            if style.get("italic"):
                style_updates["italic"] = True
                fields.append("italic")

            if style.get("underline"):
                style_updates["underline"] = True
                fields.append("underline")

            if style.get("strikethrough"):
                style_updates["strikethrough"] = True
                fields.append("strikethrough")

            if style.get("link"):
                style_updates["link"] = style["link"]
                fields.append("link")

            if style.get("foregroundColor"):
                style_updates["foregroundColor"] = style["foregroundColor"]
                fields.append("foregroundColor")

            if style.get("backgroundColor"):
                style_updates["backgroundColor"] = style["backgroundColor"]
                fields.append("backgroundColor")

            if style.get("fontSize"):
                style_updates["fontSize"] = style["fontSize"]
                fields.append("fontSize")

            if style.get("weightedFontFamily"):
                style_updates["weightedFontFamily"] = style["weightedFontFamily"]
                fields.append("weightedFontFamily")

            if style.get("baselineOffset"):
                style_updates["baselineOffset"] = style["baselineOffset"]
                fields.append("baselineOffset")

            if style.get("smallCaps"):
                style_updates["smallCaps"] = True
                fields.append("smallCaps")

            # Only add formatting request if there's something to format
            if fields:
                range_spec: dict[str, Any] = {
                    "startIndex": current_index,
                    "endIndex": current_index + text_len,
                }
                if tab_id:
                    range_spec["tabId"] = tab_id

                requests.append({
                    "updateTextStyle": {
                        "range": range_spec,
                        "textStyle": style_updates,
                        "fields": ",".join(fields),
                    }
                })

            current_index += text_len

        return requests

    def _extract_text_from_content(self, content: list[dict]) -> str:
        """Extract plain text from document content elements."""
        text_parts = []
        for element in content:
            if "paragraph" in element:
                para = element["paragraph"]
                for pe in para.get("elements", []):
                    if "textRun" in pe:
                        text_parts.append(pe["textRun"].get("content", ""))
        return "".join(text_parts)

    def find_text(
        self,
        document_id: str,
        search_text: str,
        tab_id: str | None = None,
        occurrence: int = 1,
    ) -> dict[str, Any]:
        """Find text in document and return its position.

        Args:
            document_id: The document ID.
            search_text: Text to search for.
            tab_id: Optional tab ID to search in.
            occurrence: Which occurrence to find (1-based, default: 1).

        Returns:
            Dict with index, end_index, length, and total_occurrences.
        """
        try:
            doc = self.execute(self.service.documents().get(
                documentId=document_id,
                includeTabsContent=True,
            ))

            try:
                content = self._get_tab_content(doc, tab_id)
            except ValueError as e:
                output_error(
                    error_code="NOT_FOUND",
                    operation="docs.find_text",
                    message=str(e),
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            # Build text with position tracking
            text_positions: list[tuple[str, int]] = []  # (text, start_index)
            for element in content:
                if "paragraph" in element:
                    para = element["paragraph"]
                    for pe in para.get("elements", []):
                        if "textRun" in pe:
                            start_idx = pe.get("startIndex", 0)
                            text_content = pe["textRun"].get("content", "")
                            text_positions.append((text_content, start_idx))

            # Concatenate all text
            full_text = "".join(t[0] for t in text_positions)

            # Find all occurrences
            occurrences = []
            start = 0
            while True:
                idx = full_text.find(search_text, start)
                if idx == -1:
                    break
                occurrences.append(idx)
                start = idx + 1

            if not occurrences:
                output_error(
                    error_code="NOT_FOUND",
                    operation="docs.find_text",
                    message=f"Text not found: '{search_text}'",
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            if occurrence < 1 or occurrence > len(occurrences):
                output_error(
                    error_code="INVALID_ARGS",
                    operation="docs.find_text",
                    message=f"Occurrence {occurrence} out of range (found {len(occurrences)})",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            text_offset = occurrences[occurrence - 1]

            # Map text offset to document index
            # Need to find which element contains this offset and calculate real index
            current_offset = 0
            doc_index = 1  # Default to start
            for text, start_idx in text_positions:
                if current_offset + len(text) > text_offset:
                    # This element contains our target
                    char_offset = text_offset - current_offset
                    doc_index = start_idx + char_offset
                    break
                current_offset += len(text)

            result = {
                "index": doc_index,
                "end_index": doc_index + len(search_text),
                "length": len(search_text),
                "occurrence": occurrence,
                "total_occurrences": len(occurrences),
            }

            output_success(
                operation="docs.find_text",
                document_id=document_id,
                search_text=search_text,
                **result,
            )
            return result

        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="docs.find_text",
                message=f"Google Docs API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_image_at_text(
        self,
        document_id: str,
        image_url: str,
        after_text: str,
        width: float | None = None,
        height: float | None = None,
        tab_id: str | None = None,
        occurrence: int = 1,
    ) -> dict[str, Any]:
        """Insert an image after specified text.

        This is a convenience method that finds the text and inserts
        the image immediately after it, avoiding paragraph boundary issues.

        Args:
            document_id: The document ID.
            image_url: URL of the image to insert.
            after_text: Text to insert image after.
            width: Image width in points.
            height: Image height in points.
            tab_id: Optional tab ID.
            occurrence: Which occurrence of text (1-based, default: 1).
        """
        # First, find the text position
        try:
            position = self.find_text(
                document_id=document_id,
                search_text=after_text,
                tab_id=tab_id,
                occurrence=occurrence,
            )
        except SystemExit:
            # find_text already output the error
            raise

        # Insert image at the end of the found text
        insert_index = position["end_index"]

        # Now insert the image at that position
        return self.insert_image(
            document_id=document_id,
            image_url=image_url,
            index=insert_index,
            width=width,
            height=height,
            tab_id=tab_id,
        )

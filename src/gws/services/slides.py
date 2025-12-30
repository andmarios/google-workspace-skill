"""Google Slides service operations."""

import uuid
from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode


class SlidesService(BaseService):
    """Google Slides operations."""

    SERVICE_NAME = "slides"
    VERSION = "v1"

    PREDEFINED_LAYOUTS = {
        "BLANK": "BLANK",
        "TITLE": "TITLE",
        "TITLE_AND_BODY": "TITLE_AND_BODY",
        "TITLE_AND_TWO_COLUMNS": "TITLE_AND_TWO_COLUMNS",
        "TITLE_ONLY": "TITLE_ONLY",
        "SECTION_HEADER": "SECTION_HEADER",
        "ONE_COLUMN_TEXT": "ONE_COLUMN_TEXT",
        "MAIN_POINT": "MAIN_POINT",
        "BIG_NUMBER": "BIG_NUMBER",
    }

    def _generate_object_id(self) -> str:
        """Generate a unique object ID for new elements."""
        return f"gws_{uuid.uuid4().hex[:12]}"

    def metadata(self, presentation_id: str) -> dict[str, Any]:
        """Get presentation metadata."""
        try:
            presentation = (
                self.service.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )

            slides = [
                {
                    "object_id": slide["objectId"],
                    "index": i,
                    "element_count": len(slide.get("pageElements", [])),
                }
                for i, slide in enumerate(presentation.get("slides", []))
            ]

            output_success(
                operation="slides.metadata",
                presentation_id=presentation_id,
                title=presentation.get("title", ""),
                slide_count=len(slides),
                slides=slides,
            )
            return presentation
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.metadata",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def read(
        self,
        presentation_id: str,
        page_object_id: str | None = None,
    ) -> dict[str, Any]:
        """Read presentation or page content."""
        try:
            if page_object_id:
                page = (
                    self.service.presentations()
                    .pages()
                    .get(presentationId=presentation_id, pageObjectId=page_object_id)
                    .execute()
                )

                elements = []
                for elem in page.get("pageElements", []):
                    elem_info = {
                        "object_id": elem["objectId"],
                        "type": self._get_element_type(elem),
                    }
                    if "shape" in elem and "text" in elem["shape"]:
                        elem_info["text"] = self._extract_text(elem["shape"]["text"])
                    elements.append(elem_info)

                output_success(
                    operation="slides.read",
                    presentation_id=presentation_id,
                    page_object_id=page_object_id,
                    element_count=len(elements),
                    elements=elements,
                )
                return page
            else:
                presentation = (
                    self.service.presentations()
                    .get(presentationId=presentation_id)
                    .execute()
                )

                slides_info = []
                for i, slide in enumerate(presentation.get("slides", [])):
                    slide_info = {
                        "object_id": slide["objectId"],
                        "index": i,
                        "elements": [],
                    }
                    for elem in slide.get("pageElements", []):
                        elem_info = {
                            "object_id": elem["objectId"],
                            "type": self._get_element_type(elem),
                        }
                        if "shape" in elem and "text" in elem["shape"]:
                            elem_info["text"] = self._extract_text(elem["shape"]["text"])
                        slide_info["elements"].append(elem_info)
                    slides_info.append(slide_info)

                output_success(
                    operation="slides.read",
                    presentation_id=presentation_id,
                    title=presentation.get("title", ""),
                    slide_count=len(slides_info),
                    slides=slides_info,
                )
                return presentation
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.read",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def _get_element_type(self, element: dict) -> str:
        """Determine element type."""
        if "shape" in element:
            return element["shape"].get("shapeType", "SHAPE")
        if "image" in element:
            return "IMAGE"
        if "table" in element:
            return "TABLE"
        if "line" in element:
            return "LINE"
        if "video" in element:
            return "VIDEO"
        return "UNKNOWN"

    def _extract_text(self, text_content: dict) -> str:
        """Extract plain text from text content."""
        parts = []
        for element in text_content.get("textElements", []):
            if "textRun" in element:
                parts.append(element["textRun"].get("content", ""))
        return "".join(parts).strip()

    def create(
        self,
        title: str,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new presentation."""
        try:
            presentation = (
                self.service.presentations()
                .create(body={"title": title})
                .execute()
            )
            presentation_id = presentation["presentationId"]

            # Move to folder if specified
            if folder_id:
                file = self.drive_service.files().get(
                    fileId=presentation_id, fields="parents"
                ).execute()
                previous_parents = ",".join(file.get("parents", []))

                self.drive_service.files().update(
                    fileId=presentation_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields="id, parents",
                ).execute()

            output_success(
                operation="slides.create",
                presentation_id=presentation_id,
                title=title,
                web_view_link=f"https://docs.google.com/presentation/d/{presentation_id}/edit",
            )
            return presentation
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.create",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_slide(
        self,
        presentation_id: str,
        layout: str = "BLANK",
        insertion_index: int | None = None,
    ) -> dict[str, Any]:
        """Add a new slide to the presentation."""
        try:
            slide_id = self._generate_object_id()

            request: dict[str, Any] = {
                "createSlide": {
                    "objectId": slide_id,
                    "slideLayoutReference": {
                        "predefinedLayout": self.PREDEFINED_LAYOUTS.get(layout, layout)
                    },
                }
            }

            if insertion_index is not None:
                request["createSlide"]["insertionIndex"] = insertion_index

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.add_slide",
                presentation_id=presentation_id,
                slide_id=slide_id,
                layout=layout,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.add_slide",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_slide(
        self,
        presentation_id: str,
        slide_id: str,
    ) -> dict[str, Any]:
        """Delete a slide from the presentation."""
        try:
            request = {"deleteObject": {"objectId": slide_id}}

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.delete_slide",
                presentation_id=presentation_id,
                deleted_slide_id=slide_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.delete_slide",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def duplicate_slide(
        self,
        presentation_id: str,
        slide_id: str,
    ) -> dict[str, Any]:
        """Duplicate a slide."""
        try:
            new_slide_id = self._generate_object_id()

            request = {
                "duplicateObject": {
                    "objectId": slide_id,
                    "objectIds": {slide_id: new_slide_id},
                }
            }

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.duplicate_slide",
                presentation_id=presentation_id,
                original_slide_id=slide_id,
                new_slide_id=new_slide_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.duplicate_slide",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_text(
        self,
        presentation_id: str,
        object_id: str,
        text: str,
        insertion_index: int = 0,
    ) -> dict[str, Any]:
        """Insert text into a shape."""
        try:
            request = {
                "insertText": {
                    "objectId": object_id,
                    "insertionIndex": insertion_index,
                    "text": text,
                }
            }

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.insert_text",
                presentation_id=presentation_id,
                object_id=object_id,
                text_length=len(text),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_text",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def replace_text(
        self,
        presentation_id: str,
        find: str,
        replace_with: str,
        match_case: bool = False,
        page_object_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Replace text throughout the presentation."""
        try:
            request: dict[str, Any] = {
                "replaceAllText": {
                    "containsText": {
                        "text": find,
                        "matchCase": match_case,
                    },
                    "replaceText": replace_with,
                }
            }

            if page_object_ids:
                request["replaceAllText"]["pageObjectIds"] = page_object_ids

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            replies = result.get("replies", [{}])
            occurrences = replies[0].get("replaceAllText", {}).get(
                "occurrencesChanged", 0
            )

            output_success(
                operation="slides.replace_text",
                presentation_id=presentation_id,
                find=find,
                replace_with=replace_with,
                occurrences_changed=occurrences,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.replace_text",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_textbox(
        self,
        presentation_id: str,
        page_object_id: str,
        text: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        """Create a text box on a slide."""
        try:
            textbox_id = self._generate_object_id()

            requests = [
                {
                    "createShape": {
                        "objectId": textbox_id,
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": page_object_id,
                            "size": {
                                "width": {"magnitude": width, "unit": "PT"},
                                "height": {"magnitude": height, "unit": "PT"},
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": x,
                                "translateY": y,
                                "unit": "PT",
                            },
                        },
                    }
                },
                {
                    "insertText": {
                        "objectId": textbox_id,
                        "insertionIndex": 0,
                        "text": text,
                    }
                },
            ]

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            output_success(
                operation="slides.create_textbox",
                presentation_id=presentation_id,
                page_object_id=page_object_id,
                textbox_id=textbox_id,
                position={"x": x, "y": y, "width": width, "height": height},
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.create_textbox",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_image(
        self,
        presentation_id: str,
        page_object_id: str,
        image_url: str,
        x: float,
        y: float,
        width: float | None = None,
        height: float | None = None,
    ) -> dict[str, Any]:
        """Insert an image on a slide."""
        try:
            image_id = self._generate_object_id()

            element_properties: dict[str, Any] = {
                "pageObjectId": page_object_id,
                "transform": {
                    "scaleX": 1,
                    "scaleY": 1,
                    "translateX": x,
                    "translateY": y,
                    "unit": "PT",
                },
            }

            if width is not None and height is not None:
                element_properties["size"] = {
                    "width": {"magnitude": width, "unit": "PT"},
                    "height": {"magnitude": height, "unit": "PT"},
                }

            request = {
                "createImage": {
                    "objectId": image_id,
                    "url": image_url,
                    "elementProperties": element_properties,
                }
            }

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.insert_image",
                presentation_id=presentation_id,
                page_object_id=page_object_id,
                image_id=image_id,
                image_url=image_url,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_image",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_element(
        self,
        presentation_id: str,
        object_id: str,
    ) -> dict[str, Any]:
        """Delete an element from a slide."""
        try:
            request = {"deleteObject": {"objectId": object_id}}

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.delete_element",
                presentation_id=presentation_id,
                deleted_object_id=object_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.delete_element",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def format_text(
        self,
        presentation_id: str,
        object_id: str,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        font_size: int | None = None,
        foreground_color: str | None = None,
    ) -> dict[str, Any]:
        """Apply formatting to text in an element."""
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
                from gws.utils.colors import parse_hex_color
                rgb = parse_hex_color(foreground_color)
                text_style["foregroundColor"] = {"opaqueColor": {"rgbColor": rgb}}
                fields.append("foregroundColor")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.format_text",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request = {
                "updateTextStyle": {
                    "objectId": object_id,
                    "style": text_style,
                    "textRange": {"type": "ALL"},
                    "fields": ",".join(fields),
                }
            }

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.format_text",
                presentation_id=presentation_id,
                object_id=object_id,
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.format_text",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

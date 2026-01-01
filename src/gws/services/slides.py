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

    def format_text_extended(
        self,
        presentation_id: str,
        object_id: str,
        start_index: int | None = None,
        end_index: int | None = None,
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
        """Apply extended formatting to text in an element.

        Args:
            presentation_id: The presentation ID.
            object_id: The shape/text box object ID.
            start_index: Start character index (0-based). If None, applies to all text.
            end_index: End character index (exclusive). If None, applies to all text.
            bold: Bold formatting.
            italic: Italic formatting.
            underline: Underline formatting.
            strikethrough: Strikethrough formatting.
            small_caps: Small caps formatting.
            font_family: Font family name (e.g., "Arial", "Roboto").
            font_weight: Font weight (100-900, in increments of 100).
            font_size: Font size in points.
            foreground_color: Text color (hex, e.g., "#FF0000").
            background_color: Text background/highlight color (hex).
            baseline_offset: Baseline offset ("SUPERSCRIPT" or "SUBSCRIPT").
            link_url: URL to link the text to.
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
            if font_size is not None:
                text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
                fields.append("fontSize")
            if foreground_color is not None:
                rgb = parse_hex_color(foreground_color)
                text_style["foregroundColor"] = {"opaqueColor": {"rgbColor": rgb}}
                fields.append("foregroundColor")
            if background_color is not None:
                rgb = parse_hex_color(background_color)
                text_style["backgroundColor"] = {"opaqueColor": {"rgbColor": rgb}}
                fields.append("backgroundColor")
            if baseline_offset is not None:
                valid_offsets = {"SUPERSCRIPT", "SUBSCRIPT", "NONE"}
                if baseline_offset.upper() not in valid_offsets:
                    output_error(
                        error_code="INVALID_ARGS",
                        operation="slides.format_text_extended",
                        message=f"baseline_offset must be one of: {valid_offsets}",
                    )
                    raise SystemExit(ExitCode.INVALID_ARGS)
                text_style["baselineOffset"] = baseline_offset.upper()
                fields.append("baselineOffset")
            if link_url is not None:
                text_style["link"] = {"url": link_url}
                fields.append("link")
            if font_family is not None or font_weight is not None:
                weighted_font: dict[str, Any] = {}
                if font_family is not None:
                    weighted_font["fontFamily"] = font_family
                if font_weight is not None:
                    if font_weight < 100 or font_weight > 900 or font_weight % 100 != 0:
                        output_error(
                            error_code="INVALID_ARGS",
                            operation="slides.format_text_extended",
                            message="font_weight must be 100-900 in increments of 100",
                        )
                        raise SystemExit(ExitCode.INVALID_ARGS)
                    weighted_font["weight"] = font_weight
                text_style["weightedFontFamily"] = weighted_font
                fields.append("weightedFontFamily")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.format_text_extended",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Build text range
            if start_index is not None and end_index is not None:
                text_range = {
                    "type": "FIXED_RANGE",
                    "startIndex": start_index,
                    "endIndex": end_index,
                }
            else:
                text_range = {"type": "ALL"}

            request = {
                "updateTextStyle": {
                    "objectId": object_id,
                    "style": text_style,
                    "textRange": text_range,
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
                operation="slides.format_text_extended",
                presentation_id=presentation_id,
                object_id=object_id,
                formatting=fields,
                text_range=text_range,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.format_text_extended",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def format_paragraph(
        self,
        presentation_id: str,
        object_id: str,
        start_index: int | None = None,
        end_index: int | None = None,
        alignment: str | None = None,
        line_spacing: float | None = None,
        space_above: float | None = None,
        space_below: float | None = None,
        indent_first_line: float | None = None,
        indent_start: float | None = None,
        indent_end: float | None = None,
    ) -> dict[str, Any]:
        """Apply paragraph formatting to text in an element.

        Args:
            presentation_id: The presentation ID.
            object_id: The shape/text box object ID.
            start_index: Start character index (0-based). If None, applies to all.
            end_index: End character index (exclusive). If None, applies to all.
            alignment: Paragraph alignment (START, CENTER, END, JUSTIFIED).
            line_spacing: Line spacing as percentage (100 = single, 200 = double).
            space_above: Space above paragraph in points.
            space_below: Space below paragraph in points.
            indent_first_line: First line indent in points.
            indent_start: Start (left) indent in points.
            indent_end: End (right) indent in points.
        """
        try:
            paragraph_style: dict[str, Any] = {}
            fields = []

            if alignment is not None:
                valid_alignments = {"START", "CENTER", "END", "JUSTIFIED"}
                if alignment.upper() not in valid_alignments:
                    output_error(
                        error_code="INVALID_ARGS",
                        operation="slides.format_paragraph",
                        message=f"alignment must be one of: {valid_alignments}",
                    )
                    raise SystemExit(ExitCode.INVALID_ARGS)
                paragraph_style["alignment"] = alignment.upper()
                fields.append("alignment")
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
                paragraph_style["indentFirstLine"] = {
                    "magnitude": indent_first_line,
                    "unit": "PT",
                }
                fields.append("indentFirstLine")
            if indent_start is not None:
                paragraph_style["indentStart"] = {
                    "magnitude": indent_start,
                    "unit": "PT",
                }
                fields.append("indentStart")
            if indent_end is not None:
                paragraph_style["indentEnd"] = {"magnitude": indent_end, "unit": "PT"}
                fields.append("indentEnd")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.format_paragraph",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Build text range
            if start_index is not None and end_index is not None:
                text_range = {
                    "type": "FIXED_RANGE",
                    "startIndex": start_index,
                    "endIndex": end_index,
                }
            else:
                text_range = {"type": "ALL"}

            request = {
                "updateParagraphStyle": {
                    "objectId": object_id,
                    "style": paragraph_style,
                    "textRange": text_range,
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
                operation="slides.format_paragraph",
                presentation_id=presentation_id,
                object_id=object_id,
                formatting=fields,
                text_range=text_range,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.format_paragraph",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_shape(
        self,
        presentation_id: str,
        page_object_id: str,
        shape_type: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        """Create a shape on a slide.

        Args:
            presentation_id: The presentation ID.
            page_object_id: The slide/page object ID.
            shape_type: Shape type (RECTANGLE, ELLIPSE, ROUND_RECTANGLE, etc.).
            x: X position in points.
            y: Y position in points.
            width: Width in points.
            height: Height in points.
        """
        try:
            shape_id = self._generate_object_id()

            request = {
                "createShape": {
                    "objectId": shape_id,
                    "shapeType": shape_type.upper(),
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
            }

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.create_shape",
                presentation_id=presentation_id,
                page_object_id=page_object_id,
                shape_id=shape_id,
                shape_type=shape_type.upper(),
                position={"x": x, "y": y, "width": width, "height": height},
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.create_shape",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def format_shape(
        self,
        presentation_id: str,
        object_id: str,
        fill_color: str | None = None,
        outline_color: str | None = None,
        outline_weight: float | None = None,
        outline_dash_style: str | None = None,
    ) -> dict[str, Any]:
        """Format a shape's appearance.

        Args:
            presentation_id: The presentation ID.
            object_id: The shape object ID.
            fill_color: Fill color (hex, e.g., "#FF0000").
            outline_color: Outline color (hex).
            outline_weight: Outline weight in points.
            outline_dash_style: Dash style (SOLID, DOT, DASH, DASH_DOT, LONG_DASH).
        """
        try:
            from gws.utils.colors import parse_hex_color

            shape_properties: dict[str, Any] = {}
            fields = []

            if fill_color is not None:
                rgb = parse_hex_color(fill_color)
                shape_properties["shapeBackgroundFill"] = {
                    "solidFill": {"color": {"rgbColor": rgb}}
                }
                fields.append("shapeBackgroundFill")

            if (
                outline_color is not None
                or outline_weight is not None
                or outline_dash_style is not None
            ):
                outline: dict[str, Any] = {}
                if outline_color is not None:
                    rgb = parse_hex_color(outline_color)
                    outline["outlineFill"] = {"solidFill": {"color": {"rgbColor": rgb}}}
                if outline_weight is not None:
                    outline["weight"] = {"magnitude": outline_weight, "unit": "PT"}
                if outline_dash_style is not None:
                    valid_styles = {"SOLID", "DOT", "DASH", "DASH_DOT", "LONG_DASH"}
                    if outline_dash_style.upper() not in valid_styles:
                        output_error(
                            error_code="INVALID_ARGS",
                            operation="slides.format_shape",
                            message=f"outline_dash_style must be one of: {valid_styles}",
                        )
                        raise SystemExit(ExitCode.INVALID_ARGS)
                    outline["dashStyle"] = outline_dash_style.upper()
                shape_properties["outline"] = outline
                fields.append("outline")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.format_shape",
                    message="At least one formatting option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request = {
                "updateShapeProperties": {
                    "objectId": object_id,
                    "shapeProperties": shape_properties,
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
                operation="slides.format_shape",
                presentation_id=presentation_id,
                object_id=object_id,
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.format_shape",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_table(
        self,
        presentation_id: str,
        page_object_id: str,
        rows: int,
        columns: int,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        """Insert a table on a slide.

        Args:
            presentation_id: The presentation ID.
            page_object_id: The slide/page object ID.
            rows: Number of rows.
            columns: Number of columns.
            x: X position in points.
            y: Y position in points.
            width: Width in points.
            height: Height in points.
        """
        try:
            table_id = self._generate_object_id()

            request = {
                "createTable": {
                    "objectId": table_id,
                    "rows": rows,
                    "columns": columns,
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
            }

            result = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
                .execute()
            )

            output_success(
                operation="slides.insert_table",
                presentation_id=presentation_id,
                page_object_id=page_object_id,
                table_id=table_id,
                rows=rows,
                columns=columns,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_table",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_table_row(
        self,
        presentation_id: str,
        table_id: str,
        row_index: int,
        insert_below: bool = True,
    ) -> dict[str, Any]:
        """Insert a row in a table.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            row_index: Row index to insert at.
            insert_below: Insert below (True) or above (False) the specified row.
        """
        try:
            request = {
                "insertTableRows": {
                    "tableObjectId": table_id,
                    "cellLocation": {"rowIndex": row_index},
                    "insertBelow": insert_below,
                    "number": 1,
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
                operation="slides.insert_table_row",
                presentation_id=presentation_id,
                table_id=table_id,
                row_index=row_index,
                insert_below=insert_below,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_table_row",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_table_column(
        self,
        presentation_id: str,
        table_id: str,
        column_index: int,
        insert_right: bool = True,
    ) -> dict[str, Any]:
        """Insert a column in a table.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            column_index: Column index to insert at.
            insert_right: Insert to the right (True) or left (False).
        """
        try:
            request = {
                "insertTableColumns": {
                    "tableObjectId": table_id,
                    "cellLocation": {"columnIndex": column_index},
                    "insertRight": insert_right,
                    "number": 1,
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
                operation="slides.insert_table_column",
                presentation_id=presentation_id,
                table_id=table_id,
                column_index=column_index,
                insert_right=insert_right,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_table_column",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_table_row(
        self,
        presentation_id: str,
        table_id: str,
        row_index: int,
    ) -> dict[str, Any]:
        """Delete a row from a table.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            row_index: Row index to delete.
        """
        try:
            request = {
                "deleteTableRow": {
                    "tableObjectId": table_id,
                    "cellLocation": {"rowIndex": row_index},
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
                operation="slides.delete_table_row",
                presentation_id=presentation_id,
                table_id=table_id,
                row_index=row_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.delete_table_row",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_table_column(
        self,
        presentation_id: str,
        table_id: str,
        column_index: int,
    ) -> dict[str, Any]:
        """Delete a column from a table.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            column_index: Column index to delete.
        """
        try:
            request = {
                "deleteTableColumn": {
                    "tableObjectId": table_id,
                    "cellLocation": {"columnIndex": column_index},
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
                operation="slides.delete_table_column",
                presentation_id=presentation_id,
                table_id=table_id,
                column_index=column_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.delete_table_column",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def style_table_cell(
        self,
        presentation_id: str,
        table_id: str,
        row_index: int,
        column_index: int,
        background_color: str | None = None,
        end_row_index: int | None = None,
        end_column_index: int | None = None,
    ) -> dict[str, Any]:
        """Style table cells.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            row_index: Starting row index.
            column_index: Starting column index.
            background_color: Cell background color (hex).
            end_row_index: Ending row index (exclusive). If None, styles single row.
            end_column_index: Ending column index (exclusive). If None, styles single column.
        """
        try:
            from gws.utils.colors import parse_hex_color

            cell_properties: dict[str, Any] = {}
            fields = []

            if background_color is not None:
                rgb = parse_hex_color(background_color)
                cell_properties["tableCellBackgroundFill"] = {
                    "solidFill": {"color": {"rgbColor": rgb}}
                }
                fields.append("tableCellBackgroundFill")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.style_table_cell",
                    message="At least one styling option required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Default to single cell if end indices not provided
            if end_row_index is None:
                end_row_index = row_index + 1
            if end_column_index is None:
                end_column_index = column_index + 1

            request = {
                "updateTableCellProperties": {
                    "objectId": table_id,
                    "tableRange": {
                        "location": {
                            "rowIndex": row_index,
                            "columnIndex": column_index,
                        },
                        "rowSpan": end_row_index - row_index,
                        "columnSpan": end_column_index - column_index,
                    },
                    "tableCellProperties": cell_properties,
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
                operation="slides.style_table_cell",
                presentation_id=presentation_id,
                table_id=table_id,
                row_index=row_index,
                column_index=column_index,
                formatting=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.style_table_cell",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def insert_text_in_table_cell(
        self,
        presentation_id: str,
        table_id: str,
        row_index: int,
        column_index: int,
        text: str,
    ) -> dict[str, Any]:
        """Insert text into a table cell.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            row_index: Row index of the cell.
            column_index: Column index of the cell.
            text: Text to insert.
        """
        try:
            request = {
                "insertText": {
                    "objectId": table_id,
                    "cellLocation": {
                        "rowIndex": row_index,
                        "columnIndex": column_index,
                    },
                    "insertionIndex": 0,
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
                operation="slides.insert_text_in_table_cell",
                presentation_id=presentation_id,
                table_id=table_id,
                row_index=row_index,
                column_index=column_index,
                text_length=len(text),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_text_in_table_cell",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

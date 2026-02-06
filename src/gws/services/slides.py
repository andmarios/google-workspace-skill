"""Google Slides service operations."""

import uuid
from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
import json
from gws.output import output_success, output_error, output_external_content
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
            presentation = self.execute(
                self.service.presentations()
                .get(presentationId=presentation_id)
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
                page = self.execute(
                    self.service.presentations()
                    .pages()
                    .get(presentationId=presentation_id, pageObjectId=page_object_id)
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

                output_external_content(
                    operation="slides.read",
                    source_type="slide",
                    source_id=presentation_id,
                    content_fields={
                        "elements": json.dumps(elements),
                    },
                    presentation_id=presentation_id,
                    page_object_id=page_object_id,
                    element_count=len(elements),
                )
                return page
            else:
                presentation = self.execute(
                    self.service.presentations()
                    .get(presentationId=presentation_id)
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

                output_external_content(
                    operation="slides.read",
                    source_type="slide",
                    source_id=presentation_id,
                    content_fields={
                        "slides": json.dumps(slides_info),
                    },
                    presentation_id=presentation_id,
                    title=presentation.get("title", ""),
                    slide_count=len(slides_info),
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
            presentation = self.execute(
                self.service.presentations()
                .create(body={"title": title})
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
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

    # ===== Phase 6: Slides Enhancements =====

    def set_slide_background(
        self,
        presentation_id: str,
        slide_id: str,
        color: str | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        """Set slide background to a solid color or image.

        Args:
            presentation_id: The presentation ID.
            slide_id: The slide object ID.
            color: Background color (hex, e.g., "#FFFFFF").
            image_url: Background image URL (publicly accessible).
        """
        try:
            if not color and not image_url:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.set_slide_background",
                    message="Either color or image_url must be provided",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            page_properties: dict[str, Any] = {}
            fields = []

            if color:
                from gws.utils.colors import parse_hex_color
                rgb = parse_hex_color(color)
                page_properties["pageBackgroundFill"] = {
                    "solidFill": {"color": {"rgbColor": rgb}}
                }
                fields.append("pageBackgroundFill")
            elif image_url:
                page_properties["pageBackgroundFill"] = {
                    "stretchedPictureFill": {"contentUrl": image_url}
                }
                fields.append("pageBackgroundFill")

            request = {
                "updatePageProperties": {
                    "objectId": slide_id,
                    "pageProperties": page_properties,
                    "fields": ",".join(fields),
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.set_slide_background",
                presentation_id=presentation_id,
                slide_id=slide_id,
                background_type="color" if color else "image",
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.set_slide_background",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_bullets(
        self,
        presentation_id: str,
        object_id: str,
        bullet_preset: str = "BULLET_DISC_CIRCLE_SQUARE",
        start_index: int | None = None,
        end_index: int | None = None,
    ) -> dict[str, Any]:
        """Create bullet list formatting for text.

        Args:
            presentation_id: The presentation ID.
            object_id: The shape/text box object ID.
            bullet_preset: Bullet style preset. Options:
                BULLET_DISC_CIRCLE_SQUARE, BULLET_DIAMONDX_ARROW3D_SQUARE,
                BULLET_CHECKBOX, BULLET_ARROW_DIAMOND_DISC,
                BULLET_STAR_CIRCLE_SQUARE, BULLET_ARROW3D_CIRCLE_SQUARE,
                BULLET_LEFTTRIANGLE_DIAMOND_DISC, NUMBERED_DIGIT_ALPHA_ROMAN,
                NUMBERED_DIGIT_ALPHA_ROMAN_PARENS, NUMBERED_DIGIT_NESTED,
                NUMBERED_UPPERALPHA_ALPHA_ROMAN, NUMBERED_UPPERROMAN_UPPERALPHA_DIGIT,
                NUMBERED_ZERODIGIT_ALPHA_ROMAN
            start_index: Start character index (0-based). If None, applies to all.
            end_index: End character index (exclusive). If None, applies to all.
        """
        try:
            if start_index is not None and end_index is not None:
                text_range = {
                    "type": "FIXED_RANGE",
                    "startIndex": start_index,
                    "endIndex": end_index,
                }
            else:
                text_range = {"type": "ALL"}

            request = {
                "createParagraphBullets": {
                    "objectId": object_id,
                    "textRange": text_range,
                    "bulletPreset": bullet_preset,
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.create_bullets",
                presentation_id=presentation_id,
                object_id=object_id,
                bullet_preset=bullet_preset,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.create_bullets",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def remove_bullets(
        self,
        presentation_id: str,
        object_id: str,
        start_index: int | None = None,
        end_index: int | None = None,
    ) -> dict[str, Any]:
        """Remove bullet list formatting from text.

        Args:
            presentation_id: The presentation ID.
            object_id: The shape/text box object ID.
            start_index: Start character index (0-based). If None, applies to all.
            end_index: End character index (exclusive). If None, applies to all.
        """
        try:
            if start_index is not None and end_index is not None:
                text_range = {
                    "type": "FIXED_RANGE",
                    "startIndex": start_index,
                    "endIndex": end_index,
                }
            else:
                text_range = {"type": "ALL"}

            request = {
                "deleteParagraphBullets": {
                    "objectId": object_id,
                    "textRange": text_range,
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.remove_bullets",
                presentation_id=presentation_id,
                object_id=object_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.remove_bullets",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def style_table_borders(
        self,
        presentation_id: str,
        table_id: str,
        row_index: int,
        column_index: int,
        row_span: int = 1,
        column_span: int = 1,
        color: str = "#000000",
        weight: float = 1.0,
        dash_style: str = "SOLID",
        border_position: str = "ALL",
    ) -> dict[str, Any]:
        """Style table cell borders.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            row_index: Starting row index.
            column_index: Starting column index.
            row_span: Number of rows to style.
            column_span: Number of columns to style.
            color: Border color (hex, e.g., "#000000").
            weight: Border weight in points.
            dash_style: Dash style (SOLID, DOT, DASH, DASH_DOT, LONG_DASH).
            border_position: Which borders to style (ALL, INNER, OUTER,
                INNER_HORIZONTAL, INNER_VERTICAL, LEFT, RIGHT, TOP, BOTTOM).
        """
        try:
            from gws.utils.colors import parse_hex_color

            valid_positions = {
                "ALL", "INNER", "OUTER", "INNER_HORIZONTAL", "INNER_VERTICAL",
                "LEFT", "RIGHT", "TOP", "BOTTOM"
            }
            if border_position.upper() not in valid_positions:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.style_table_borders",
                    message=f"border_position must be one of: {valid_positions}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            valid_styles = {"SOLID", "DOT", "DASH", "DASH_DOT", "LONG_DASH"}
            if dash_style.upper() not in valid_styles:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.style_table_borders",
                    message=f"dash_style must be one of: {valid_styles}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            rgb = parse_hex_color(color)

            request = {
                "updateTableBorderProperties": {
                    "objectId": table_id,
                    "tableRange": {
                        "location": {
                            "rowIndex": row_index,
                            "columnIndex": column_index,
                        },
                        "rowSpan": row_span,
                        "columnSpan": column_span,
                    },
                    "borderPosition": border_position.upper(),
                    "tableBorderProperties": {
                        "tableBorderFill": {
                            "solidFill": {"color": {"rgbColor": rgb}}
                        },
                        "weight": {"magnitude": weight, "unit": "PT"},
                        "dashStyle": dash_style.upper(),
                    },
                    "fields": "tableBorderFill,weight,dashStyle",
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.style_table_borders",
                presentation_id=presentation_id,
                table_id=table_id,
                border_position=border_position.upper(),
                row_index=row_index,
                column_index=column_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.style_table_borders",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def merge_table_cells(
        self,
        presentation_id: str,
        table_id: str,
        row_index: int,
        column_index: int,
        row_span: int,
        column_span: int,
    ) -> dict[str, Any]:
        """Merge table cells.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            row_index: Starting row index.
            column_index: Starting column index.
            row_span: Number of rows to merge.
            column_span: Number of columns to merge.
        """
        try:
            request = {
                "mergeTableCells": {
                    "objectId": table_id,
                    "tableRange": {
                        "location": {
                            "rowIndex": row_index,
                            "columnIndex": column_index,
                        },
                        "rowSpan": row_span,
                        "columnSpan": column_span,
                    },
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.merge_table_cells",
                presentation_id=presentation_id,
                table_id=table_id,
                row_index=row_index,
                column_index=column_index,
                row_span=row_span,
                column_span=column_span,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.merge_table_cells",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def unmerge_table_cells(
        self,
        presentation_id: str,
        table_id: str,
        row_index: int,
        column_index: int,
        row_span: int,
        column_span: int,
    ) -> dict[str, Any]:
        """Unmerge table cells.

        Args:
            presentation_id: The presentation ID.
            table_id: The table object ID.
            row_index: Starting row index.
            column_index: Starting column index.
            row_span: Number of rows in merged region.
            column_span: Number of columns in merged region.
        """
        try:
            request = {
                "unmergeTableCells": {
                    "objectId": table_id,
                    "tableRange": {
                        "location": {
                            "rowIndex": row_index,
                            "columnIndex": column_index,
                        },
                        "rowSpan": row_span,
                        "columnSpan": column_span,
                    },
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.unmerge_table_cells",
                presentation_id=presentation_id,
                table_id=table_id,
                row_index=row_index,
                column_index=column_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.unmerge_table_cells",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_line(
        self,
        presentation_id: str,
        page_object_id: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        line_category: str = "STRAIGHT",
        color: str = "#000000",
        weight: float = 1.0,
        dash_style: str = "SOLID",
        start_arrow: str | None = None,
        end_arrow: str | None = None,
    ) -> dict[str, Any]:
        """Create a line or arrow on a slide.

        Args:
            presentation_id: The presentation ID.
            page_object_id: The slide/page object ID.
            start_x: Starting X position in points.
            start_y: Starting Y position in points.
            end_x: Ending X position in points.
            end_y: Ending Y position in points.
            line_category: Line category (STRAIGHT, BENT, CURVED).
            color: Line color (hex, e.g., "#000000").
            weight: Line weight in points.
            dash_style: Dash style (SOLID, DOT, DASH, DASH_DOT, LONG_DASH).
            start_arrow: Start arrow type (NONE, STEALTH_ARROW, FILL_ARROW,
                FILL_CIRCLE, FILL_SQUARE, FILL_DIAMOND, OPEN_ARROW,
                OPEN_CIRCLE, OPEN_SQUARE, OPEN_DIAMOND).
            end_arrow: End arrow type (same options as start_arrow).
        """
        try:
            from gws.utils.colors import parse_hex_color

            line_id = self._generate_object_id()

            # Calculate width and height from start/end points
            width = abs(end_x - start_x) or 1  # Minimum 1pt
            height = abs(end_y - start_y) or 1

            valid_categories = {"STRAIGHT", "BENT", "CURVED"}
            if line_category.upper() not in valid_categories:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.create_line",
                    message=f"line_category must be one of: {valid_categories}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request = {
                "createLine": {
                    "objectId": line_id,
                    "lineCategory": line_category.upper(),
                    "elementProperties": {
                        "pageObjectId": page_object_id,
                        "size": {
                            "width": {"magnitude": width, "unit": "PT"},
                            "height": {"magnitude": height, "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1 if end_x >= start_x else -1,
                            "scaleY": 1 if end_y >= start_y else -1,
                            "translateX": min(start_x, end_x),
                            "translateY": min(start_y, end_y),
                            "unit": "PT",
                        },
                    },
                }
            }

            # Create the line first
            requests = [request]

            # Then update line properties
            rgb = parse_hex_color(color)
            line_properties: dict[str, Any] = {
                "lineFill": {"solidFill": {"color": {"rgbColor": rgb}}},
                "weight": {"magnitude": weight, "unit": "PT"},
                "dashStyle": dash_style.upper(),
            }
            fields = ["lineFill", "weight", "dashStyle"]

            if start_arrow:
                line_properties["startArrow"] = start_arrow.upper()
                fields.append("startArrow")
            if end_arrow:
                line_properties["endArrow"] = end_arrow.upper()
                fields.append("endArrow")

            update_request = {
                "updateLineProperties": {
                    "objectId": line_id,
                    "lineProperties": line_properties,
                    "fields": ",".join(fields),
                }
            }
            requests.append(update_request)

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
            )

            output_success(
                operation="slides.create_line",
                presentation_id=presentation_id,
                page_object_id=page_object_id,
                line_id=line_id,
                line_category=line_category.upper(),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.create_line",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def reorder_slides(
        self,
        presentation_id: str,
        slide_ids: list[str],
        insertion_index: int,
    ) -> dict[str, Any]:
        """Move slides to a new position.

        Args:
            presentation_id: The presentation ID.
            slide_ids: List of slide object IDs to move.
            insertion_index: Target index where slides will be moved (0-based).
        """
        try:
            request = {
                "updateSlidesPosition": {
                    "slideObjectIds": slide_ids,
                    "insertionIndex": insertion_index,
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.reorder_slides",
                presentation_id=presentation_id,
                slide_ids=slide_ids,
                insertion_index=insertion_index,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.reorder_slides",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # SPEAKER NOTES
    # =========================================================================

    def get_speaker_notes(
        self,
        presentation_id: str,
        slide_id: str,
    ) -> dict[str, Any]:
        """Get speaker notes for a slide.

        Args:
            presentation_id: The presentation ID.
            slide_id: The slide object ID.
        """
        try:
            presentation = self.execute(
                self.service.presentations()
                .get(presentationId=presentation_id)
            )

            notes_text = ""
            notes_page_id = None

            for slide in presentation.get("slides", []):
                if slide.get("objectId") == slide_id:
                    notes_page = slide.get("slideProperties", {}).get("notesPage", {})
                    notes_page_id = notes_page.get("objectId")

                    # Find the notes shape within the notes page
                    for element in notes_page.get("pageElements", []):
                        shape = element.get("shape", {})
                        if shape.get("shapeType") == "TEXT_BOX":
                            placeholder = shape.get("placeholder", {})
                            if placeholder.get("type") == "BODY":
                                text_content = shape.get("text", {})
                                for text_element in text_content.get("textElements", []):
                                    if "textRun" in text_element:
                                        notes_text += text_element["textRun"].get("content", "")
                    break

            output_success(
                operation="slides.get_speaker_notes",
                presentation_id=presentation_id,
                slide_id=slide_id,
                notes_page_id=notes_page_id,
                notes_text=notes_text.strip(),
            )
            return {"notes_text": notes_text.strip(), "notes_page_id": notes_page_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.get_speaker_notes",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_speaker_notes(
        self,
        presentation_id: str,
        slide_id: str,
        notes_text: str,
    ) -> dict[str, Any]:
        """Set speaker notes for a slide.

        Args:
            presentation_id: The presentation ID.
            slide_id: The slide object ID.
            notes_text: The speaker notes text content.
        """
        try:
            # First, get the presentation to find the notes shape ID
            presentation = self.execute(
                self.service.presentations()
                .get(presentationId=presentation_id)
            )

            notes_shape_id = None

            for slide in presentation.get("slides", []):
                if slide.get("objectId") == slide_id:
                    notes_page = slide.get("slideProperties", {}).get("notesPage", {})

                    for element in notes_page.get("pageElements", []):
                        shape = element.get("shape", {})
                        if shape.get("shapeType") == "TEXT_BOX":
                            placeholder = shape.get("placeholder", {})
                            if placeholder.get("type") == "BODY":
                                notes_shape_id = element.get("objectId")
                                break
                    break

            if not notes_shape_id:
                output_error(
                    error_code="NOT_FOUND",
                    operation="slides.set_speaker_notes",
                    message=f"Speaker notes shape not found for slide {slide_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            # Build requests: only delete existing text if notes are non-empty
            requests: list[dict[str, Any]] = []

            # Check if notes shape has existing text content
            for slide in presentation.get("slides", []):
                if slide.get("objectId") == slide_id:
                    notes_page = slide.get("slideProperties", {}).get("notesPage", {})
                    for element in notes_page.get("pageElements", []):
                        if element.get("objectId") == notes_shape_id:
                            text_content = element.get("shape", {}).get("text", {})
                            text_elements = text_content.get("textElements", [])
                            has_text = any(
                                te.get("textRun", {}).get("content", "").strip()
                                for te in text_elements
                            )
                            if has_text:
                                requests.append({
                                    "deleteText": {
                                        "objectId": notes_shape_id,
                                        "textRange": {"type": "ALL"},
                                    }
                                })
                            break
                    break

            requests.append({
                "insertText": {
                    "objectId": notes_shape_id,
                    "insertionIndex": 0,
                    "text": notes_text,
                }
            })

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
            )

            output_success(
                operation="slides.set_speaker_notes",
                presentation_id=presentation_id,
                slide_id=slide_id,
                notes_shape_id=notes_shape_id,
                text_length=len(notes_text),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.set_speaker_notes",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # VIDEO INSERTION
    # =========================================================================

    def insert_video(
        self,
        presentation_id: str,
        page_object_id: str,
        video_url: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        """Insert a video on a slide.

        Args:
            presentation_id: The presentation ID.
            page_object_id: The slide/page object ID.
            video_url: YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID).
            x: X position in points.
            y: Y position in points.
            width: Width in points.
            height: Height in points.
        """
        try:
            import re

            # Extract YouTube video ID from URL
            video_id = None
            patterns = [
                r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            ]
            for pattern in patterns:
                match = re.search(pattern, video_url)
                if match:
                    video_id = match.group(1)
                    break

            if not video_id:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.insert_video",
                    message="Invalid YouTube URL. Please provide a valid YouTube video URL.",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            object_id = self._generate_object_id()

            request = {
                "createVideo": {
                    "objectId": object_id,
                    "source": "YOUTUBE",
                    "id": video_id,
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

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.insert_video",
                presentation_id=presentation_id,
                page_object_id=page_object_id,
                video_object_id=object_id,
                video_id=video_id,
                position={"x": x, "y": y, "width": width, "height": height},
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_video",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_video_properties(
        self,
        presentation_id: str,
        video_object_id: str,
        autoplay: bool | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        mute: bool | None = None,
    ) -> dict[str, Any]:
        """Update video playback properties.

        Args:
            presentation_id: The presentation ID.
            video_object_id: The video object ID.
            autoplay: Whether the video autoplays when presenting.
            start_time: Start time in seconds.
            end_time: End time in seconds.
            mute: Whether the video is muted.
        """
        try:
            video_properties: dict[str, Any] = {}
            fields = []

            if autoplay is not None:
                video_properties["autoPlay"] = autoplay
                fields.append("autoPlay")

            if start_time is not None:
                video_properties["start"] = start_time
                fields.append("start")

            if end_time is not None:
                video_properties["end"] = end_time
                fields.append("end")

            if mute is not None:
                video_properties["mute"] = mute
                fields.append("mute")

            if not fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="slides.update_video_properties",
                    message="At least one video property required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request = {
                "updateVideoProperties": {
                    "objectId": video_object_id,
                    "videoProperties": video_properties,
                    "fields": ",".join(fields),
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.update_video_properties",
                presentation_id=presentation_id,
                video_object_id=video_object_id,
                properties_updated=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.update_video_properties",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # ELEMENT TRANSFORMS
    # =========================================================================

    def transform_element(
        self,
        presentation_id: str,
        object_id: str,
        scale_x: float | None = None,
        scale_y: float | None = None,
        translate_x: float | None = None,
        translate_y: float | None = None,
        rotate: float | None = None,
        apply_mode: str = "RELATIVE",
    ) -> dict[str, Any]:
        """Transform a page element (scale, translate, rotate).

        Args:
            presentation_id: The presentation ID.
            object_id: The element object ID.
            scale_x: Horizontal scale factor.
            scale_y: Vertical scale factor.
            translate_x: Horizontal translation in EMU.
            translate_y: Vertical translation in EMU.
            rotate: Rotation angle in degrees.
            apply_mode: 'RELATIVE' (add to current) or 'ABSOLUTE' (replace).
        """
        try:
            # Build transform matrix — always set scaleX/scaleY to ensure
            # the matrix is invertible (determinant != 0)
            transform: dict[str, Any] = {
                "unit": "EMU",
                "scaleX": scale_x if scale_x is not None else 1.0,
                "scaleY": scale_y if scale_y is not None else 1.0,
            }
            if translate_x is not None:
                transform["translateX"] = translate_x
            if translate_y is not None:
                transform["translateY"] = translate_y

            # Rotation requires converting degrees to affine transform
            # For simplicity, we handle rotation as shearX/shearY if provided
            if rotate is not None:
                import math
                rad = math.radians(rotate)
                cos_r = math.cos(rad)
                sin_r = math.sin(rad)
                transform["scaleX"] = transform.get("scaleX", 1.0) * cos_r
                transform["scaleY"] = transform.get("scaleY", 1.0) * cos_r
                transform["shearX"] = -sin_r
                transform["shearY"] = sin_r

            if len(transform) == 1:  # Only 'unit'
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="slides.transform_element",
                    message="At least one transform parameter required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request = {
                "updatePageElementTransform": {
                    "objectId": object_id,
                    "transform": transform,
                    "applyMode": apply_mode,
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.transform_element",
                presentation_id=presentation_id,
                object_id=object_id,
                apply_mode=apply_mode,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.transform_element",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # IMAGE PROPERTIES
    # =========================================================================

    def update_image_properties(
        self,
        presentation_id: str,
        object_id: str,
        transparency: float | None = None,
        outline_color: str | None = None,
        outline_weight: float | None = None,
    ) -> dict[str, Any]:
        """Update image properties.

        Args:
            presentation_id: The presentation ID.
            object_id: The image element object ID.
            transparency: Image transparency (0.0 = opaque, 1.0 = fully transparent).
            outline_color: Outline color (hex, e.g., '#000000').
            outline_weight: Outline weight in points.
        """
        try:
            from gws.utils.colors import parse_hex_color

            image_properties: dict[str, Any] = {}
            fields = []

            if transparency is not None:
                image_properties["transparency"] = transparency
                fields.append("transparency")

            if outline_color is not None or outline_weight is not None:
                outline: dict[str, Any] = {}
                if outline_color:
                    rgb = parse_hex_color(outline_color)
                    outline["outlineFill"] = {
                        "solidFill": {
                            "color": {"rgbColor": rgb}
                        }
                    }
                    fields.append("outline.outlineFill.solidFill.color")
                if outline_weight is not None:
                    outline["weight"] = {"magnitude": outline_weight, "unit": "PT"}
                    fields.append("outline.weight")
                image_properties["outline"] = outline

            if not fields:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="slides.update_image_properties",
                    message="At least one image property required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request = {
                "updateImageProperties": {
                    "objectId": object_id,
                    "imageProperties": image_properties,
                    "fields": ",".join(fields),
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.update_image_properties",
                presentation_id=presentation_id,
                object_id=object_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.update_image_properties",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # GROUPING
    # =========================================================================

    def group_objects(
        self,
        presentation_id: str,
        children_object_ids: list[str],
        group_object_id: str | None = None,
    ) -> dict[str, Any]:
        """Group multiple page elements.

        Args:
            presentation_id: The presentation ID.
            children_object_ids: List of object IDs to group.
            group_object_id: Optional ID for the new group (auto-generated if not provided).
        """
        import uuid

        try:
            request: dict[str, Any] = {
                "groupObjects": {
                    "groupObjectId": group_object_id or f"group_{uuid.uuid4().hex[:8]}",
                    "childrenObjectIds": children_object_ids,
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.group_objects",
                presentation_id=presentation_id,
                group_object_id=request["groupObjects"]["groupObjectId"],
                children_count=len(children_object_ids),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.group_objects",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def ungroup_objects(
        self,
        presentation_id: str,
        group_object_ids: list[str],
    ) -> dict[str, Any]:
        """Ungroup one or more groups.

        Args:
            presentation_id: The presentation ID.
            group_object_ids: List of group object IDs to ungroup.
        """
        try:
            requests = [
                {"ungroupObjects": {"objectIds": group_object_ids}}
            ]

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
            )

            output_success(
                operation="slides.ungroup_objects",
                presentation_id=presentation_id,
                ungrouped_count=len(group_object_ids),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.ungroup_objects",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # SHAPE REPLACEMENT
    # =========================================================================

    def replace_shapes_with_image(
        self,
        presentation_id: str,
        contains_text: str,
        image_url: str,
        image_replace_method: str = "CENTER_INSIDE",
        page_object_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Replace all shapes containing specific text with an image.

        Args:
            presentation_id: The presentation ID.
            contains_text: Text to search for in shapes.
            image_url: URL of the image to insert.
            image_replace_method: How to replace ('CENTER_INSIDE' or 'CENTER_CROP').
            page_object_ids: Optional list of page IDs to limit the search.
        """
        try:
            request: dict[str, Any] = {
                "replaceAllShapesWithImage": {
                    "containsText": {
                        "text": contains_text,
                        "matchCase": False,
                    },
                    "imageUrl": image_url,
                    "imageReplaceMethod": image_replace_method,
                }
            }

            if page_object_ids:
                request["replaceAllShapesWithImage"]["pageObjectIds"] = page_object_ids

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            # Get replacement count from response
            replies = result.get("replies", [{}])
            occurrences = replies[0].get("replaceAllShapesWithImage", {}).get("occurrencesChanged", 0)

            output_success(
                operation="slides.replace_shapes_with_image",
                presentation_id=presentation_id,
                contains_text=contains_text,
                occurrences_replaced=occurrences,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.replace_shapes_with_image",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # ACCESSIBILITY
    # =========================================================================

    def set_alt_text(
        self,
        presentation_id: str,
        object_id: str,
        title: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Set alt text (accessibility text) on a page element.

        Args:
            presentation_id: The presentation ID.
            object_id: The element object ID.
            title: Brief title for the element.
            description: Detailed description for screen readers.
        """
        try:
            alt_text: dict[str, Any] = {}
            fields = []

            if title is not None:
                alt_text["title"] = title
                fields.append("title")
            if description is not None:
                alt_text["description"] = description
                fields.append("description")

            if not fields:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="slides.set_alt_text",
                    message="At least one of title or description required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            request = {
                "updatePageElementAltText": {
                    "objectId": object_id,
                    **alt_text,
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.set_alt_text",
                presentation_id=presentation_id,
                object_id=object_id,
                updated_fields=fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.set_alt_text",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # EMBEDDED CHARTS
    # =========================================================================

    def insert_sheets_chart(
        self,
        presentation_id: str,
        page_object_id: str,
        spreadsheet_id: str,
        chart_id: int,
        x: float,
        y: float,
        width: float,
        height: float,
        linking_mode: str = "LINKED",
    ) -> dict[str, Any]:
        """Insert a chart from Google Sheets.

        Args:
            presentation_id: The presentation ID.
            page_object_id: The page (slide) to insert on.
            spreadsheet_id: The source spreadsheet ID.
            chart_id: The chart ID in the spreadsheet.
            x: X position in points from top-left.
            y: Y position in points from top-left.
            width: Width in points.
            height: Height in points.
            linking_mode: 'LINKED' (updates with source) or 'NOT_LINKED_IMAGE' (static).
        """
        import uuid

        try:
            element_id = f"chart_{uuid.uuid4().hex[:8]}"

            request = {
                "createSheetsChart": {
                    "objectId": element_id,
                    "spreadsheetId": spreadsheet_id,
                    "chartId": chart_id,
                    "linkingMode": linking_mode,
                    "elementProperties": {
                        "pageObjectId": page_object_id,
                        "size": {
                            "width": {"magnitude": width, "unit": "PT"},
                            "height": {"magnitude": height, "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": x * 12700,  # PT to EMU
                            "translateY": y * 12700,  # PT to EMU
                            "unit": "EMU",
                        },
                    },
                }
            }

            result = self.execute(
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": [request]}
                )
            )

            output_success(
                operation="slides.insert_sheets_chart",
                presentation_id=presentation_id,
                page_object_id=page_object_id,
                element_id=element_id,
                spreadsheet_id=spreadsheet_id,
                chart_id=chart_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="slides.insert_sheets_chart",
                message=f"Google Slides API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

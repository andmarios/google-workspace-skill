"""Document conversion service (Markdown to Google Workspace formats)."""

import io
import re
from pathlib import Path
from typing import Any

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode


class ConvertService(BaseService):
    """Document conversion operations."""

    SERVICE_NAME = "drive"
    VERSION = "v3"

    def md_to_doc(
        self,
        input_path: str,
        title: str | None = None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Convert Markdown file to Google Doc.

        Uses Google's native Markdown import (added July 2024).
        """
        try:
            path = Path(input_path)
            if not path.exists():
                output_error(
                    error_code="FILE_NOT_FOUND",
                    operation="convert.md_to_doc",
                    message=f"File not found: {input_path}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            doc_title = title or path.stem

            # Upload markdown file and convert to Google Doc
            file_metadata = {
                "name": doc_title,
                "mimeType": "application/vnd.google-apps.document",
            }

            if folder_id:
                file_metadata["parents"] = [folder_id]

            media = MediaFileUpload(
                str(path),
                mimetype="text/markdown",
                resumable=True,
            )

            file = (
                self.drive_service.files()
                .create(body=file_metadata, media_body=media, fields="id,name,webViewLink")
                .execute()
            )

            output_success(
                operation="convert.md_to_doc",
                document_id=file["id"],
                title=file["name"],
                web_view_link=file["webViewLink"],
                source_file=str(path),
            )
            return file
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="convert.md_to_doc",
                message=f"Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def md_to_pdf(
        self,
        input_path: str,
        output_path: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Convert Markdown to PDF via Google Docs.

        1. Upload Markdown as Google Doc
        2. Export as PDF
        3. Delete the temporary Doc
        """
        try:
            # First create the doc
            path = Path(input_path)
            if not path.exists():
                output_error(
                    error_code="FILE_NOT_FOUND",
                    operation="convert.md_to_pdf",
                    message=f"File not found: {input_path}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            doc_title = title or f"_temp_{path.stem}"

            # Upload as Doc
            file_metadata = {
                "name": doc_title,
                "mimeType": "application/vnd.google-apps.document",
            }

            media = MediaFileUpload(
                str(path),
                mimetype="text/markdown",
                resumable=True,
            )

            file = (
                self.drive_service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )

            doc_id = file["id"]

            try:
                # Export as PDF
                request = self.drive_service.files().export_media(
                    fileId=doc_id,
                    mimeType="application/pdf",
                )

                output_file = Path(output_path)
                fh = io.FileIO(str(output_file), "wb")
                downloader = MediaIoBaseDownload(fh, request)

                done = False
                while not done:
                    _, done = downloader.next_chunk()

                fh.close()

                output_success(
                    operation="convert.md_to_pdf",
                    output_path=str(output_file),
                    source_file=str(path),
                    file_size=output_file.stat().st_size,
                )
            finally:
                # Delete the temporary doc
                self.drive_service.files().delete(fileId=doc_id).execute()

            return {"output_path": str(output_file)}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="convert.md_to_pdf",
                message=f"Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def md_to_slides(
        self,
        input_path: str,
        title: str | None = None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Convert Markdown to Google Slides.

        Parsing rules:
        - # Heading → New slide with title
        - ## Subheading → Subtitle
        - Bullet lists → Slide bullet points
        - --- → Slide break
        """
        try:
            path = Path(input_path)
            if not path.exists():
                output_error(
                    error_code="FILE_NOT_FOUND",
                    operation="convert.md_to_slides",
                    message=f"File not found: {input_path}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            pres_title = title or path.stem

            # Read markdown content
            content = path.read_text(encoding="utf-8")
            slides_data = self._parse_markdown_to_slides(content)

            # Create presentation using Slides API
            from googleapiclient.discovery import build
            from gws.auth.oauth import AuthManager

            auth_manager = AuthManager()
            credentials = auth_manager.get_credentials()
            slides_service = build("slides", "v1", credentials=credentials)

            # Create empty presentation
            presentation = (
                slides_service.presentations()
                .create(body={"title": pres_title})
                .execute()
            )
            presentation_id = presentation["presentationId"]

            try:
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
                        fields="id",
                    ).execute()

                # Build slides from parsed content
                requests = self._build_slide_requests(slides_data)

                if requests:
                    slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={"requests": requests},
                    ).execute()

                output_success(
                    operation="convert.md_to_slides",
                    presentation_id=presentation_id,
                    title=pres_title,
                    slide_count=len(slides_data),
                    web_view_link=f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                    source_file=str(path),
                )
                return {"presentation_id": presentation_id}
            except Exception as e:
                # Clean up on error
                self.drive_service.files().delete(fileId=presentation_id).execute()
                raise e

        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="convert.md_to_slides",
                message=f"API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def _parse_markdown_to_slides(self, content: str) -> list[dict]:
        """Parse markdown into slide structure."""
        slides = []
        current_slide: dict[str, Any] = {"title": "", "subtitle": "", "bullets": []}

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            # Slide break
            if line == "---":
                if current_slide["title"] or current_slide["bullets"]:
                    slides.append(current_slide)
                    current_slide = {"title": "", "subtitle": "", "bullets": []}
                i += 1
                continue

            # H1 = new slide title
            if line.startswith("# "):
                if current_slide["title"] or current_slide["bullets"]:
                    slides.append(current_slide)
                    current_slide = {"title": "", "subtitle": "", "bullets": []}
                current_slide["title"] = line[2:].strip()
                i += 1
                continue

            # H2 = subtitle
            if line.startswith("## "):
                current_slide["subtitle"] = line[3:].strip()
                i += 1
                continue

            # Bullet points
            if line.startswith("- ") or line.startswith("* "):
                current_slide["bullets"].append(line[2:].strip())
                i += 1
                continue

            # Numbered list
            match = re.match(r"^\d+\.\s+(.+)$", line)
            if match:
                current_slide["bullets"].append(match.group(1).strip())
                i += 1
                continue

            i += 1

        # Don't forget the last slide
        if current_slide["title"] or current_slide["bullets"]:
            slides.append(current_slide)

        return slides

    def _build_slide_requests(self, slides_data: list[dict]) -> list[dict]:
        """Build Slides API requests from parsed content."""
        import uuid
        requests = []

        for i, slide in enumerate(slides_data):
            slide_id = f"slide_{uuid.uuid4().hex[:8]}"

            # Create slide (skip first one since presentation comes with one)
            if i > 0:
                requests.append({
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {"predefinedLayout": "BLANK"},
                    }
                })
            else:
                # Use the first slide (object id "p")
                slide_id = "p"

            # Add title text box
            if slide["title"]:
                title_id = f"title_{uuid.uuid4().hex[:8]}"
                requests.extend([
                    {
                        "createShape": {
                            "objectId": title_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": slide_id,
                                "size": {
                                    "width": {"magnitude": 600, "unit": "PT"},
                                    "height": {"magnitude": 50, "unit": "PT"},
                                },
                                "transform": {
                                    "scaleX": 1, "scaleY": 1,
                                    "translateX": 36, "translateY": 30,
                                    "unit": "PT",
                                },
                            },
                        }
                    },
                    {
                        "insertText": {
                            "objectId": title_id,
                            "insertionIndex": 0,
                            "text": slide["title"],
                        }
                    },
                    {
                        "updateTextStyle": {
                            "objectId": title_id,
                            "style": {
                                "bold": True,
                                "fontSize": {"magnitude": 32, "unit": "PT"},
                            },
                            "textRange": {"type": "ALL"},
                            "fields": "bold,fontSize",
                        }
                    },
                ])

            # Add subtitle if present
            if slide.get("subtitle"):
                subtitle_id = f"subtitle_{uuid.uuid4().hex[:8]}"
                requests.extend([
                    {
                        "createShape": {
                            "objectId": subtitle_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": slide_id,
                                "size": {
                                    "width": {"magnitude": 600, "unit": "PT"},
                                    "height": {"magnitude": 30, "unit": "PT"},
                                },
                                "transform": {
                                    "scaleX": 1, "scaleY": 1,
                                    "translateX": 36, "translateY": 85,
                                    "unit": "PT",
                                },
                            },
                        }
                    },
                    {
                        "insertText": {
                            "objectId": subtitle_id,
                            "insertionIndex": 0,
                            "text": slide["subtitle"],
                        }
                    },
                    {
                        "updateTextStyle": {
                            "objectId": subtitle_id,
                            "style": {
                                "fontSize": {"magnitude": 20, "unit": "PT"},
                            },
                            "textRange": {"type": "ALL"},
                            "fields": "fontSize",
                        }
                    },
                ])

            # Add bullets
            if slide["bullets"]:
                body_id = f"body_{uuid.uuid4().hex[:8]}"
                bullet_text = "\n".join(f"• {bullet}" for bullet in slide["bullets"])
                y_offset = 130 if slide.get("subtitle") else 100

                requests.extend([
                    {
                        "createShape": {
                            "objectId": body_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": slide_id,
                                "size": {
                                    "width": {"magnitude": 600, "unit": "PT"},
                                    "height": {"magnitude": 300, "unit": "PT"},
                                },
                                "transform": {
                                    "scaleX": 1, "scaleY": 1,
                                    "translateX": 36, "translateY": y_offset,
                                    "unit": "PT",
                                },
                            },
                        }
                    },
                    {
                        "insertText": {
                            "objectId": body_id,
                            "insertionIndex": 0,
                            "text": bullet_text,
                        }
                    },
                    {
                        "updateTextStyle": {
                            "objectId": body_id,
                            "style": {
                                "fontSize": {"magnitude": 18, "unit": "PT"},
                            },
                            "textRange": {"type": "ALL"},
                            "fields": "fontSize",
                        }
                    },
                ])

        return requests

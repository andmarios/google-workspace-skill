"""Document conversion service (Markdown to Google Workspace formats)."""

import io
import re
import tempfile
import shutil
from pathlib import Path
from typing import Any

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode
from gws.utils.diagrams import render_diagrams_in_markdown, find_diagram_blocks


class ConvertService(BaseService):
    """Document conversion operations."""

    SERVICE_NAME = "drive"
    VERSION = "v3"

    def _create_temp_folder(self) -> str:
        """Create a temporary folder in Drive for diagram images.

        Returns:
            The folder ID
        """
        import uuid
        folder_name = f"_gws_temp_{uuid.uuid4().hex[:8]}"
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = self.execute(
            self.drive_service.files().create(body=file_metadata, fields="id")
        )
        return folder["id"]

    def _delete_temp_folder(self, folder_id: str) -> None:
        """Delete a temporary folder and all its contents.

        Args:
            folder_id: The folder ID to delete
        """
        try:
            self.execute(self.drive_service.files().delete(fileId=folder_id))
        except Exception:
            pass  # Ignore cleanup errors

    def _set_pageless_mode(self, document_id: str) -> None:
        """Set a document to pageless mode.

        Args:
            document_id: The Google Doc ID
        """
        from googleapiclient.discovery import build
        from gws.auth.oauth import AuthManager

        auth_manager = AuthManager()
        credentials = auth_manager.get_credentials()
        docs_service = build("docs", "v1", credentials=credentials)

        requests = [{
            "updateDocumentStyle": {
                "documentStyle": {
                    "documentFormat": {
                        "documentMode": "PAGELESS",
                    }
                },
                "fields": "documentFormat",
            }
        }]

        self.execute(
            docs_service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            )
        )

    def _process_diagrams(
        self,
        markdown: str,
        temp_dir: Path,
        mermaid_theme: str = "default",
    ) -> tuple[str, str | None]:
        """Render diagrams and upload to Drive temp folder, returning modified markdown.

        Args:
            markdown: Original markdown content
            temp_dir: Temporary directory for rendered images
            mermaid_theme: Theme for Mermaid diagrams (default, neutral, dark, forest)

        Returns:
            Tuple of (modified markdown, temp folder ID for cleanup or None)
        """
        blocks = find_diagram_blocks(markdown)
        if not blocks:
            return markdown, None

        # Create temp folder in Drive
        temp_folder_id = self._create_temp_folder()

        # Render diagrams locally
        modified_md, rendered_paths = render_diagrams_in_markdown(
            markdown, temp_dir, output_format="png", mermaid_theme=mermaid_theme
        )

        # Upload each rendered diagram to Drive temp folder and get public URLs
        for path in rendered_paths:
            # Upload to Drive temp folder
            file_metadata = {"name": path.name, "parents": [temp_folder_id]}
            media = MediaFileUpload(str(path), mimetype="image/png")
            uploaded = self.execute(
                self.drive_service.files()
                .create(body=file_metadata, media_body=media, fields="id")
            )
            file_id = uploaded["id"]

            # Make publicly accessible
            self.execute(
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body={"type": "anyone", "role": "reader"},
                )
            )

            # Get the web content link for embedding
            # Use the direct image URL format
            image_url = f"https://drive.google.com/uc?export=view&id={file_id}"

            # Replace local path with Drive URL in markdown
            modified_md = modified_md.replace(str(path.absolute()), image_url)

        return modified_md, temp_folder_id

    def _resize_document_images(
        self,
        document_id: str,
        max_width_pt: float = 450.0,
        max_height_pt: float = 600.0,
    ) -> int:
        """Resize oversized images in a Google Doc by replacing them.

        The Docs API doesn't support direct resizing of inline images,
        so we find oversized images, delete them, and re-insert with correct size.

        Args:
            document_id: The Google Doc ID
            max_width_pt: Maximum width in points (450pt ≈ 6 inches)
            max_height_pt: Maximum height in points (600pt ≈ 8.3 inches)

        Returns:
            Number of images resized
        """
        from googleapiclient.discovery import build
        from gws.auth.oauth import AuthManager

        auth_manager = AuthManager()
        credentials = auth_manager.get_credentials()
        docs_service = build("docs", "v1", credentials=credentials)

        # Get document structure
        doc = self.execute(docs_service.documents().get(documentId=document_id))

        # Find inline objects (images) that need resizing
        inline_objects = doc.get("inlineObjects", {})
        if not inline_objects:
            return 0

        # Collect images that need resizing with their info
        images_to_resize = []
        for obj_id, obj_data in inline_objects.items():
            props = obj_data.get("inlineObjectProperties", {})
            embedded = props.get("embeddedObject", {})
            size = embedded.get("size", {})

            width = size.get("width", {}).get("magnitude", 0)
            height = size.get("height", {}).get("magnitude", 0)

            # Check if image exceeds either dimension
            needs_resize = (width > max_width_pt or height > max_height_pt) and width > 0 and height > 0

            if needs_resize:
                # Get the image URI
                image_props = embedded.get("imageProperties", {})
                content_uri = image_props.get("contentUri", "")
                source_uri = image_props.get("sourceUri", "")
                uri = source_uri or content_uri

                if uri:
                    # Calculate scale factors for both dimensions
                    width_scale = max_width_pt / width if width > max_width_pt else 1.0
                    height_scale = max_height_pt / height if height > max_height_pt else 1.0

                    # Use the smaller scale to ensure both dimensions fit
                    scale = min(width_scale, height_scale)
                    new_width = width * scale
                    new_height = height * scale

                    images_to_resize.append({
                        "object_id": obj_id,
                        "uri": uri,
                        "new_width": new_width,
                        "new_height": new_height,
                    })

        if not images_to_resize:
            return 0

        # Find positions of these images in the document body
        body = doc.get("body", {}).get("content", [])
        image_positions = {}

        for element in body:
            if "paragraph" in element:
                para = element["paragraph"]
                for pe in para.get("elements", []):
                    if "inlineObjectElement" in pe:
                        ioe = pe["inlineObjectElement"]
                        obj_id = ioe.get("inlineObjectId")
                        if obj_id:
                            # Get the start index of this element
                            start_index = pe.get("startIndex", 0)
                            image_positions[obj_id] = start_index

        # Process each image - delete and re-insert with new size
        # Process in reverse order to preserve indices
        requests = []
        for img_info in sorted(
            images_to_resize,
            key=lambda x: image_positions.get(x["object_id"], 0),
            reverse=True,
        ):
            obj_id = img_info["object_id"]
            if obj_id not in image_positions:
                continue

            position = image_positions[obj_id]

            # Delete the old image
            requests.append({
                "deleteContentRange": {
                    "range": {
                        "startIndex": position,
                        "endIndex": position + 1,
                    }
                }
            })

            # Insert new image with correct size
            requests.append({
                "insertInlineImage": {
                    "uri": img_info["uri"],
                    "location": {"index": position},
                    "objectSize": {
                        "width": {"magnitude": img_info["new_width"], "unit": "PT"},
                        "height": {"magnitude": img_info["new_height"], "unit": "PT"},
                    },
                }
            })

        if requests:
            self.execute(
                docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={"requests": requests},
                )
            )

        return len(images_to_resize)

    def md_to_doc(
        self,
        input_path: str,
        title: str | None = None,
        folder_id: str | None = None,
        render_diagrams: bool = False,
        mermaid_theme: str = "default",
        pageless: bool = True,
    ) -> dict[str, Any]:
        """Convert Markdown file to Google Doc.

        Uses Google's native Markdown import (added July 2024).

        Args:
            input_path: Path to markdown file
            title: Document title (defaults to filename)
            folder_id: Optional folder to create document in
            render_diagrams: If True, render Mermaid/PlantUML diagrams via Kroki
            mermaid_theme: Theme for Mermaid diagrams (default, neutral, dark, forest)
            pageless: If True (default), create document in pageless mode
        """
        temp_dir = None
        temp_folder_id = None

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

            # Read markdown content
            markdown_content = path.read_text(encoding="utf-8")
            upload_path = path

            # Process diagrams if requested
            diagrams_rendered = 0
            if render_diagrams:
                temp_dir = Path(tempfile.mkdtemp(prefix="gws_diagrams_"))
                blocks = find_diagram_blocks(markdown_content)
                diagrams_rendered = len(blocks)

                if blocks:
                    markdown_content, temp_folder_id = self._process_diagrams(
                        markdown_content, temp_dir, mermaid_theme=mermaid_theme
                    )
                    # Write modified markdown to temp file
                    temp_md = temp_dir / "converted.md"
                    temp_md.write_text(markdown_content, encoding="utf-8")
                    upload_path = temp_md

            # Upload markdown file and convert to Google Doc
            file_metadata = {
                "name": doc_title,
                "mimeType": "application/vnd.google-apps.document",
            }

            if folder_id:
                file_metadata["parents"] = [folder_id]

            media = MediaFileUpload(
                str(upload_path),
                mimetype="text/markdown",
                resumable=True,
            )

            # Use retry logic for transient API errors (500, 502, 503)
            request = self.drive_service.files().create(
                body=file_metadata, media_body=media, fields="id,name,webViewLink"
            )
            file = self.execute(request)

            # Resize any oversized images to fit the page
            images_resized = self._resize_document_images(file["id"])

            # Set pageless mode if requested
            if pageless:
                self._set_pageless_mode(file["id"])

            result = {
                "document_id": file["id"],
                "title": file["name"],
                "web_view_link": file["webViewLink"],
                "source_file": str(path),
                "pageless": pageless,
            }

            if render_diagrams and diagrams_rendered > 0:
                result["diagrams_rendered"] = diagrams_rendered
            if images_resized > 0:
                result["images_resized"] = images_resized

            output_success(operation="convert.md_to_doc", **result)
            return file

        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="convert.md_to_doc",
                message=f"Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)
        finally:
            # Cleanup local temp directory
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            # Cleanup Drive temp folder (deletes folder and all diagram images)
            if temp_folder_id:
                self._delete_temp_folder(temp_folder_id)

    def md_to_pdf(
        self,
        input_path: str,
        output_path: str,
        title: str | None = None,
        render_diagrams: bool = False,
        mermaid_theme: str = "default",
    ) -> dict[str, Any]:
        """Convert Markdown to PDF via Google Docs.

        1. Upload Markdown as Google Doc (optionally rendering diagrams)
        2. Export as PDF
        3. Delete the temporary Doc and diagram images

        Args:
            input_path: Path to markdown file
            output_path: Path for output PDF file
            title: Temporary doc title
            render_diagrams: If True, render Mermaid/PlantUML diagrams via Kroki
            mermaid_theme: Theme for Mermaid diagrams (default, neutral, dark, forest)
        """
        temp_dir = None
        temp_folder_id = None

        try:
            path = Path(input_path)
            if not path.exists():
                output_error(
                    error_code="FILE_NOT_FOUND",
                    operation="convert.md_to_pdf",
                    message=f"File not found: {input_path}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            doc_title = title or f"_temp_{path.stem}"

            # Read markdown content
            markdown_content = path.read_text(encoding="utf-8")
            upload_path = path

            # Process diagrams if requested
            diagrams_rendered = 0
            if render_diagrams:
                temp_dir = Path(tempfile.mkdtemp(prefix="gws_diagrams_"))
                blocks = find_diagram_blocks(markdown_content)
                diagrams_rendered = len(blocks)

                if blocks:
                    markdown_content, temp_folder_id = self._process_diagrams(
                        markdown_content, temp_dir, mermaid_theme=mermaid_theme
                    )
                    # Write modified markdown to temp file
                    temp_md = temp_dir / "converted.md"
                    temp_md.write_text(markdown_content, encoding="utf-8")
                    upload_path = temp_md

            # Upload as Doc
            file_metadata = {
                "name": doc_title,
                "mimeType": "application/vnd.google-apps.document",
            }

            media = MediaFileUpload(
                str(upload_path),
                mimetype="text/markdown",
                resumable=True,
            )

            # Use retry logic for transient API errors (500, 502, 503)
            request = self.drive_service.files().create(
                body=file_metadata, media_body=media, fields="id"
            )
            file = self.execute(request)

            doc_id = file["id"]

            try:
                # Resize any oversized images to fit the page
                self._resize_document_images(doc_id)

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

                result = {
                    "output_path": str(output_file),
                    "source_file": str(path),
                    "file_size": output_file.stat().st_size,
                }
                if render_diagrams and diagrams_rendered > 0:
                    result["diagrams_rendered"] = diagrams_rendered

                output_success(operation="convert.md_to_pdf", **result)
            finally:
                # Delete the temporary doc
                self.execute(self.drive_service.files().delete(fileId=doc_id))
                # Delete Drive temp folder (deletes folder and all diagram images)
                if temp_folder_id:
                    self._delete_temp_folder(temp_folder_id)

            return {"output_path": str(output_file)}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="convert.md_to_pdf",
                message=f"Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)
        finally:
            # Cleanup local temp directory
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

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
            presentation = self.execute(
                slides_service.presentations()
                .create(body={"title": pres_title})
            )
            presentation_id = presentation["presentationId"]

            try:
                # Move to folder if specified
                if folder_id:
                    file = self.execute(
                        self.drive_service.files().get(
                            fileId=presentation_id, fields="parents"
                        )
                    )
                    previous_parents = ",".join(file.get("parents", []))

                    self.execute(
                        self.drive_service.files().update(
                            fileId=presentation_id,
                            addParents=folder_id,
                            removeParents=previous_parents,
                            fields="id",
                        )
                    )

                # Build slides from parsed content
                requests = self._build_slide_requests(slides_data)

                if requests:
                    self.execute(
                        slides_service.presentations().batchUpdate(
                            presentationId=presentation_id,
                            body={"requests": requests},
                        )
                    )

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
                self.execute(self.drive_service.files().delete(fileId=presentation_id))
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

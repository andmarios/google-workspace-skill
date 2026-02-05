"""Google Drive service operations."""

import mimetypes
from pathlib import Path
from typing import Any

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode


class DriveService(BaseService):
    """Google Drive operations."""

    SERVICE_NAME = "drive"
    VERSION = "v3"

    # Common fields to request for file metadata
    FILE_FIELDS = (
        "id, name, mimeType, webViewLink, webContentLink, parents, "
        "createdTime, modifiedTime, size, description, starred, trashed"
    )
    LIST_FIELDS = (
        "nextPageToken, files(id, name, mimeType, webViewLink, parents, "
        "createdTime, modifiedTime, size)"
    )

    # MIME type mappings for common extensions
    MIME_TYPES = {
        ".json": "application/json",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".html": "text/html",
        ".htm": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".zip": "application/zip",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    # Export formats for Google native types
    EXPORT_FORMATS = {
        "application/vnd.google-apps.document": "application/pdf",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "application/pdf",
        "application/vnd.google-apps.drawing": "image/png",
    }

    def _detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type from file extension."""
        ext = Path(file_path).suffix.lower()
        if ext in self.MIME_TYPES:
            return self.MIME_TYPES[ext]
        # Fall back to mimetypes module
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def _file_to_dict(self, file: Any) -> dict[str, Any]:
        """Convert Google Drive file object to dictionary."""
        return {
            "id": file.get("id"),
            "name": file.get("name"),
            "mime_type": file.get("mimeType"),
            "web_view_link": file.get("webViewLink"),
            "web_content_link": file.get("webContentLink"),
            "parents": file.get("parents"),
            "created_time": file.get("createdTime"),
            "modified_time": file.get("modifiedTime"),
            "size": file.get("size"),
        }

    def upload(
        self,
        file_path: str,
        folder_id: str | None = None,
        name: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file to Google Drive."""
        path = Path(file_path)
        if not path.exists():
            output_error(
                error_code="FILE_NOT_FOUND",
                operation="drive.upload",
                message=f"File not found: {file_path}",
            )
            raise SystemExit(ExitCode.OPERATION_FAILED)

        file_name = name or path.name
        content_type = mime_type or self._detect_mime_type(file_path)

        file_metadata: dict[str, Any] = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(file_path, mimetype=content_type, resumable=True)

        try:
            result = self.execute(
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields=self.FILE_FIELDS,
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.upload",
                file=self._file_to_dict(result),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.upload",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def download(self, file_id: str, output_path: str) -> dict[str, Any]:
        """Download a file from Google Drive."""
        try:
            # Get file metadata first
            file = self.execute(self.service.files().get(
                fileId=file_id, fields="id, name, mimeType", supportsAllDrives=True
            ))

            # Handle Google native formats (need export)
            if file.get("mimeType", "").startswith("application/vnd.google-apps."):
                return self.export(
                    file_id=file_id,
                    output_path=output_path,
                    export_mime_type=self.EXPORT_FORMATS.get(file["mimeType"], "application/pdf"),
                )

            # Regular file download
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            # Write to file
            Path(output_path).write_bytes(fh.getvalue())

            output_success(
                operation="drive.download",
                file_id=file_id,
                output_path=output_path,
                name=file.get("name"),
                mime_type=file.get("mimeType"),
            )
            return {"file_id": file_id, "output_path": output_path}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.download",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def export(
        self,
        file_id: str,
        output_path: str,
        export_mime_type: str = "application/pdf",
    ) -> dict[str, Any]:
        """Export a Google native file (Docs, Sheets, Slides) to a different format."""
        try:
            request = self.service.files().export_media(
                fileId=file_id, mimeType=export_mime_type
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            Path(output_path).write_bytes(fh.getvalue())

            output_success(
                operation="drive.export",
                file_id=file_id,
                output_path=output_path,
                export_mime_type=export_mime_type,
            )
            return {"file_id": file_id, "output_path": output_path}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.export",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_files(
        self,
        folder_id: str | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List files in Drive or a specific folder."""
        try:
            query_parts = ["trashed = false"]
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")

            result = self.execute(
                self.service.files()
                .list(
                    q=" and ".join(query_parts),
                    pageSize=max_results,
                    pageToken=page_token,
                    fields=self.LIST_FIELDS,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
            )

            files = [self._file_to_dict(f) for f in result.get("files", [])]

            output_success(
                operation="drive.list",
                folder_id=folder_id,
                files=files,
                next_page_token=result.get("nextPageToken"),
                count=len(files),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def search(
        self,
        query: str,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Search files with a query."""
        try:
            # Add trashed filter if not already in query
            full_query = query if "trashed" in query else f"{query} and trashed = false"

            result = self.execute(
                self.service.files()
                .list(
                    q=full_query,
                    pageSize=max_results,
                    pageToken=page_token,
                    fields=self.LIST_FIELDS,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
            )

            files = [self._file_to_dict(f) for f in result.get("files", [])]

            output_success(
                operation="drive.search",
                query=query,
                files=files,
                next_page_token=result.get("nextPageToken"),
                count=len(files),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.search",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_metadata(self, file_id: str) -> dict[str, Any]:
        """Get detailed file metadata."""
        try:
            fields = (
                "id, name, mimeType, webViewLink, webContentLink, parents, "
                "createdTime, modifiedTime, size, description, starred, trashed, "
                "owners, permissions"
            )
            file = self.execute(self.service.files().get(
                fileId=file_id, fields=fields, supportsAllDrives=True
            ))

            # Format owners and permissions
            owners = [
                {"email": o.get("emailAddress"), "name": o.get("displayName")}
                for o in file.get("owners", [])
            ]
            permissions = [
                {
                    "id": p.get("id"),
                    "type": p.get("type"),
                    "role": p.get("role"),
                    "email": p.get("emailAddress"),
                }
                for p in file.get("permissions", [])
            ]

            file_data = self._file_to_dict(file)
            file_data["description"] = file.get("description")
            file_data["starred"] = file.get("starred")
            file_data["trashed"] = file.get("trashed")
            file_data["owners"] = owners
            file_data["permissions"] = permissions

            output_success(operation="drive.get_metadata", file=file_data)
            return file
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.get_metadata",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_folder(
        self, name: str, parent_id: str | None = None
    ) -> dict[str, Any]:
        """Create a new folder."""
        try:
            file_metadata: dict[str, Any] = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                file_metadata["parents"] = [parent_id]

            result = self.execute(
                self.service.files()
                .create(
                    body=file_metadata,
                    fields="id, name, mimeType, webViewLink, parents, createdTime",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.create_folder",
                folder={
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "web_view_link": result.get("webViewLink"),
                    "parents": result.get("parents"),
                    "created_time": result.get("createdTime"),
                },
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.create_folder",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def move(self, file_id: str, folder_id: str) -> dict[str, Any]:
        """Move a file to a different folder."""
        try:
            # Get current parents
            file = self.execute(self.service.files().get(
                fileId=file_id, fields="parents", supportsAllDrives=True
            ))
            previous_parents = ",".join(file.get("parents", []))

            result = self.execute(
                self.service.files()
                .update(
                    fileId=file_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields="id, name, parents, webViewLink",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.move",
                file={
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "parents": result.get("parents"),
                    "web_view_link": result.get("webViewLink"),
                },
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.move",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def share(
        self,
        file_id: str,
        email: str | None = None,
        role: str = "reader",
        share_type: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Share a file with a user, group, domain, or make public.

        Args:
            file_id: The file ID to share.
            email: Email address for user/group sharing.
            role: Permission role (reader, writer, commenter).
            share_type: Type of sharing (user, group, domain, anyone).
            domain: Domain for domain-wide sharing (e.g., 'company.com').
                   Auto-sets share_type to 'domain' if provided.
        """
        try:
            # Auto-detect type from domain parameter
            if domain:
                if share_type and share_type != "domain":
                    output_error(
                        error_code="INVALID_ARGUMENT",
                        operation="drive.share",
                        message=f"Cannot use --domain with --type {share_type}. Domain sharing requires type 'domain'.",
                    )
                    raise SystemExit(ExitCode.INVALID_ARGS)
                share_type = "domain"

            # Validate domain sharing has a domain
            if share_type == "domain" and not domain:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="drive.share",
                    message="Domain sharing requires --domain parameter (e.g., --domain company.com).",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Determine permission type
            perm_type = share_type or ("user" if email else "anyone")

            permission: dict[str, Any] = {"type": perm_type, "role": role}
            if email and perm_type == "user":
                permission["emailAddress"] = email
            if domain and perm_type == "domain":
                permission["domain"] = domain

            result = self.execute(
                self.service.permissions()
                .create(
                    fileId=file_id,
                    body=permission,
                    fields="id, type, role, emailAddress, domain",
                    supportsAllDrives=True,
                )
            )

            # Get updated file info with sharing link
            file = self.execute(
                self.service.files()
                .get(fileId=file_id, fields="webViewLink, webContentLink", supportsAllDrives=True)
            )

            output_success(
                operation="drive.share",
                permission={
                    "id": result.get("id"),
                    "type": result.get("type"),
                    "role": result.get("role"),
                    "email": result.get("emailAddress"),
                    "domain": result.get("domain"),
                },
                web_view_link=file.get("webViewLink"),
                web_content_link=file.get("webContentLink"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.share",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def copy(
        self,
        file_id: str,
        name: str | None = None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Copy a file."""
        try:
            file_metadata: dict[str, Any] = {}
            if name:
                file_metadata["name"] = name
            if folder_id:
                file_metadata["parents"] = [folder_id]

            result = self.execute(
                self.service.files()
                .copy(
                    fileId=file_id,
                    body=file_metadata,
                    fields="id, name, mimeType, webViewLink, parents, createdTime",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.copy",
                file=self._file_to_dict(result),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.copy",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update(
        self,
        file_id: str,
        file_path: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Update a file's content."""
        path = Path(file_path)
        if not path.exists():
            output_error(
                error_code="FILE_NOT_FOUND",
                operation="drive.update",
                message=f"File not found: {file_path}",
            )
            raise SystemExit(ExitCode.OPERATION_FAILED)

        try:
            file_metadata: dict[str, Any] = {}
            if name:
                file_metadata["name"] = name

            mime_type = self._detect_mime_type(file_path)
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

            result = self.execute(
                self.service.files()
                .update(
                    fileId=file_id,
                    body=file_metadata if file_metadata else None,
                    media_body=media,
                    fields="id, name, mimeType, webViewLink, modifiedTime, size",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.update",
                file=self._file_to_dict(result),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.update",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete(self, file_id: str, permanent: bool = False) -> dict[str, Any]:
        """Delete a file (trash or permanent)."""
        try:
            if permanent:
                self.execute(self.service.files().delete(fileId=file_id, supportsAllDrives=True))
            else:
                self.execute(self.service.files().update(
                    fileId=file_id, body={"trashed": True}, supportsAllDrives=True
                ))

            output_success(
                operation="drive.delete",
                file_id=file_id,
                permanent=permanent,
            )
            return {"file_id": file_id, "permanent": permanent}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.delete",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # COMMENTS
    # =========================================================================

    def list_comments(
        self,
        file_id: str,
        include_deleted: bool = False,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """List comments on a file.

        Args:
            file_id: The file ID.
            include_deleted: Include deleted comments.
            max_results: Maximum comments to return.
        """
        try:
            result = self.execute(
                self.service.comments()
                .list(
                    fileId=file_id,
                    includeDeleted=include_deleted,
                    pageSize=max_results,
                    fields="comments(id,content,author,createdTime,modifiedTime,resolved,replies)",
                )
            )

            comments = []
            for comment in result.get("comments", []):
                comments.append({
                    "comment_id": comment.get("id"),
                    "content": comment.get("content"),
                    "author": comment.get("author", {}).get("displayName"),
                    "created_time": comment.get("createdTime"),
                    "resolved": comment.get("resolved", False),
                    "reply_count": len(comment.get("replies", [])),
                })

            output_success(
                operation="drive.list_comments",
                file_id=file_id,
                comment_count=len(comments),
                comments=comments,
            )
            return {"comments": comments}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list_comments",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_comment(
        self,
        file_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Add a comment to a file.

        Args:
            file_id: The file ID.
            content: The comment text.
        """
        try:
            result = self.execute(
                self.service.comments()
                .create(
                    fileId=file_id,
                    body={"content": content},
                    fields="id,content,author,createdTime",
                )
            )

            output_success(
                operation="drive.add_comment",
                file_id=file_id,
                comment_id=result.get("id"),
                content=result.get("content"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.add_comment",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def resolve_comment(
        self,
        file_id: str,
        comment_id: str,
    ) -> dict[str, Any]:
        """Resolve a comment on a file.

        Args:
            file_id: The file ID.
            comment_id: The comment ID.
        """
        try:
            result = self.execute(
                self.service.comments()
                .update(
                    fileId=file_id,
                    commentId=comment_id,
                    body={"resolved": True},
                    fields="id,content,resolved",
                )
            )

            output_success(
                operation="drive.resolve_comment",
                file_id=file_id,
                comment_id=comment_id,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.resolve_comment",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_comment(
        self,
        file_id: str,
        comment_id: str,
    ) -> dict[str, Any]:
        """Delete a comment from a file.

        Args:
            file_id: The file ID.
            comment_id: The comment ID.
        """
        try:
            self.execute(self.service.comments().delete(
                fileId=file_id, commentId=comment_id
            ))

            output_success(
                operation="drive.delete_comment",
                file_id=file_id,
                comment_id=comment_id,
            )
            return {"file_id": file_id, "comment_id": comment_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.delete_comment",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def reply_to_comment(
        self,
        file_id: str,
        comment_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Reply to a comment on a file.

        Args:
            file_id: The file ID.
            comment_id: The comment ID to reply to.
            content: The reply text.
        """
        try:
            result = self.execute(
                self.service.replies()
                .create(
                    fileId=file_id,
                    commentId=comment_id,
                    body={"content": content},
                    fields="id,content,author,createdTime",
                )
            )

            output_success(
                operation="drive.reply_to_comment",
                file_id=file_id,
                comment_id=comment_id,
                reply_id=result.get("id"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.reply_to_comment",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # REVISIONS
    # =========================================================================

    def list_revisions(
        self,
        file_id: str,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """List revisions of a file.

        Args:
            file_id: The file ID.
            max_results: Maximum revisions to return.
        """
        try:
            result = self.execute(
                self.service.revisions()
                .list(
                    fileId=file_id,
                    pageSize=max_results,
                    fields="revisions(id,mimeType,modifiedTime,lastModifyingUser,originalFilename,size)",
                    supportsAllDrives=True,
                )
            )

            revisions = []
            for rev in result.get("revisions", []):
                revisions.append({
                    "revision_id": rev.get("id"),
                    "modified_time": rev.get("modifiedTime"),
                    "last_modifying_user": rev.get("lastModifyingUser", {}).get("displayName"),
                    "original_filename": rev.get("originalFilename"),
                    "size": rev.get("size"),
                })

            output_success(
                operation="drive.list_revisions",
                file_id=file_id,
                revision_count=len(revisions),
                revisions=revisions,
            )
            return {"revisions": revisions}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list_revisions",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_revision(
        self,
        file_id: str,
        revision_id: str,
    ) -> dict[str, Any]:
        """Get metadata for a specific revision.

        Args:
            file_id: The file ID.
            revision_id: The revision ID.
        """
        try:
            result = self.execute(
                self.service.revisions()
                .get(
                    fileId=file_id,
                    revisionId=revision_id,
                    fields="id,mimeType,modifiedTime,lastModifyingUser,originalFilename,size,keepForever,publishAuto,published",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.get_revision",
                file_id=file_id,
                revision_id=revision_id,
                modified_time=result.get("modifiedTime"),
                last_modifying_user=result.get("lastModifyingUser", {}).get("displayName"),
                keep_forever=result.get("keepForever", False),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.get_revision",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_revision(
        self,
        file_id: str,
        revision_id: str,
    ) -> dict[str, Any]:
        """Delete a revision (cannot delete the last remaining revision).

        Args:
            file_id: The file ID.
            revision_id: The revision ID to delete.
        """
        try:
            self.execute(self.service.revisions().delete(
                fileId=file_id, revisionId=revision_id, supportsAllDrives=True
            ))

            output_success(
                operation="drive.delete_revision",
                file_id=file_id,
                revision_id=revision_id,
            )
            return {"file_id": file_id, "revision_id": revision_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.delete_revision",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # TRASH MANAGEMENT
    # =========================================================================

    def list_trash(
        self,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """List files in trash.

        Args:
            max_results: Maximum files to return.
        """
        try:
            result = self.execute(
                self.service.files()
                .list(
                    q="trashed=true",
                    pageSize=max_results,
                    fields="files(id,name,mimeType,trashedTime,trashingUser)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
            )

            files = []
            for f in result.get("files", []):
                files.append({
                    "file_id": f.get("id"),
                    "name": f.get("name"),
                    "mime_type": f.get("mimeType"),
                    "trashed_time": f.get("trashedTime"),
                    "trashing_user": f.get("trashingUser", {}).get("displayName"),
                })

            output_success(
                operation="drive.list_trash",
                file_count=len(files),
                files=files,
            )
            return {"files": files}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list_trash",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def restore_from_trash(
        self,
        file_id: str,
    ) -> dict[str, Any]:
        """Restore a file from trash.

        Args:
            file_id: The file ID to restore.
        """
        try:
            result = self.execute(
                self.service.files()
                .update(
                    fileId=file_id,
                    body={"trashed": False},
                    fields="id,name,mimeType,webViewLink",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.restore_from_trash",
                file_id=file_id,
                name=result.get("name"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.restore_from_trash",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def empty_trash(self) -> dict[str, Any]:
        """Permanently delete all files in trash."""
        try:
            self.execute(self.service.files().emptyTrash())

            output_success(
                operation="drive.empty_trash",
                status="Trash emptied",
            )
            return {"status": "trash_emptied"}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.empty_trash",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # PERMISSIONS
    # =========================================================================

    def list_permissions(
        self,
        file_id: str,
    ) -> dict[str, Any]:
        """List all permissions on a file.

        Args:
            file_id: The file ID.
        """
        try:
            result = self.execute(
                self.service.permissions()
                .list(
                    fileId=file_id,
                    fields="permissions(id,type,role,emailAddress,displayName,domain,expirationTime,deleted)",
                    supportsAllDrives=True,
                )
            )

            permissions = []
            for perm in result.get("permissions", []):
                permissions.append({
                    "permission_id": perm.get("id"),
                    "type": perm.get("type"),
                    "role": perm.get("role"),
                    "email_address": perm.get("emailAddress"),
                    "display_name": perm.get("displayName"),
                    "domain": perm.get("domain"),
                    "expiration_time": perm.get("expirationTime"),
                    "deleted": perm.get("deleted", False),
                })

            output_success(
                operation="drive.list_permissions",
                file_id=file_id,
                permission_count=len(permissions),
                permissions=permissions,
            )
            return {"permissions": permissions}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list_permissions",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_permission(
        self,
        file_id: str,
        permission_id: str,
    ) -> dict[str, Any]:
        """Get a specific permission.

        Args:
            file_id: The file ID.
            permission_id: The permission ID.
        """
        try:
            result = self.execute(
                self.service.permissions()
                .get(
                    fileId=file_id,
                    permissionId=permission_id,
                    fields="id,type,role,emailAddress,displayName,domain,expirationTime,deleted,pendingOwner",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.get_permission",
                file_id=file_id,
                permission_id=permission_id,
                type=result.get("type"),
                role=result.get("role"),
                email_address=result.get("emailAddress"),
                display_name=result.get("displayName"),
                domain=result.get("domain"),
                expiration_time=result.get("expirationTime"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.get_permission",
                    message=f"Permission not found: {permission_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.get_permission",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_permission(
        self,
        file_id: str,
        permission_id: str,
        role: str,
        expiration_time: str | None = None,
    ) -> dict[str, Any]:
        """Update a permission's role.

        Args:
            file_id: The file ID.
            permission_id: The permission ID.
            role: New role (reader, commenter, writer, organizer, owner).
            expiration_time: Optional expiration (ISO 8601 format).
        """
        try:
            body: dict[str, Any] = {"role": role}
            if expiration_time:
                body["expirationTime"] = expiration_time

            result = self.execute(
                self.service.permissions()
                .update(
                    fileId=file_id,
                    permissionId=permission_id,
                    body=body,
                    fields="id,type,role,emailAddress,expirationTime",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.update_permission",
                file_id=file_id,
                permission_id=permission_id,
                new_role=role,
                email_address=result.get("emailAddress"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.update_permission",
                    message=f"Permission not found: {permission_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.update_permission",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_permission(
        self,
        file_id: str,
        permission_id: str,
    ) -> dict[str, Any]:
        """Remove a permission from a file (unshare).

        Args:
            file_id: The file ID.
            permission_id: The permission ID to remove.
        """
        try:
            self.execute(self.service.permissions().delete(
                fileId=file_id,
                permissionId=permission_id,
                supportsAllDrives=True,
            ))

            output_success(
                operation="drive.delete_permission",
                file_id=file_id,
                permission_id=permission_id,
                deleted=True,
            )
            return {"deleted": True, "permission_id": permission_id}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.delete_permission",
                    message=f"Permission not found: {permission_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.delete_permission",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def transfer_ownership(
        self,
        file_id: str,
        new_owner_email: str,
    ) -> dict[str, Any]:
        """Transfer ownership of a file to another user.

        Args:
            file_id: The file ID.
            new_owner_email: Email address of the new owner.
        """
        try:
            result = self.execute(
                self.service.permissions()
                .create(
                    fileId=file_id,
                    body={
                        "type": "user",
                        "role": "owner",
                        "emailAddress": new_owner_email,
                    },
                    transferOwnership=True,
                    fields="id,emailAddress,role",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.transfer_ownership",
                file_id=file_id,
                new_owner=new_owner_email,
                permission_id=result.get("id"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.transfer_ownership",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # REPLIES (extended)
    # =========================================================================

    def list_replies(
        self,
        file_id: str,
        comment_id: str,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """List replies to a comment.

        Args:
            file_id: The file ID.
            comment_id: The comment ID.
            max_results: Maximum replies to return.
        """
        try:
            result = self.execute(
                self.service.replies()
                .list(
                    fileId=file_id,
                    commentId=comment_id,
                    pageSize=max_results,
                    fields="replies(id,content,author,createdTime,modifiedTime)",
                )
            )

            replies = []
            for reply in result.get("replies", []):
                replies.append({
                    "reply_id": reply.get("id"),
                    "content": reply.get("content"),
                    "author": reply.get("author", {}).get("displayName"),
                    "created_time": reply.get("createdTime"),
                    "modified_time": reply.get("modifiedTime"),
                })

            output_success(
                operation="drive.list_replies",
                file_id=file_id,
                comment_id=comment_id,
                reply_count=len(replies),
                replies=replies,
            )
            return {"replies": replies}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list_replies",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_reply(
        self,
        file_id: str,
        comment_id: str,
        reply_id: str,
    ) -> dict[str, Any]:
        """Get a specific reply.

        Args:
            file_id: The file ID.
            comment_id: The comment ID.
            reply_id: The reply ID.
        """
        try:
            result = self.execute(
                self.service.replies()
                .get(
                    fileId=file_id,
                    commentId=comment_id,
                    replyId=reply_id,
                    fields="id,content,author,createdTime,modifiedTime,action",
                )
            )

            output_success(
                operation="drive.get_reply",
                file_id=file_id,
                comment_id=comment_id,
                reply_id=reply_id,
                content=result.get("content"),
                author=result.get("author", {}).get("displayName"),
                created_time=result.get("createdTime"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.get_reply",
                    message=f"Reply not found: {reply_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.get_reply",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_reply(
        self,
        file_id: str,
        comment_id: str,
        reply_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Update a reply's content.

        Args:
            file_id: The file ID.
            comment_id: The comment ID.
            reply_id: The reply ID.
            content: New reply content.
        """
        try:
            result = self.execute(
                self.service.replies()
                .update(
                    fileId=file_id,
                    commentId=comment_id,
                    replyId=reply_id,
                    body={"content": content},
                    fields="id,content,modifiedTime",
                )
            )

            output_success(
                operation="drive.update_reply",
                file_id=file_id,
                comment_id=comment_id,
                reply_id=reply_id,
                content=result.get("content"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.update_reply",
                    message=f"Reply not found: {reply_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.update_reply",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_reply(
        self,
        file_id: str,
        comment_id: str,
        reply_id: str,
    ) -> dict[str, Any]:
        """Delete a reply.

        Args:
            file_id: The file ID.
            comment_id: The comment ID.
            reply_id: The reply ID to delete.
        """
        try:
            self.execute(
                self.service.replies()
                .delete(
                    fileId=file_id,
                    commentId=comment_id,
                    replyId=reply_id,
                )
            )

            output_success(
                operation="drive.delete_reply",
                file_id=file_id,
                comment_id=comment_id,
                reply_id=reply_id,
            )
            return {"file_id": file_id, "comment_id": comment_id, "reply_id": reply_id}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.delete_reply",
                    message=f"Reply not found: {reply_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.delete_reply",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # REVISIONS (extended)
    # =========================================================================

    def update_revision(
        self,
        file_id: str,
        revision_id: str,
        keep_forever: bool | None = None,
        published: bool | None = None,
        publish_auto: bool | None = None,
    ) -> dict[str, Any]:
        """Update revision metadata.

        Args:
            file_id: The file ID.
            revision_id: The revision ID.
            keep_forever: Whether to keep this revision forever (prevents auto-deletion).
            published: Whether this revision is published (for Google Docs/Sheets/Slides).
            publish_auto: Whether future revisions automatically publish.
        """
        try:
            body: dict[str, Any] = {}
            if keep_forever is not None:
                body["keepForever"] = keep_forever
            if published is not None:
                body["published"] = published
            if publish_auto is not None:
                body["publishAuto"] = publish_auto

            if not body:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="drive.update_revision",
                    message="At least one update field required (keep_forever, published, publish_auto)",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            result = self.execute(
                self.service.revisions()
                .update(
                    fileId=file_id,
                    revisionId=revision_id,
                    body=body,
                    fields="id,modifiedTime,keepForever,published,publishAuto",
                    supportsAllDrives=True,
                )
            )

            output_success(
                operation="drive.update_revision",
                file_id=file_id,
                revision_id=revision_id,
                keep_forever=result.get("keepForever"),
                published=result.get("published"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.update_revision",
                    message=f"Revision not found: {revision_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.update_revision",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # CHANGES
    # =========================================================================

    def get_start_page_token(self) -> dict[str, Any]:
        """Get the starting page token for listing future changes."""
        try:
            result = self.execute(
                self.service.changes()
                .getStartPageToken(supportsAllDrives=True)
            )

            output_success(
                operation="drive.get_start_page_token",
                start_page_token=result.get("startPageToken"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.get_start_page_token",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_changes(
        self,
        page_token: str,
        page_size: int = 100,
        include_removed: bool = True,
    ) -> dict[str, Any]:
        """List changes to files.

        Args:
            page_token: The token for continuing a previous list request.
            page_size: Maximum number of changes to return.
            include_removed: Whether to include deleted files/drives.
        """
        try:
            result = self.execute(
                self.service.changes()
                .list(
                    pageToken=page_token,
                    pageSize=page_size,
                    includeRemoved=include_removed,
                    fields="nextPageToken,newStartPageToken,changes(fileId,changeType,time,removed,file(id,name,mimeType,trashed))",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
            )

            changes = []
            for change in result.get("changes", []):
                change_data = {
                    "file_id": change.get("fileId"),
                    "change_type": change.get("changeType"),
                    "time": change.get("time"),
                    "removed": change.get("removed", False),
                }
                if change.get("file"):
                    change_data["file"] = {
                        "name": change["file"].get("name"),
                        "mime_type": change["file"].get("mimeType"),
                        "trashed": change["file"].get("trashed", False),
                    }
                changes.append(change_data)

            output_success(
                operation="drive.list_changes",
                change_count=len(changes),
                next_page_token=result.get("nextPageToken"),
                new_start_page_token=result.get("newStartPageToken"),
                changes=changes,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list_changes",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # SHARED DRIVES
    # =========================================================================

    def list_shared_drives(
        self,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List shared drives the user has access to.

        Args:
            max_results: Maximum number of shared drives to return.
            page_token: Token for pagination.
        """
        try:
            result = self.execute(
                self.service.drives()
                .list(
                    pageSize=max_results,
                    pageToken=page_token,
                    fields="nextPageToken,drives(id,name,createdTime,hidden)",
                )
            )

            drives = []
            for drive in result.get("drives", []):
                drives.append({
                    "drive_id": drive.get("id"),
                    "name": drive.get("name"),
                    "created_time": drive.get("createdTime"),
                    "hidden": drive.get("hidden", False),
                })

            output_success(
                operation="drive.list_shared_drives",
                drive_count=len(drives),
                next_page_token=result.get("nextPageToken"),
                drives=drives,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.list_shared_drives",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_shared_drive(self, drive_id: str) -> dict[str, Any]:
        """Get metadata for a shared drive.

        Args:
            drive_id: The shared drive ID.
        """
        try:
            result = self.execute(
                self.service.drives()
                .get(
                    driveId=drive_id,
                    fields="id,name,createdTime,hidden,capabilities,restrictions",
                )
            )

            output_success(
                operation="drive.get_shared_drive",
                drive_id=drive_id,
                name=result.get("name"),
                created_time=result.get("createdTime"),
                capabilities=result.get("capabilities"),
                restrictions=result.get("restrictions"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.get_shared_drive",
                    message=f"Shared drive not found: {drive_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.get_shared_drive",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_shared_drive(self, name: str) -> dict[str, Any]:
        """Create a new shared drive.

        Args:
            name: Name for the shared drive.
        """
        import uuid

        try:
            result = self.execute(
                self.service.drives()
                .create(
                    requestId=str(uuid.uuid4()),
                    body={"name": name},
                    fields="id,name,createdTime",
                )
            )

            output_success(
                operation="drive.create_shared_drive",
                drive_id=result.get("id"),
                name=result.get("name"),
                created_time=result.get("createdTime"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.create_shared_drive",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_shared_drive(self, drive_id: str) -> dict[str, Any]:
        """Delete a shared drive (must be empty).

        Args:
            drive_id: The shared drive ID to delete.
        """
        try:
            self.execute(self.service.drives().delete(driveId=drive_id))

            output_success(
                operation="drive.delete_shared_drive",
                drive_id=drive_id,
                deleted=True,
            )
            return {"drive_id": drive_id, "deleted": True}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="drive.delete_shared_drive",
                    message=f"Shared drive not found: {drive_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="drive.delete_shared_drive",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # FILE IDS
    # =========================================================================

    def generate_ids(
        self,
        count: int = 10,
        space: str = "drive",
    ) -> dict[str, Any]:
        """Generate file IDs for use with create operations.

        Args:
            count: Number of IDs to generate (max 1000).
            space: Space for the IDs ('drive' or 'appDataFolder').
        """
        try:
            result = self.execute(
                self.service.files()
                .generateIds(
                    count=count,
                    space=space,
                    fields="ids,space,kind",
                )
            )

            output_success(
                operation="drive.generate_ids",
                count=len(result.get("ids", [])),
                space=result.get("space"),
                ids=result.get("ids"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="drive.generate_ids",
                message=f"Google Drive API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

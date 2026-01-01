"""Drive CLI commands."""

import typer
from typing import Annotated, Optional

from gws.services.drive import DriveService

app = typer.Typer(
    name="drive",
    help="Google Drive file operations.",
    no_args_is_help=True,
)


@app.command("list")
def list_files(
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Folder ID to list contents of."),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of files to return."),
    ] = 100,
    page_token: Annotated[
        Optional[str],
        typer.Option("--page-token", help="Token for pagination."),
    ] = None,
) -> None:
    """List files in Drive or a specific folder."""
    service = DriveService()
    service.list_files(folder_id=folder_id, max_results=max_results, page_token=page_token)


@app.command("search")
def search_files(
    query: Annotated[str, typer.Argument(help="Search query (Drive query syntax).")],
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of files to return."),
    ] = 100,
    page_token: Annotated[
        Optional[str],
        typer.Option("--page-token", help="Token for pagination."),
    ] = None,
) -> None:
    """Search files with a query.

    Query syntax examples:
    - name contains 'report'
    - mimeType = 'application/pdf'
    - modifiedTime > '2024-01-01'
    - 'folder_id' in parents
    """
    service = DriveService()
    service.search(query=query, max_results=max_results, page_token=page_token)


@app.command("get")
def get_metadata(
    file_id: Annotated[str, typer.Argument(help="File ID to get metadata for.")],
) -> None:
    """Get detailed file metadata."""
    service = DriveService()
    service.get_metadata(file_id=file_id)


@app.command("upload")
def upload_file(
    file_path: Annotated[str, typer.Argument(help="Local file path to upload.")],
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Destination folder ID."),
    ] = None,
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Name for the uploaded file."),
    ] = None,
    mime_type: Annotated[
        Optional[str],
        typer.Option("--mime-type", help="MIME type (auto-detected if not specified)."),
    ] = None,
) -> None:
    """Upload a file to Google Drive."""
    service = DriveService()
    service.upload(file_path=file_path, folder_id=folder_id, name=name, mime_type=mime_type)


@app.command("download")
def download_file(
    file_id: Annotated[str, typer.Argument(help="File ID to download.")],
    output_path: Annotated[str, typer.Argument(help="Local path to save the file.")],
) -> None:
    """Download a file from Google Drive."""
    service = DriveService()
    service.download(file_id=file_id, output_path=output_path)


@app.command("export")
def export_file(
    file_id: Annotated[str, typer.Argument(help="File ID to export.")],
    output_path: Annotated[str, typer.Argument(help="Local path to save the file.")],
    mime_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Export MIME type (e.g., application/pdf)."),
    ] = "application/pdf",
) -> None:
    """Export a Google native file (Docs, Sheets, Slides) to another format."""
    service = DriveService()
    service.export(file_id=file_id, output_path=output_path, export_mime_type=mime_type)


@app.command("create-folder")
def create_folder(
    name: Annotated[str, typer.Argument(help="Folder name.")],
    parent_id: Annotated[
        Optional[str],
        typer.Option("--parent", "-p", help="Parent folder ID."),
    ] = None,
) -> None:
    """Create a new folder."""
    service = DriveService()
    service.create_folder(name=name, parent_id=parent_id)


@app.command("move")
def move_file(
    file_id: Annotated[str, typer.Argument(help="File ID to move.")],
    folder_id: Annotated[str, typer.Argument(help="Destination folder ID.")],
) -> None:
    """Move a file to a different folder."""
    service = DriveService()
    service.move(file_id=file_id, folder_id=folder_id)


@app.command("copy")
def copy_file(
    file_id: Annotated[str, typer.Argument(help="File ID to copy.")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Name for the copy."),
    ] = None,
    folder_id: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Destination folder ID."),
    ] = None,
) -> None:
    """Copy a file."""
    service = DriveService()
    service.copy(file_id=file_id, name=name, folder_id=folder_id)


@app.command("share")
def share_file(
    file_id: Annotated[str, typer.Argument(help="File ID to share.")],
    email: Annotated[
        Optional[str],
        typer.Option("--email", "-e", help="Email address to share with."),
    ] = None,
    role: Annotated[
        str,
        typer.Option("--role", "-r", help="Permission role: reader, writer, commenter."),
    ] = "reader",
    share_type: Annotated[
        Optional[str],
        typer.Option("--type", "-t", help="Share type: user, group, domain, anyone."),
    ] = None,
) -> None:
    """Share a file with a user or make public.

    Without --email, shares with 'anyone' (public link).
    """
    service = DriveService()
    service.share(file_id=file_id, email=email, role=role, share_type=share_type)


@app.command("update")
def update_file(
    file_id: Annotated[str, typer.Argument(help="File ID to update.")],
    file_path: Annotated[str, typer.Argument(help="Local file with new content.")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="New name for the file."),
    ] = None,
) -> None:
    """Update a file's content."""
    service = DriveService()
    service.update(file_id=file_id, file_path=file_path, name=name)


@app.command("delete")
def delete_file(
    file_id: Annotated[str, typer.Argument(help="File ID to delete.")],
    permanent: Annotated[
        bool,
        typer.Option("--permanent", "-p", help="Permanently delete (skip trash)."),
    ] = False,
) -> None:
    """Delete a file (moves to trash by default)."""
    service = DriveService()
    service.delete(file_id=file_id, permanent=permanent)


# ===== Comments =====


@app.command("list-comments")
def list_comments(
    file_id: Annotated[str, typer.Argument(help="File ID to list comments for.")],
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", help="Include deleted comments."),
    ] = False,
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of comments to return."),
    ] = 20,
) -> None:
    """List comments on a file."""
    service = DriveService()
    service.list_comments(
        file_id=file_id, include_deleted=include_deleted, max_results=max_results
    )


@app.command("add-comment")
def add_comment(
    file_id: Annotated[str, typer.Argument(help="File ID to comment on.")],
    content: Annotated[str, typer.Argument(help="Comment text.")],
) -> None:
    """Add a comment to a file."""
    service = DriveService()
    service.add_comment(file_id=file_id, content=content)


@app.command("resolve-comment")
def resolve_comment(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    comment_id: Annotated[str, typer.Argument(help="Comment ID to resolve.")],
) -> None:
    """Mark a comment as resolved."""
    service = DriveService()
    service.resolve_comment(file_id=file_id, comment_id=comment_id)


@app.command("delete-comment")
def delete_comment(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    comment_id: Annotated[str, typer.Argument(help="Comment ID to delete.")],
) -> None:
    """Delete a comment."""
    service = DriveService()
    service.delete_comment(file_id=file_id, comment_id=comment_id)


@app.command("reply-to-comment")
def reply_to_comment(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    comment_id: Annotated[str, typer.Argument(help="Comment ID to reply to.")],
    content: Annotated[str, typer.Argument(help="Reply text.")],
) -> None:
    """Reply to a comment."""
    service = DriveService()
    service.reply_to_comment(file_id=file_id, comment_id=comment_id, content=content)


# ===== Revisions =====


@app.command("list-revisions")
def list_revisions(
    file_id: Annotated[str, typer.Argument(help="File ID to list revisions for.")],
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of revisions to return."),
    ] = 20,
) -> None:
    """List revisions of a file."""
    service = DriveService()
    service.list_revisions(file_id=file_id, max_results=max_results)


@app.command("get-revision")
def get_revision(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    revision_id: Annotated[str, typer.Argument(help="Revision ID.")],
) -> None:
    """Get metadata for a specific revision."""
    service = DriveService()
    service.get_revision(file_id=file_id, revision_id=revision_id)


@app.command("delete-revision")
def delete_revision(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    revision_id: Annotated[str, typer.Argument(help="Revision ID to delete.")],
) -> None:
    """Delete a revision (cannot delete the last remaining revision)."""
    service = DriveService()
    service.delete_revision(file_id=file_id, revision_id=revision_id)


# ===== Trash =====


@app.command("list-trash")
def list_trash(
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of files to return."),
    ] = 20,
) -> None:
    """List files in trash."""
    service = DriveService()
    service.list_trash(max_results=max_results)


@app.command("restore")
def restore_from_trash(
    file_id: Annotated[str, typer.Argument(help="File ID to restore from trash.")],
) -> None:
    """Restore a file from trash."""
    service = DriveService()
    service.restore_from_trash(file_id=file_id)


@app.command("empty-trash")
def empty_trash() -> None:
    """Permanently delete all files in trash."""
    service = DriveService()
    service.empty_trash()


# ===== Permissions =====


@app.command("list-permissions")
def list_permissions(
    file_id: Annotated[str, typer.Argument(help="File ID to list permissions for.")],
) -> None:
    """List all permissions on a file (who has access)."""
    service = DriveService()
    service.list_permissions(file_id=file_id)


@app.command("get-permission")
def get_permission(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    permission_id: Annotated[str, typer.Argument(help="Permission ID.")],
) -> None:
    """Get details of a specific permission."""
    service = DriveService()
    service.get_permission(file_id=file_id, permission_id=permission_id)


@app.command("update-permission")
def update_permission(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    permission_id: Annotated[str, typer.Argument(help="Permission ID to update.")],
    role: Annotated[str, typer.Argument(help="New role (reader, commenter, writer, organizer).")],
    expiration: Annotated[
        Optional[str],
        typer.Option("--expiration", "-e", help="Expiration time (ISO 8601 format)."),
    ] = None,
) -> None:
    """Update a permission's role."""
    service = DriveService()
    service.update_permission(
        file_id=file_id,
        permission_id=permission_id,
        role=role,
        expiration_time=expiration,
    )


@app.command("delete-permission")
def delete_permission(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    permission_id: Annotated[str, typer.Argument(help="Permission ID to remove.")],
) -> None:
    """Remove a permission from a file (unshare)."""
    service = DriveService()
    service.delete_permission(file_id=file_id, permission_id=permission_id)


@app.command("transfer-ownership")
def transfer_ownership(
    file_id: Annotated[str, typer.Argument(help="File ID.")],
    new_owner_email: Annotated[str, typer.Argument(help="Email of the new owner.")],
) -> None:
    """Transfer ownership of a file to another user."""
    service = DriveService()
    service.transfer_ownership(file_id=file_id, new_owner_email=new_owner_email)

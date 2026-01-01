"""Gmail CLI commands."""

import sys
import typer
from typing import Annotated, Optional

from gws.services.gmail import GmailService

app = typer.Typer(
    name="gmail",
    help="Gmail email operations.",
    no_args_is_help=True,
)


@app.command("list")
def list_messages(
    query: Annotated[
        Optional[str],
        typer.Option("--query", "-q", help="Gmail search query (e.g., 'from:someone')."),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum messages to return."),
    ] = 10,
    labels: Annotated[
        Optional[str],
        typer.Option("--labels", "-l", help="Comma-separated label IDs."),
    ] = None,
) -> None:
    """List recent messages."""
    label_ids = labels.split(",") if labels else None

    service = GmailService()
    service.list_messages(
        query=query,
        max_results=max_results,
        label_ids=label_ids,
    )


@app.command("read")
def read_message(
    message_id: Annotated[str, typer.Argument(help="Message ID to read.")],
    full: Annotated[
        bool,
        typer.Option("--full", "-f", help="Get full message format."),
    ] = True,
) -> None:
    """Read a message by ID."""
    format_type = "full" if full else "metadata"

    service = GmailService()
    service.read_message(message_id=message_id, format_type=format_type)


@app.command("send")
def send_message(
    to: Annotated[str, typer.Argument(help="Recipient email address.")],
    subject: Annotated[str, typer.Argument(help="Email subject.")],
    body: Annotated[
        Optional[str],
        typer.Argument(help="Email body text."),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read body from stdin."),
    ] = False,
    cc: Annotated[
        Optional[str],
        typer.Option("--cc", help="CC recipients."),
    ] = None,
    bcc: Annotated[
        Optional[str],
        typer.Option("--bcc", help="BCC recipients."),
    ] = None,
    plain_text: Annotated[
        bool,
        typer.Option("--plain", help="Send as plain text instead of HTML."),
    ] = False,
    from_name: Annotated[
        Optional[str],
        typer.Option("--from-name", "-n", help="Sender display name."),
    ] = None,
    signature: Annotated[
        Optional[str],
        typer.Option("--signature", "-s", help="Email signature to append."),
    ] = None,
) -> None:
    """Send an email message (HTML by default)."""
    if stdin:
        body = sys.stdin.read()
    elif body is None:
        typer.echo("Error: Either provide body argument or use --stdin", err=True)
        raise typer.Exit(1)

    service = GmailService()
    service.send_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html=not plain_text,
        from_name=from_name,
        signature=signature,
    )


@app.command("reply")
def reply_to_message(
    message_id: Annotated[str, typer.Argument(help="Message ID to reply to.")],
    body: Annotated[
        Optional[str],
        typer.Argument(help="Reply body text."),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read body from stdin."),
    ] = False,
    plain_text: Annotated[
        bool,
        typer.Option("--plain", help="Send as plain text instead of HTML."),
    ] = False,
    from_name: Annotated[
        Optional[str],
        typer.Option("--from-name", "-n", help="Sender display name."),
    ] = None,
    signature: Annotated[
        Optional[str],
        typer.Option("--signature", "-s", help="Email signature to append."),
    ] = None,
) -> None:
    """Reply to an existing message (HTML by default)."""
    if stdin:
        body = sys.stdin.read()
    elif body is None:
        typer.echo("Error: Either provide body argument or use --stdin", err=True)
        raise typer.Exit(1)

    service = GmailService()
    service.reply_to_message(
        message_id=message_id,
        body=body,
        html=not plain_text,
        from_name=from_name,
        signature=signature,
    )


@app.command("search")
def search_messages(
    query: Annotated[str, typer.Argument(help="Gmail search query.")],
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum messages to return."),
    ] = 10,
) -> None:
    """Search messages using Gmail query syntax.

    Examples:
        from:someone@example.com
        subject:meeting
        is:unread
        has:attachment
        after:2024/01/01
    """
    service = GmailService()
    service.search_messages(query=query, max_results=max_results)


@app.command("delete")
def delete_message(
    message_id: Annotated[str, typer.Argument(help="Message ID to delete.")],
    permanent: Annotated[
        bool,
        typer.Option("--permanent", "-p", help="Permanently delete (skip trash)."),
    ] = False,
) -> None:
    """Delete a message (move to trash by default)."""
    service = GmailService()
    service.delete_message(message_id=message_id, permanent=permanent)


@app.command("mark-read")
def mark_read(
    message_id: Annotated[str, typer.Argument(help="Message ID to mark as read.")],
) -> None:
    """Mark a message as read."""
    service = GmailService()
    service.mark_as_read(message_id=message_id)


@app.command("mark-unread")
def mark_unread(
    message_id: Annotated[str, typer.Argument(help="Message ID to mark as unread.")],
) -> None:
    """Mark a message as unread."""
    service = GmailService()
    service.mark_as_unread(message_id=message_id)


# ===== Label Commands =====


@app.command("labels")
def list_labels() -> None:
    """List all labels in the mailbox."""
    service = GmailService()
    service.list_labels()


@app.command("create-label")
def create_label(
    name: Annotated[str, typer.Argument(help="Label name to create.")],
    hide_in_message_list: Annotated[
        bool,
        typer.Option("--hide-in-list", help="Hide label in message list."),
    ] = False,
    visibility: Annotated[
        str,
        typer.Option("--visibility", "-v", help="Label list visibility (labelShow, labelShowIfUnread, labelHide)."),
    ] = "labelShow",
) -> None:
    """Create a new label."""
    message_visibility = "hide" if hide_in_message_list else "show"

    service = GmailService()
    service.create_label(
        name=name,
        message_list_visibility=message_visibility,
        label_list_visibility=visibility,
    )


@app.command("delete-label")
def delete_label(
    label_id: Annotated[str, typer.Argument(help="Label ID to delete.")],
) -> None:
    """Delete a label."""
    service = GmailService()
    service.delete_label(label_id=label_id)


@app.command("add-labels")
def add_labels(
    message_id: Annotated[str, typer.Argument(help="Message ID.")],
    label_ids: Annotated[str, typer.Argument(help="Comma-separated label IDs to add.")],
) -> None:
    """Add labels to a message."""
    labels = [l.strip() for l in label_ids.split(",")]

    service = GmailService()
    service.add_labels(message_id=message_id, label_ids=labels)


@app.command("remove-labels")
def remove_labels(
    message_id: Annotated[str, typer.Argument(help="Message ID.")],
    label_ids: Annotated[str, typer.Argument(help="Comma-separated label IDs to remove.")],
) -> None:
    """Remove labels from a message."""
    labels = [l.strip() for l in label_ids.split(",")]

    service = GmailService()
    service.remove_labels(message_id=message_id, label_ids=labels)


# ===== Draft Commands =====


@app.command("drafts")
def list_drafts(
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum drafts to return."),
    ] = 10,
) -> None:
    """List drafts in the mailbox."""
    service = GmailService()
    service.list_drafts(max_results=max_results)


@app.command("get-draft")
def get_draft(
    draft_id: Annotated[str, typer.Argument(help="Draft ID to read.")],
) -> None:
    """Read a draft by ID."""
    service = GmailService()
    service.get_draft(draft_id=draft_id)


@app.command("create-draft")
def create_draft(
    to: Annotated[str, typer.Argument(help="Recipient email address.")],
    subject: Annotated[str, typer.Argument(help="Email subject.")],
    body: Annotated[
        Optional[str],
        typer.Argument(help="Email body text."),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read body from stdin."),
    ] = False,
    cc: Annotated[
        Optional[str],
        typer.Option("--cc", help="CC recipients."),
    ] = None,
    bcc: Annotated[
        Optional[str],
        typer.Option("--bcc", help="BCC recipients."),
    ] = None,
    plain_text: Annotated[
        bool,
        typer.Option("--plain", help="Create as plain text instead of HTML."),
    ] = False,
) -> None:
    """Create a new draft (HTML by default)."""
    if stdin:
        body = sys.stdin.read()
    elif body is None:
        typer.echo("Error: Either provide body argument or use --stdin", err=True)
        raise typer.Exit(1)

    service = GmailService()
    service.create_draft(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html=not plain_text,
    )


@app.command("update-draft")
def update_draft(
    draft_id: Annotated[str, typer.Argument(help="Draft ID to update.")],
    to: Annotated[
        Optional[str],
        typer.Option("--to", help="New recipient."),
    ] = None,
    subject: Annotated[
        Optional[str],
        typer.Option("--subject", "-s", help="New subject."),
    ] = None,
    body: Annotated[
        Optional[str],
        typer.Option("--body", "-b", help="New body content."),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read body from stdin."),
    ] = False,
    cc: Annotated[
        Optional[str],
        typer.Option("--cc", help="New CC recipients."),
    ] = None,
    bcc: Annotated[
        Optional[str],
        typer.Option("--bcc", help="New BCC recipients."),
    ] = None,
    plain_text: Annotated[
        bool,
        typer.Option("--plain", help="Update as plain text instead of HTML."),
    ] = False,
) -> None:
    """Update an existing draft."""
    if stdin:
        body = sys.stdin.read()

    service = GmailService()
    service.update_draft(
        draft_id=draft_id,
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html=not plain_text,
    )


@app.command("send-draft")
def send_draft(
    draft_id: Annotated[str, typer.Argument(help="Draft ID to send.")],
) -> None:
    """Send a draft."""
    service = GmailService()
    service.send_draft(draft_id=draft_id)


@app.command("delete-draft")
def delete_draft(
    draft_id: Annotated[str, typer.Argument(help="Draft ID to delete.")],
) -> None:
    """Delete a draft."""
    service = GmailService()
    service.delete_draft(draft_id=draft_id)


# ===== Attachment Commands =====


@app.command("send-with-attachment")
def send_with_attachment(
    to: Annotated[str, typer.Argument(help="Recipient email address.")],
    subject: Annotated[str, typer.Argument(help="Email subject.")],
    body: Annotated[str, typer.Argument(help="Email body text.")],
    attachments: Annotated[str, typer.Argument(help="Comma-separated file paths to attach.")],
    cc: Annotated[
        Optional[str],
        typer.Option("--cc", help="CC recipients."),
    ] = None,
    bcc: Annotated[
        Optional[str],
        typer.Option("--bcc", help="BCC recipients."),
    ] = None,
    plain_text: Annotated[
        bool,
        typer.Option("--plain", help="Send as plain text instead of HTML."),
    ] = False,
    from_name: Annotated[
        Optional[str],
        typer.Option("--from-name", "-n", help="Sender display name."),
    ] = None,
) -> None:
    """Send an email with file attachments (HTML by default)."""
    attachment_list = [p.strip() for p in attachments.split(",")]

    service = GmailService()
    service.send_with_attachment(
        to=to,
        subject=subject,
        body=body,
        attachment_paths=attachment_list,
        cc=cc,
        bcc=bcc,
        html=not plain_text,
        from_name=from_name,
    )


@app.command("list-attachments")
def list_attachments(
    message_id: Annotated[str, typer.Argument(help="Message ID.")],
) -> None:
    """List attachments in a message."""
    service = GmailService()
    service.list_attachments(message_id=message_id)


@app.command("download-attachment")
def download_attachment(
    message_id: Annotated[str, typer.Argument(help="Message ID containing the attachment.")],
    attachment_id: Annotated[str, typer.Argument(help="Attachment ID.")],
    output_path: Annotated[str, typer.Argument(help="Path to save the downloaded file.")],
) -> None:
    """Download an attachment to a file."""
    service = GmailService()
    service.download_attachment(
        message_id=message_id,
        attachment_id=attachment_id,
        output_path=output_path,
    )

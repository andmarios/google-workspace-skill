"""Gmail CLI commands."""

import sys
import typer
from typing import Annotated, Optional

from gws.commands._account import account_callback
from gws.services.gmail import GmailService

app = typer.Typer(
    name="gmail",
    help="Gmail email operations.",
    no_args_is_help=True,
    callback=account_callback,
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
    labels = [label.strip() for label in label_ids.split(",")]

    service = GmailService()
    service.add_labels(message_id=message_id, label_ids=labels)


@app.command("remove-labels")
def remove_labels(
    message_id: Annotated[str, typer.Argument(help="Message ID.")],
    label_ids: Annotated[str, typer.Argument(help="Comma-separated label IDs to remove.")],
) -> None:
    """Remove labels from a message."""
    labels = [label.strip() for label in label_ids.split(",")]

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


# ===== Thread Commands =====


@app.command("threads")
def list_threads(
    query: Annotated[
        Optional[str],
        typer.Option("--query", "-q", help="Gmail search query."),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum threads to return."),
    ] = 10,
    labels: Annotated[
        Optional[str],
        typer.Option("--labels", "-l", help="Comma-separated label IDs."),
    ] = None,
) -> None:
    """List email threads."""
    label_ids = labels.split(",") if labels else None

    service = GmailService()
    service.list_threads(
        query=query,
        max_results=max_results,
        label_ids=label_ids,
    )


@app.command("get-thread")
def get_thread(
    thread_id: Annotated[str, typer.Argument(help="Thread ID.")],
    full: Annotated[
        bool,
        typer.Option("--full", "-f", help="Get full message format."),
    ] = False,
) -> None:
    """Get a thread with all its messages."""
    format_type = "full" if full else "metadata"

    service = GmailService()
    service.get_thread(thread_id=thread_id, format_type=format_type)


@app.command("trash-thread")
def trash_thread(
    thread_id: Annotated[str, typer.Argument(help="Thread ID to trash.")],
) -> None:
    """Move a thread to trash."""
    service = GmailService()
    service.trash_thread(thread_id=thread_id)


@app.command("untrash-thread")
def untrash_thread(
    thread_id: Annotated[str, typer.Argument(help="Thread ID to restore.")],
) -> None:
    """Restore a thread from trash."""
    service = GmailService()
    service.untrash_thread(thread_id=thread_id)


@app.command("modify-thread-labels")
def modify_thread_labels(
    thread_id: Annotated[str, typer.Argument(help="Thread ID.")],
    add_labels: Annotated[
        Optional[str],
        typer.Option("--add", "-a", help="Comma-separated label IDs to add."),
    ] = None,
    remove_labels: Annotated[
        Optional[str],
        typer.Option("--remove", "-r", help="Comma-separated label IDs to remove."),
    ] = None,
) -> None:
    """Add or remove labels from all messages in a thread."""
    add_label_ids = [label.strip() for label in add_labels.split(",")] if add_labels else None
    remove_label_ids = [label.strip() for label in remove_labels.split(",")] if remove_labels else None

    service = GmailService()
    service.modify_thread_labels(
        thread_id=thread_id,
        add_label_ids=add_label_ids,
        remove_label_ids=remove_label_ids,
    )


# ===== Settings Commands =====


@app.command("get-vacation")
def get_vacation_settings() -> None:
    """Get vacation responder settings."""
    service = GmailService()
    service.get_vacation_settings()


@app.command("set-vacation")
def set_vacation_settings(
    enable: Annotated[bool, typer.Argument(help="Enable (true) or disable (false) vacation responder.")],
    subject: Annotated[
        Optional[str],
        typer.Option("--subject", "-s", help="Response subject line."),
    ] = None,
    message: Annotated[
        Optional[str],
        typer.Option("--message", "-m", help="Plain text response message."),
    ] = None,
    html_message: Annotated[
        Optional[str],
        typer.Option("--html", help="HTML response message."),
    ] = None,
    start_time: Annotated[
        Optional[int],
        typer.Option("--start", help="Start time (Unix timestamp in milliseconds)."),
    ] = None,
    end_time: Annotated[
        Optional[int],
        typer.Option("--end", help="End time (Unix timestamp in milliseconds)."),
    ] = None,
    restrict_to_contacts: Annotated[
        bool,
        typer.Option("--contacts-only", help="Only respond to contacts."),
    ] = False,
    restrict_to_domain: Annotated[
        bool,
        typer.Option("--domain-only", help="Only respond to same domain."),
    ] = False,
) -> None:
    """Set vacation responder settings."""
    service = GmailService()
    service.set_vacation_settings(
        enable=enable,
        subject=subject,
        message=message,
        html_message=html_message,
        start_time=start_time,
        end_time=end_time,
        restrict_to_contacts=restrict_to_contacts,
        restrict_to_domain=restrict_to_domain,
    )


@app.command("get-signature")
def get_signature(
    send_as_email: Annotated[
        Optional[str],
        typer.Option("--email", "-e", help="Send-as email address (default: primary)."),
    ] = None,
) -> None:
    """Get email signature."""
    service = GmailService()
    service.get_signature(send_as_email=send_as_email)


@app.command("set-signature")
def set_signature(
    signature: Annotated[str, typer.Argument(help="HTML signature content.")],
    send_as_email: Annotated[
        Optional[str],
        typer.Option("--email", "-e", help="Send-as email address (default: primary)."),
    ] = None,
) -> None:
    """Set email signature."""
    service = GmailService()
    service.set_signature(signature=signature, send_as_email=send_as_email)


# ===== Filters =====


@app.command("filters")
def list_filters() -> None:
    """List all mail filters."""
    service = GmailService()
    service.list_filters()


@app.command("get-filter")
def get_filter(
    filter_id: Annotated[str, typer.Argument(help="Filter ID to retrieve.")],
) -> None:
    """Get a specific mail filter."""
    service = GmailService()
    service.get_filter(filter_id=filter_id)


@app.command("create-filter")
def create_filter(
    from_address: Annotated[
        Optional[str],
        typer.Option("--from", "-f", help="Match messages from this address."),
    ] = None,
    to_address: Annotated[
        Optional[str],
        typer.Option("--to", "-t", help="Match messages to this address."),
    ] = None,
    subject: Annotated[
        Optional[str],
        typer.Option("--subject", "-s", help="Match messages with this subject."),
    ] = None,
    query: Annotated[
        Optional[str],
        typer.Option("--query", "-q", help="Gmail search query to match."),
    ] = None,
    has_attachment: Annotated[
        Optional[bool],
        typer.Option("--has-attachment", help="Match messages with attachments."),
    ] = None,
    add_labels: Annotated[
        Optional[str],
        typer.Option("--add-labels", help="Comma-separated label IDs to add."),
    ] = None,
    remove_labels: Annotated[
        Optional[str],
        typer.Option("--remove-labels", help="Comma-separated label IDs to remove."),
    ] = None,
    archive: Annotated[
        bool,
        typer.Option("--archive", help="Skip inbox (archive) matching messages."),
    ] = False,
    star: Annotated[
        bool,
        typer.Option("--star", help="Star matching messages."),
    ] = False,
    mark_important: Annotated[
        Optional[bool],
        typer.Option("--important/--not-important", help="Mark as important or not."),
    ] = None,
    never_spam: Annotated[
        bool,
        typer.Option("--never-spam", help="Never send to spam."),
    ] = False,
    trash: Annotated[
        bool,
        typer.Option("--trash", help="Delete matching messages."),
    ] = False,
    forward_to: Annotated[
        Optional[str],
        typer.Option("--forward", help="Forward to this email address."),
    ] = None,
) -> None:
    """Create a mail filter.

    Example: Create filter to archive newsletters:
        gws gmail create-filter --from newsletter@example.com --archive --add-labels Label_123
    """
    add_label_ids = [label.strip() for label in add_labels.split(",")] if add_labels else None
    remove_label_ids = [label.strip() for label in remove_labels.split(",")] if remove_labels else None

    service = GmailService()
    service.create_filter(
        from_address=from_address,
        to_address=to_address,
        subject=subject,
        query=query,
        has_attachment=has_attachment,
        add_label_ids=add_label_ids,
        remove_label_ids=remove_label_ids,
        archive=archive,
        star=star,
        mark_important=mark_important,
        never_spam=never_spam,
        trash=trash,
        forward_to=forward_to,
    )


@app.command("delete-filter")
def delete_filter(
    filter_id: Annotated[str, typer.Argument(help="Filter ID to delete.")],
) -> None:
    """Delete a mail filter."""
    service = GmailService()
    service.delete_filter(filter_id=filter_id)


# ===== Additional Message Operations =====


@app.command("untrash")
def untrash_message(
    message_id: Annotated[str, typer.Argument(help="Message ID to restore from trash.")],
) -> None:
    """Remove a message from trash."""
    service = GmailService()
    service.untrash_message(message_id=message_id)


@app.command("batch-modify")
def batch_modify_messages(
    message_ids: Annotated[str, typer.Argument(help="Comma-separated message IDs.")],
    add_labels: Annotated[
        Optional[str],
        typer.Option("--add-labels", "-a", help="Comma-separated label IDs to add."),
    ] = None,
    remove_labels: Annotated[
        Optional[str],
        typer.Option("--remove-labels", "-r", help="Comma-separated label IDs to remove."),
    ] = None,
) -> None:
    """Modify labels on multiple messages at once."""
    ids = [m.strip() for m in message_ids.split(",")]
    add_label_ids = [label.strip() for label in add_labels.split(",")] if add_labels else None
    remove_label_ids = [label.strip() for label in remove_labels.split(",")] if remove_labels else None

    service = GmailService()
    service.batch_modify_messages(
        message_ids=ids,
        add_label_ids=add_label_ids,
        remove_label_ids=remove_label_ids,
    )


# ===== Label Operations (extended) =====


@app.command("get-label")
def get_label(
    label_id: Annotated[str, typer.Argument(help="Label ID.")],
) -> None:
    """Get details of a specific label."""
    service = GmailService()
    service.get_label(label_id=label_id)


@app.command("update-label")
def update_label(
    label_id: Annotated[str, typer.Argument(help="Label ID to update.")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="New label name."),
    ] = None,
    message_list_visibility: Annotated[
        Optional[str],
        typer.Option("--message-visibility", help="'show' or 'hide' in message list."),
    ] = None,
    label_list_visibility: Annotated[
        Optional[str],
        typer.Option("--label-visibility", help="'labelShow', 'labelShowIfUnread', or 'labelHide'."),
    ] = None,
    text_color: Annotated[
        Optional[str],
        typer.Option("--text-color", help="Text color (hex, e.g., '#000000')."),
    ] = None,
    background_color: Annotated[
        Optional[str],
        typer.Option("--background-color", help="Background color (hex)."),
    ] = None,
) -> None:
    """Update a label's name, visibility, or colors."""
    service = GmailService()
    service.update_label(
        label_id=label_id,
        name=name,
        message_list_visibility=message_list_visibility,
        label_list_visibility=label_list_visibility,
        text_color=text_color,
        background_color=background_color,
    )


# ===== Thread Operations (extended) =====


@app.command("delete-thread")
def delete_thread(
    thread_id: Annotated[str, typer.Argument(help="Thread ID to permanently delete.")],
) -> None:
    """Permanently delete a thread (cannot be undone)."""
    service = GmailService()
    service.delete_thread(thread_id=thread_id)


# ===== History =====


@app.command("history")
def list_history(
    start_history_id: Annotated[str, typer.Argument(help="History ID to start from.")],
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of history records."),
    ] = 100,
    history_types: Annotated[
        Optional[str],
        typer.Option("--types", "-t", help="Comma-separated types (messageAdded,messageDeleted,labelAdded,labelRemoved)."),
    ] = None,
    label_id: Annotated[
        Optional[str],
        typer.Option("--label", "-l", help="Only return changes to messages with this label."),
    ] = None,
) -> None:
    """List changes to the mailbox since a given history ID."""
    types = [t.strip() for t in history_types.split(",")] if history_types else None

    service = GmailService()
    service.list_history(
        start_history_id=start_history_id,
        max_results=max_results,
        history_types=types,
        label_id=label_id,
    )

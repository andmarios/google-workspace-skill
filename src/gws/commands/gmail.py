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
    html: Annotated[
        bool,
        typer.Option("--html", help="Send as HTML email."),
    ] = False,
) -> None:
    """Send an email message."""
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
        html=html,
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
    html: Annotated[
        bool,
        typer.Option("--html", help="Send as HTML reply."),
    ] = False,
) -> None:
    """Reply to an existing message."""
    if stdin:
        body = sys.stdin.read()
    elif body is None:
        typer.echo("Error: Either provide body argument or use --stdin", err=True)
        raise typer.Exit(1)

    service = GmailService()
    service.reply_to_message(
        message_id=message_id,
        body=body,
        html=html,
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

"""Google Gmail service operations."""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode


class GmailService(BaseService):
    """Google Gmail operations."""

    SERVICE_NAME = "gmail"
    VERSION = "v1"

    def list_messages(
        self,
        query: str | None = None,
        max_results: int = 10,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """List messages matching criteria."""
        try:
            params: dict[str, Any] = {
                "userId": "me",
                "maxResults": max_results,
            }

            if query:
                params["q"] = query
            if label_ids:
                params["labelIds"] = label_ids

            result = self.service.users().messages().list(**params).execute()

            messages = []
            for msg_ref in result.get("messages", []):
                # Get minimal message info
                msg = (
                    self.service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_ref["id"],
                        format="metadata",
                        metadataHeaders=["From", "To", "Subject", "Date"],
                    )
                    .execute()
                )

                headers = {
                    h["name"]: h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }

                messages.append({
                    "id": msg["id"],
                    "thread_id": msg["threadId"],
                    "subject": headers.get("Subject", "(no subject)"),
                    "from": headers.get("From", ""),
                    "to": headers.get("To", ""),
                    "date": headers.get("Date", ""),
                    "snippet": msg.get("snippet", "")[:100],
                })

            output_success(
                operation="gmail.list",
                message_count=len(messages),
                messages=messages,
                next_page_token=result.get("nextPageToken"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.list",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def read_message(
        self,
        message_id: str,
        format_type: str = "full",
    ) -> dict[str, Any]:
        """Read a message by ID."""
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format=format_type)
                .execute()
            )

            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            # Extract body
            body = self._extract_body(msg.get("payload", {}))

            # Extract attachments info
            attachments = self._extract_attachments(msg.get("payload", {}))

            output_success(
                operation="gmail.read",
                message_id=message_id,
                thread_id=msg["threadId"],
                subject=headers.get("Subject", "(no subject)"),
                from_address=headers.get("From", ""),
                to_address=headers.get("To", ""),
                cc=headers.get("Cc", ""),
                date=headers.get("Date", ""),
                labels=msg.get("labelIds", []),
                body=body,
                attachments=attachments,
            )
            return msg
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.read",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def _extract_body(self, payload: dict) -> str:
        """Extract message body from payload."""
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if "data" in part.get("body", {}):
                        return base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
                elif part["mimeType"] == "multipart/alternative":
                    return self._extract_body(part)

        return ""

    def _extract_attachments(self, payload: dict) -> list[dict]:
        """Extract attachment info from payload."""
        attachments = []

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("filename"):
                    attachments.append({
                        "filename": part["filename"],
                        "mime_type": part["mimeType"],
                        "size": part.get("body", {}).get("size", 0),
                        "attachment_id": part.get("body", {}).get("attachmentId"),
                    })
                if "parts" in part:
                    attachments.extend(self._extract_attachments(part))

        return attachments

    def get_profile(self) -> dict[str, Any]:
        """Get the current user's Gmail profile."""
        try:
            profile = self.service.users().getProfile(userId="me").execute()
            return profile
        except HttpError:
            return {}

    def _unescape_text(self, text: str) -> str:
        """Remove unnecessary escape sequences from text.

        This handles cases where shell environments escape special characters
        like exclamation marks (\\! -> !).
        """
        # Unescape common shell-escaped characters
        return text.replace("\\!", "!")

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
        html: bool = False,
        from_name: str | None = None,
        signature: str | None = None,
    ) -> dict[str, Any]:
        """Send a new email message."""
        try:
            # Unescape shell-escaped characters
            subject = self._unescape_text(subject)
            body = self._unescape_text(body)
            if signature:
                signature = self._unescape_text(signature)

            # Append signature if provided
            full_body = body
            if signature:
                full_body = f"{body}\n\n--\n{signature}"

            # Use MIMEText directly - MIMEMultipart only needed for attachments
            subtype = "html" if html else "plain"
            message = MIMEText(full_body, subtype, "utf-8")

            message["to"] = to
            message["subject"] = subject

            # Set From with display name if provided
            if from_name:
                profile = self.get_profile()
                email_address = profile.get("emailAddress", "")
                if email_address:
                    message["from"] = f'"{from_name}" <{email_address}>'

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )

            output_success(
                operation="gmail.send",
                message_id=result["id"],
                thread_id=result["threadId"],
                to=to,
                subject=subject,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.send",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def reply_to_message(
        self,
        message_id: str,
        body: str,
        html: bool = False,
        from_name: str | None = None,
        signature: str | None = None,
    ) -> dict[str, Any]:
        """Reply to an existing message."""
        try:
            # Unescape shell-escaped characters
            body = self._unescape_text(body)
            if signature:
                signature = self._unescape_text(signature)

            # Get the original message
            original = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="metadata")
                .execute()
            )

            thread_id = original["threadId"]
            headers = {
                h["name"]: h["value"]
                for h in original.get("payload", {}).get("headers", [])
            }

            # Append signature if provided
            full_body = body
            if signature:
                full_body = f"{body}\n\n--\n{signature}"

            # Build reply - use MIMEText directly
            subtype = "html" if html else "plain"
            message = MIMEText(full_body, subtype, "utf-8")

            # Set From with display name if provided
            if from_name:
                profile = self.get_profile()
                email_address = profile.get("emailAddress", "")
                if email_address:
                    message["from"] = f'"{from_name}" <{email_address}>'

            # Reply to the sender
            reply_to = headers.get("Reply-To", headers.get("From", ""))
            message["to"] = reply_to
            message["subject"] = f"Re: {headers.get('Subject', '')}"

            # Set references for threading
            message_id_header = headers.get("Message-ID", "")
            if message_id_header:
                message["In-Reply-To"] = message_id_header
                message["References"] = message_id_header

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw, "threadId": thread_id})
                .execute()
            )

            output_success(
                operation="gmail.reply",
                message_id=result["id"],
                thread_id=result["threadId"],
                to=reply_to,
                subject=message["subject"],
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.reply",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def search_messages(
        self,
        query: str,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Search messages using Gmail query syntax."""
        return self.list_messages(query=query, max_results=max_results)

    def delete_message(
        self,
        message_id: str,
        permanent: bool = False,
    ) -> dict[str, Any]:
        """Delete a message (move to trash or permanent delete)."""
        try:
            if permanent:
                self.service.users().messages().delete(
                    userId="me", id=message_id
                ).execute()
                output_success(
                    operation="gmail.delete",
                    message_id=message_id,
                    permanent=True,
                )
            else:
                result = (
                    self.service.users()
                    .messages()
                    .trash(userId="me", id=message_id)
                    .execute()
                )
                output_success(
                    operation="gmail.delete",
                    message_id=message_id,
                    permanent=False,
                    moved_to_trash=True,
                )
                return result

            return {"id": message_id, "deleted": True}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.delete",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def mark_as_read(self, message_id: str) -> dict[str, Any]:
        """Mark a message as read by removing the UNREAD label."""
        try:
            result = (
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": ["UNREAD"]},
                )
                .execute()
            )
            output_success(
                operation="gmail.mark-read",
                message_id=message_id,
                labels=result.get("labelIds", []),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.mark-read",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def mark_as_unread(self, message_id: str) -> dict[str, Any]:
        """Mark a message as unread by adding the UNREAD label."""
        try:
            result = (
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"addLabelIds": ["UNREAD"]},
                )
                .execute()
            )
            output_success(
                operation="gmail.mark-unread",
                message_id=message_id,
                labels=result.get("labelIds", []),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.mark-unread",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

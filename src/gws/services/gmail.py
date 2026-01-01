"""Google Gmail service operations."""

import base64
import mimetypes
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
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

    # ===== Label Operations =====

    def list_labels(self) -> dict[str, Any]:
        """List all labels in the mailbox."""
        try:
            result = self.service.users().labels().list(userId="me").execute()

            labels = []
            for label in result.get("labels", []):
                labels.append({
                    "id": label["id"],
                    "name": label["name"],
                    "type": label.get("type", "user"),
                    "message_list_visibility": label.get("messageListVisibility"),
                    "label_list_visibility": label.get("labelListVisibility"),
                })

            output_success(
                operation="gmail.list_labels",
                label_count=len(labels),
                labels=labels,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.list_labels",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_label(
        self,
        name: str,
        message_list_visibility: str = "show",
        label_list_visibility: str = "labelShow",
    ) -> dict[str, Any]:
        """Create a new label.

        Args:
            name: Label name.
            message_list_visibility: Show label in message list (show/hide).
            label_list_visibility: Show in label list (labelShow/labelShowIfUnread/labelHide).
        """
        try:
            label_body = {
                "name": name,
                "messageListVisibility": message_list_visibility,
                "labelListVisibility": label_list_visibility,
            }

            result = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_body)
                .execute()
            )

            output_success(
                operation="gmail.create_label",
                label_id=result["id"],
                name=result["name"],
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.create_label",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_label(self, label_id: str) -> dict[str, Any]:
        """Delete a label.

        Args:
            label_id: The label ID to delete.
        """
        try:
            self.service.users().labels().delete(userId="me", id=label_id).execute()

            output_success(
                operation="gmail.delete_label",
                label_id=label_id,
            )
            return {"deleted": True, "label_id": label_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.delete_label",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_labels(
        self,
        message_id: str,
        label_ids: list[str],
    ) -> dict[str, Any]:
        """Add labels to a message.

        Args:
            message_id: The message ID.
            label_ids: List of label IDs to add.
        """
        try:
            result = (
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"addLabelIds": label_ids},
                )
                .execute()
            )

            output_success(
                operation="gmail.add_labels",
                message_id=message_id,
                added_labels=label_ids,
                current_labels=result.get("labelIds", []),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.add_labels",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def remove_labels(
        self,
        message_id: str,
        label_ids: list[str],
    ) -> dict[str, Any]:
        """Remove labels from a message.

        Args:
            message_id: The message ID.
            label_ids: List of label IDs to remove.
        """
        try:
            result = (
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": label_ids},
                )
                .execute()
            )

            output_success(
                operation="gmail.remove_labels",
                message_id=message_id,
                removed_labels=label_ids,
                current_labels=result.get("labelIds", []),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.remove_labels",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # ===== Draft Operations =====

    def list_drafts(self, max_results: int = 10) -> dict[str, Any]:
        """List drafts in the mailbox.

        Args:
            max_results: Maximum number of drafts to return.
        """
        try:
            result = (
                self.service.users()
                .drafts()
                .list(userId="me", maxResults=max_results)
                .execute()
            )

            drafts = []
            for draft_ref in result.get("drafts", []):
                # Get draft details
                draft = (
                    self.service.users()
                    .drafts()
                    .get(userId="me", id=draft_ref["id"], format="metadata")
                    .execute()
                )

                msg = draft.get("message", {})
                headers = {
                    h["name"]: h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }

                drafts.append({
                    "id": draft["id"],
                    "message_id": msg.get("id"),
                    "subject": headers.get("Subject", "(no subject)"),
                    "to": headers.get("To", ""),
                    "snippet": msg.get("snippet", "")[:100],
                })

            output_success(
                operation="gmail.list_drafts",
                draft_count=len(drafts),
                drafts=drafts,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.list_drafts",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_draft(self, draft_id: str) -> dict[str, Any]:
        """Get a draft by ID.

        Args:
            draft_id: The draft ID.
        """
        try:
            draft = (
                self.service.users()
                .drafts()
                .get(userId="me", id=draft_id, format="full")
                .execute()
            )

            msg = draft.get("message", {})
            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            body = self._extract_body(msg.get("payload", {}))

            output_success(
                operation="gmail.get_draft",
                draft_id=draft["id"],
                message_id=msg.get("id"),
                subject=headers.get("Subject", "(no subject)"),
                to=headers.get("To", ""),
                cc=headers.get("Cc", ""),
                body=body,
            )
            return draft
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.get_draft",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
        html: bool = False,
    ) -> dict[str, Any]:
        """Create a new draft.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body content.
            cc: CC recipients.
            bcc: BCC recipients.
            html: If True, body is HTML.
        """
        try:
            # Unescape shell-escaped characters
            subject = self._unescape_text(subject)
            body = self._unescape_text(body)

            subtype = "html" if html else "plain"
            message = MIMEText(body, subtype, "utf-8")

            message["to"] = to
            message["subject"] = subject

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = (
                self.service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )

            output_success(
                operation="gmail.create_draft",
                draft_id=result["id"],
                to=to,
                subject=subject,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.create_draft",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_draft(
        self,
        draft_id: str,
        to: str | None = None,
        subject: str | None = None,
        body: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        html: bool = False,
    ) -> dict[str, Any]:
        """Update an existing draft.

        Args:
            draft_id: The draft ID to update.
            to: New recipient (optional).
            subject: New subject (optional).
            body: New body content (optional).
            cc: New CC recipients (optional).
            bcc: New BCC recipients (optional).
            html: If True, body is HTML.
        """
        try:
            # Get current draft to preserve values
            current_draft = (
                self.service.users()
                .drafts()
                .get(userId="me", id=draft_id, format="full")
                .execute()
            )

            current_msg = current_draft.get("message", {})
            current_headers = {
                h["name"]: h["value"]
                for h in current_msg.get("payload", {}).get("headers", [])
            }
            current_body = self._extract_body(current_msg.get("payload", {}))

            # Use new values or preserve existing
            final_to = to if to is not None else current_headers.get("To", "")
            final_subject = subject if subject is not None else current_headers.get("Subject", "")
            final_body = body if body is not None else current_body
            final_cc = cc if cc is not None else current_headers.get("Cc")
            final_bcc = bcc if bcc is not None else current_headers.get("Bcc")

            # Unescape shell-escaped characters
            final_subject = self._unescape_text(final_subject)
            final_body = self._unescape_text(final_body)

            subtype = "html" if html else "plain"
            message = MIMEText(final_body, subtype, "utf-8")

            message["to"] = final_to
            message["subject"] = final_subject

            if final_cc:
                message["cc"] = final_cc
            if final_bcc:
                message["bcc"] = final_bcc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = (
                self.service.users()
                .drafts()
                .update(
                    userId="me",
                    id=draft_id,
                    body={"message": {"raw": raw}},
                )
                .execute()
            )

            output_success(
                operation="gmail.update_draft",
                draft_id=result["id"],
                to=final_to,
                subject=final_subject,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.update_draft",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def send_draft(self, draft_id: str) -> dict[str, Any]:
        """Send a draft.

        Args:
            draft_id: The draft ID to send.
        """
        try:
            result = (
                self.service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )

            output_success(
                operation="gmail.send_draft",
                message_id=result["id"],
                thread_id=result.get("threadId"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.send_draft",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_draft(self, draft_id: str) -> dict[str, Any]:
        """Delete a draft.

        Args:
            draft_id: The draft ID to delete.
        """
        try:
            self.service.users().drafts().delete(userId="me", id=draft_id).execute()

            output_success(
                operation="gmail.delete_draft",
                draft_id=draft_id,
            )
            return {"deleted": True, "draft_id": draft_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.delete_draft",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # ===== Attachment Operations =====

    def send_with_attachment(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_paths: list[str],
        cc: str | None = None,
        bcc: str | None = None,
        html: bool = False,
        from_name: str | None = None,
    ) -> dict[str, Any]:
        """Send an email with file attachments.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body content.
            attachment_paths: List of file paths to attach.
            cc: CC recipients.
            bcc: BCC recipients.
            html: If True, body is HTML.
            from_name: Sender display name.
        """
        try:
            # Unescape shell-escaped characters
            subject = self._unescape_text(subject)
            body = self._unescape_text(body)

            # Create multipart message for attachments
            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject

            if from_name:
                profile = self.get_profile()
                email_address = profile.get("emailAddress", "")
                if email_address:
                    message["from"] = f'"{from_name}" <{email_address}>'

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            # Add body
            subtype = "html" if html else "plain"
            message.attach(MIMEText(body, subtype, "utf-8"))

            # Add attachments
            attached_files = []
            for file_path in attachment_paths:
                if not os.path.isfile(file_path):
                    output_error(
                        error_code="NOT_FOUND",
                        operation="gmail.send_with_attachment",
                        message=f"File not found: {file_path}",
                    )
                    raise SystemExit(ExitCode.NOT_FOUND)

                # Guess MIME type
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    content_type = "application/octet-stream"

                main_type, sub_type = content_type.split("/", 1)

                with open(file_path, "rb") as f:
                    attachment = MIMEBase(main_type, sub_type)
                    attachment.set_payload(f.read())

                encoders.encode_base64(attachment)
                filename = os.path.basename(file_path)
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=filename,
                )
                message.attach(attachment)
                attached_files.append(filename)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )

            output_success(
                operation="gmail.send_with_attachment",
                message_id=result["id"],
                thread_id=result["threadId"],
                to=to,
                subject=subject,
                attachments=attached_files,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.send_with_attachment",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_attachments(self, message_id: str) -> dict[str, Any]:
        """List attachments in a message.

        Args:
            message_id: The message ID.
        """
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            attachments = self._extract_attachments(msg.get("payload", {}))

            output_success(
                operation="gmail.list_attachments",
                message_id=message_id,
                attachment_count=len(attachments),
                attachments=attachments,
            )
            return {"message_id": message_id, "attachments": attachments}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.list_attachments",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        output_path: str,
    ) -> dict[str, Any]:
        """Download an attachment to a file.

        Args:
            message_id: The message ID containing the attachment.
            attachment_id: The attachment ID.
            output_path: Path to save the downloaded file.
        """
        try:
            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            # Decode base64 data
            data = attachment.get("data", "")
            file_data = base64.urlsafe_b64decode(data)

            # Write to file
            with open(output_path, "wb") as f:
                f.write(file_data)

            output_success(
                operation="gmail.download_attachment",
                message_id=message_id,
                attachment_id=attachment_id,
                output_path=output_path,
                size=len(file_data),
            )
            return {"output_path": output_path, "size": len(file_data)}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.download_attachment",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # THREAD OPERATIONS
    # =========================================================================

    def list_threads(
        self,
        query: str | None = None,
        max_results: int = 10,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """List email threads.

        Args:
            query: Gmail search query (same syntax as search_messages).
            max_results: Maximum number of threads to return.
            label_ids: List of label IDs to filter by.
        """
        try:
            params: dict[str, Any] = {
                "userId": "me",
                "maxResults": max_results,
            }
            if query:
                params["q"] = query
            if label_ids:
                params["labelIds"] = label_ids

            result = self.service.users().threads().list(**params).execute()

            threads = []
            for thread in result.get("threads", []):
                thread_id = thread.get("id")
                snippet = thread.get("snippet", "")
                threads.append({
                    "thread_id": thread_id,
                    "snippet": snippet[:100] + "..." if len(snippet) > 100 else snippet,
                })

            output_success(
                operation="gmail.list_threads",
                thread_count=len(threads),
                threads=threads,
            )
            return {"threads": threads}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.list_threads",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_thread(
        self,
        thread_id: str,
        format_type: str = "metadata",
    ) -> dict[str, Any]:
        """Get a thread with all its messages.

        Args:
            thread_id: The thread ID.
            format_type: Message format (full, metadata, minimal).
        """
        try:
            thread = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format=format_type)
                .execute()
            )

            messages = []
            for msg in thread.get("messages", []):
                msg_info = {
                    "message_id": msg.get("id"),
                    "snippet": msg.get("snippet", "")[:100],
                }

                # Extract headers if available
                headers = msg.get("payload", {}).get("headers", [])
                for header in headers:
                    name = header.get("name", "").lower()
                    if name in ("from", "to", "subject", "date"):
                        msg_info[name] = header.get("value", "")

                messages.append(msg_info)

            output_success(
                operation="gmail.get_thread",
                thread_id=thread_id,
                message_count=len(messages),
                messages=messages,
            )
            return {"thread_id": thread_id, "messages": messages}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.get_thread",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def trash_thread(self, thread_id: str) -> dict[str, Any]:
        """Move a thread to trash.

        Args:
            thread_id: The thread ID.
        """
        try:
            self.service.users().threads().trash(userId="me", id=thread_id).execute()

            output_success(
                operation="gmail.trash_thread",
                thread_id=thread_id,
            )
            return {"thread_id": thread_id, "status": "trashed"}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.trash_thread",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def untrash_thread(self, thread_id: str) -> dict[str, Any]:
        """Remove a thread from trash.

        Args:
            thread_id: The thread ID.
        """
        try:
            self.service.users().threads().untrash(userId="me", id=thread_id).execute()

            output_success(
                operation="gmail.untrash_thread",
                thread_id=thread_id,
            )
            return {"thread_id": thread_id, "status": "untrashed"}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.untrash_thread",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def modify_thread_labels(
        self,
        thread_id: str,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add or remove labels from all messages in a thread.

        Args:
            thread_id: The thread ID.
            add_label_ids: Label IDs to add.
            remove_label_ids: Label IDs to remove.
        """
        try:
            body: dict[str, Any] = {}
            if add_label_ids:
                body["addLabelIds"] = add_label_ids
            if remove_label_ids:
                body["removeLabelIds"] = remove_label_ids

            if not body:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="gmail.modify_thread_labels",
                    message="Must specify labels to add or remove",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            self.service.users().threads().modify(
                userId="me", id=thread_id, body=body
            ).execute()

            output_success(
                operation="gmail.modify_thread_labels",
                thread_id=thread_id,
                added_labels=add_label_ids or [],
                removed_labels=remove_label_ids or [],
            )
            return {"thread_id": thread_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.modify_thread_labels",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # SETTINGS
    # =========================================================================

    def get_vacation_settings(self) -> dict[str, Any]:
        """Get vacation responder settings."""
        try:
            settings = (
                self.service.users()
                .settings()
                .getVacation(userId="me")
                .execute()
            )

            output_success(
                operation="gmail.get_vacation_settings",
                enabled=settings.get("enableAutoReply", False),
                subject=settings.get("responseSubject", ""),
                body_plain_text=settings.get("responseBodyPlainText", ""),
                restrict_to_contacts=settings.get("restrictToContacts", False),
                restrict_to_domain=settings.get("restrictToDomain", False),
                start_time=settings.get("startTime"),
                end_time=settings.get("endTime"),
            )
            return settings
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.get_vacation_settings",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_vacation_settings(
        self,
        enable: bool,
        subject: str | None = None,
        message: str | None = None,
        html_message: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        restrict_to_contacts: bool = False,
        restrict_to_domain: bool = False,
    ) -> dict[str, Any]:
        """Set vacation responder settings.

        Args:
            enable: Whether to enable the vacation responder.
            subject: Response subject line.
            message: Plain text response message.
            html_message: HTML response message.
            start_time: Start time (Unix timestamp in milliseconds).
            end_time: End time (Unix timestamp in milliseconds).
            restrict_to_contacts: Only respond to contacts.
            restrict_to_domain: Only respond to same domain.
        """
        try:
            body: dict[str, Any] = {
                "enableAutoReply": enable,
                "restrictToContacts": restrict_to_contacts,
                "restrictToDomain": restrict_to_domain,
            }

            if subject:
                body["responseSubject"] = subject
            if message:
                body["responseBodyPlainText"] = message
            if html_message:
                body["responseBodyHtml"] = html_message
            if start_time:
                body["startTime"] = start_time
            if end_time:
                body["endTime"] = end_time

            result = (
                self.service.users()
                .settings()
                .updateVacation(userId="me", body=body)
                .execute()
            )

            output_success(
                operation="gmail.set_vacation_settings",
                enabled=enable,
                subject=subject,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.set_vacation_settings",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_signature(self, send_as_email: str | None = None) -> dict[str, Any]:
        """Get email signature.

        Args:
            send_as_email: Email address of the send-as alias (default: primary).
        """
        try:
            # Get primary email if not specified
            if not send_as_email:
                profile = self.service.users().getProfile(userId="me").execute()
                send_as_email = profile.get("emailAddress", "")

            result = (
                self.service.users()
                .settings()
                .sendAs()
                .get(userId="me", sendAsEmail=send_as_email)
                .execute()
            )

            output_success(
                operation="gmail.get_signature",
                send_as_email=send_as_email,
                signature=result.get("signature", ""),
                display_name=result.get("displayName", ""),
                is_primary=result.get("isPrimary", False),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.get_signature",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_signature(
        self,
        signature: str,
        send_as_email: str | None = None,
    ) -> dict[str, Any]:
        """Set email signature.

        Args:
            signature: HTML signature content.
            send_as_email: Email address of the send-as alias (default: primary).
        """
        try:
            # Get primary email if not specified
            if not send_as_email:
                profile = self.service.users().getProfile(userId="me").execute()
                send_as_email = profile.get("emailAddress", "")

            result = (
                self.service.users()
                .settings()
                .sendAs()
                .patch(
                    userId="me",
                    sendAsEmail=send_as_email,
                    body={"signature": signature}
                )
                .execute()
            )

            output_success(
                operation="gmail.set_signature",
                send_as_email=send_as_email,
                signature_length=len(signature),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.set_signature",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

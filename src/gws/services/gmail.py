"""Google Gmail service operations."""

import base64
import json
import mimetypes
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, getaddresses
from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error, output_external_content, screen_download
from gws.exceptions import ExitCode

# Gmail batch HTTP requests are limited to 100 individual requests per batch.
# https://developers.google.com/workspace/gmail/api/guides/batch
_BATCH_LIMIT = 100


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

            result = self.execute(self.service.users().messages().list(**params))

            messages: list[dict[str, Any]] = []
            batch_errors: dict[str, str] = {}
            msg_refs = result.get("messages", [])

            if msg_refs:
                # Use batch requests to fetch messages (chunked to stay within
                # Gmail's 100-requests-per-batch limit)
                batch_results: dict[str, Any] = {}

                def handle_response(request_id: str, response: Any, exception: Any) -> None:
                    if exception is None:
                        batch_results[request_id] = response
                    else:
                        batch_errors[request_id] = str(exception)

                for i in range(0, len(msg_refs), _BATCH_LIMIT):
                    chunk = msg_refs[i : i + _BATCH_LIMIT]
                    batch = self.service.new_batch_http_request(callback=handle_response)
                    for msg_ref in chunk:
                        batch.add(
                            self.service.users()
                            .messages()
                            .get(
                                userId="me",
                                id=msg_ref["id"],
                                format="metadata",
                                metadataHeaders=["From", "To", "Subject", "Date"],
                            ),
                            request_id=msg_ref["id"],
                        )
                    batch.execute()

                # Process batch results in original order
                for msg_ref in msg_refs:
                    msg = batch_results.get(msg_ref["id"])
                    if not msg:
                        continue

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

            ext_kwargs: dict[str, Any] = {
                "message_count": len(messages),
                "next_page_token": result.get("nextPageToken"),
            }
            if batch_errors:
                ext_kwargs["failed_ids"] = batch_errors
            output_external_content(
                operation="gmail.list",
                source_type="email",
                source_id=f"gmail.list:{query or 'all'}",
                content_fields={"messages": json.dumps(messages, default=str)},
                **ext_kwargs,
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
            msg = self.execute(
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format=format_type)
            )

            # Build case-insensitive header lookup (Gmail API may return lowercase
            # header names for messages sent via the API)
            raw_headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            headers = {k.lower(): v for k, v in raw_headers.items()}

            # Extract body
            body = self._extract_body(msg.get("payload", {}))

            # Extract attachments info
            attachments = self._extract_attachments(msg.get("payload", {}))

            output_external_content(
                operation="gmail.read",
                source_type="email",
                source_id=message_id,
                content_fields={
                    "subject": headers.get("subject", "(no subject)"),
                    "body": body,
                },
                message_id=message_id,
                thread_id=msg["threadId"],
                history_id=msg.get("historyId"),
                from_address=headers.get("from", ""),
                to_address=headers.get("to", ""),
                cc=headers.get("cc", ""),
                date=headers.get("date", ""),
                labels=msg.get("labelIds", []),
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

    def _header_map(self, payload: dict) -> dict[str, str]:
        """Return a case-insensitive header map keyed by lowercase name.

        Gmail returns header names with the case they were written in. Messages
        built locally via MIMEText use lowercase names ('to', 'cc', 'subject'),
        so any read of draft/self-built headers MUST look them up case-
        insensitively or they come back empty.
        """
        return {
            h["name"].lower(): h["value"]
            for h in payload.get("headers", [])
        }

    @staticmethod
    def _merge_addresses(values: list[str], exclude: list[str] | None = None) -> str:
        """Parse address header strings, drop excluded emails (case-insensitive)
        and duplicates while preserving order, and return a comma-joined string.
        """
        exclude_l = {e.lower() for e in (exclude or []) if e}
        seen: set[str] = set()
        out: list[str] = []
        for name, addr in getaddresses([v for v in values if v]):
            if not addr:
                continue
            key = addr.lower()
            if key in exclude_l or key in seen:
                continue
            seen.add(key)
            out.append(formataddr((name, addr)) if name else addr)
        return ", ".join(out)

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
        """Get the current user's Gmail profile.

        Best-effort: returns empty dict on API errors since profile data
        (display name for email sender) is non-critical.
        """
        try:
            profile = self.execute(self.service.users().getProfile(userId="me"))
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

            # Set From with display name (explicit > account config)
            effective_name = from_name or self.auth_manager.config.get_account_display_name(
                self.auth_manager.account_name
            )
            if effective_name:
                profile = self.get_profile()
                email_address = profile.get("emailAddress", "")
                if email_address:
                    message["from"] = f'"{effective_name}" <{email_address}>'

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = self.execute(
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
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
        cc: str | None = None,
        bcc: str | None = None,
        reply_all: bool = False,
        draft: bool = False,
    ) -> dict[str, Any]:
        """Reply to an existing message (stays threaded via In-Reply-To/References).

        By default replies only to the sender. With reply_all=True, also
        addresses the original To recipients and Cc's the original Cc list,
        excluding your own address. Explicit cc/bcc are unioned in.
        With draft=True, saves the reply as a draft in the thread instead of
        sending it.
        """
        try:
            # Unescape shell-escaped characters
            body = self._unescape_text(body)
            if signature:
                signature = self._unescape_text(signature)

            # Get the original message
            original = self.execute(
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
            )

            thread_id = original["threadId"]
            # Case-insensitive: sent/self-built messages may use lowercase names.
            ci_headers = self._header_map(original.get("payload", {}))

            # Append signature if provided
            full_body = body
            if signature:
                full_body = f"{body}\n\n--\n{signature}"

            subtype = "html" if html else "plain"
            message = MIMEText(full_body, subtype, "utf-8")

            # Our own address — needed to set a named From and to exclude
            # ourselves from reply-all recipients.
            self_email = ""
            if from_name or reply_all:
                self_email = self.get_profile().get("emailAddress", "")
            if from_name and self_email:
                message["from"] = f'"{from_name}" <{self_email}>'

            # Primary recipient: original sender (Reply-To > From > To).
            reply_to = (
                ci_headers.get("reply-to")
                or ci_headers.get("from")
                or ci_headers.get("to", "")
            )
            if reply_all:
                to_value = self._merge_addresses(
                    [reply_to, ci_headers.get("to", "")], exclude=[self_email]
                )
            else:
                to_value = reply_to
            message["to"] = to_value
            message["subject"] = f"Re: {ci_headers.get('subject', '')}"

            # Cc: original Cc (reply-all only) unioned with an explicit --cc,
            # minus ourselves and anyone already addressed in To.
            cc_sources = []
            if reply_all:
                cc_sources.append(ci_headers.get("cc", ""))
            if cc:
                cc_sources.append(cc)
            if cc_sources:
                to_emails = [addr for _, addr in getaddresses([to_value])]
                combined_cc = self._merge_addresses(
                    cc_sources, exclude=[self_email, *to_emails]
                )
                if combined_cc:
                    message["cc"] = combined_cc

            if bcc:
                bcc_value = self._merge_addresses([bcc], exclude=[self_email])
                if bcc_value:
                    message["bcc"] = bcc_value

            # Set references for threading (RFC 5322: parent's References + its Message-ID)
            message_id_header = ci_headers.get("message-id", "")
            if message_id_header:
                message["In-Reply-To"] = message_id_header
                parent_refs = ci_headers.get("references", "")
                message["References"] = f"{parent_refs} {message_id_header}".strip()

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            if draft:
                result = self.execute(
                    self.service.users()
                    .drafts()
                    .create(
                        userId="me",
                        body={"message": {"raw": raw, "threadId": thread_id}},
                    )
                )
                draft_message = result.get("message", {})
                output_success(
                    operation="gmail.reply",
                    draft=True,
                    draft_id=result["id"],
                    message_id=draft_message.get("id"),
                    thread_id=draft_message.get("threadId", thread_id),
                    to=reply_to,
                    subject=message["subject"],
                )
                return result

            result = self.execute(
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw, "threadId": thread_id})
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
                self.execute(self.service.users().messages().delete(
                    userId="me", id=message_id
                ))
                output_success(
                    operation="gmail.delete",
                    message_id=message_id,
                    permanent=True,
                )
            else:
                result = self.execute(
                    self.service.users()
                    .messages()
                    .trash(userId="me", id=message_id)
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
            result = self.execute(
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": ["UNREAD"]},
                )
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
            result = self.execute(
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"addLabelIds": ["UNREAD"]},
                )
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
            result = self.execute(self.service.users().labels().list(userId="me"))

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

            result = self.execute(
                self.service.users()
                .labels()
                .create(userId="me", body=label_body)
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
            self.execute(self.service.users().labels().delete(userId="me", id=label_id))

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
            result = self.execute(
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"addLabelIds": label_ids},
                )
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
            result = self.execute(
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": label_ids},
                )
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
            result = self.execute(
                self.service.users()
                .drafts()
                .list(userId="me", maxResults=max_results)
            )

            drafts = []
            draft_refs = result.get("drafts", [])

            if draft_refs:
                batch_results: dict[str, Any] = {}

                def handle_draft_response(request_id: str, response: Any, exception: Any) -> None:
                    if exception is None:
                        batch_results[request_id] = response

                for i in range(0, len(draft_refs), _BATCH_LIMIT):
                    chunk = draft_refs[i : i + _BATCH_LIMIT]
                    batch = self.service.new_batch_http_request(callback=handle_draft_response)
                    for draft_ref in chunk:
                        batch.add(
                            self.service.users()
                            .drafts()
                            .get(userId="me", id=draft_ref["id"], format="metadata"),
                            request_id=draft_ref["id"],
                        )
                    batch.execute()

                for draft_ref in draft_refs:
                    draft = batch_results.get(draft_ref["id"])
                    if not draft:
                        continue

                    msg = draft.get("message", {})
                    headers = self._header_map(msg.get("payload", {}))

                    drafts.append({
                        "id": draft["id"],
                        "message_id": msg.get("id"),
                        "subject": headers.get("subject", "(no subject)"),
                        "to": headers.get("to", ""),
                        "snippet": msg.get("snippet", "")[:100],
                    })

            output_external_content(
                operation="gmail.list_drafts",
                source_type="email",
                source_id="gmail.list_drafts",
                content_fields={"drafts": json.dumps(drafts, default=str)},
                draft_count=len(drafts),
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
            draft = self.execute(
                self.service.users()
                .drafts()
                .get(userId="me", id=draft_id, format="full")
            )

            msg = draft.get("message", {})
            headers = self._header_map(msg.get("payload", {}))

            body = self._extract_body(msg.get("payload", {}))

            output_external_content(
                operation="gmail.get_draft",
                source_type="email",
                source_id=draft["id"],
                content_fields={
                    "subject": headers.get("subject", "(no subject)"),
                    "body": body,
                },
                draft_id=draft["id"],
                message_id=msg.get("id"),
                to=headers.get("to", ""),
                cc=headers.get("cc", ""),
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

            result = self.execute(
                self.service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
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
            current_draft = self.execute(
                self.service.users()
                .drafts()
                .get(userId="me", id=draft_id, format="full")
            )

            current_msg = current_draft.get("message", {})
            current_headers = self._header_map(current_msg.get("payload", {}))
            current_body = self._extract_body(current_msg.get("payload", {}))

            # Use new values or preserve existing
            final_to = to if to is not None else current_headers.get("to", "")
            final_subject = subject if subject is not None else current_headers.get("subject", "")
            final_body = body if body is not None else current_body
            final_cc = cc if cc is not None else current_headers.get("cc")
            final_bcc = bcc if bcc is not None else current_headers.get("bcc")

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

            # Keep reply drafts (from `reply --draft`) in their thread
            if current_headers.get("in-reply-to"):
                message["In-Reply-To"] = current_headers["in-reply-to"]
            if current_headers.get("references"):
                message["References"] = current_headers["references"]

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            draft_message = {"raw": raw}
            if current_msg.get("threadId"):
                draft_message["threadId"] = current_msg["threadId"]

            result = self.execute(
                self.service.users()
                .drafts()
                .update(
                    userId="me",
                    id=draft_id,
                    body={"message": draft_message},
                )
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
            result = self.execute(
                self.service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
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
            self.execute(self.service.users().drafts().delete(userId="me", id=draft_id))

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

            # Set From with display name (explicit > account config)
            effective_name = from_name or self.auth_manager.config.get_account_display_name(
                self.auth_manager.account_name
            )
            if effective_name:
                profile = self.get_profile()
                email_address = profile.get("emailAddress", "")
                if email_address:
                    message["from"] = f'"{effective_name}" <{email_address}>'

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

            result = self.execute(
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
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
            msg = self.execute(
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
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
        force: bool = False,
    ) -> dict[str, Any]:
        """Download an attachment to a file.

        Args:
            message_id: The message ID containing the attachment.
            attachment_id: The attachment ID.
            output_path: Path to save the downloaded file.
            force: If True, skip security screening.
        """
        try:
            attachment = self.execute(
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
            )

            # Decode base64 data
            data = attachment.get("data", "")
            file_data = base64.urlsafe_b64decode(data)

            # Screen content before writing to disk
            verdict = screen_download(
                file_data, "gmail.download_attachment", "email",
                f"gmail.attachment:{message_id}:{attachment_id}", force=force,
            )
            if not verdict.allowed:
                output_error(
                    error_code="SECURITY_BLOCKED",
                    operation="gmail.download_attachment",
                    message="Attachment blocked by security screening. Use --force to bypass.",
                    details={"warnings": verdict.warnings},
                )
                raise SystemExit(ExitCode.API_ERROR)

            # Write to file
            with open(output_path, "wb") as f:
                f.write(file_data)

            response_kwargs: dict[str, Any] = {
                "operation": "gmail.download_attachment",
                "message_id": message_id,
                "attachment_id": attachment_id,
                "output_path": output_path,
                "size": len(file_data),
            }
            if verdict.is_binary and verdict.advisory:
                response_kwargs["security_advisory"] = verdict.advisory
            if verdict.warnings:
                response_kwargs["security_warnings"] = verdict.warnings
            output_success(**response_kwargs)
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

            result = self.execute(self.service.users().threads().list(**params))

            threads = []
            for thread in result.get("threads", []):
                thread_id = thread.get("id")
                snippet = thread.get("snippet", "")
                threads.append({
                    "thread_id": thread_id,
                    "snippet": snippet[:100] + "..." if len(snippet) > 100 else snippet,
                })

            output_external_content(
                operation="gmail.list_threads",
                source_type="email",
                source_id=f"gmail.list_threads:{query or 'all'}",
                content_fields={"threads": json.dumps(threads, default=str)},
                thread_count=len(threads),
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
            thread = self.execute(
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format=format_type)
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

            output_external_content(
                operation="gmail.get_thread",
                source_type="email",
                source_id=f"gmail.thread:{thread_id}",
                content_fields={"messages": json.dumps(messages, default=str)},
                thread_id=thread_id,
                message_count=len(messages),
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
            self.execute(self.service.users().threads().trash(userId="me", id=thread_id))

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
            self.execute(self.service.users().threads().untrash(userId="me", id=thread_id))

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

            self.execute(self.service.users().threads().modify(
                userId="me", id=thread_id, body=body
            ))

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
            settings = self.execute(
                self.service.users()
                .settings()
                .getVacation(userId="me")
            )

            output_external_content(
                operation="gmail.get_vacation_settings",
                source_type="email",
                source_id="gmail.vacation_settings",
                content_fields={
                    "subject": settings.get("responseSubject", ""),
                    "body_plain_text": settings.get("responseBodyPlainText", ""),
                },
                enabled=settings.get("enableAutoReply", False),
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

            result = self.execute(
                self.service.users()
                .settings()
                .updateVacation(userId="me", body=body)
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
                profile = self.execute(self.service.users().getProfile(userId="me"))
                send_as_email = profile.get("emailAddress", "")

            result = self.execute(
                self.service.users()
                .settings()
                .sendAs()
                .get(userId="me", sendAsEmail=send_as_email)
            )

            output_external_content(
                operation="gmail.get_signature",
                source_type="email",
                source_id=f"gmail.signature:{send_as_email}",
                content_fields={
                    "signature": result.get("signature", ""),
                    "display_name": result.get("displayName", ""),
                },
                send_as_email=send_as_email,
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
                profile = self.execute(self.service.users().getProfile(userId="me"))
                send_as_email = profile.get("emailAddress", "")

            result = self.execute(
                self.service.users()
                .settings()
                .sendAs()
                .patch(
                    userId="me",
                    sendAsEmail=send_as_email,
                    body={"signature": signature}
                )
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

    # ===== Filters =====

    def list_filters(self) -> dict[str, Any]:
        """List all mail filters."""
        try:
            result = self.execute(
                self.service.users()
                .settings()
                .filters()
                .list(userId="me")
            )

            filters = []
            for f in result.get("filter", []):
                criteria = f.get("criteria", {})
                action = f.get("action", {})

                filters.append({
                    "id": f.get("id"),
                    "criteria": {
                        "from": criteria.get("from"),
                        "to": criteria.get("to"),
                        "subject": criteria.get("subject"),
                        "query": criteria.get("query"),
                        "has_attachment": criteria.get("hasAttachment"),
                        "size": criteria.get("size"),
                        "size_comparison": criteria.get("sizeComparison"),
                    },
                    "action": {
                        "add_label_ids": action.get("addLabelIds", []),
                        "remove_label_ids": action.get("removeLabelIds", []),
                        "forward": action.get("forward"),
                        "star": action.get("star", False),
                        "mark_important": action.get("markImportant", False),
                        "archive": "INBOX" in action.get("removeLabelIds", []),
                        "trash": "TRASH" in action.get("addLabelIds", []),
                        "never_spam": "SPAM" in action.get("removeLabelIds", []),
                    },
                })

            output_success(
                operation="gmail.list_filters",
                filter_count=len(filters),
                filters=filters,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.list_filters",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_filter(self, filter_id: str) -> dict[str, Any]:
        """Get a specific mail filter."""
        try:
            result = self.execute(
                self.service.users()
                .settings()
                .filters()
                .get(userId="me", id=filter_id)
            )

            criteria = result.get("criteria", {})
            action = result.get("action", {})

            output_success(
                operation="gmail.get_filter",
                filter_id=filter_id,
                criteria={
                    "from": criteria.get("from"),
                    "to": criteria.get("to"),
                    "subject": criteria.get("subject"),
                    "query": criteria.get("query"),
                    "has_attachment": criteria.get("hasAttachment"),
                },
                action={
                    "add_label_ids": action.get("addLabelIds", []),
                    "remove_label_ids": action.get("removeLabelIds", []),
                    "forward": action.get("forward"),
                    "star": action.get("star", False),
                    "mark_important": action.get("markImportant", False),
                },
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="gmail.get_filter",
                    message=f"Filter not found: {filter_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="gmail.get_filter",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_filter(
        self,
        from_address: str | None = None,
        to_address: str | None = None,
        subject: str | None = None,
        query: str | None = None,
        has_attachment: bool | None = None,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
        archive: bool = False,
        star: bool = False,
        mark_important: bool | None = None,
        never_spam: bool = False,
        trash: bool = False,
        forward_to: str | None = None,
    ) -> dict[str, Any]:
        """Create a mail filter.

        Args:
            from_address: Match messages from this address.
            to_address: Match messages to this address.
            subject: Match messages with this subject.
            query: Gmail search query to match.
            has_attachment: Match messages with attachments.
            add_label_ids: Label IDs to add to matching messages.
            remove_label_ids: Label IDs to remove from matching messages.
            archive: Skip inbox (archive) matching messages.
            star: Star matching messages.
            mark_important: Mark matching messages as important (True/False/None).
            never_spam: Never send matching messages to spam.
            trash: Delete matching messages.
            forward_to: Forward matching messages to this address.
        """
        try:
            # Build criteria
            criteria: dict[str, Any] = {}
            if from_address:
                criteria["from"] = from_address
            if to_address:
                criteria["to"] = to_address
            if subject:
                criteria["subject"] = subject
            if query:
                criteria["query"] = query
            if has_attachment is not None:
                criteria["hasAttachment"] = has_attachment

            if not criteria:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="gmail.create_filter",
                    message="At least one filter criteria is required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Build action
            action: dict[str, Any] = {}
            add_labels = list(add_label_ids) if add_label_ids else []
            remove_labels = list(remove_label_ids) if remove_label_ids else []

            if archive:
                remove_labels.append("INBOX")
            if trash:
                add_labels.append("TRASH")
            if never_spam:
                remove_labels.append("SPAM")

            if add_labels:
                action["addLabelIds"] = add_labels
            if remove_labels:
                action["removeLabelIds"] = remove_labels
            if star:
                action["star"] = True
            if mark_important is not None:
                action["markImportant"] = mark_important
            if forward_to:
                action["forward"] = forward_to

            if not action:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="gmail.create_filter",
                    message="At least one filter action is required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            body = {"criteria": criteria, "action": action}

            result = self.execute(
                self.service.users()
                .settings()
                .filters()
                .create(userId="me", body=body)
            )

            output_success(
                operation="gmail.create_filter",
                filter_id=result.get("id"),
                criteria=criteria,
                action=action,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.create_filter",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_filter(self, filter_id: str) -> dict[str, Any]:
        """Delete a mail filter."""
        try:
            self.execute(self.service.users().settings().filters().delete(
                userId="me", id=filter_id
            ))

            output_success(
                operation="gmail.delete_filter",
                filter_id=filter_id,
                deleted=True,
            )
            return {"deleted": True, "filter_id": filter_id}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="gmail.delete_filter",
                    message=f"Filter not found: {filter_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="gmail.delete_filter",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # ADDITIONAL MESSAGE OPERATIONS
    # =========================================================================

    def untrash_message(self, message_id: str) -> dict[str, Any]:
        """Remove a message from trash."""
        try:
            result = self.execute(
                self.service.users()
                .messages()
                .untrash(userId="me", id=message_id)
            )

            output_success(
                operation="gmail.untrash_message",
                message_id=message_id,
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="gmail.untrash_message",
                    message=f"Message not found: {message_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="gmail.untrash_message",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def batch_modify_messages(
        self,
        message_ids: list[str],
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Modify labels on multiple messages at once.

        Args:
            message_ids: List of message IDs to modify.
            add_label_ids: Labels to add to all messages.
            remove_label_ids: Labels to remove from all messages.
        """
        try:
            body: dict[str, Any] = {"ids": message_ids}
            if add_label_ids:
                body["addLabelIds"] = add_label_ids
            if remove_label_ids:
                body["removeLabelIds"] = remove_label_ids

            self.execute(
                self.service.users()
                .messages()
                .batchModify(userId="me", body=body)
            )

            output_success(
                operation="gmail.batch_modify",
                message_count=len(message_ids),
                add_label_ids=add_label_ids,
                remove_label_ids=remove_label_ids,
            )
            return {"modified": len(message_ids)}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.batch_modify",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # LABEL OPERATIONS (extended)
    # =========================================================================

    def get_label(self, label_id: str) -> dict[str, Any]:
        """Get details of a specific label."""
        try:
            result = self.execute(
                self.service.users()
                .labels()
                .get(userId="me", id=label_id)
            )

            output_success(
                operation="gmail.get_label",
                label_id=label_id,
                name=result.get("name"),
                label_type=result.get("type"),
                message_list_visibility=result.get("messageListVisibility"),
                label_list_visibility=result.get("labelListVisibility"),
                messages_total=result.get("messagesTotal"),
                messages_unread=result.get("messagesUnread"),
                threads_total=result.get("threadsTotal"),
                threads_unread=result.get("threadsUnread"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="gmail.get_label",
                    message=f"Label not found: {label_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="gmail.get_label",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_label(
        self,
        label_id: str,
        name: str | None = None,
        message_list_visibility: str | None = None,
        label_list_visibility: str | None = None,
        text_color: str | None = None,
        background_color: str | None = None,
    ) -> dict[str, Any]:
        """Update a label's properties.

        Args:
            label_id: The label ID to update.
            name: New label name.
            message_list_visibility: 'show' or 'hide' in message list.
            label_list_visibility: 'labelShow', 'labelShowIfUnread', or 'labelHide'.
            text_color: Text color (hex, e.g., '#000000').
            background_color: Background color (hex, e.g., '#ffffff').
        """
        try:
            body: dict[str, Any] = {}

            if name is not None:
                body["name"] = name
            if message_list_visibility is not None:
                body["messageListVisibility"] = message_list_visibility
            if label_list_visibility is not None:
                body["labelListVisibility"] = label_list_visibility
            if text_color is not None or background_color is not None:
                body["color"] = {}
                if text_color:
                    body["color"]["textColor"] = text_color
                if background_color:
                    body["color"]["backgroundColor"] = background_color

            if not body:
                output_error(
                    error_code="INVALID_ARGUMENT",
                    operation="gmail.update_label",
                    message="At least one update field required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            result = self.execute(
                self.service.users()
                .labels()
                .patch(userId="me", id=label_id, body=body)
            )

            output_success(
                operation="gmail.update_label",
                label_id=label_id,
                name=result.get("name"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="gmail.update_label",
                    message=f"Label not found: {label_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="gmail.update_label",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # THREAD OPERATIONS (extended)
    # =========================================================================

    def delete_thread(self, thread_id: str) -> dict[str, Any]:
        """Permanently delete a thread (cannot be undone)."""
        try:
            self.execute(
                self.service.users()
                .threads()
                .delete(userId="me", id=thread_id)
            )

            output_success(
                operation="gmail.delete_thread",
                thread_id=thread_id,
                deleted=True,
            )
            return {"deleted": True, "thread_id": thread_id}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="gmail.delete_thread",
                    message=f"Thread not found: {thread_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="gmail.delete_thread",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # HISTORY
    # =========================================================================

    def list_history(
        self,
        start_history_id: str,
        max_results: int = 100,
        history_types: list[str] | None = None,
        label_id: str | None = None,
    ) -> dict[str, Any]:
        """List changes to the mailbox since a given history ID.

        Args:
            start_history_id: History ID to start from (from a previous sync).
            max_results: Maximum number of history records to return.
            history_types: Types to filter (messageAdded, messageDeleted, labelAdded, labelRemoved).
            label_id: Only return changes to messages with this label.
        """
        try:
            params: dict[str, Any] = {
                "userId": "me",
                "startHistoryId": start_history_id,
                "maxResults": max_results,
            }
            if history_types:
                params["historyTypes"] = history_types
            if label_id:
                params["labelId"] = label_id

            result = self.execute(
                self.service.users()
                .history()
                .list(**params)
            )

            history_records = result.get("history", [])
            output_success(
                operation="gmail.list_history",
                history_count=len(history_records),
                history_id=result.get("historyId"),
                next_page_token=result.get("nextPageToken"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="gmail.list_history",
                message=f"Gmail API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

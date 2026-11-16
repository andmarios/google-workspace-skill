"""Tests for `gmail reply --draft` (threaded reply saved as a draft)."""

import base64
import email
import json
from unittest.mock import MagicMock, patch

import pytest

from gws.services.gmail import GmailService


@pytest.fixture
def gmail_service():
    """Create a GmailService with fully mocked auth and API."""
    mock_auth = MagicMock()
    mock_auth.get_credentials.return_value = MagicMock(valid=True)
    mock_auth.config.get_account_display_name.return_value = ""
    mock_auth.account_name = None

    with patch("gws.services.base.resolve_auth_provider", return_value=mock_auth), \
         patch("gws.services.base.build") as mock_build:
        mock_gmail_api = MagicMock()
        mock_build.side_effect = lambda name, version, credentials=None: (
            mock_gmail_api if name == "gmail" else MagicMock()
        )
        service = GmailService()
        service._mock_gmail_api = mock_gmail_api
        yield service


def _setup(service, headers):
    api = service._mock_gmail_api
    api.users().messages().get().execute.return_value = {
        "id": "m1",
        "threadId": "t1",
        "payload": {"headers": [{"name": k, "value": v} for k, v in headers.items()]},
    }
    api.users().messages().send().execute.return_value = {"id": "r1", "threadId": "t1"}
    api.users().drafts().create().execute.return_value = {
        "id": "d1",
        "message": {"id": "r1", "threadId": "t1", "labelIds": ["DRAFT"]},
    }
    # Drop the setup calls above so call assertions only see the code under test.
    api.users().messages().send.reset_mock()
    api.users().drafts().create.reset_mock()


def _decode(raw_b64):
    return email.message_from_bytes(base64.urlsafe_b64decode(raw_b64))


def _draft_body(service):
    return service._mock_gmail_api.users().drafts().create.call_args.kwargs["body"]


def _sent_body(service):
    return service._mock_gmail_api.users().messages().send.call_args.kwargs["body"]


HEADERS = {
    "From": "alice@x.com",
    "To": "me@x.com, bob@x.com",
    "Cc": "carol@x.com",
    "Subject": "Hi",
    "Message-ID": "<m1@x>",
    "References": "<m0@x>",
}


def test_draft_creates_threaded_draft_and_never_sends(gmail_service, capsys):
    _setup(gmail_service, HEADERS)
    gmail_service.reply_to_message("m1", "body", draft=True)

    api = gmail_service._mock_gmail_api
    api.users().messages().send.assert_not_called()
    body = _draft_body(gmail_service)
    assert body["message"]["threadId"] == "t1"
    mime = _decode(body["message"]["raw"])
    assert mime["to"] == "alice@x.com"
    assert mime["subject"] == "Re: Hi"
    assert mime["In-Reply-To"] == "<m1@x>"

    out = json.loads(capsys.readouterr().out)
    assert out["operation"] == "gmail.reply"
    assert out["draft"] is True
    assert out["draft_id"] == "d1"
    assert out["message_id"] == "r1"
    assert out["thread_id"] == "t1"


def test_no_draft_sends_unchanged(gmail_service, capsys):
    _setup(gmail_service, HEADERS)
    gmail_service.reply_to_message("m1", "body")

    gmail_service._mock_gmail_api.users().drafts().create.assert_not_called()
    body = _sent_body(gmail_service)
    assert body["threadId"] == "t1"
    assert _decode(body["raw"])["In-Reply-To"] == "<m1@x>"

    out = json.loads(capsys.readouterr().out)
    assert "draft" not in out
    assert out["message_id"] == "r1"


@pytest.mark.parametrize("draft", [False, True])
def test_references_chain_parent_references_and_message_id(gmail_service, capsys, draft):
    _setup(gmail_service, HEADERS)
    gmail_service.reply_to_message("m1", "body", draft=draft)
    capsys.readouterr()
    raw = _draft_body(gmail_service)["message"]["raw"] if draft else _sent_body(gmail_service)["raw"]
    assert _decode(raw)["References"] == "<m0@x> <m1@x>"


def test_references_without_parent_references(gmail_service, capsys):
    _setup(gmail_service, {"from": "alice@x.com", "subject": "Hi", "message-id": "<m1@x>"})
    gmail_service.reply_to_message("m1", "body", draft=True)
    capsys.readouterr()
    assert _decode(_draft_body(gmail_service)["message"]["raw"])["References"] == "<m1@x>"


def test_reply_all_recipients_same_in_draft_mode(gmail_service, capsys):
    def recipients(draft):
        with patch.object(GmailService, "get_profile", return_value={"emailAddress": "me@x.com"}):
            _setup(gmail_service, HEADERS)
            gmail_service.reply_to_message(
                "m1", "body", reply_all=True, cc="dan@x.com", bcc="eve@x.com", draft=draft
            )
        capsys.readouterr()
        raw = (
            _draft_body(gmail_service)["message"]["raw"] if draft
            else _sent_body(gmail_service)["raw"]
        )
        mime = _decode(raw)
        return mime["to"], mime["cc"], mime["bcc"]

    sent = recipients(draft=False)
    drafted = recipients(draft=True)
    assert drafted == sent
    to, cc, bcc = drafted
    assert "alice@x.com" in to and "bob@x.com" in to and "me@x.com" not in to
    assert "carol@x.com" in cc and "dan@x.com" in cc
    assert bcc == "eve@x.com"


def _update_draft(service, headers, thread_id=None):
    api = service._mock_gmail_api
    msg = {
        "id": "r1",
        "payload": {
            "headers": [{"name": k, "value": v} for k, v in headers.items()],
            "body": {"data": base64.urlsafe_b64encode(b"old body").decode()},
        },
    }
    if thread_id:
        msg["threadId"] = thread_id
    api.users().drafts().get().execute.return_value = {"id": "d1", "message": msg}
    api.users().drafts().update().execute.return_value = {"id": "d1"}
    api.users().drafts().update.reset_mock()
    service.update_draft("d1", body="new body")
    return api.users().drafts().update.call_args.kwargs["body"]["message"]


def test_update_draft_keeps_reply_thread(gmail_service, capsys):
    # Lowercase names, as stored for drafts built locally via MIMEText.
    headers = {
        "to": "alice@x.com",
        "subject": "Re: Hi",
        "in-reply-to": "<m1@x>",
        "references": "<m0@x> <m1@x>",
    }
    message = _update_draft(gmail_service, headers, thread_id="t1")
    capsys.readouterr()
    assert message["threadId"] == "t1"
    mime = _decode(message["raw"])
    assert mime["In-Reply-To"] == "<m1@x>"
    assert mime["References"] == "<m0@x> <m1@x>"


def test_update_plain_draft_adds_no_threading(gmail_service, capsys):
    message = _update_draft(gmail_service, {"to": "alice@x.com", "subject": "Hi"})
    capsys.readouterr()
    assert "threadId" not in message
    mime = _decode(message["raw"])
    assert mime["In-Reply-To"] is None
    assert mime["References"] is None

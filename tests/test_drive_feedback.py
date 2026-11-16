"""Tests for drive list folder-visibility check and drive get last modifier."""

import json
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from gws.exceptions import ExitCode


@pytest.fixture
def drive():
    """DriveService with a mocked Drive API and captured output."""
    mock_auth = MagicMock()
    mock_auth.get_credentials.return_value = MagicMock(valid=True)
    api = MagicMock()

    with patch("gws.services.base.resolve_auth_provider", return_value=mock_auth), \
         patch("gws.services.base.build", return_value=api), \
         patch("gws.services.drive.output_external_content") as ext, \
         patch("gws.services.drive.output_error") as err:
        from gws.services.drive import DriveService

        service = DriveService()
        service._api, service._ext, service._err = api, ext, err
        yield service


def _http_error(status: int) -> HttpError:
    return HttpError(MagicMock(status=status, reason="Not Found"), b"{}")


def test_empty_folder_listing_and_folder_404_is_not_found(drive):
    drive._api.files().list().execute.return_value = {"files": []}
    drive._api.files().get().execute.side_effect = _http_error(404)

    with pytest.raises(SystemExit) as exc:
        drive.list_files(folder_id="hidden-folder")

    assert exc.value.code == ExitCode.NOT_FOUND == 4
    assert drive._err.call_args.kwargs["error_code"] == "NOT_FOUND"
    assert "hidden-folder" in drive._err.call_args.kwargs["message"]
    drive._ext.assert_not_called()


def test_empty_folder_listing_and_folder_visible_is_success(drive):
    drive._api.files().list().execute.return_value = {"files": []}
    drive._api.files().get().execute.return_value = {"id": "empty-folder"}

    drive.list_files(folder_id="empty-folder")

    assert drive._ext.call_args.kwargs["file_count"] == 0
    drive._err.assert_not_called()


def test_non_empty_listing_skips_folder_lookup(drive):
    drive._api.files().list().execute.return_value = {
        "files": [{"id": "f1", "name": "a.txt", "mimeType": "text/plain"}]
    }
    drive._api.files().get.reset_mock()

    drive.list_files(folder_id="some-folder")

    drive._api.files().get.assert_not_called()
    assert drive._ext.call_args.kwargs["file_count"] == 1


def test_get_metadata_includes_last_modifying_user(drive):
    drive._api.files().get().execute.return_value = {
        "id": "f1",
        "name": "a.txt",
        "mimeType": "text/plain",
        "lastModifyingUser": {"displayName": "Ada", "emailAddress": "ada@example.com"},
    }

    drive.get_metadata("f1")

    assert "lastModifyingUser(displayName,emailAddress)" in (
        drive._api.files().get.call_args.kwargs["fields"]
    )
    file_data = json.loads(drive._ext.call_args.kwargs["content_fields"]["file"])
    assert file_data["last_modifying_user"] == {"email": "ada@example.com", "name": "Ada"}

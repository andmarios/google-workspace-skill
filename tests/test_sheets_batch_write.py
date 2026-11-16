"""Tests for sheets batch-write and the Office-file error hint."""

import json
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from typer.testing import CliRunner

from gws.commands.sheets import app
from gws.config import Config

runner = CliRunner()


@pytest.fixture
def sheets_service():
    """Create a SheetsService with a mocked API client."""
    mock_auth = MagicMock()
    mock_auth.get_credentials.return_value.valid = True
    with patch("gws.services.base.resolve_auth_provider", return_value=mock_auth), \
         patch("gws.services.base.build", return_value=MagicMock()):
        from gws.services.sheets import SheetsService

        yield SheetsService()


def _http_error(status: int, message: str) -> HttpError:
    resp = MagicMock()
    resp.status = status
    return HttpError(resp, json.dumps({"error": {"code": status, "message": message}}).encode())


def test_batch_write_sends_all_ranges_in_one_request(sheets_service, capsys):
    values_api = sheets_service.service.spreadsheets().values()
    values_api.batchUpdate.return_value.execute.return_value = {
        "totalUpdatedRows": 3,
        "totalUpdatedColumns": 2,
        "totalUpdatedCells": 5,
        "responses": [{"updatedRange": "Sheet1!B2:C3"}, {"updatedRange": "Sheet1!E23"}],
    }

    sheets_service.batch_write(
        spreadsheet_id="sheet-1",
        data={"Sheet1\\!B2:C3": [["a", "b"], ["c", "d"]], "Sheet1!E23": [["=SUM(1,2)"]]},
    )

    values_api.batchUpdate.assert_called_once_with(
        spreadsheetId="sheet-1",
        body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": "Sheet1!B2:C3", "values": [["a", "b"], ["c", "d"]]},
                {"range": "Sheet1!E23", "values": [["=SUM(1,2)"]]},
            ],
        },
    )
    out = json.loads(capsys.readouterr().out)
    assert out["operation"] == "sheets.batch_write"
    assert out["ranges"] == ["Sheet1!B2:C3", "Sheet1!E23"]
    assert (out["updated_rows"], out["updated_columns"], out["updated_cells"]) == (3, 2, 5)


@pytest.mark.parametrize("raw", [
    "not json",
    '[["a", "b"]]',
    "{}",
    '{"Sheet1!A1": ["a", "b"]}',
    '{"Sheet1!A1": "a"}',
])
def test_batch_write_rejects_invalid_input(raw):
    with patch("gws.commands._account.Config.load", return_value=Config()), \
         patch("gws.commands.sheets.SheetsService") as service_cls:
        result = runner.invoke(app, ["batch-write", "sheet-1", "--stdin"], input=raw)

    assert result.exit_code == 3
    assert json.loads(result.stdout)["error_code"] == "INVALID_ARGS"
    service_cls.assert_not_called()


def test_batch_write_requires_input():
    with patch("gws.commands._account.Config.load", return_value=Config()), \
         patch("gws.commands.sheets.SheetsService") as service_cls:
        result = runner.invoke(app, ["batch-write", "sheet-1"])

    assert result.exit_code == 3
    service_cls.assert_not_called()


def test_office_file_hint_on_unsupported_document(sheets_service, capsys):
    sheets_service.service.spreadsheets().get.return_value.execute.side_effect = _http_error(
        400, "This operation is not supported for this document"
    )

    with pytest.raises(SystemExit):
        sheets_service.metadata(spreadsheet_id="xlsx-1")

    message = json.loads(capsys.readouterr().out)["message"]
    assert "Office file" in message
    assert "gws-cli drive download xlsx-1" in message


@pytest.mark.parametrize("status,reason", [
    (400, "Unable to parse range: Nope!A1"),
    (404, "Requested entity was not found."),
])
def test_no_office_file_hint_on_other_errors(sheets_service, capsys, status, reason):
    sheets_service.service.spreadsheets().values().get.return_value.execute.side_effect = (
        _http_error(status, reason)
    )

    with pytest.raises(SystemExit):
        sheets_service.read(spreadsheet_id="sheet-1", range_notation="Nope!A1")

    message = json.loads(capsys.readouterr().out)["message"]
    assert reason in message
    assert "Office file" not in message

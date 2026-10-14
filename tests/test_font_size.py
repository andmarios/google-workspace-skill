"""Tests for font size parsing in the Docs, Slides and Sheets CLI commands.

Docs and Slides send font sizes as Dimension.magnitude (double), so decimal
point sizes are valid. Sheets sends TextFormat.fontSize, which is int32, so
the CLI must keep rejecting decimals instead of letting the API return a 400.
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from gws.cli import app
from gws.config import Config

runner = CliRunner()


@pytest.fixture(autouse=True)
def config_dir(tmp_path, monkeypatch):
    """Isolate config so tests never touch ~/.config/gws-cli."""
    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(Config, "CONFIG_PATH", tmp_path / "gws_config.json")
    monkeypatch.delenv("GWS_ACCOUNT", raising=False)
    return tmp_path


@pytest.mark.parametrize(
    ("service_class", "method", "args"),
    [
        ("gws.commands.docs.DocsService", "format_text",
         ["docs", "format", "doc-1", "1", "10", "--font-size", "14.5"]),
        ("gws.commands.docs.DocsService", "format_text_extended",
         ["docs", "format-text-extended", "doc-1", "1", "10", "--size", "14.5"]),
        ("gws.commands.slides.SlidesService", "format_text",
         ["slides", "format-text", "pres-1", "shape-1", "--font-size", "14.5"]),
        ("gws.commands.slides.SlidesService", "format_text_extended",
         ["slides", "format-text-extended", "pres-1", "shape-1", "--size", "14.5"]),
    ],
)
def test_docs_and_slides_accept_decimal_font_size(service_class, method, args):
    with patch(service_class) as service:
        result = runner.invoke(app, args)

    assert result.exit_code == 0, result.output
    call = getattr(service.return_value, method).call_args
    assert call.kwargs["font_size"] == 14.5


@pytest.mark.parametrize(
    "args",
    [
        ["sheets", "format", "sheet-1", "0", "0", "1", "0", "1", "--font-size", "14.5"],
        ["sheets", "format-extended", "sheet-1", "0", "0", "1", "0", "1", "--size", "14.5"],
    ],
)
def test_sheets_rejects_decimal_font_size(args):
    with patch("gws.commands.sheets.SheetsService") as service:
        result = runner.invoke(app, args)

    assert result.exit_code == 2  # Typer usage error, before any API call
    service.assert_not_called()


@pytest.mark.parametrize(
    ("args", "method"),
    [
        (["sheets", "format", "sheet-1", "0", "0", "1", "0", "1", "--font-size", "14"],
         "format_cells"),
        (["sheets", "format-extended", "sheet-1", "0", "0", "1", "0", "1", "--size", "14"],
         "format_cells_extended"),
    ],
)
def test_sheets_sends_integer_font_size(args, method):
    with patch("gws.commands.sheets.SheetsService") as service:
        result = runner.invoke(app, args)

    assert result.exit_code == 0, result.output
    font_size = getattr(service.return_value, method).call_args.kwargs["font_size"]
    assert font_size == 14
    assert isinstance(font_size, int)

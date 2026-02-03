"""Tests for Google Docs service operations."""

import json
import pytest
from unittest.mock import MagicMock, patch, call


# =============================================================================
# TEST FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture
def docs_service():
    """Create a DocsService with fully mocked API."""
    with patch("gws.auth.oauth.AuthManager") as mock_auth_class, \
         patch("gws.services.base.build") as mock_build:

        # Mock auth manager
        mock_auth = MagicMock()
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_auth.get_credentials.return_value = mock_creds
        mock_auth_class.return_value = mock_auth

        # Create mock APIs
        mock_docs_api = MagicMock()
        mock_drive_api = MagicMock()

        def build_side_effect(service_name, version, credentials=None):
            if service_name == "docs":
                return mock_docs_api
            elif service_name == "drive":
                return mock_drive_api
            return MagicMock()

        mock_build.side_effect = build_side_effect

        from gws.services.docs import DocsService

        service = DocsService()
        # Store mocks for test access
        service._mock_docs_api = mock_docs_api
        service._mock_drive_api = mock_drive_api

        yield service


def setup_doc_response(service, doc_data: dict):
    """Configure mock to return specific document data."""
    service.service.documents().get().execute.return_value = doc_data


def setup_batch_response(service, replies: list | None = None):
    """Configure mock to return batch update response."""
    response = {
        "documentId": "test-doc-123",
        "replies": replies or [{}],
    }
    service.service.documents().batchUpdate().execute.return_value = response


# =============================================================================
# BASIC OPERATIONS TESTS
# =============================================================================


class TestBasicOperations:
    """Test basic document operations (read, create, insert, etc.)."""

    def test_read_document(self, docs_service, capsys):
        """Test reading document content."""
        setup_doc_response(docs_service, {
            "documentId": "doc-123",
            "title": "Test Doc",
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Hello World\n"}}
                            ]
                        },
                        "startIndex": 1,
                        "endIndex": 13,
                    },
                ]
            },
        })

        docs_service.read(document_id="doc-123")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.read"
        # Content is now wrapped with security markers
        assert output["content"]["trust_level"] == "external"
        assert "Hello World" in output["content"]["data"]

    def test_structure_document(self, docs_service, capsys):
        """Test getting document heading structure."""
        doc_data = {
            "documentId": "doc-123",
            "title": "Test Doc",
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "paragraph": {
                            "paragraphStyle": {"namedStyleType": "HEADING_1"},
                            "elements": [{"textRun": {"content": "Chapter 1\n"}}],
                        },
                        "startIndex": 1,
                        "endIndex": 11,
                    },
                ]
            },
        }
        docs_service.service.documents().get().execute.return_value = doc_data

        docs_service.structure(document_id="doc-123")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert len(output["headings"]) == 1
        assert output["headings"][0]["text"] == "Chapter 1"
        assert output["headings"][0]["style"] == "HEADING_1"
        assert output["headings"][0]["level"] == 1

    def test_insert_text(self, docs_service, capsys):
        """Test inserting text at index."""
        setup_batch_response(docs_service)

        docs_service.insert(document_id="doc-123", text="New text", index=5)

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.insert"

        # Verify batchUpdate was called with correct request
        call_args = docs_service.service.documents().batchUpdate.call_args
        assert call_args is not None

    def test_append_text(self, docs_service, capsys):
        """Test appending text to document end."""
        setup_doc_response(docs_service, {
            "documentId": "doc-123",
            "body": {
                "content": [
                    {"endIndex": 1},
                    {"paragraph": {}, "startIndex": 1, "endIndex": 20},
                ]
            },
        })
        setup_batch_response(docs_service)

        docs_service.append(document_id="doc-123", text="Appended text")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.append"

    def test_replace_text(self, docs_service, capsys):
        """Test replacing text throughout document."""
        response = {
            "documentId": "doc-123",
            "replies": [{"replaceAllText": {"occurrencesChanged": 3}}],
        }
        docs_service.service.documents().batchUpdate().execute.return_value = response

        docs_service.replace(
            document_id="doc-123",
            find="old",
            replace_with="new",
            match_case=True,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["occurrences_changed"] == 3

    def test_delete_content(self, docs_service, capsys):
        """Test deleting content in range."""
        setup_batch_response(docs_service)

        docs_service.delete_content(
            document_id="doc-123",
            start_index=5,
            end_index=10,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.delete"


# =============================================================================
# TABLE OPERATIONS TESTS (Phase 1)
# =============================================================================


class TestTableOperations:
    """Test table operations."""

    def test_list_tables(self, docs_service, capsys):
        """Test listing tables in document."""
        doc_data = {
            "documentId": "doc-123",
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {
                            "tableRows": [
                                {"tableCells": [{}, {}]},
                                {"tableCells": [{}, {}]},
                                {"tableCells": [{}, {}]},
                            ],
                        },
                        "startIndex": 10,
                        "endIndex": 50,
                    },
                    {
                        "table": {
                            "tableRows": [
                                {"tableCells": [{}, {}, {}, {}]},
                                {"tableCells": [{}, {}, {}, {}]},
                            ],
                        },
                        "startIndex": 55,
                        "endIndex": 100,
                    },
                ]
            },
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        docs_service.list_tables(document_id="doc-123")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["table_count"] == 2
        assert len(output["tables"]) == 2
        assert output["tables"][0]["rows"] == 3
        assert output["tables"][1]["columns"] == 4

    def test_insert_table(self, docs_service, capsys):
        """Test inserting a new table."""
        setup_doc_response(docs_service, {
            "body": {"content": [{"endIndex": 100}]}
        })
        setup_batch_response(docs_service)

        docs_service.insert_table(
            document_id="doc-123",
            rows=3,
            columns=4,
            index=50,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.insert_table"
        assert output["rows"] == 3
        assert output["columns"] == 4

    def test_insert_table_at_end(self, docs_service, capsys):
        """Test inserting table at document end."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {"paragraph": {}, "endIndex": 50},
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.insert_table(
            document_id="doc-123",
            rows=2,
            columns=2,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["index"] == 49  # endIndex - 1

    def test_insert_table_row(self, docs_service, capsys):
        """Test inserting a row into a table."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {
                            "rows": 2,
                            "columns": 2,
                            "tableRows": [{}, {}],
                        },
                        "startIndex": 10,
                        "endIndex": 50,
                    },
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.insert_table_row(
            document_id="doc-123",
            table_index=0,
            row_index=1,
            insert_below=True,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.insert_table_row"

    def test_delete_table_row(self, docs_service, capsys):
        """Test deleting a row from a table."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {"rows": 3, "columns": 2, "tableRows": [{}, {}, {}]},
                        "startIndex": 10,
                    },
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.delete_table_row(
            document_id="doc-123",
            table_index=0,
            row_index=1,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.delete_table_row"

    def test_merge_table_cells(self, docs_service, capsys):
        """Test merging table cells."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {"rows": 3, "columns": 3, "tableRows": [{}, {}, {}]},
                        "startIndex": 10,
                    },
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.merge_table_cells(
            document_id="doc-123",
            table_index=0,
            start_row=0,
            start_column=0,
            end_row=1,
            end_column=2,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.merge_table_cells"

    def test_style_table_cell(self, docs_service, capsys):
        """Test styling table cells."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {"rows": 2, "columns": 2, "tableRows": [{}, {}]},
                        "startIndex": 10,
                    },
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.style_table_cell(
            document_id="doc-123",
            table_index=0,
            start_row=0,
            start_column=0,
            background_color="#FFFF00",
            border_color="#000000",
            border_width=1.0,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.style_table_cell"

    def test_set_column_width(self, docs_service, capsys):
        """Test setting table column width."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {"rows": 2, "columns": 3, "tableRows": [{}, {}]},
                        "startIndex": 10,
                    },
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.set_column_width(
            document_id="doc-123",
            table_index=0,
            column_index=1,
            width=150.0,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["width"] == 150.0

    def test_set_table_column_widths(self, docs_service, capsys):
        """Test setting multiple column widths in one call."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {"rows": 2, "columns": 4, "tableRows": [{}, {}]},
                        "startIndex": 10,
                    },
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.set_table_column_widths(
            document_id="doc-123",
            table_index=0,
            column_widths={0: 70, 1: 90, 2: 170, 3: 50},
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["columns_updated"] == 4
        # JSON keys are always strings
        assert output["column_widths"] == {"0": 70, "1": 90, "2": 170, "3": 50}

    def test_set_table_column_widths_empty(self, docs_service, capsys):
        """Test error when no column widths provided."""
        from gws.exceptions import ExitCode

        with pytest.raises(SystemExit) as exc_info:
            docs_service.set_table_column_widths(
                document_id="doc-123",
                table_index=0,
                column_widths={},
            )

        assert exc_info.value.code == ExitCode.INVALID_ARGS
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"

    def test_set_table_column_widths_invalid_table(self, docs_service, capsys):
        """Test error when table index is invalid."""
        from gws.exceptions import ExitCode

        setup_doc_response(docs_service, {
            "body": {"content": [{"endIndex": 1}]}
        })

        with pytest.raises(SystemExit) as exc_info:
            docs_service.set_table_column_widths(
                document_id="doc-123",
                table_index=5,
                column_widths={0: 100},
            )

        assert exc_info.value.code == ExitCode.INVALID_ARGS

    def test_pin_table_header(self, docs_service, capsys):
        """Test pinning table header rows."""
        setup_doc_response(docs_service, {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "table": {"rows": 5, "columns": 2, "tableRows": []},
                        "startIndex": 10,
                    },
                ]
            }
        })
        setup_batch_response(docs_service)

        docs_service.pin_table_header(
            document_id="doc-123",
            table_index=0,
            rows_to_pin=2,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["rows_pinned"] == 2


# =============================================================================
# PARAGRAPH STYLE TESTS (Phase 2)
# =============================================================================


class TestParagraphStyles:
    """Test paragraph formatting operations."""

    def test_format_paragraph_alignment(self, docs_service, capsys):
        """Test paragraph alignment."""
        setup_batch_response(docs_service)

        docs_service.format_paragraph(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            alignment="CENTER",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "alignment" in output["formatting"]

    def test_format_paragraph_named_style(self, docs_service, capsys):
        """Test applying named paragraph style."""
        setup_batch_response(docs_service)

        docs_service.format_paragraph(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            named_style="HEADING_1",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "namedStyleType" in output["formatting"]

    def test_format_paragraph_spacing(self, docs_service, capsys):
        """Test paragraph spacing."""
        setup_batch_response(docs_service)

        docs_service.format_paragraph(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            space_above=12.0,
            space_below=6.0,
            line_spacing=150,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"

    def test_format_paragraph_indentation(self, docs_service, capsys):
        """Test paragraph indentation."""
        setup_batch_response(docs_service)

        docs_service.format_paragraph(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            indent_first_line=36.0,
            indent_start=18.0,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"

    def test_set_paragraph_border(self, docs_service, capsys):
        """Test adding paragraph borders."""
        setup_batch_response(docs_service)

        docs_service.set_paragraph_border(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            color="#0000FF",
            width=2.0,
            top=True,
            bottom=True,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.set_paragraph_border"


# =============================================================================
# EXTENDED TEXT STYLE TESTS (Phase 3)
# =============================================================================


class TestExtendedTextStyles:
    """Test extended text formatting operations."""

    def test_format_text_font(self, docs_service, capsys):
        """Test applying custom font."""
        setup_batch_response(docs_service)

        docs_service.format_text_extended(
            document_id="doc-123",
            start_index=1,
            end_index=20,
            font_family="Arial",
            font_weight=700,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "weightedFontFamily" in output["formatting"]

    def test_format_text_background_color(self, docs_service, capsys):
        """Test text highlight/background color."""
        setup_batch_response(docs_service)

        docs_service.format_text_extended(
            document_id="doc-123",
            start_index=1,
            end_index=20,
            background_color="#FFFF00",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "backgroundColor" in output["formatting"]

    def test_format_text_strikethrough(self, docs_service, capsys):
        """Test strikethrough formatting."""
        setup_batch_response(docs_service)

        docs_service.format_text_extended(
            document_id="doc-123",
            start_index=1,
            end_index=20,
            strikethrough=True,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "strikethrough" in output["formatting"]

    def test_format_text_superscript(self, docs_service, capsys):
        """Test superscript formatting."""
        setup_batch_response(docs_service)

        docs_service.format_text_extended(
            document_id="doc-123",
            start_index=1,
            end_index=5,
            baseline_offset="SUPERSCRIPT",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "baselineOffset" in output["formatting"]

    def test_format_text_subscript(self, docs_service, capsys):
        """Test subscript formatting."""
        setup_batch_response(docs_service)

        docs_service.format_text_extended(
            document_id="doc-123",
            start_index=1,
            end_index=5,
            baseline_offset="SUBSCRIPT",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"

    def test_format_text_small_caps(self, docs_service, capsys):
        """Test small caps formatting."""
        setup_batch_response(docs_service)

        docs_service.format_text_extended(
            document_id="doc-123",
            start_index=1,
            end_index=20,
            small_caps=True,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "smallCaps" in output["formatting"]

    def test_insert_link(self, docs_service, capsys):
        """Test adding hyperlink to text."""
        setup_batch_response(docs_service)

        docs_service.insert_link(
            document_id="doc-123",
            start_index=1,
            end_index=10,
            url="https://example.com",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["url"] == "https://example.com"


# =============================================================================
# HEADER/FOOTER TESTS (Phase 4)
# =============================================================================


class TestHeadersFooters:
    """Test header and footer operations."""

    def test_create_header(self, docs_service, capsys):
        """Test creating a document header."""
        setup_batch_response(docs_service, [
            {"createHeader": {"headerId": "kix.header123"}}
        ])

        docs_service.create_header(
            document_id="doc-123",
            header_type="DEFAULT",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["header_id"] == "kix.header123"

    def test_create_first_page_header(self, docs_service, capsys):
        """Test creating first-page-only header."""
        setup_batch_response(docs_service, [
            {"createHeader": {"headerId": "kix.firstheader"}}
        ])

        docs_service.create_header(
            document_id="doc-123",
            header_type="FIRST_PAGE_HEADER",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["header_type"] == "FIRST_PAGE_HEADER"

    def test_create_footer(self, docs_service, capsys):
        """Test creating a document footer."""
        setup_batch_response(docs_service, [
            {"createFooter": {"footerId": "kix.footer456"}}
        ])

        docs_service.create_footer(
            document_id="doc-123",
            footer_type="DEFAULT",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["footer_id"] == "kix.footer456"

    def test_delete_header(self, docs_service, capsys):
        """Test deleting a header."""
        setup_batch_response(docs_service)

        docs_service.delete_header(
            document_id="doc-123",
            header_id="kix.header123",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["header_id"] == "kix.header123"

    def test_delete_footer(self, docs_service, capsys):
        """Test deleting a footer."""
        setup_batch_response(docs_service)

        docs_service.delete_footer(
            document_id="doc-123",
            footer_id="kix.footer456",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["footer_id"] == "kix.footer456"

    def test_get_headers_footers(self, docs_service, capsys):
        """Test listing headers and footers."""
        setup_doc_response(docs_service, {
            "documentId": "doc-123",
            "body": {"content": []},
            "headers": {
                "kix.header1": {
                    "headerId": "kix.header1",
                    "content": [
                        {"paragraph": {"elements": [{"textRun": {"content": "Header\n"}}]}}
                    ],
                }
            },
            "footers": {
                "kix.footer1": {
                    "footerId": "kix.footer1",
                    "content": [
                        {"paragraph": {"elements": [{"textRun": {"content": "Footer\n"}}]}}
                    ],
                }
            },
        })

        docs_service.get_headers_footers(document_id="doc-123")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert len(output["headers"]) == 1
        assert len(output["footers"]) == 1

    def test_insert_text_in_segment(self, docs_service, capsys):
        """Test inserting text into header/footer."""
        setup_batch_response(docs_service)

        docs_service.insert_text_in_segment(
            document_id="doc-123",
            segment_id="kix.header123",
            text="Company Name",
            index=0,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["segment_id"] == "kix.header123"


# =============================================================================
# LIST/BULLET TESTS (Phase 5)
# =============================================================================


class TestLists:
    """Test list and bullet operations."""

    def test_create_bullets(self, docs_service, capsys):
        """Test creating a bulleted list."""
        setup_batch_response(docs_service)

        docs_service.create_bullets(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            preset="BULLET_DISC_CIRCLE_SQUARE",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.create_bullets"
        assert output["preset"] == "BULLET_DISC_CIRCLE_SQUARE"

    def test_create_numbered_list(self, docs_service, capsys):
        """Test creating a numbered list."""
        setup_batch_response(docs_service)

        docs_service.create_numbered_list(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            preset="NUMBERED_DECIMAL_NESTED",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.create_numbered_list"

    def test_create_checkbox_list(self, docs_service, capsys):
        """Test creating a checkbox list."""
        setup_batch_response(docs_service)

        docs_service.create_bullets(
            document_id="doc-123",
            start_index=1,
            end_index=50,
            preset="BULLET_CHECKBOX",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"

    def test_remove_bullets(self, docs_service, capsys):
        """Test removing bullets from paragraphs."""
        setup_batch_response(docs_service)

        docs_service.remove_bullets(
            document_id="doc-123",
            start_index=1,
            end_index=50,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.remove_bullets"


# =============================================================================
# SECTION AND DOCUMENT STYLE TESTS (Phase 6)
# =============================================================================


class TestSectionsAndDocumentStyle:
    """Test section and document style operations."""

    def test_insert_section_break_next_page(self, docs_service, capsys):
        """Test inserting a next-page section break."""
        setup_batch_response(docs_service)

        docs_service.insert_section_break(
            document_id="doc-123",
            index=50,
            break_type="NEXT_PAGE",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["break_type"] == "NEXT_PAGE"

    def test_insert_section_break_continuous(self, docs_service, capsys):
        """Test inserting a continuous section break."""
        setup_batch_response(docs_service)

        docs_service.insert_section_break(
            document_id="doc-123",
            index=50,
            break_type="CONTINUOUS",
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["break_type"] == "CONTINUOUS"

    def test_update_document_margins(self, docs_service, capsys):
        """Test updating document margins."""
        setup_batch_response(docs_service)

        docs_service.update_document_style(
            document_id="doc-123",
            margin_top=72.0,
            margin_bottom=72.0,
            margin_left=72.0,
            margin_right=72.0,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "marginTop" in output["updated_fields"]

    def test_update_document_page_size(self, docs_service, capsys):
        """Test updating document page size."""
        setup_batch_response(docs_service)

        docs_service.update_document_style(
            document_id="doc-123",
            page_width=595.0,  # A4
            page_height=842.0,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "pageSize" in output["updated_fields"]

    def test_update_first_page_header_footer(self, docs_service, capsys):
        """Test enabling different first page header/footer."""
        setup_batch_response(docs_service)

        docs_service.update_document_style(
            document_id="doc-123",
            use_first_page_header_footer=True,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "useFirstPageHeaderFooter" in output["updated_fields"]


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    def test_format_text_extended_no_options(self, docs_service, capsys):
        """Test error when no formatting options provided."""
        from gws.exceptions import ExitCode

        with pytest.raises(SystemExit) as exc_info:
            docs_service.format_text_extended(
                document_id="doc-123",
                start_index=1,
                end_index=10,
            )

        assert exc_info.value.code == ExitCode.INVALID_ARGS

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"
        assert output["error_code"] == "INVALID_ARGS"

    def test_format_paragraph_no_options(self, docs_service, capsys):
        """Test error when no paragraph formatting options provided."""
        from gws.exceptions import ExitCode

        with pytest.raises(SystemExit) as exc_info:
            docs_service.format_paragraph(
                document_id="doc-123",
                start_index=1,
                end_index=10,
            )

        assert exc_info.value.code == ExitCode.INVALID_ARGS

    def test_update_document_style_no_options(self, docs_service, capsys):
        """Test error when no document style options provided."""
        from gws.exceptions import ExitCode

        with pytest.raises(SystemExit) as exc_info:
            docs_service.update_document_style(document_id="doc-123")

        assert exc_info.value.code == ExitCode.INVALID_ARGS

    def test_table_not_found(self, docs_service, capsys):
        """Test error when table index is out of range."""
        from gws.exceptions import ExitCode

        doc_data = {"body": {"content": [{"endIndex": 1}]}}
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        with pytest.raises(SystemExit) as exc_info:
            docs_service.insert_table_row(
                document_id="doc-123",
                table_index=0,  # No tables exist
                row_index=0,
            )

        assert exc_info.value.code == ExitCode.INVALID_ARGS

        output = json.loads(capsys.readouterr().out)
        assert output["error_code"] == "INVALID_ARGS"
        assert "Table index" in output["message"]


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================


class TestHelperMethods:
    """Test internal helper methods by testing through public API."""

    def test_extract_text(self, docs_service, capsys):
        """Test text extraction via read operation."""
        doc_data = {
            "documentId": "doc-123",
            "title": "Test",
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "First paragraph\n"}},
                            ]
                        },
                        "startIndex": 1,
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Second paragraph\n"}},
                            ]
                        },
                        "startIndex": 17,
                    },
                ]
            },
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        docs_service.read(document_id="doc-123")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        # Content is now wrapped with security markers
        assert output["content"]["trust_level"] == "external"
        assert "First paragraph" in output["content"]["data"]
        assert "Second paragraph" in output["content"]["data"]

    def test_extract_structure(self, docs_service, capsys):
        """Test structure extraction via structure operation."""
        doc_data = {
            "documentId": "doc-123",
            "title": "Test",
            "body": {
                "content": [
                    {"endIndex": 1},
                    {
                        "paragraph": {
                            "paragraphStyle": {"namedStyleType": "HEADING_1"},
                            "elements": [{"textRun": {"content": "Main Title\n"}}],
                        },
                    },
                    {
                        "paragraph": {
                            "paragraphStyle": {"namedStyleType": "HEADING_2"},
                            "elements": [{"textRun": {"content": "Subtitle\n"}}],
                        },
                    },
                    {
                        "paragraph": {
                            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                            "elements": [{"textRun": {"content": "Body text\n"}}],
                        },
                    },
                ]
            },
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        docs_service.structure(document_id="doc-123")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["heading_count"] == 2
        assert output["headings"][0]["level"] == 1
        assert output["headings"][1]["level"] == 2


# =============================================================================
# COLOR PARSING TESTS
# =============================================================================


class TestColorParsing:
    """Test hex color parsing utility."""

    def test_parse_hex_color(self):
        """Test parsing hex colors."""
        from gws.utils.colors import parse_hex_color

        # Standard 6-digit hex
        rgb = parse_hex_color("#FF0000")
        assert rgb["red"] == 1.0
        assert rgb["green"] == 0.0
        assert rgb["blue"] == 0.0

        # Without hash
        rgb = parse_hex_color("00FF00")
        assert rgb["green"] == 1.0

        # Mixed colors
        rgb = parse_hex_color("#808080")
        assert abs(rgb["red"] - 0.502) < 0.01

    def test_parse_hex_color_invalid(self):
        """Test fallback for invalid/short colors returns black."""
        from gws.utils.colors import parse_hex_color

        # Short color returns black (fallback)
        rgb = parse_hex_color("#FFF")
        assert rgb["red"] == 0.0
        assert rgb["green"] == 0.0
        assert rgb["blue"] == 0.0

        # Invalid hex characters raise ValueError when parsed
        with pytest.raises(ValueError):
            parse_hex_color("#GGGGGG")


# =============================================================================
# FIND TEXT TESTS
# =============================================================================


class TestFindText:
    """Test find_text functionality for locating text positions."""

    def test_find_text_single_occurrence(self, docs_service, capsys):
        """Test finding text that appears once."""
        doc_data = {
            "documentId": "doc-123",
            "title": "Test Doc",
            "tabs": [{
                "tabProperties": {"tabId": "t.0"},
                "documentTab": {
                    "body": {
                        "content": [
                            {"endIndex": 1},
                            {
                                "paragraph": {
                                    "elements": [
                                        {
                                            "startIndex": 1,
                                            "endIndex": 14,
                                            "textRun": {"content": "Hello World!\n"},
                                        }
                                    ]
                                },
                                "startIndex": 1,
                                "endIndex": 14,
                            },
                        ]
                    }
                }
            }],
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        docs_service.find_text(document_id="doc-123", search_text="World")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "docs.find_text"
        assert output["index"] == 7  # "Hello " is 6 chars, so World starts at index 7
        assert output["end_index"] == 12
        assert output["length"] == 5
        assert output["total_occurrences"] == 1

    def test_find_text_multiple_occurrences(self, docs_service, capsys):
        """Test finding a specific occurrence when text appears multiple times."""
        doc_data = {
            "documentId": "doc-123",
            "title": "Test Doc",
            "tabs": [{
                "tabProperties": {"tabId": "t.0"},
                "documentTab": {
                    "body": {
                        "content": [
                            {"endIndex": 1},
                            {
                                "paragraph": {
                                    "elements": [
                                        {
                                            "startIndex": 1,
                                            "endIndex": 25,
                                            "textRun": {"content": "foo bar foo baz foo end\n"},
                                        }
                                    ]
                                },
                                "startIndex": 1,
                                "endIndex": 25,
                            },
                        ]
                    }
                }
            }],
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        # Find the second occurrence
        docs_service.find_text(
            document_id="doc-123",
            search_text="foo",
            occurrence=2,
        )

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["occurrence"] == 2
        assert output["total_occurrences"] == 3
        # "foo bar " is 8 chars, so second foo starts at index 9
        assert output["index"] == 9

    def test_find_text_not_found(self, docs_service, capsys):
        """Test error when text is not found."""
        doc_data = {
            "documentId": "doc-123",
            "title": "Test Doc",
            "tabs": [{
                "tabProperties": {"tabId": "t.0"},
                "documentTab": {
                    "body": {
                        "content": [
                            {"endIndex": 1},
                            {
                                "paragraph": {
                                    "elements": [
                                        {
                                            "startIndex": 1,
                                            "endIndex": 14,
                                            "textRun": {"content": "Hello World!\n"},
                                        }
                                    ]
                                },
                                "startIndex": 1,
                                "endIndex": 14,
                            },
                        ]
                    }
                }
            }],
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        with pytest.raises(SystemExit) as exc_info:
            docs_service.find_text(document_id="doc-123", search_text="nonexistent")

        assert exc_info.value.code == 4  # NOT_FOUND
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"
        assert output["error_code"] == "NOT_FOUND"

    def test_find_text_occurrence_out_of_range(self, docs_service, capsys):
        """Test error when occurrence number exceeds actual occurrences."""
        doc_data = {
            "documentId": "doc-123",
            "title": "Test Doc",
            "tabs": [{
                "tabProperties": {"tabId": "t.0"},
                "documentTab": {
                    "body": {
                        "content": [
                            {"endIndex": 1},
                            {
                                "paragraph": {
                                    "elements": [
                                        {
                                            "startIndex": 1,
                                            "endIndex": 12,
                                            "textRun": {"content": "test test\n"},
                                        }
                                    ]
                                },
                                "startIndex": 1,
                                "endIndex": 12,
                            },
                        ]
                    }
                }
            }],
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        with pytest.raises(SystemExit) as exc_info:
            docs_service.find_text(
                document_id="doc-123",
                search_text="test",
                occurrence=5,  # Only 2 occurrences exist
            )

        assert exc_info.value.code == 3  # INVALID_ARGS
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"
        assert "out of range" in output["message"]


# =============================================================================
# INSERT IMAGE AT TEXT TESTS
# =============================================================================


class TestInsertImageAtText:
    """Test insert_image_at_text functionality."""

    def test_insert_image_at_text_success(self, docs_service, capsys):
        """Test inserting image after specific text."""
        # Setup doc response for find_text
        doc_data = {
            "documentId": "doc-123",
            "title": "Test Doc",
            "tabs": [{
                "tabProperties": {"tabId": "t.0"},
                "documentTab": {
                    "body": {
                        "content": [
                            {"endIndex": 1},
                            {
                                "paragraph": {
                                    "elements": [
                                        {
                                            "startIndex": 1,
                                            "endIndex": 20,
                                            "textRun": {"content": "Figure 1: Caption\n"},
                                        }
                                    ]
                                },
                                "startIndex": 1,
                                "endIndex": 20,
                            },
                        ]
                    }
                }
            }],
        }
        docs_service.service.documents().get.return_value.execute.return_value = doc_data

        # Setup batch response for insert_image
        batch_response = {
            "documentId": "doc-123",
            "replies": [{}],
        }
        docs_service.service.documents().batchUpdate.return_value.execute.return_value = batch_response

        docs_service.insert_image_at_text(
            document_id="doc-123",
            image_url="https://example.com/image.png",
            after_text="Figure 1:",
            width=300,
            height=200,
        )

        # Parse the output - it contains two pretty-printed JSON objects
        output = capsys.readouterr().out

        # Check both operations are present in output
        assert '"operation": "docs.find_text"' in output
        assert '"operation": "docs.insert_image"' in output
        assert '"status": "success"' in output
        # Verify the index was found (Figure 1: starts at position 1)
        assert '"index": 1' in output


# =============================================================================
# RETRY UTILITY TESTS
# =============================================================================


class TestRetryUtility:
    """Test retry logic for transient API errors."""

    def test_execute_with_retry_success_first_try(self):
        """Test successful execution on first try."""
        from gws.utils.retry import execute_with_retry

        mock_request = MagicMock()
        mock_request.execute.return_value = {"id": "file-123"}

        result = execute_with_retry(mock_request, max_retries=3)

        assert result == {"id": "file-123"}
        assert mock_request.execute.call_count == 1

    def test_execute_with_retry_success_after_retry(self):
        """Test successful execution after transient failure."""
        from gws.utils.retry import execute_with_retry
        from googleapiclient.errors import HttpError

        mock_request = MagicMock()
        # First call raises 500, second succeeds
        mock_response = MagicMock()
        mock_response.status = 500
        error = HttpError(mock_response, b"Internal Error")

        mock_request.execute.side_effect = [
            error,
            {"id": "file-123"},
        ]

        result = execute_with_retry(mock_request, max_retries=3, initial_delay=0.01)

        assert result == {"id": "file-123"}
        assert mock_request.execute.call_count == 2

    def test_execute_with_retry_gives_up_after_max_retries(self):
        """Test that retry gives up after max attempts."""
        from gws.utils.retry import execute_with_retry
        from googleapiclient.errors import HttpError

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 500
        error = HttpError(mock_response, b"Internal Error")

        mock_request.execute.side_effect = error

        with pytest.raises(HttpError):
            execute_with_retry(mock_request, max_retries=2, initial_delay=0.01)

        # Initial + 2 retries = 3 attempts
        assert mock_request.execute.call_count == 3

    def test_execute_with_retry_non_retryable_error(self):
        """Test that non-retryable errors are raised immediately."""
        from gws.utils.retry import execute_with_retry
        from googleapiclient.errors import HttpError

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 404  # Not retryable
        error = HttpError(mock_response, b"Not Found")

        mock_request.execute.side_effect = error

        with pytest.raises(HttpError):
            execute_with_retry(mock_request, max_retries=3, initial_delay=0.01)

        # Should fail immediately without retry
        assert mock_request.execute.call_count == 1

    def test_is_retryable_error(self):
        """Test detection of retryable errors."""
        from gws.utils.retry import is_retryable_error
        from googleapiclient.errors import HttpError

        # Retryable status codes
        for status in [429, 500, 502, 503]:
            mock_response = MagicMock()
            mock_response.status = status
            error = HttpError(mock_response, b"Error")
            assert is_retryable_error(error) is True

        # Non-retryable status codes
        for status in [400, 401, 403, 404, 409]:
            mock_response = MagicMock()
            mock_response.status = status
            error = HttpError(mock_response, b"Error")
            assert is_retryable_error(error) is False

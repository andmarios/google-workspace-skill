"""Pytest configuration and fixtures for Google Workspace tests."""

import json
import pytest
from typing import Any
from unittest.mock import MagicMock, patch


class MockHttpError(Exception):
    """Mock HttpError from Google API."""

    def __init__(self, reason: str = "Test error"):
        self.reason = reason
        super().__init__(reason)


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth credentials."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    return creds


@pytest.fixture
def mock_docs_api():
    """Mock Google Docs API service."""
    service = MagicMock()

    # Mock documents().get()
    doc_response = {
        "documentId": "test-doc-123",
        "title": "Test Document",
        "body": {
            "content": [
                {"endIndex": 1},
                {
                    "paragraph": {
                        "elements": [
                            {
                                "textRun": {
                                    "content": "Hello World\n",
                                    "textStyle": {},
                                }
                            }
                        ]
                    },
                    "startIndex": 1,
                    "endIndex": 13,
                },
            ]
        },
        "headers": {},
        "footers": {},
    }
    service.documents().get().execute.return_value = doc_response

    # Mock documents().batchUpdate()
    batch_response = {
        "documentId": "test-doc-123",
        "replies": [{}],
    }
    service.documents().batchUpdate().execute.return_value = batch_response

    return service


@pytest.fixture
def mock_drive_api():
    """Mock Google Drive API service."""
    service = MagicMock()

    # Mock files().create()
    create_response = {
        "id": "new-doc-123",
        "name": "New Document",
        "mimeType": "application/vnd.google-apps.document",
    }
    service.files().create().execute.return_value = create_response

    return service


@pytest.fixture
def mock_docs_service(mock_credentials, mock_docs_api, mock_drive_api):
    """Create a DocsService with mocked dependencies."""
    with patch("gws.services.base.Credentials") as mock_creds_class, \
         patch("gws.services.base.build") as mock_build, \
         patch("gws.services.base.Path") as mock_path:

        # Setup credential mocking
        mock_path.return_value.exists.return_value = True
        mock_creds_class.from_authorized_user_file.return_value = mock_credentials

        # Setup build to return different services
        def build_side_effect(service_name, version, credentials=None):
            if service_name == "docs":
                return mock_docs_api
            elif service_name == "drive":
                return mock_drive_api
            return MagicMock()

        mock_build.side_effect = build_side_effect

        # Import after mocking to avoid import-time issues
        from gws.services.docs import DocsService

        service = DocsService()
        service._docs_api = mock_docs_api
        service._drive_api = mock_drive_api

        yield service


@pytest.fixture
def sample_doc_with_tables():
    """Sample document structure with tables."""
    return {
        "documentId": "doc-with-tables-123",
        "title": "Document with Tables",
        "body": {
            "content": [
                {"endIndex": 1},
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": "Introduction\n"}}]
                    },
                    "startIndex": 1,
                    "endIndex": 14,
                },
                {
                    "table": {
                        "rows": 3,
                        "columns": 2,
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {"textRun": {"content": "Header 1\n"}}
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {"textRun": {"content": "Header 2\n"}}
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                ]
                            },
                        ],
                    },
                    "startIndex": 14,
                    "endIndex": 50,
                },
            ]
        },
        "headers": {},
        "footers": {},
    }


@pytest.fixture
def sample_doc_with_headers_footers():
    """Sample document structure with headers and footers."""
    return {
        "documentId": "doc-with-hf-123",
        "title": "Document with Headers/Footers",
        "body": {"content": [{"endIndex": 1}]},
        "headers": {
            "kix.header123": {
                "headerId": "kix.header123",
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Header Text\n"}}]
                        }
                    }
                ],
            }
        },
        "footers": {
            "kix.footer456": {
                "footerId": "kix.footer456",
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Footer Text\n"}}]
                        }
                    }
                ],
            }
        },
    }


@pytest.fixture
def capture_output(capsys):
    """Capture stdout/stderr and parse JSON output."""

    class OutputCapture:
        def get_json(self) -> dict[str, Any]:
            captured = capsys.readouterr()
            return json.loads(captured.out)

        def get_output(self) -> str:
            captured = capsys.readouterr()
            return captured.out

    return OutputCapture()

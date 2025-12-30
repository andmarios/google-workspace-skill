# Google Workspace CLI (gws)

A unified command-line interface for managing Google Workspace services including Docs, Sheets, Slides, Drive, Gmail, Calendar, and Contacts.

## Features

- **Unified CLI**: Single `gws` command with intuitive subcommands
- **8 Services**: Drive, Docs, Sheets, Slides, Gmail, Calendar, Contacts + Document Converter
- **64 Operations**: Comprehensive coverage of Google Workspace APIs
- **JSON Output**: Machine-readable output for scripting and automation
- **OAuth Loopback**: Automatic browser-based authentication (no manual code copying)
- **Cross-Platform**: Works on Linux, macOS, and Windows
- **Zero Setup**: Just `uv run` - no Python installation required

## Installation

### Using uv (Recommended)

```bash
# Run directly without installation
uv run gws --help

# Or install as a tool for global access
uv tool install .
gws --help
```

### Prerequisites

1. **uv** package manager: https://docs.astral.sh/uv/
2. **Google Cloud Project** with OAuth credentials:
   - Create project at https://console.cloud.google.com
   - Enable APIs: Drive, Docs, Sheets, Slides, Gmail, Calendar, People
   - Create OAuth 2.0 credentials (Desktop application)
   - Download `client_secret.json` to `~/.claude/.google/`

## Quick Start

```bash
# 1. Authenticate with Google (opens browser)
uv run gws auth

# 2. List your Drive files
uv run gws drive list

# 3. Read a Google Doc
uv run gws docs read <document_id>

# 4. Create a spreadsheet
uv run gws sheets create "My Spreadsheet"
```

## Services

### Drive (11 operations)
File management: upload, download, list, search, get metadata, copy, move, share, create folder, update, delete

```bash
uv run gws drive list --max 20
uv run gws drive upload ./report.pdf --folder <folder_id>
uv run gws drive share <file_id> --role reader
```

### Docs (10 operations)
Document editing: read, structure, create, insert, append, replace, format, delete range, page break, insert image

```bash
uv run gws docs read <document_id>
uv run gws docs create "New Document" --content "Hello World"
uv run gws docs format <document_id> 1 50 --bold
```

### Sheets (11 operations)
Spreadsheet management: metadata, read, create, write, append, clear, add/delete/rename sheets, format, batch get

```bash
uv run gws sheets read <spreadsheet_id> "A1:D10"
uv run gws sheets write <spreadsheet_id> "A1:B2" --values '[["A","B"],["1","2"]]'
uv run gws sheets format <spreadsheet_id> <sheet_id> 0 1 0 3 --bold --bg-color "#FFE0B2"
```

### Slides (12 operations)
Presentation editing: metadata, read, create, add/delete/duplicate slides, textbox, insert text, replace text, format, insert image, delete element

```bash
uv run gws slides create "New Presentation"
uv run gws slides create-textbox <pres_id> <slide_id> "Hello" --x 100 --y 100 --width 400 --height 50
uv run gws slides insert-image <pres_id> <slide_id> "https://..." --x 50 --y 200 --width 300 --height 200
```

### Gmail (6 operations)
Email management: list, read, send, reply, search, delete

```bash
uv run gws gmail list --max 10
uv run gws gmail send "recipient@example.com" "Subject" "Body text"
uv run gws gmail search "is:unread from:boss@company.com"
```

### Calendar (6 operations)
Event management: list calendars, list events, get, create, update, delete

```bash
uv run gws calendar calendars
uv run gws calendar create "Meeting" "2025-01-15T10:00:00" "2025-01-15T11:00:00"
uv run gws calendar list --max 5
```

### Contacts (5 operations)
Contact management via People API: list, get, create, update, delete

```bash
uv run gws contacts list --max 20
uv run gws contacts create "John Doe" --email "john@example.com"
```

### Convert (3 operations)
Document conversion: Markdown to Google Docs, Slides, or PDF

```bash
uv run gws convert md-to-doc ./report.md --title "Q4 Report"
uv run gws convert md-to-slides ./deck.md --title "Presentation"
uv run gws convert md-to-pdf ./report.md ./report.pdf
```

## Configuration

Enable/disable services based on your security needs:

```bash
# View current configuration
uv run gws config

# List all services with status
uv run gws config list

# Disable Gmail access
uv run gws config disable gmail

# Re-enable Gmail
uv run gws config enable gmail

# Reset to defaults (all enabled)
uv run gws config reset
```

## Output Format

All commands output JSON for easy parsing:

```json
{
  "status": "success",
  "operation": "docs.read",
  "document_id": "1abc...",
  "content": "Document content here..."
}
```

## Project Structure

```
src/gws/
├── cli.py              # Main Typer CLI app
├── config.py           # Service configuration
├── output.py           # JSON output formatting
├── exceptions.py       # Exit codes
├── auth/
│   ├── oauth.py        # OAuth loopback flow
│   └── scopes.py       # API scope definitions
├── services/
│   ├── base.py         # Base service class
│   ├── drive.py        # Drive operations
│   ├── docs.py         # Docs operations
│   ├── sheets.py       # Sheets operations
│   ├── slides.py       # Slides operations
│   ├── gmail.py        # Gmail operations
│   ├── calendar.py     # Calendar operations
│   ├── contacts.py     # Contacts operations
│   └── convert.py      # Document converter
└── commands/           # CLI command definitions
```

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Type checking
uv run mypy src/
```

## License

MIT License - See [LICENSE](LICENSE) file for details.

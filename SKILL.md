---
name: google-workspace
description: Manage Google Workspace with Docs, Sheets, Slides, Drive, Gmail, Calendar, and Contacts operations. Full document/spreadsheet/presentation editing, file management, email, and scheduling.
category: productivity
version: 1.0.0
key_capabilities: Docs (read/edit/format), Sheets (read/write/format), Slides (create/edit), Drive (upload/download/share), Gmail (send/search), Calendar (events), Contacts (manage), Convert (markdown)
when_to_use: Document operations, spreadsheet data, presentations, Drive file management, email, calendar events, contacts
---

# Google Workspace Skill

Manage Google Workspace documents, spreadsheets, presentations, drive files, emails, calendar events, and contacts via CLI.

## Purpose

**Google Docs:** Read, create, insert/append text, find-replace, format, page breaks, images

**Google Sheets:** Read, create, write/append data, format cells, manage sheets

**Google Slides:** Read, create presentations, add/delete slides, text boxes, images, formatting

**Google Drive:** Upload, download, search, share, create folders, move, copy, delete

**Gmail:** List, read, send, reply, search emails

**Calendar:** List calendars, create/update/delete events

**Contacts:** List, create, update, delete contacts (People API)

**Convert:** Markdown to Google Docs, Slides, or PDF

## When to Use

- User requests to read, create, or edit a Google Doc, Sheet, or Slides presentation
- User wants to upload, download, search, or share Drive files
- User wants to send, read, or search emails
- User wants to create or manage calendar events
- User wants to manage contacts
- User wants to convert Markdown to Google formats
- Keywords: "Google Doc", "spreadsheet", "presentation", "slides", "Drive", "upload", "share", "email", "calendar", "contacts"

## Safety Guidelines

**Destructive operations** - Always confirm with user before:
- Deleting documents, files, sheets, or slides (even to trash)
- Using `replace` or `replace-text` which affects ALL occurrences
- Deleting content ranges from documents
- Clearing spreadsheet ranges
- Sending emails
- Deleting calendar events or contacts

**Best practices:**
- Read document/spreadsheet/presentation first before modifying
- Show user what will change before executing
- Prefer `append` over `write` when adding new data
- Delete moves to trash by default (recoverable from Drive)
- For emails, confirm recipient and content before sending

## Quick Reference

All commands use `uv run gws <service> <command>`. Authentication is automatic on first use.

## Authentication

```bash
# Authenticate (opens browser automatically)
uv run gws auth

# Check auth status
uv run gws auth status

# Force re-authentication
uv run gws auth --force

# Logout
uv run gws auth logout
```

**Credential files** are stored in `~/.claude/.google/`:
- `client_secret.json` - OAuth client credentials (required)
- `token.json` - User access token (auto-generated)
- `gws_config.json` - Service enable/disable config

## Services Overview

| Service | Operations | Description |
|---------|------------|-------------|
| `drive` | 11 | File upload, download, share, organize |
| `docs` | 10 | Read, create, edit, format documents |
| `sheets` | 11 | Read, write, format spreadsheets |
| `slides` | 12 | Create and edit presentations |
| `gmail` | 6 | List, read, send, search emails |
| `calendar` | 6 | Manage calendar events |
| `contacts` | 5 | Manage contacts (People API) |
| `convert` | 3 | Markdown to Docs/Slides/PDF |

## Drive Operations

```bash
# List files (default: 10)
uv run gws drive list --max 20

# Search files
uv run gws drive search "name contains 'report'"

# Get file metadata
uv run gws drive get <file_id>

# Download file
uv run gws drive download <file_id> /path/to/output.pdf

# Upload file
uv run gws drive upload /path/to/file.pdf --folder <folder_id>

# Create folder
uv run gws drive create-folder "New Folder" --parent <parent_id>

# Copy file
uv run gws drive copy <file_id> --name "Copy of File"

# Move file
uv run gws drive move <file_id> <target_folder_id>

# Share file
uv run gws drive share <file_id> --role reader  # anyone with link
uv run gws drive share <file_id> --email user@example.com --role writer

# Update file content
uv run gws drive update <file_id> /path/to/new-content.pdf

# Delete file (moves to trash)
uv run gws drive delete <file_id>

# Export Google file format
uv run gws drive export <file_id> /path/to/output.pdf --format pdf
```

## Docs Operations

```bash
# Read document content (plain text)
uv run gws docs read <document_id>

# Get document structure (headings)
uv run gws docs structure <document_id>

# Create new document
uv run gws docs create "Document Title" --content "Initial content"

# Insert text at index
uv run gws docs insert <document_id> "Text to insert" --index 10

# Append text to end
uv run gws docs append <document_id> "Text to append"

# Replace text
uv run gws docs replace <document_id> "old text" "new text"

# Format text (bold, italic, underline)
uv run gws docs format <document_id> 1 50 --bold --italic

# Delete content range
uv run gws docs delete <document_id> 10 50

# Insert page break
uv run gws docs page-break <document_id> 100

# Insert image from URL
uv run gws docs insert-image <document_id> "https://example.com/image.png" --width 300
```

## Sheets Operations

```bash
# Get spreadsheet metadata
uv run gws sheets metadata <spreadsheet_id>

# Read cell range
uv run gws sheets read <spreadsheet_id> "A1:C10"
uv run gws sheets read <spreadsheet_id> "Sheet2!A1:B5"

# Create new spreadsheet
uv run gws sheets create "Spreadsheet Title" --sheets "Data,Summary"

# Write to cells
uv run gws sheets write <spreadsheet_id> "A1:C2" --values '[["A","B","C"],["1","2","3"]]'

# Append rows
uv run gws sheets append <spreadsheet_id> "A1:C1" --values '[["New","Row","Data"]]'

# Clear range
uv run gws sheets clear <spreadsheet_id> "A1:C10"

# Add new sheet
uv run gws sheets add-sheet <spreadsheet_id> "New Sheet"

# Rename sheet
uv run gws sheets rename-sheet <spreadsheet_id> <sheet_id> "Renamed Sheet"

# Delete sheet
uv run gws sheets delete-sheet <spreadsheet_id> <sheet_id>

# Format cells (bold, background color)
uv run gws sheets format <spreadsheet_id> <sheet_id> 0 5 0 3 --bold --bg-color "#FFE0B2"

# Batch get multiple ranges
uv run gws sheets batch-get <spreadsheet_id> "A1:B5,C1:D5"
```

## Slides Operations

```bash
# Get presentation metadata
uv run gws slides metadata <presentation_id>

# Read all slides with elements
uv run gws slides read <presentation_id>

# Create new presentation
uv run gws slides create "Presentation Title"

# Add slide
uv run gws slides add-slide <presentation_id> --layout TITLE_AND_BODY

# Delete slide
uv run gws slides delete-slide <presentation_id> <slide_id>

# Duplicate slide
uv run gws slides duplicate-slide <presentation_id> <slide_id>

# Create textbox
uv run gws slides create-textbox <presentation_id> <slide_id> "Text content" \
    --x 100 --y 100 --width 400 --height 50

# Insert text into element
uv run gws slides insert-text <presentation_id> <element_id> "Text to insert" --index 0

# Replace text in presentation
uv run gws slides replace-text <presentation_id> "{{placeholder}}" "Replacement"

# Format text
uv run gws slides format-text <presentation_id> <element_id> --bold --font-size 24

# Insert image
uv run gws slides insert-image <presentation_id> <slide_id> "https://example.com/image.png" \
    --x 100 --y 100 --width 300 --height 200

# Delete element
uv run gws slides delete-element <presentation_id> <element_id>
```

**Slide layouts**: BLANK, TITLE, TITLE_AND_BODY, TITLE_AND_TWO_COLUMNS, TITLE_ONLY, SECTION_HEADER, CAPTION_ONLY, BIG_NUMBER

## Gmail Operations

```bash
# List recent messages
uv run gws gmail list --max 10

# Read message
uv run gws gmail read <message_id>

# Search messages
uv run gws gmail search "is:unread from:user@example.com" --max 5

# Send email
uv run gws gmail send "recipient@example.com" "Subject" "Email body"

# Reply to message
uv run gws gmail reply <message_id> "Reply body"

# Delete message (moves to trash)
uv run gws gmail delete <message_id>
```

**Gmail search operators**: `is:unread`, `from:`, `to:`, `subject:`, `has:attachment`, `after:`, `before:`

## Calendar Operations

```bash
# List calendars
uv run gws calendar calendars

# List upcoming events
uv run gws calendar list --max 10

# Get event details
uv run gws calendar get <event_id>

# Create event (ISO 8601 datetime format)
uv run gws calendar create "Meeting" "2025-01-15T10:00:00" "2025-01-15T11:00:00" \
    --description "Discuss project" --location "Conference Room A"

# Update event
uv run gws calendar update <event_id> --summary "Updated Meeting" --location "Room B"

# Delete event
uv run gws calendar delete <event_id>
```

## Contacts Operations

```bash
# List contacts
uv run gws contacts list --max 20

# Get contact details
uv run gws contacts get <resource_name>

# Create contact
uv run gws contacts create "John Doe" --email "john@example.com" --phone "+1234567890"

# Update contact
uv run gws contacts update <resource_name> --email "newemail@example.com"

# Delete contact
uv run gws contacts delete <resource_name>
```

## Document Conversion

```bash
# Markdown to Google Doc (uses Google's native MD import)
uv run gws convert md-to-doc /path/to/document.md --title "My Document"

# Markdown to Google Slides
uv run gws convert md-to-slides /path/to/presentation.md --title "My Presentation"

# Markdown to PDF (via temp Google Doc)
uv run gws convert md-to-pdf /path/to/document.md /path/to/output.pdf
```

**Markdown formatting requirements**:
- Bullet lists MUST use asterisks (`*`) not dashes (`-`) for proper rendering
- Tables, bold, italic, code blocks, and links are supported

**Diagram rendering** (with `--render-diagrams` / `-d` flag):
```bash
uv run gws convert md-to-doc report.md --render-diagrams
uv run gws convert md-to-pdf report.md output.pdf -d
```

Supported diagram types (rendered via Kroki API):
- Mermaid (flowcharts, sequence, class, state, ER, Gantt)
- PlantUML
- GraphViz/DOT
- D2, Excalidraw, Ditaa, and 15+ more

Diagrams are automatically resized to fit the page width and height.

Mermaid diagrams use the `neutral` theme by default for professional grayscale output.

**Markdown to Slides parsing**:
- `# Heading` - New slide with title
- `## Subheading` - Subtitle
- `- item` or `* item` - Bullet points
- `1. item` - Numbered list items
- `---` - Force slide break

## Configuration

```bash
# Show current config
uv run gws config

# List all services with status
uv run gws config list

# Disable a service
uv run gws config disable gmail

# Enable a service
uv run gws config enable gmail

# Reset to defaults
uv run gws config reset
```

### Kroki Server Configuration

By default, diagrams are rendered using the public Kroki server at `https://kroki.io`. For privacy or performance, you can configure a self-hosted Kroki instance:

```bash
# Set custom Kroki server URL
uv run gws config set-kroki http://localhost:8000

# View current Kroki URL
uv run gws config
```

To run a local Kroki server with Docker:
```bash
docker run -d -p 8000:8000 yuzutech/kroki
```

## Output Format

All commands output JSON for easy parsing:

```json
{
  "status": "success",
  "operation": "docs.read",
  "document_id": "abc123",
  "content": "Document text..."
}
```

Error format:
```json
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "operation": "docs.read",
  "message": "Document not found"
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Authentication error |
| 2 | API error |
| 3 | Invalid arguments |
| 4 | Not found |

## Common Patterns

### Read and Process Document
```bash
# Get document content and pipe to another command
uv run gws docs read <doc_id> | jq -r '.content'
```

### Batch Operations
```bash
# List files and process each
uv run gws drive list --max 100 | jq -r '.files[].id' | while read id; do
  uv run gws drive get "$id"
done
```

### Create and Populate Spreadsheet
```bash
# Create spreadsheet and get ID
ID=$(uv run gws sheets create "Report" | jq -r '.spreadsheet_id')

# Write data
uv run gws sheets write "$ID" "A1:C1" --values '[["Name","Value","Date"]]'
```

## Known Limitations

1. **Port conflicts**: OAuth uses ports 8080-8099; kill stale processes if auth fails
2. **Sheet names with `!`**: Use simple range notation (e.g., `A1:C3`) when possible
3. **Slides images**: Both `--width` and `--height` must be specified together
4. **Gmail API**: Must be enabled in GCP console before first use

## Troubleshooting

**Auth fails with port conflict**:
```bash
# Kill any processes using OAuth ports
lsof -ti:8080 | xargs kill -9
```

**Token expired**:
```bash
# Force re-authentication
uv run gws auth --force
```

**API not enabled**:
Enable the required API in Google Cloud Console:
- Drive API, Docs API, Sheets API, Slides API, Gmail API, Calendar API, People API

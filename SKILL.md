---
name: google-workspace
description: Manage Google Workspace with Docs, Sheets, Slides, Drive, Gmail, Calendar, and Contacts operations. Full document/spreadsheet/presentation editing, file management, email, and scheduling.
category: productivity
version: 1.0.0
key_capabilities: Docs (read/edit/format), Sheets (read/write/format), Slides (create/edit), Drive (upload/download/share), Gmail (send/search), Calendar (events), Contacts (manage), Convert (markdown)
when_to_use: Document operations, spreadsheet data, presentations, Drive file management, email, calendar events, contacts
allowed_tools:
  - Bash(uv run gws:*)
  - Bash(cd * && uv run gws:*)
  - Read(/home/piper/.claude/.google-workspace/**)
---

# Google Workspace Skill

Manage Google Workspace documents, spreadsheets, presentations, drive files, emails, calendar events, and contacts via CLI.

## Purpose

**Google Docs:** Read, create, insert/append text, find-replace, format (text, paragraph, extended), tables (insert, style, merge, row/column ops), headers/footers, lists/bullets, page breaks, section breaks, document styling, images

**Google Sheets:** Read, create, write/append data, full cell formatting (fonts, colors, alignment, number formats), borders, merge/unmerge cells, row/column sizing, freeze panes, conditional formatting (rules and color scales)

**Google Slides:** Read, create presentations, add/delete slides, text boxes, images, full text formatting (fonts, colors, effects, superscript/subscript, links), paragraph formatting (alignment, spacing, indentation), shapes (create and style), tables (insert, style cells, add/delete rows/columns)

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

## Critical Rules

**IMPORTANT - You MUST follow these rules:**

1. **Bullet lists in Markdown**: ALWAYS use asterisks (`*`) NOT dashes (`-`) for bullet points. Google Docs API requires asterisks for proper list rendering. This applies to ALL markdown content being converted to Google Docs.
   - CORRECT: `* Item one`
   - WRONG: `- Item one`

2. **Never modify original files**: When converting Markdown to Google Docs, NEVER edit the user's original markdown file. Instead:
   - Create a temporary copy in `/tmp/` with the required formatting changes (e.g., converting `-` to `*` for bullets)
   - Upload the temporary copy to Google Docs
   - Delete the temporary file after successful upload
   - This preserves the user's original file formatting

3. **Read before modify**: ALWAYS read the document first before making changes to understand structure and indices.

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

**Credential files** are stored in `~/.claude/.google-workspace/`:
- `client_secret.json` - OAuth client credentials (required)
- `token.json` - User access token (auto-generated)
- `gws_config.json` - Service enable/disable config

## Services Reference

| Service | Ops | Reference | Description |
|---------|-----|-----------|-------------|
| `drive` | 28 | [reference/drive.md](reference/drive.md) | File upload, download, share, organize, comments, revisions, trash, permissions |
| `docs` | 48 | [reference/docs.md](reference/docs.md) | Full document editing, tables, formatting, headers/footers, lists, named ranges, footnotes, suggestions |
| `sheets` | 49 | [reference/sheets.md](reference/sheets.md) | Read, write, format, borders, merge, conditional formatting, charts, data validation, sorting, filters, pivot tables |
| `slides` | 36 | [reference/slides.md](reference/slides.md) | Create, edit, shapes, tables, backgrounds, bullets, lines, cell merging, speaker notes, videos |
| `gmail` | 35 | [reference/gmail.md](reference/gmail.md) | List, read, send, search, labels, drafts, attachments, threads, vacation, signatures, filters |
| `calendar` | 23 | [reference/calendar.md](reference/calendar.md) | Manage events, recurring events, attendees, RSVP, free/busy, calendar sharing, reminders |
| `contacts` | 15 | (below) | Manage contacts, groups, photos (People API) |
| `convert` | 3 | (below) | Markdown to Docs/Slides/PDF |

For design best practices (typography, visual hierarchy, API efficiency), see [SKILL-advanced.md](SKILL-advanced.md).

## Contacts Operations

### Basic Operations

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

### Contact Groups

```bash
# List all contact groups
uv run gws contacts groups

# Get a group with its members
uv run gws contacts get-group <group_resource_name>

# Get group without member list
uv run gws contacts get-group <group_resource_name> --no-members

# Create a new group
uv run gws contacts create-group "Work Colleagues"

# Rename a group
uv run gws contacts update-group <group_resource_name> "New Group Name"

# Delete a group (keeps contacts)
uv run gws contacts delete-group <group_resource_name>

# Delete group AND its contacts
uv run gws contacts delete-group <group_resource_name> --delete-contacts

# Add contacts to a group
uv run gws contacts add-to-group <group_resource_name> "people/c123,people/c456"

# Remove contacts from a group
uv run gws contacts remove-from-group <group_resource_name> "people/c123"
```

### Contact Photos

```bash
# Get a contact's photo URL
uv run gws contacts get-photo <resource_name>

# Set a contact's photo from a local file (JPEG or PNG, max 2MB)
uv run gws contacts set-photo <resource_name> /path/to/photo.jpg

# Delete a contact's photo
uv run gws contacts delete-photo <resource_name>
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
2. **Sheet names with exclamation marks**: Use simple range notation (e.g., `A1:C3`) when possible
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

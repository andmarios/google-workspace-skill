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
  - Read(/home/piper/.claude/.google/**)
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

**Credential files** are stored in `~/.claude/.google/`:
- `client_secret.json` - OAuth client credentials (required)
- `token.json` - User access token (auto-generated)
- `gws_config.json` - Service enable/disable config

## Services Overview

| Service | Operations | Description |
|---------|------------|-------------|
| `drive` | 11 | File upload, download, share, organize |
| `docs` | 37 | Full document editing, tables, formatting, headers/footers, lists |
| `sheets` | 23 | Read, write, format, borders, merge, conditional formatting |
| `slides` | 24 | Create, edit, shapes, tables, professional formatting |
| `gmail` | 8 | List, read, send, search, mark read/unread |
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

### Basic Operations

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

# Replace all occurrences
uv run gws docs replace <document_id> "old text" "new text"

# Delete content range
uv run gws docs delete <document_id> 10 50

# Insert page break
uv run gws docs page-break <document_id> 100

# Insert image from URL
uv run gws docs insert-image <document_id> "https://example.com/image.png" --width 300
```

### Text Formatting

```bash
# Basic formatting (bold, italic, underline)
uv run gws docs format <document_id> 1 50 --bold --italic --underline

# Extended formatting (fonts, colors, effects)
uv run gws docs format-text-extended <document_id> 1 50 \
    --font "Arial" --size 14 --color "#FF0000" \
    --bg-color "#FFFF00" --strikethrough --small-caps

# Superscript/subscript
uv run gws docs format-text-extended <document_id> 10 12 --superscript
uv run gws docs format-text-extended <document_id> 20 22 --subscript

# Add hyperlink to text
uv run gws docs insert-link <document_id> 5 15 "https://example.com"
```

### Paragraph Formatting

```bash
# Alignment and named styles
uv run gws docs format-paragraph <document_id> 1 100 --align CENTER
uv run gws docs format-paragraph <document_id> 1 50 --style HEADING_1

# Spacing and indentation
uv run gws docs format-paragraph <document_id> 1 100 \
    --space-above 12 --space-below 6 --line-spacing 150 \
    --indent-first 36 --indent-left 18

# Paragraph borders
uv run gws docs paragraph-border <document_id> 1 100 \
    --all --color "#0000FF" --width 2

# Keep lines together
uv run gws docs format-paragraph <document_id> 1 100 --keep-together --keep-with-next
```

**Named styles**: TITLE, SUBTITLE, HEADING_1 through HEADING_6, NORMAL_TEXT

### Tables

```bash
# List tables in document
uv run gws docs list-tables <document_id>

# Insert table (rows, columns)
uv run gws docs insert-table <document_id> 3 4 --index 50

# Row and column operations
uv run gws docs insert-table-row <document_id> 0 1 --above
uv run gws docs insert-table-column <document_id> 0 2 --left
uv run gws docs delete-table-row <document_id> 0 2
uv run gws docs delete-table-column <document_id> 0 1

# Merge/unmerge cells
uv run gws docs merge-cells <document_id> 0 0 0 1 2    # start_row, start_col, end_row, end_col
uv run gws docs unmerge-cells <document_id> 0 0 0 1 2

# Style table cells
uv run gws docs style-table-cell <document_id> 0 0 0 \
    --bg-color "#FFFF00" --border-color "#000000" --border-width 1 --padding 5

# Set column width (points)
uv run gws docs set-column-width <document_id> 0 1 150

# Pin header rows
uv run gws docs pin-table-header <document_id> 0 --rows 2
```

### Lists and Bullets

```bash
# Create bulleted list
uv run gws docs create-bullets <document_id> 1 100 --preset BULLET_DISC_CIRCLE_SQUARE

# Create numbered list
uv run gws docs create-numbered <document_id> 1 100 --preset NUMBERED_DECIMAL_NESTED

# Remove bullets/numbering
uv run gws docs remove-bullets <document_id> 1 100
```

**Bullet presets**: BULLET_DISC_CIRCLE_SQUARE, BULLET_CHECKBOX, BULLET_DIAMONDX_ARROW3D_SQUARE

**Number presets**: NUMBERED_DECIMAL_NESTED, NUMBERED_DECIMAL_ALPHA_ROMAN

### Headers and Footers

```bash
# List headers/footers
uv run gws docs list-headers-footers <document_id>

# Create header/footer
uv run gws docs create-header <document_id> --type DEFAULT
uv run gws docs create-footer <document_id> --type FIRST_PAGE_FOOTER

# Insert text into header/footer
uv run gws docs insert-segment-text <document_id> <header_id> "Company Name" --index 0

# Delete header/footer
uv run gws docs delete-header <document_id> <header_id>
uv run gws docs delete-footer <document_id> <footer_id>
```

**Header/footer types**: DEFAULT, FIRST_PAGE_HEADER, FIRST_PAGE_FOOTER

### Sections and Document Style

```bash
# Insert section break
uv run gws docs insert-section-break <document_id> 100 --type NEXT_PAGE

# Update document margins and page size (points, 72pt = 1 inch)
uv run gws docs document-style <document_id> \
    --margin-top 72 --margin-bottom 72 --margin-left 72 --margin-right 72

# Change page size (612x792 = Letter, 595x842 = A4)
uv run gws docs document-style <document_id> --page-width 595 --page-height 842

# Different first page header/footer
uv run gws docs document-style <document_id> --first-page-diff
```

**Section break types**: NEXT_PAGE, CONTINUOUS

## Sheets Operations

### Basic Operations

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

# Batch get multiple ranges
uv run gws sheets batch-get <spreadsheet_id> "A1:B5,C1:D5"
```

### Sheet Management

```bash
# Add new sheet
uv run gws sheets add-sheet <spreadsheet_id> "New Sheet"

# Rename sheet
uv run gws sheets rename-sheet <spreadsheet_id> <sheet_id> "Renamed Sheet"

# Delete sheet
uv run gws sheets delete-sheet <spreadsheet_id> <sheet_id>
```

### Cell Formatting

```bash
# Basic formatting (bold, background color)
uv run gws sheets format <spreadsheet_id> <sheet_id> 0 5 0 3 --bold --bg-color "#FFE0B2"

# Extended formatting (full typography and alignment control)
uv run gws sheets format-extended <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --bold --italic --font "Arial" --size 12 \
    --color "#000000" --bg-color "#E3F2FD" \
    --h-align CENTER --v-align MIDDLE --wrap WRAP

# Number formatting
uv run gws sheets format-extended <spreadsheet_id> <sheet_id> 1 10 2 3 \
    --number-format "#,##0.00"      # Currency style
uv run gws sheets format-extended <spreadsheet_id> <sheet_id> 1 10 4 5 \
    --number-format "0%"             # Percentage style
```

**Horizontal alignment**: LEFT, CENTER, RIGHT
**Vertical alignment**: TOP, MIDDLE, BOTTOM
**Text wrap**: OVERFLOW_CELL, CLIP, WRAP
**Number formats**: Use spreadsheet pattern syntax (e.g., `#,##0.00`, `0%`, `yyyy-mm-dd`)

### Cell Borders

```bash
# Add borders to all sides of a range
uv run gws sheets set-borders <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --all --color "#000000" --style SOLID --width 1

# Custom border configuration
uv run gws sheets set-borders <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --top --bottom --left --right \
    --color "#0000FF" --style DASHED --width 2

# Grid lines (inner borders)
uv run gws sheets set-borders <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --all --inner-horizontal --inner-vertical
```

**Border styles**: SOLID, DOTTED, DASHED, SOLID_MEDIUM, SOLID_THICK, DOUBLE

### Merge and Unmerge Cells

```bash
# Merge all cells in range
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4

# Merge types
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4 --type MERGE_ALL
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4 --type MERGE_COLUMNS
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4 --type MERGE_ROWS

# Unmerge cells
uv run gws sheets unmerge-cells <spreadsheet_id> <sheet_id> 0 3 0 4
```

**Merge types**: MERGE_ALL (single cell), MERGE_COLUMNS (merge within columns), MERGE_ROWS (merge within rows)

### Row and Column Sizing

```bash
# Set column width (pixels)
uv run gws sheets set-column-width <spreadsheet_id> <sheet_id> 0 3 150

# Set row height (pixels)
uv run gws sheets set-row-height <spreadsheet_id> <sheet_id> 0 5 30

# Auto-resize columns to fit content
uv run gws sheets auto-resize-columns <spreadsheet_id> <sheet_id> 0 5
```

### Freeze Panes

```bash
# Freeze header rows (first N rows stay visible when scrolling)
uv run gws sheets freeze-rows <spreadsheet_id> <sheet_id> 1

# Freeze columns (first N columns stay visible)
uv run gws sheets freeze-columns <spreadsheet_id> <sheet_id> 2

# Unfreeze (set to 0)
uv run gws sheets freeze-rows <spreadsheet_id> <sheet_id> 0
uv run gws sheets freeze-columns <spreadsheet_id> <sheet_id> 0
```

### Conditional Formatting

```bash
# Highlight cells greater than a value
uv run gws sheets add-conditional-format <spreadsheet_id> <sheet_id> 1 100 2 3 \
    --condition NUMBER_GREATER --values 100 --bg-color "#FFCDD2"

# Highlight cells containing text
uv run gws sheets add-conditional-format <spreadsheet_id> <sheet_id> 1 100 0 1 \
    --condition TEXT_CONTAINS --values "urgent" \
    --bg-color "#FFEB3B" --color "#000000" --bold

# Highlight blank cells
uv run gws sheets add-conditional-format <spreadsheet_id> <sheet_id> 1 100 0 5 \
    --condition BLANK --bg-color "#E0E0E0"

# Color scale (gradient from min to max)
uv run gws sheets add-color-scale <spreadsheet_id> <sheet_id> 1 100 2 3 \
    --min-color "#FFFFFF" --max-color "#4CAF50"

# Three-color scale (with midpoint)
uv run gws sheets add-color-scale <spreadsheet_id> <sheet_id> 1 100 2 3 \
    --min-color "#F44336" --mid-color "#FFEB3B" --max-color "#4CAF50"

# Clear all conditional formatting from sheet
uv run gws sheets clear-conditional-formats <spreadsheet_id> <sheet_id>
```

**Condition types**: NUMBER_GREATER, NUMBER_LESS, NUMBER_EQ, NUMBER_BETWEEN, TEXT_CONTAINS, TEXT_NOT_CONTAINS, TEXT_STARTS_WITH, TEXT_ENDS_WITH, BLANK, NOT_BLANK, DATE_BEFORE, DATE_AFTER

## Slides Operations

### Basic Operations

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
```

**Slide layouts**: BLANK, TITLE, TITLE_AND_BODY, TITLE_AND_TWO_COLUMNS, TITLE_ONLY, SECTION_HEADER, CAPTION_ONLY, BIG_NUMBER

### Text Boxes and Content

```bash
# Create textbox
uv run gws slides create-textbox <presentation_id> <slide_id> "Text content" \
    --x 100 --y 100 --width 400 --height 50

# Insert text into element
uv run gws slides insert-text <presentation_id> <element_id> "Text to insert" --index 0

# Replace text in presentation
uv run gws slides replace-text <presentation_id> "{{placeholder}}" "Replacement"

# Insert image
uv run gws slides insert-image <presentation_id> <slide_id> "https://example.com/image.png" \
    --x 100 --y 100 --width 300 --height 200

# Delete element
uv run gws slides delete-element <presentation_id> <element_id>
```

### Text Formatting

```bash
# Basic formatting
uv run gws slides format-text <presentation_id> <element_id> --bold --font-size 24

# Extended formatting (full typography control)
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --bold --italic --underline --strikethrough \
    --font "Arial" --weight 700 --size 18 \
    --color "#1A237E" --bg-color "#E3F2FD"

# Format specific text range (start_index to end_index)
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 0 --end 10 --bold --color "#FF0000"

# Superscript/subscript
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 5 --end 7 --baseline SUPERSCRIPT
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 10 --end 12 --baseline SUBSCRIPT

# Add hyperlink
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 0 --end 15 --link "https://example.com"

# Small caps
uv run gws slides format-text-extended <presentation_id> <element_id> --small-caps
```

**Baseline offsets**: SUPERSCRIPT, SUBSCRIPT, NONE
**Font weights**: 100 (thin) to 900 (black), 400 is normal, 700 is bold

### Paragraph Formatting

```bash
# Paragraph alignment
uv run gws slides format-paragraph <presentation_id> <element_id> --align CENTER

# Line spacing and paragraph spacing (points)
uv run gws slides format-paragraph <presentation_id> <element_id> \
    --line-spacing 150 --space-above 12 --space-below 6

# Indentation (points)
uv run gws slides format-paragraph <presentation_id> <element_id> \
    --indent-first 36 --indent-start 18 --indent-end 0

# Format specific paragraph range
uv run gws slides format-paragraph <presentation_id> <element_id> \
    --start 0 --end 100 --align JUSTIFIED
```

**Alignments**: START, CENTER, END, JUSTIFIED

### Shapes

```bash
# Create shape
uv run gws slides create-shape <presentation_id> <slide_id> RECTANGLE \
    --x 100 --y 100 --width 200 --height 100

# Create other shape types
uv run gws slides create-shape <presentation_id> <slide_id> ELLIPSE \
    --x 350 --y 100 --width 150 --height 150
uv run gws slides create-shape <presentation_id> <slide_id> ROUND_RECTANGLE \
    --x 100 --y 250 --width 200 --height 80

# Format shape appearance
uv run gws slides format-shape <presentation_id> <shape_id> \
    --fill-color "#4CAF50" --outline-color "#2E7D32" \
    --outline-weight 2 --outline-dash SOLID

# Dashed outline
uv run gws slides format-shape <presentation_id> <shape_id> \
    --outline-dash DASH --outline-weight 3
```

**Shape types**: RECTANGLE, ROUND_RECTANGLE, ELLIPSE, TRIANGLE, RIGHT_TRIANGLE, PARALLELOGRAM, TRAPEZOID, PENTAGON, HEXAGON, HEPTAGON, OCTAGON, STAR_4, STAR_5, STAR_6, ARROW_EAST, ARROW_NORTH, PLUS, and many more

**Outline dash styles**: SOLID, DASH, DOT, DASH_DOT, LONG_DASH, LONG_DASH_DOT

### Tables

```bash
# Insert table
uv run gws slides insert-table <presentation_id> <slide_id> 4 3 \
    --x 100 --y 150 --width 500 --height 200

# Insert text into table cell
uv run gws slides insert-table-text <presentation_id> <table_id> 0 0 "Header 1"
uv run gws slides insert-table-text <presentation_id> <table_id> 0 1 "Header 2"
uv run gws slides insert-table-text <presentation_id> <table_id> 1 0 "Row 1 Data"

# Style table cell (background color)
uv run gws slides style-table-cell <presentation_id> <table_id> 0 0 \
    --bg-color "#1565C0"

# Style header row
uv run gws slides style-table-cell <presentation_id> <table_id> 0 0 --bg-color "#E3F2FD"
uv run gws slides style-table-cell <presentation_id> <table_id> 0 1 --bg-color "#E3F2FD"
uv run gws slides style-table-cell <presentation_id> <table_id> 0 2 --bg-color "#E3F2FD"

# Insert row (below specified row index)
uv run gws slides insert-table-row <presentation_id> <table_id> 2

# Insert row above
uv run gws slides insert-table-row <presentation_id> <table_id> 0 --above

# Insert column (right of specified column index)
uv run gws slides insert-table-column <presentation_id> <table_id> 1

# Insert column to the left
uv run gws slides insert-table-column <presentation_id> <table_id> 0 --left

# Delete row
uv run gws slides delete-table-row <presentation_id> <table_id> 3

# Delete column
uv run gws slides delete-table-column <presentation_id> <table_id> 2
```

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

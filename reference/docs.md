# Google Docs Operations

## Contents
- [Basic Operations](#basic-operations)
- [Finding Text](#finding-text)
- [Markdown Insertion](#markdown-insertion)
- [Page Format (Pageless Mode)](#page-format-pageless-mode)
- [Document Tabs](#document-tabs)
- [Text Formatting](#text-formatting)
- [Paragraph Formatting](#paragraph-formatting)
- [Tables](#tables)
- [Lists and Bullets](#lists-and-bullets)
- [Headers and Footers](#headers-and-footers)
- [Sections and Document Style](#sections-and-document-style)
- [Named Ranges (Bookmarks)](#named-ranges-bookmarks)
- [Footnotes](#footnotes)
- [Suggestions (Tracked Changes)](#suggestions-tracked-changes)

## Basic Operations

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

## Finding Text

Find text positions for precise insertions and insert images at specific text locations.

```bash
# Find text and get its character index
uv run gws docs find-text <document_id> "Section Title"
# Returns: {"index": 3067, "end_index": 3080, "length": 13, ...}

# Find a specific occurrence (if text appears multiple times)
uv run gws docs find-text <document_id> "Summary" --occurrence 2

# Find text in a specific tab
uv run gws docs find-text <document_id> "Introduction" --tab <tab_id>

# Insert image directly after specific text (avoids index calculation)
uv run gws docs insert-image-at-text <document_id> "https://example.com/diagram.png" "Flowchart:"

# With sizing
uv run gws docs insert-image-at-text <document_id> "https://example.com/chart.png" "Figure 1:" \
    --width 400 --height 300

# After a specific occurrence
uv run gws docs insert-image-at-text <document_id> "https://..." "Data Analysis" --occurrence 2
```

**Response structure for find-text:**
```json
{
  "status": "success",
  "operation": "docs.find_text",
  "index": 3067,
  "end_index": 3080,
  "length": 13,
  "occurrence": 1,
  "total_occurrences": 3
}
```

**Tip**: Use `insert-image-at-text` instead of `insert-image` with manual indices to avoid "insertion index must be inside the bounds of an existing paragraph" errors.

## Markdown Insertion

Insert markdown content into an existing document with automatic formatting conversion. Google converts the markdown to formatted text (bold, italic, links, headings, etc.).

```bash
# Insert markdown at the beginning of the document
uv run gws docs insert-markdown <document_id> "# New Section\n\n**Bold** and *italic* text"

# Insert at a specific position
uv run gws docs insert-markdown <document_id> "## Subheading" --index 50

# Insert from a markdown file
uv run gws docs insert-markdown <document_id> --file notes.md

# Insert from stdin (piping)
cat notes.md | uv run gws docs insert-markdown <document_id> --stdin

# Insert into a specific tab
uv run gws docs insert-markdown <document_id> --file content.md --tab <tab_id>
```

**Supported Markdown Features**: Headers, bold, italic, links, code blocks, lists, and other standard markdown formatting.

## Page Format (Pageless Mode)

Google Docs supports two page formats:
- **PAGES**: Traditional page-based format with page breaks
- **PAGELESS**: Continuous scrolling format without page breaks

```bash
# Get current page format
uv run gws docs get-page-format <document_id>

# Switch to pageless mode
uv run gws docs set-page-format <document_id> pageless

# Switch back to pages mode
uv run gws docs set-page-format <document_id> pages
```

**Note**: Switching to PAGELESS mode hides headers, footers, page numbers, and other page-specific elements. Content remains but these features become invisible.

## Document Tabs

Google Docs supports multiple tabs within a single document. All reading and editing commands support an optional `--tab` parameter to target a specific tab.

### Listing and Reading Tabs

```bash
# List all tabs in a document
uv run gws docs list-tabs <document_id>

# Read content from a specific tab
uv run gws docs read <document_id> --tab <tab_id>

# Get structure of a specific tab
uv run gws docs structure <document_id> --tab <tab_id>
```

### Editing Within Tabs

All editing commands support the `--tab` option:

```bash
# Insert text into a specific tab
uv run gws docs insert <document_id> "Text" --index 10 --tab <tab_id>

# Append to a specific tab
uv run gws docs append <document_id> "Text" --tab <tab_id>

# Replace text in a specific tab
uv run gws docs replace <document_id> "old" "new" --tab <tab_id>

# Format text in a specific tab
uv run gws docs format <document_id> 1 50 --bold --tab <tab_id>

# Delete content in a specific tab
uv run gws docs delete <document_id> 10 50 --tab <tab_id>

# Insert page break in a specific tab
uv run gws docs page-break <document_id> 100 --tab <tab_id>

# Insert image in a specific tab
uv run gws docs insert-image <document_id> "https://..." --tab <tab_id>
```

### Tab Management

```bash
# Create a new tab
uv run gws docs create-tab <document_id> "Tab Title"

# Create tab at specific position (0-indexed)
uv run gws docs create-tab <document_id> "Tab Title" --index 0

# Rename a tab
uv run gws docs rename-tab <document_id> <tab_id> "New Title"

# Move tab to a new position
uv run gws docs reorder-tab <document_id> <tab_id> 2

# Delete a tab
uv run gws docs delete-tab <document_id> <tab_id>
```

**Note**: Tab IDs are returned by the `list-tabs` command. When no `--tab` is specified, operations target the first (default) tab.

## Text Formatting

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

## Paragraph Formatting

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

## Tables

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

## Lists and Bullets

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

## Headers and Footers

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

## Sections and Document Style

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

## Named Ranges (Bookmarks)

```bash
# Create a named range
uv run gws docs create-named-range <document_id> "Section1" 1 100

# List all named ranges
uv run gws docs list-named-ranges <document_id>

# Delete named range by name
uv run gws docs delete-named-range <document_id> --name "Section1"

# Delete named range by ID
uv run gws docs delete-named-range <document_id> --id "kix.abc123"
```

## Footnotes

```bash
# Insert a footnote reference at a position
uv run gws docs insert-footnote <document_id> 50

# List all footnotes in document
uv run gws docs list-footnotes <document_id>

# Add content to a footnote (use insert-segment-text with footnote ID)
uv run gws docs insert-segment-text <document_id> <footnote_id> "Footnote text here" --index 0
```

## Suggestions (Tracked Changes)

```bash
# Get all pending suggestions in a document
uv run gws docs suggestions <document_id>

# Check if document has pending suggestions
uv run gws docs document-mode <document_id>

# Accept a specific suggestion
uv run gws docs accept-suggestion <document_id> <suggestion_id>

# Reject a specific suggestion
uv run gws docs reject-suggestion <document_id> <suggestion_id>

# Accept all pending suggestions
uv run gws docs accept-all-suggestions <document_id>

# Reject all pending suggestions
uv run gws docs reject-all-suggestions <document_id>
```

**Note**: Suggestion IDs can be obtained from the `suggestions` command output.

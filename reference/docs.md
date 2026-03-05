# Google Docs Operations

## Contents
- [Basic Operations](#basic-operations)
- [Exporting Documents](#exporting-documents)
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
- [Images](#images)
- [Positioned Objects](#positioned-objects)
- [Footnotes](#footnotes)
- [Suggestions (Tracked Changes)](#suggestions-tracked-changes)

## Basic Operations

```bash
# Read document content (plain text)
uvx gws-cli docs read <document_id>

# Get document structure (headings)
uvx gws-cli docs structure <document_id>

# Create new document
uvx gws-cli docs create "Document Title" --content "Initial content"

# Insert text at index
uvx gws-cli docs insert <document_id> "Text to insert" --index 10

# Append text to end
uvx gws-cli docs append <document_id> "Text to append"

# Append multi-line content via stdin
cat <<'EOF' | uvx gws-cli docs append <document_id> --stdin
This is a multi-paragraph addition.

It preserves line breaks and formatting.
Useful for templates or boilerplate content.
EOF

# Replace all occurrences
uvx gws-cli docs replace <document_id> "old text" "new text"

# Delete content range
uvx gws-cli docs delete <document_id> 10 50

# Insert page break
uvx gws-cli docs page-break <document_id> 100

# Insert image from URL
uvx gws-cli docs insert-image <document_id> "https://example.com/image.png" --width 300
```

## Exporting Documents

Export a Google Doc to various file formats. The default format is markdown.

```bash
# Export as Markdown (default)
uvx gws-cli docs export <document_id> report.md

# Export as PDF
uvx gws-cli docs export <document_id> report.pdf --format pdf

# Export as Word document (DOCX)
uvx gws-cli docs export <document_id> report.docx --format docx

# Export as plain text
uvx gws-cli docs export <document_id> report.txt --format txt

# Export as HTML
uvx gws-cli docs export <document_id> report.html --format html

# Export as RTF
uvx gws-cli docs export <document_id> report.rtf --format rtf

# Export as EPUB (e-book)
uvx gws-cli docs export <document_id> report.epub --format epub

# Export as ODT (LibreOffice)
uvx gws-cli docs export <document_id> report.odt --format odt

# You can also pass a raw MIME type
uvx gws-cli docs export <document_id> output.zip --format "application/zip"
```

**Supported formats:**

| Format     | Aliases      | MIME Type |
|------------|-------------|-----------|
| Markdown   | `markdown`, `md` | `text/markdown` |
| PDF        | `pdf`       | `application/pdf` |
| Word       | `docx`      | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| Plain text | `txt`, `text` | `text/plain` |
| HTML       | `html`      | `text/html` |
| RTF        | `rtf`       | `application/rtf` |
| EPUB       | `epub`      | `application/epub+zip` |
| ODT        | `odt`       | `application/vnd.oasis.opendocument.text` |

**Note**: Markdown export preserves headings, bold, italic, links, and lists. Complex formatting like custom fonts, colors, and images may not convert perfectly. For full-fidelity export, use PDF or DOCX.

## Finding Text

Find text positions for precise insertions and insert images at specific text locations.

```bash
# Find text and get its character index
uvx gws-cli docs find-text <document_id> "Section Title"
# Returns: {"index": 3067, "end_index": 3080, "length": 13, ...}

# Find a specific occurrence (if text appears multiple times)
uvx gws-cli docs find-text <document_id> "Summary" --occurrence 2

# Find text in a specific tab
uvx gws-cli docs find-text <document_id> "Introduction" --tab <tab_id>

# Insert image directly after specific text (avoids index calculation)
uvx gws-cli docs insert-image-at-text <document_id> "https://example.com/diagram.png" "Flowchart:"

# With sizing
uvx gws-cli docs insert-image-at-text <document_id> "https://example.com/chart.png" "Figure 1:" \
    --width 400 --height 300

# After a specific occurrence
uvx gws-cli docs insert-image-at-text <document_id> "https://..." "Data Analysis" --occurrence 2
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
uvx gws-cli docs insert-markdown <document_id> "# New Section\n\n**Bold** and *italic* text"

# Insert at a specific position
uvx gws-cli docs insert-markdown <document_id> "## Subheading" --index 50

# Insert from a markdown file
uvx gws-cli docs insert-markdown <document_id> --file notes.md

# Insert from stdin (piping from file)
cat notes.md | uvx gws-cli docs insert-markdown <document_id> --stdin

# Insert markdown via heredoc
cat <<'EOF' | uvx gws-cli docs insert-markdown <document_id> --stdin
## New Section

This content will be **formatted** with:
* Bullet points
* Links: [example](https://example.com)
* And other markdown features
EOF

# Insert at specific position from stdin
cat notes.md | uvx gws-cli docs insert-markdown <document_id> --stdin --index 50

# Insert into a specific tab
uvx gws-cli docs insert-markdown <document_id> --file content.md --tab <tab_id>
```

**Supported Markdown Features**: Headers, bold, italic, links, code blocks, lists, and other standard markdown formatting.

## Page Format (Pageless Mode)

Google Docs supports two page formats:
- **PAGES**: Traditional page-based format with page breaks
- **PAGELESS**: Continuous scrolling format without page breaks

```bash
# Get current page format
uvx gws-cli docs get-page-format <document_id>

# Switch to pageless mode
uvx gws-cli docs set-page-format <document_id> pageless

# Switch back to pages mode
uvx gws-cli docs set-page-format <document_id> pages
```

**Note**: Switching to PAGELESS mode hides headers, footers, page numbers, and other page-specific elements. Content remains but these features become invisible.

## Document Tabs

Google Docs supports multiple tabs within a single document. All reading and editing commands support an optional `--tab` parameter to target a specific tab.

### Listing and Reading Tabs

```bash
# List all tabs in a document
uvx gws-cli docs list-tabs <document_id>

# Read content from a specific tab
uvx gws-cli docs read <document_id> --tab <tab_id>

# Get structure of a specific tab
uvx gws-cli docs structure <document_id> --tab <tab_id>
```

### Editing Within Tabs

All editing commands support the `--tab` option:

```bash
# Insert text into a specific tab
uvx gws-cli docs insert <document_id> "Text" --index 10 --tab <tab_id>

# Append to a specific tab
uvx gws-cli docs append <document_id> "Text" --tab <tab_id>

# Replace text in a specific tab
uvx gws-cli docs replace <document_id> "old" "new" --tab <tab_id>

# Format text in a specific tab
uvx gws-cli docs format <document_id> 1 50 --bold --tab <tab_id>

# Delete content in a specific tab
uvx gws-cli docs delete <document_id> 10 50 --tab <tab_id>

# Insert page break in a specific tab
uvx gws-cli docs page-break <document_id> 100 --tab <tab_id>

# Insert image in a specific tab
uvx gws-cli docs insert-image <document_id> "https://..." --tab <tab_id>
```

### Tab Management

```bash
# Create a new tab
uvx gws-cli docs create-tab <document_id> "Tab Title"

# Create tab at specific position (0-indexed)
uvx gws-cli docs create-tab <document_id> "Tab Title" --index 0

# Rename a tab
uvx gws-cli docs rename-tab <document_id> <tab_id> "New Title"

# Move tab to a new position
uvx gws-cli docs reorder-tab <document_id> <tab_id> 2

# Delete a tab
uvx gws-cli docs delete-tab <document_id> <tab_id>
```

**Note**: Tab IDs are returned by the `list-tabs` command. When no `--tab` is specified, operations target the first (default) tab.

## Text Formatting

```bash
# Basic formatting (bold, italic, underline)
uvx gws-cli docs format <document_id> 1 50 --bold --italic --underline

# Extended formatting (fonts, colors, effects)
uvx gws-cli docs format-text-extended <document_id> 1 50 \
    --font "Arial" --size 14 --color "#FF0000" \
    --bg-color "#FFFF00" --strikethrough --small-caps

# Superscript/subscript
uvx gws-cli docs format-text-extended <document_id> 10 12 --superscript
uvx gws-cli docs format-text-extended <document_id> 20 22 --subscript

# Add hyperlink to text
uvx gws-cli docs insert-link <document_id> 5 15 "https://example.com"
```

## Paragraph Formatting

```bash
# Alignment and named styles
uvx gws-cli docs format-paragraph <document_id> 1 100 --align CENTER
uvx gws-cli docs format-paragraph <document_id> 1 50 --style HEADING_1

# Spacing and indentation
uvx gws-cli docs format-paragraph <document_id> 1 100 \
    --space-above 12 --space-below 6 --line-spacing 150 \
    --indent-first 36 --indent-left 18

# Paragraph borders
uvx gws-cli docs paragraph-border <document_id> 1 100 \
    --all --color "#0000FF" --width 2

# Keep lines together
uvx gws-cli docs format-paragraph <document_id> 1 100 --keep-together --keep-with-next
```

**Named styles**: TITLE, SUBTITLE, HEADING_1 through HEADING_6, NORMAL_TEXT

## Tables

```bash
# List tables in document
uvx gws-cli docs list-tables <document_id>

# Insert table (rows, columns)
uvx gws-cli docs insert-table <document_id> 3 4 --index 50

# Row and column operations
uvx gws-cli docs insert-table-row <document_id> 0 1 --above
uvx gws-cli docs insert-table-column <document_id> 0 2 --left
uvx gws-cli docs delete-table-row <document_id> 0 2
uvx gws-cli docs delete-table-column <document_id> 0 1

# Merge/unmerge cells
uvx gws-cli docs merge-cells <document_id> 0 0 0 1 2    # start_row, start_col, end_row, end_col
uvx gws-cli docs unmerge-cells <document_id> 0 0 0 1 2

# Style table cells
uvx gws-cli docs style-table-cell <document_id> 0 0 0 \
    --bg-color "#FFFF00" --border-color "#000000" --border-width 1 --padding 5

# Set column width (points)
uvx gws-cli docs set-column-width <document_id> 0 1 150

# Set multiple column widths in one API call (more efficient)
uvx gws-cli docs set-table-column-widths <document_id> 0 '{"0":70,"1":90,"2":170,"3":50}'

# Pin header rows
uvx gws-cli docs pin-table-header <document_id> 0 --rows 2
```

## Lists and Bullets

```bash
# Create bulleted list
uvx gws-cli docs create-bullets <document_id> 1 100 --preset BULLET_DISC_CIRCLE_SQUARE

# Create numbered list
uvx gws-cli docs create-numbered <document_id> 1 100 --preset NUMBERED_DECIMAL_NESTED

# Remove bullets/numbering
uvx gws-cli docs remove-bullets <document_id> 1 100
```

**Bullet presets**: BULLET_DISC_CIRCLE_SQUARE, BULLET_CHECKBOX, BULLET_DIAMONDX_ARROW3D_SQUARE

**Number presets**: NUMBERED_DECIMAL_NESTED, NUMBERED_DECIMAL_ALPHA_ROMAN

## Headers and Footers

```bash
# List headers/footers
uvx gws-cli docs list-headers-footers <document_id>

# Create header/footer
uvx gws-cli docs create-header <document_id> --type DEFAULT
uvx gws-cli docs create-footer <document_id> --type FIRST_PAGE_FOOTER

# Insert text into header/footer
uvx gws-cli docs insert-segment-text <document_id> <header_id> "Company Name" --index 0

# Delete header/footer
uvx gws-cli docs delete-header <document_id> <header_id>
uvx gws-cli docs delete-footer <document_id> <footer_id>
```

**Header/footer types**: DEFAULT, FIRST_PAGE_HEADER, FIRST_PAGE_FOOTER

## Sections and Document Style

```bash
# Insert section break
uvx gws-cli docs insert-section-break <document_id> 100 --type NEXT_PAGE

# Update document margins and page size (points, 72pt = 1 inch)
uvx gws-cli docs document-style <document_id> \
    --margin-top 72 --margin-bottom 72 --margin-left 72 --margin-right 72

# Change page size (612x792 = Letter, 595x842 = A4)
uvx gws-cli docs document-style <document_id> --page-width 595 --page-height 842

# Different first page header/footer
uvx gws-cli docs document-style <document_id> --first-page-diff
```

**Section break types**: NEXT_PAGE, CONTINUOUS

## Named Ranges (Bookmarks)

```bash
# Create a named range
uvx gws-cli docs create-named-range <document_id> "Section1" 1 100

# List all named ranges
uvx gws-cli docs list-named-ranges <document_id>

# Delete named range by name
uvx gws-cli docs delete-named-range <document_id> --name "Section1"

# Delete named range by ID
uvx gws-cli docs delete-named-range <document_id> --id "kix.abc123"

# Replace content within a named range (useful for templates)
uvx gws-cli docs replace-named-range <document_id> "New content" --name "Section1"

# Replace by named range ID
uvx gws-cli docs replace-named-range <document_id> "Updated text" --id "kix.abc123"
```

**Template workflow**: Create a document template with named ranges as placeholders (e.g., `{{NAME}}`, `{{DATE}}`), then use `replace-named-range` to fill in values programmatically.

## Images

```bash
# Insert image from URL (see Basic Operations)
uvx gws-cli docs insert-image <document_id> "https://example.com/image.png" --width 300

# Insert image after specific text (see Finding Text)
uvx gws-cli docs insert-image-at-text <document_id> "https://example.com/chart.png" "Figure 1:"

# Replace an existing image with a new one
uvx gws-cli docs replace-image <document_id> <image_object_id> "https://example.com/new-image.png"

# Replace image with specific method (CENTER_CROP is default)
uvx gws-cli docs replace-image <document_id> <image_object_id> "https://example.com/new-image.png" --method CENTER_CROP
```

**Note**: The `image_object_id` can be found in the document structure. Use `replace-image` to update charts, diagrams, or photos without changing their position or size in the document.

## Positioned Objects

Positioned objects are floating elements that can be placed anywhere on a page, including floating images, drawings, and other objects that are not inline with text.

```bash
# Delete a positioned object (floating image, drawing, etc.)
uvx gws-cli docs delete-positioned-object <document_id> <object_id>

# Delete positioned object in a specific tab
uvx gws-cli docs delete-positioned-object <document_id> <object_id> --tab <tab_id>
```

**Note**: Object IDs for positioned objects can be found in the document structure. Inline images are deleted using the standard `delete` command with their index range.

## Footnotes

```bash
# Insert a footnote reference at a position
uvx gws-cli docs insert-footnote <document_id> 50

# List all footnotes in document
uvx gws-cli docs list-footnotes <document_id>

# Add content to a footnote (use insert-segment-text with footnote ID)
uvx gws-cli docs insert-segment-text <document_id> <footnote_id> "Footnote text here" --index 0
```

## Suggestions (Tracked Changes)

```bash
# Get all pending suggestions in a document
uvx gws-cli docs suggestions <document_id>

# Check if document has pending suggestions
uvx gws-cli docs document-mode <document_id>

# Accept a specific suggestion
uvx gws-cli docs accept-suggestion <document_id> <suggestion_id>

# Reject a specific suggestion
uvx gws-cli docs reject-suggestion <document_id> <suggestion_id>

# Accept all pending suggestions
uvx gws-cli docs accept-all-suggestions <document_id>

# Reject all pending suggestions
uvx gws-cli docs reject-all-suggestions <document_id>
```

**Note**: Suggestion IDs can be obtained from the `suggestions` command output.

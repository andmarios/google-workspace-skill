# Document Typesetting Standards

This guide defines the typesetting rules for creating professional documents with Google Docs. Claude MUST follow these rules when creating, converting, or formatting documents.

> **Purpose**: Ensure every document produced is visually consistent, professionally formatted, and follows established typographic conventions.

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Typography & Fonts](#2-typography--fonts)
3. [Document Structure](#3-document-structure)
4. [Text Formatting](#4-text-formatting)
5. [Table Standards](#5-table-standards)
6. [Image Guidelines](#6-image-guidelines)
7. [Lists & Pagination](#7-lists--pagination)
8. [Footnotes](#8-footnotes)
9. [Horizontal Lines](#9-horizontal-lines)
10. [Pre-flight Checklist](#10-pre-flight-checklist)

---

## 1. Core Principles

### 1.1 Never Rewrite User Content

**The user's words are sacred.** When creating or converting documents:

- PRESERVE the user's exact text, words, and phrasing
- Only ADD formatting, structure, headers, footers
- NEVER rephrase, summarize, expand, or "improve" text
- If content changes are needed, ASK USER FIRST

**What you MAY change:**
- Bullet syntax (`-` to `*` for Google Docs compatibility)
- Whitespace and line breaks for formatting
- Adding structural elements (headers, footers, page breaks)

**What you MUST NOT change:**
- Word choice
- Sentence structure
- Paragraph content
- The meaning or tone of any text

### 1.2 Consistency is Paramount

Every element in a document must be consistent with its peers:

| Element | Consistency Rule |
|---------|------------------|
| Tables | ALL tables use identical styling (borders, headers, padding) |
| Headings | Same font, size, and spacing for each heading level |
| Lists | Same bullet style, indentation throughout |
| Fonts | Maximum 2 typefaces in entire document |
| Spacing | Consistent paragraph spacing throughout |
| Margins | Same margins on all pages |

### 1.3 Structure First, Then Content

When creating a document, apply structure in this order:

1. Set document margins
2. Create header and footer
3. Define heading styles
4. Insert content
5. Apply formatting
6. Add page breaks between sections
7. Verify with pre-flight checklist

---

## 2. Typography & Fonts

### 2.1 Font Limits

**Maximum 2 fonts per document:**
- **Primary font**: For headings
- **Secondary font**: For body text

Using more fonts creates visual chaos and looks unprofessional.

### 2.2 Recommended Font Combinations

| Context | Heading Font | Body Font |
|---------|--------------|-----------|
| Screen/Digital | Arial | Arial or Calibri |
| Print/Formal | Georgia Bold | Georgia |
| Modern/Tech | Roboto | Roboto |
| Traditional | Times New Roman | Times New Roman |

**Why this matters:**
- **Sans-serif** (Arial, Calibri, Roboto): Better for screen display due to cleaner rendering
- **Serif** (Georgia, Times New Roman): Better for print due to finer detail

### 2.3 Size Hierarchy

Use a consistent size hierarchy based on document purpose:

| Element | Standard Document | Formal Report |
|---------|-------------------|---------------|
| Title | 24pt | 26pt |
| Heading 1 | 18pt | 20pt |
| Heading 2 | 14pt | 16pt |
| Heading 3 | 12pt | 13pt |
| Body | 11pt | 11pt |
| Caption | 10pt | 10pt |
| Footnote | 9pt | 10pt |

**Important:** These sizes follow a proportional scale (approximately 1.25 ratio). Maintain proportional relationships.

### 2.4 Never Use Bold as a Heading Substitute

**WRONG:**
```
**Introduction**
This is the introduction text...

**Background**
This is background text...
```

**CORRECT:**
Use proper heading styles:
```bash
uv run gws docs format-paragraph <doc_id> <start> <end> --style HEADING_1
uv run gws docs format-paragraph <doc_id> <start> <end> --style HEADING_2
```

**Why this matters:**
- Bold text is just styled text - it has no semantic meaning
- Proper headings create document structure for navigation
- Headings enable table of contents generation
- Screen readers use headings for accessibility

### 2.5 Named Styles

Always use named paragraph styles:

| Style | When to Use |
|-------|-------------|
| `TITLE` | Document title (once per document) |
| `SUBTITLE` | Document subtitle (once per document) |
| `HEADING_1` | Major sections (Chapter, Part) |
| `HEADING_2` | Subsections |
| `HEADING_3` | Sub-subsections |
| `HEADING_4` to `HEADING_6` | Deeper nesting (use sparingly) |
| `NORMAL_TEXT` | Body paragraphs |

---

## 3. Document Structure

### 3.1 Headers and Footers

**Every professional document MUST have:**

- **Header**: Document title or section name
- **Footer**: Page numbers (at minimum)

**Header content (choose based on document type):**
- Document title
- Company name
- Chapter/section name
- Date

**Footer content:**
- Page numbers (required)
- Date (optional)
- "Confidential" marking (if applicable)
- Copyright notice (if applicable)

**Implementation:**
```bash
# Create header
uv run gws docs create-header <doc_id> --type DEFAULT
uv run gws docs insert-segment-text <doc_id> <header_id> "Document Title" --index 0

# Create footer with page number
uv run gws docs create-footer <doc_id> --type DEFAULT
uv run gws docs insert-segment-text <doc_id> <footer_id> "Page " --index 0
```

**First page different:**
Some documents have a title page without header/footer:
```bash
uv run gws docs document-style <doc_id> --first-page-diff
uv run gws docs create-header <doc_id> --type FIRST_PAGE_HEADER
```

### 3.2 Margins

**Standard margins: 1 inch (72pt) on all sides**

```bash
uv run gws docs document-style <doc_id> \
    --margin-top 72 --margin-bottom 72 \
    --margin-left 72 --margin-right 72
```

**When to adjust:**
- Binding edge: Add 0.5" (36pt) extra to left margin for bound documents
- Legal documents: May require wider margins
- Narrow margins: Never less than 0.75" (54pt)

### 3.3 Page Breaks

**Major sections MUST start on a new page:**

```bash
# Insert page break before a new section
uv run gws docs page-break <doc_id> <index>
```

**When to use page breaks:**
- Before each major section heading (H1)
- Before appendices
- Before bibliography/references
- After title page
- After table of contents

**NEVER use multiple blank lines or Enter presses to create space.** Always use proper page breaks.

### 3.4 Section Breaks

Section breaks allow different formatting in different parts of the document:

```bash
# Insert section break (starts new page)
uv run gws docs insert-section-break <doc_id> <index> --type NEXT_PAGE
```

**Use section breaks when:**
- Different headers/footers needed per section
- Mixing portrait and landscape pages
- Different column layouts in same document
- Different page numbering styles

---

## 4. Text Formatting

### 4.1 Text Alignment

**Body text: Left-aligned (recommended)**

```bash
uv run gws docs format-paragraph <doc_id> <start> <end> --align START
```

**Why left-aligned (ragged right) is preferred:**
- Easier to read than justified
- No awkward word spacing
- Consistent character spacing
- Better for digital documents

**Justified text (use carefully):**
- Creates formal appearance
- REQUIRES hyphenation to avoid "rivers" of whitespace
- Better for narrow columns (newspapers)
- If you use justified, enable hyphenation

**Centered text - use ONLY for:**
- Titles
- Headings (optional)
- Poetry or quotations
- Captions (sometimes)

**Right-aligned text - use ONLY for:**
- Dates
- Page numbers
- Numbers in tables
- Signatures

### 4.2 Line Spacing

**Body text: 1.15 to 1.5 line spacing**

```bash
uv run gws docs format-paragraph <doc_id> <start> <end> --line-spacing 115
```

| Document Type | Line Spacing |
|---------------|--------------|
| Business documents | 1.15 |
| Academic papers | 1.5 or 2.0 |
| Reports | 1.15 to 1.5 |
| Letters | 1.0 to 1.15 |

### 4.3 Paragraph Spacing

**Space between paragraphs: 6-12pt**

```bash
uv run gws docs format-paragraph <doc_id> <start> <end> \
    --space-above 0 --space-below 8
```

**Guidelines:**
- Space AFTER paragraphs (not before) for consistency
- Headings: More space above than below
- Body: Consistent spacing throughout
- Never use blank lines between paragraphs - use paragraph spacing

---

## 5. Table Standards

### 5.1 The Consistency Rule

**ALL tables in a document MUST have identical styling.**

Before creating any table, define ONE table style and apply it to every table:

| Property | Standard Value |
|----------|----------------|
| Header background | #F5F5F5 (light gray) |
| Header text | Bold, 11pt |
| Body text | Regular, 11pt |
| Border color | #E0E0E0 (medium gray) |
| Border width | 1pt |
| Cell padding | 5pt |
| Text alignment | Left (text), Right (numbers) |

### 5.2 Table Structure

```bash
# Insert table
uv run gws docs insert-table <doc_id> <rows> <cols> --index <position>

# Style header row
uv run gws docs style-table-cell <doc_id> 0 0 0 \
    --bg-color "#F5F5F5" --border-color "#E0E0E0" --border-width 1 --padding 5

# Pin header row for long tables
uv run gws docs pin-table-header <doc_id> 0 --rows 1
```

### 5.3 Alignment Rules

| Column Type | Alignment | Reason |
|-------------|-----------|--------|
| Text | Left | Easier to read |
| Numbers | Right | Aligns decimal points |
| Dates | Left or Right | Be consistent |
| Headers | Match column content | Visual alignment |

**Never center-align body text in tables** - it's harder to scan.

### 5.4 Border Best Practices

**Minimal borders are better:**

```
GOOD:                           BAD:
+---------------------------+   +---+---+---+---+
| Header 1 | Header 2       |   | H | H | H | H |
+---------------------------+   +---+---+---+---+
| Data     | Data           |   | D | D | D | D |
| Data     | Data           |   +---+---+---+---+
| Data     | Data           |   | D | D | D | D |
+---------------------------+   +---+---+---+---+
```

**Guidelines:**
- Horizontal lines: Header separator + bottom border (required)
- Vertical lines: Often unnecessary - use spacing instead
- Row separators: Optional light lines OR zebra striping (not both)
- Heavy borders everywhere: Avoid - looks like a spreadsheet

### 5.5 Table Captions

**Table captions go ABOVE the table:**

```
Table 1: Quarterly Revenue by Region

| Region | Q1 | Q2 | Q3 | Q4 |
| ...    | ...| ...| ...| ...|
```

This is opposite of figures (which have captions below).

---

## 6. Image Guidelines

### 6.1 Never Place Images in Lists

**WRONG:**
```
* First item
* [IMAGE HERE]
* Third item
```

**CORRECT:**
Images are standalone elements, separate from lists:

```
* First item
* Second item
* Third item

[IMAGE HERE]
Figure 1: Description of image

* Next list continues...
```

### 6.2 Image Sizing

**Never make images full-page size.** Images should:

- Be large enough to see clearly
- Have margins around them
- Not overwhelm the text
- Maintain aspect ratio (never stretch)

**Recommended maximum:**
- Width: 450pt (about 6.25 inches on letter size)
- Height: 500pt (about 7 inches)

```bash
uv run gws docs insert-image <doc_id> "https://..." --width 400
```

### 6.3 Figure Numbering and Captions

**All images must have:**
1. A figure number (Figure 1, Figure 2, etc.)
2. A descriptive caption

**Caption placement: BELOW the figure**

```
[IMAGE]
Figure 3: Sales growth by quarter, showing 15% increase in Q4
```

**Caption formatting:**
- Slightly smaller than body text (10pt)
- "Figure X:" in bold
- Description in regular weight
- Do not use "see below" or "see above" - always reference by number

### 6.4 Image Placement

**Place images as close as possible to their first text reference:**
- Immediately after the paragraph that mentions them
- Never split an image across pages
- Ensure caption stays with image

```bash
# Keep image with caption
uv run gws docs format-paragraph <doc_id> <caption_start> <caption_end> --keep-with-next
```

### 6.5 Referencing Images

**CORRECT:** "As shown in Figure 3, sales increased..."
**WRONG:** "As shown below, sales increased..."

Always reference by number because:
- Page layout may change
- Images may move during editing
- Screen readers can navigate to numbered references

---

## 7. Lists & Pagination

### 7.1 Keep Lists Together

**Lists should NEVER break across pages mid-list.**

```bash
# Apply to entire list
uv run gws docs format-paragraph <doc_id> <list_start> <list_end> --keep-together
```

If a list is too long to fit on one page, consider:
- Breaking it into multiple shorter lists with subheadings
- Moving it to the next page entirely

### 7.2 Keep Headings with Content

**A heading should NEVER appear at the bottom of a page with its content on the next page.**

```bash
# Keep heading with following paragraph
uv run gws docs format-paragraph <doc_id> <heading_start> <heading_end> --keep-with-next
```

### 7.3 Widow and Orphan Control

**Definitions:**
- **Widow**: Last line of paragraph alone at top of page - BAD
- **Orphan**: First line of paragraph alone at bottom of page - BAD

Both look unprofessional. Enable widow/orphan control:

```bash
uv run gws docs format-paragraph <doc_id> <start> <end> --keep-together
```

### 7.4 List Best Practices

**Length:**
- 3-7 items per list is optimal
- More than 7: Break into sub-lists with subheadings
- Fewer than 3: Consider prose instead

**Parallel structure:**
All list items should follow the same grammatical pattern:

**GOOD (all start with verbs):**
- Create the document
- Add the header
- Insert content

**BAD (mixed structure):**
- Creating the document
- The header should be added
- Content insertion

### 7.5 Bullet vs Numbered Lists

| Use Bullets When | Use Numbers When |
|------------------|------------------|
| Order doesn't matter | Order matters (steps) |
| Items are equal | Items have priority |
| Grouping related items | Referencing later ("see item 3") |
| Informal lists | Formal procedures |

---

## 8. Footnotes

### 8.1 When to Use Footnotes

Use footnotes for:
- Source citations (if using note-based citation style)
- Brief explanatory comments
- Cross-references
- Clarifications that would interrupt main text

Do NOT use footnotes for:
- Essential information (put it in the main text)
- Long explanations (use endnotes or appendix)
- Information on every page (use headers/footers)

### 8.2 Footnote Formatting

```bash
# Insert footnote at position
uv run gws docs insert-footnote <doc_id> <position>

# Add text to footnote
uv run gws docs insert-segment-text <doc_id> <footnote_id> "Footnote text" --index 0
```

**Formatting rules:**
- Superscript numerals: ¹, ², ³ (not asterisks)
- Place after punctuation (except dashes)
- Number consecutively through document
- Font: Same as body, 1-2pt smaller (9-10pt)

### 8.3 Footnote Placement

**Place superscript number AFTER punctuation:**

CORRECT: "This is a quoted statement."¹
WRONG: "This is a quoted statement"¹.

**Exception:** Before dashes (em-dash, en-dash):

CORRECT: The result¹—which surprised everyone—was positive.

### 8.4 Where NOT to Place Footnotes

- After section headings
- After chapter titles
- In tables (use table notes instead)
- In captions
- In headers or footers

---

## 9. Horizontal Lines

### 9.1 Allowed Uses

Horizontal lines (rules) should be used ONLY for:

- **Signature lines** in letters/forms
- **Form section separators**
- **Header/footer decorative rules** (sparingly)
- **Pull quotes** (lines above/below)

### 9.2 Forbidden Uses

**NEVER use horizontal lines for:**

- General section breaks (use page breaks or whitespace)
- Converting markdown `---` (skip these during conversion)
- Decorative purposes with no function
- Separating paragraphs

### 9.3 Markdown Conversion Rule

When converting markdown to Google Docs:

**If markdown contains `---` or `***` or `___`:**
- Do NOT convert to horizontal lines
- Either skip entirely or replace with extra paragraph spacing

This prevents random lines appearing throughout the document.

---

## 10. Pre-flight Checklist

Before delivering ANY document, verify each item:

### Document Structure
- [ ] Header present on all pages (or first page different if title page)
- [ ] Footer with page numbers on all pages
- [ ] Document title uses TITLE style
- [ ] Standard margins (1" / 72pt)

### Typography
- [ ] Maximum 2 fonts used
- [ ] All headings use proper HEADING styles (not bold text)
- [ ] Heading hierarchy is correct (H1 > H2 > H3)
- [ ] Body text is consistent size (11pt)

### Tables
- [ ] ALL tables have identical styling
- [ ] Header rows have background color (#F5F5F5)
- [ ] Text left-aligned, numbers right-aligned
- [ ] Borders are consistent (1pt, #E0E0E0)
- [ ] No centered body text in tables

### Images
- [ ] No images inside bullet lists
- [ ] All images have numbered captions below
- [ ] Images sized appropriately (not full-page)
- [ ] References use "Figure X", not "see below"

### Lists
- [ ] Lists don't break across pages
- [ ] Headings stay with following content
- [ ] No widows or orphans
- [ ] Parallel structure in list items

### Page Structure
- [ ] Major sections start on new page
- [ ] No random horizontal lines
- [ ] Proper page breaks (not blank lines)

### Content Integrity
- [ ] User's exact text preserved (no rewrites)
- [ ] Original source file unmodified
- [ ] Footnotes numbered consecutively
- [ ] Text left-aligned (or justified WITH hyphenation)

---

## Quick Reference: Commands

| Task | Command |
|------|---------|
| Set margins | `document-style --margin-top 72 --margin-bottom 72 --margin-left 72 --margin-right 72` |
| Create header | `create-header --type DEFAULT` |
| Create footer | `create-footer --type DEFAULT` |
| Apply heading style | `format-paragraph --style HEADING_1` |
| Left-align text | `format-paragraph --align START` |
| Keep together | `format-paragraph --keep-together` |
| Keep with next | `format-paragraph --keep-with-next` |
| Page break | `page-break <index>` |
| Section break | `insert-section-break --type NEXT_PAGE` |
| Style table cell | `style-table-cell --bg-color "#F5F5F5" --border-color "#E0E0E0"` |
| Insert footnote | `insert-footnote <position>` |

---

## Sources

This guide synthesizes best practices from:

- [Piktochart: Professional Fonts](https://piktochart.com/blog/professional-fonts/)
- [IK Agency: Typography Hierarchy Guide](https://www.ikagency.com/graphic-design-typography/typography-hierarchy/)
- [Hospitality Institute: Headers, Footers, Page Breaks](https://hospitality.institute/bha211/headers-footers-page-breaks-professional-documents/)
- [CSE Science Editor: Best Practices in Table Design](https://www.csescienceeditor.org/article/best-practices-in-table-design/)
- [A List Apart: Designing Tables to be Read](https://alistapart.com/article/web-typography-tables/)
- [Cornell CHEC: Captions for Figures](https://chec.engineering.cornell.edu/visuals/captions-for-figures-in-documents/)
- [BC Campus: Technical Writing - Figures and Tables](https://pressbooks.bccampus.ca/technicalwriting/chapter/figurestables/)
- [Microsoft Support: Control Pagination](https://support.microsoft.com/en-us/office/control-pagination-e9b3b005-cf62-41d0-afa2-24cfb223ab42)
- [Fonts.com: Justified vs Rag Right](https://www.fonts.com/content/learning/fontology/level-2/making-type-choices/justified-vs-rag-right)
- [Grammarly: How to Write Footnotes](https://www.grammarly.com/blog/academic-writing/footnotes/)

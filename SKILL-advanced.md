# Advanced Google Workspace Skill Guide

This guide teaches Claude how to create professional, engaging, and effective content using Google Workspace. It goes beyond API mechanics to cover design principles, best practices, and quality standards.

> **Documentation Structure**: This skill uses modular documentation for efficiency:
> - [SKILL.md](SKILL.md) — Core reference (auth, overview, contacts, conversion)
> - [reference/](reference/) — Service-specific API docs (docs, sheets, slides, drive, gmail, calendar)
> - This file — Design best practices, content creation, API efficiency

## Philosophy: Audience-Centric Design

> "The audience is the hero, not the presenter." — Nancy Duarte

Every document, presentation, email, or spreadsheet exists to serve someone. Before creating content:

1. **Identify the audience** — Who will consume this? What do they need?
2. **Define the outcome** — What should they know, feel, or do afterward?
3. **Respect their time** — Busy professionals scan; design for skimming.

---

## Google Slides: Creating Engaging Presentations

### The Duarte Storytelling Structure

Great presentations follow a narrative arc that alternates between "what is" (today) and "what could be" (tomorrow), creating tension and resolution:

```
[Today] → [Tomorrow] → [Today] → [Tomorrow] → [Call to Action]
   ↓          ↓          ↓          ↓              ↓
Current    Vision    Obstacles   Path         New Bliss
State                           Forward
```

**Structure each presentation with:**
- **Beginning**: Establish the status quo, then introduce the inciting incident
- **Middle**: Alternate between problems and possibilities
- **End**: Paint the transformed future, issue a clear call to action

### Visual Hierarchy Principles

Guide the viewer's eye with intentional design:

| Element | Size | Purpose |
|---------|------|---------|
| Title | 36-44pt | Immediate attention, one idea |
| Subtitle/Key Point | 24-28pt | Supporting context |
| Body Text | 18-20pt | Details (minimize usage) |
| Footnotes | 12-14pt | Sources, fine print |

**The One Idea Rule**: Each slide should convey exactly one concept. If you need "and" to describe what a slide covers, split it into two slides.

### Slide Design Checklist

- [ ] **White space**: Leave 15-20% margins; content shouldn't touch edges
- [ ] **6×6 guideline**: Maximum 6 bullet points, maximum 6 words each
- [ ] **Visual dominance**: Images/charts should occupy 60%+ of slide area
- [ ] **Contrast ratio**: Text on backgrounds must meet 4.5:1 (WCAG AA)
- [ ] **Consistent alignment**: Left-align body text; center titles if desired
- [ ] **Limited fonts**: Maximum 2 typefaces (one for headers, one for body)
- [ ] **Restrained color**: 2-3 colors maximum per slide

### Color Palettes for Presentations

**Professional Blue (recommended for business):**
```
Primary:    #1A365D (Dark Navy)     — Titles, emphasis
Secondary:  #2B6CB0 (Medium Blue)   — Subheads, accents
Accent:     #63B3ED (Light Blue)    — Highlights
Background: #FFFFFF or #F7FAFC      — Clean, professional
```

**Executive Gray:**
```
Primary:    #1A202C (Charcoal)
Secondary:  #4A5568 (Slate)
Accent:     #718096 (Gray)
Background: #FFFFFF
```

**Avoid**: Red/green combinations (colorblind users), pure black on pure white (harsh), more than 12 distinct colors.

### Slide Layouts by Purpose

| Purpose | Recommended Layout | Content Tips |
|---------|-------------------|--------------|
| Opening | TITLE | Large title, minimal subtitle, no bullets |
| Section divider | SECTION_HEADER | Single phrase, full-bleed color |
| Key stat | BIG_NUMBER | One number, one sentence context |
| Comparison | TITLE_AND_TWO_COLUMNS | Parallel structure, equal weight |
| Process/steps | BLANK + shapes | Icons with short labels |
| Data | TITLE_AND_BODY | Chart fills 70% of slide |
| Closing/CTA | TITLE | Clear action, contact info |

### Animation Guidelines

- **Use sparingly**: Maximum 1-2 animations per presentation
- **Prefer subtle**: Fade > Fly > Bounce (never use "exciting" effects)
- **Purpose-driven**: Only animate to reveal progressive information
- **Consistent timing**: 0.3-0.5 seconds for transitions

---

## Google Docs: Professional Document Design

### Document Architecture

Apply the **CRAP principles** (Contrast, Repetition, Alignment, Proximity):

**Heading Hierarchy:**
```
Title (H1):      18-20pt, Bold, Single use
Section (H2):    14-16pt, Bold
Subsection (H3): 12-13pt, Bold or Semibold
Body:            11-12pt, Regular
```

**Structure Pattern:**
```
Title
├── Executive Summary (if >3 pages)
├── Section H2
│   ├── Subsection H3
│   └── Subsection H3
├── Section H2
└── Conclusion/Next Steps
```

### Executive Summary Best Practices

For documents over 3 pages, include an executive summary that is:

- **Length**: 5-10% of the document (max 2 pages for 50+ page reports)
- **Standalone**: Readable without the full document
- **Structure**: Purpose → Key Findings → Recommendations → Next Steps
- **Audience-aware**: Written for decision-makers who may read only this section

### Typography Guidelines

| Element | Recommendation |
|---------|----------------|
| Body font | Arial, Calibri, or Georgia at 11-12pt |
| Line spacing | 1.15 to 1.5 for readability |
| Paragraph spacing | 6-12pt between paragraphs |
| Margins | 1 inch (72pt) minimum |
| Line length | 60-80 characters optimal |

### White Space Usage

White space improves comprehension by **up to 20%** (Nielsen Norman Group):

- Leave generous margins (never less than 0.75")
- Add space above headings (12pt) and below (6pt)
- Separate sections with extra spacing or page breaks
- Don't fill every inch—let content breathe

### Lists and Bullet Points

**Use bullets when:**
- Order doesn't matter
- Items are relatively equal in importance
- Scanning is expected

**Use numbers when:**
- Sequence matters (steps, priority)
- You'll reference items later ("see item 3")

**Bullet formatting:**
- Parallel structure (all start with verbs OR all are nouns)
- 3-7 items per list (split longer lists)
- Indent nested items consistently (18-36pt)

### Tables in Documents

| Best Practice | Rationale |
|---------------|-----------|
| Header row styling | Bold text, subtle background (#F5F5F5) |
| Alternating rows | Improves scanability (optional light gray) |
| Left-align text | Right-align numbers only |
| Adequate padding | 5-10pt cell padding |
| Pinned headers | For tables spanning pages |

### Color in Documents

**Safe professional colors:**
```
Headers/Emphasis: #1A365D (Navy) or #1F4E79 (Dark Blue)
Links:            #0066CC (accessible blue)
Cautions:         #B7791F (Dark Gold) — never red/green alone
Success:          #276749 (Forest Green)
Background tints: #F7FAFC (Blue-gray), #FFFBEB (Cream)
```

---

## Google Sheets: Data Organization Excellence

### Data Structure Principles

**The Golden Rules:**

1. **Start at A1**: Begin data in row 1, column A
2. **Headers in row 1**: Clear, concise column names
3. **One data type per column**: Don't mix text and numbers
4. **One value per cell**: Never combine data (e.g., "John, 25, NYC")
5. **No merged cells in data ranges**: Breaks sorting and formulas
6. **Tall format for analysis**: Rows are records, columns are attributes

### Header Row Standards

| Do | Don't |
|----|-------|
| `Revenue ($)` | `REVENUE!!!` |
| `Start Date` | `start date` |
| `Customer Name` | `Customer_Name_Field` |
| Single row headers | Multi-row merged headers |

### Professional Formatting

**Header row:**
- Bold, UPPERCASE or Title Case
- Background: #E3F2FD (light blue) or #F5F5F5 (light gray)
- Freeze row for scrolling

**Data rows:**
- Alternating colors: White / #FAFAFA
- Right-align numbers, left-align text
- Consistent number formats within columns

**Borders:**
- Thin borders (#E0E0E0) for grid
- Thicker bottom border on header row
- Avoid heavy borders everywhere

### Number Formatting Reference

| Data Type | Format Pattern | Example |
|-----------|----------------|---------|
| Currency | `$#,##0.00` | $1,234.56 |
| Percentage | `0.0%` | 45.5% |
| Integer | `#,##0` | 1,234 |
| Date | `yyyy-mm-dd` | 2025-01-15 |
| Phone | `(###) ###-####` | (555) 123-4567 |

### Conditional Formatting Strategy

**Use conditional formatting for:**
- Highlighting outliers (top/bottom 10%)
- Status indicators (red/yellow/green with icons)
- Data validation feedback
- Trend visualization (color scales)

**Color scale recommendations:**
```
Diverging (good/bad):  #F44336 (red) → #FFEB3B (yellow) → #4CAF50 (green)
Sequential (low/high): #FFFFFF → #1565C0 (white to blue)
```

**Always add a legend** when using color scales.

### Data Visualization (Tufte Principles)

Edward Tufte's principles for charts:

1. **Maximize data-ink ratio**: Remove gridlines, borders, and decorations that don't convey data
2. **Avoid chartjunk**: No 3D effects, no decorative images, no moiré patterns
3. **Graphical integrity**: Visual size should match numerical size (Lie Factor = 0.95-1.05)
4. **Show data variation, not design variation**: Keep styling consistent
5. **Label directly**: Put labels on the chart, not in legends when possible

### Chart Selection Guide

| Data Story | Chart Type | When to Use |
|------------|-----------|-------------|
| Comparison | Bar/Column | Discrete categories |
| Trend | Line | Time series data |
| Part-to-whole | Pie (≤5 slices) or Stacked Bar | Percentages |
| Distribution | Histogram | Frequency data |
| Correlation | Scatter | Two variables |
| Composition over time | Area | Cumulative trends |

**Pie chart rule**: Use only when you have ≤5 categories and one dominates. Otherwise, use bar charts.

### Accessibility in Charts

- **Don't rely on color alone**: Add patterns, labels, or shapes
- **Minimum 3:1 contrast** between adjacent elements
- **Maximum 6 colors** in a single visualization
- **Provide data table alternative** for screen readers
- **Test in grayscale** before adding color

---

## Gmail: Effective Email Communication

### Subject Line Formula

**Structure**: `[Action] + [Topic] + [Context/Deadline]`

**Examples:**
```
Review: Q3 Budget Proposal — Feedback by Friday
Action Required: Approve vendor contract
FYI: Product launch delayed to March 15
Decision Needed: Office location options
```

**Best practices:**
- Keep under 50 characters (fully visible on mobile)
- Front-load the important words
- Use brackets for categorization: [Urgent], [FYI], [Review]
- Avoid ALL CAPS and excessive punctuation (!!!)

### Email Structure

```
Subject: Clear, specific, actionable

Greeting: Hi [Name],

Context: One sentence establishing why you're writing.

Key Message: 2-3 sentences with the main point FIRST.

Supporting Details: Bullet points for multiple items.

Call to Action: Exactly what you need and by when.

Sign-off: Best regards,
[Your name]
```

### The "One Screen" Rule

The complete email should fit on one screen without scrolling. If longer:
- Lead with the most important information
- Use bullet points for scanability
- Consider attaching a document instead

### Professional Email Checklist

- [ ] Subject line describes the email content
- [ ] One clear purpose per email
- [ ] Most important information first
- [ ] Bullet points for multiple items
- [ ] Explicit call to action with deadline
- [ ] Correct recipient names
- [ ] Proofread for typos
- [ ] Appropriate signature

### Email Formatting

| Element | Guideline |
|---------|-----------|
| Font | Arial, Helvetica, or system default |
| Size | 10-12pt |
| Bold/Italic | Sparingly, for emphasis only |
| Colors | Avoid; use for links only |
| Line breaks | Between paragraphs (no indentation) |

### Response Time Expectations

- **Same day**: Acknowledge receipt of important emails
- **24-48 hours**: Full response for standard requests
- **Immediate**: Urgent matters (use sparingly)

If you can't respond fully, send a brief acknowledgment: "Thanks for this—I'll review and get back to you by [date]."

---

## Google Calendar: Meeting Excellence

### Meeting Invitation Essentials

Every calendar invite should include:

1. **Clear title**: Descriptive, not generic
   - ✅ "Q4 Planning: Marketing Budget Review"
   - ❌ "Meeting" or "Quick sync"

2. **Agenda in description**:
   ```
   Purpose: [One sentence]

   Agenda:
   1. [Topic] — 10 min
   2. [Topic] — 15 min
   3. [Topic] — 5 min

   Pre-work: [Any materials to review]

   Attendees:
   - [Name]: [Role in meeting]
   - [Name]: [Role in meeting]
   ```

3. **Appropriate duration**:
   - Use 25 or 50 minutes (not 30/60) to allow transition time
   - Default to shorter; extend only if necessary

4. **Location/link**: Clear join instructions

### Meeting Timing Best Practices

| Guideline | Rationale |
|-----------|-----------|
| Send invites 3-5 days ahead | Time for preparation |
| Include timezone for cross-region | Avoid confusion |
| Avoid Monday AM / Friday PM | Lower engagement |
| Cluster meetings on specific days | Protect focus time |

### Attendee Selection

**Limit attendees to those who:**
- Need to make decisions present in the meeting
- Have essential information to contribute
- Are directly responsible for outcomes

**Rule of thumb**: If someone doesn't need to speak, they can receive notes instead.

---

## Cross-Service Principles

### Accessibility Standards (WCAG 2.1 AA)

| Requirement | Standard |
|-------------|----------|
| Text contrast | 4.5:1 minimum (3:1 for large text) |
| Non-text contrast | 3:1 for UI components and graphics |
| Color independence | Don't convey meaning by color alone |
| Link clarity | Underlined or distinguishable from text |

**Test your colors**: Use tools like [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

### Universal Color Palette

These colors meet WCAG AA contrast on white backgrounds:

```
Blue:     #1A56DB (4.8:1)  — Links, headers, CTAs
Green:    #047857 (5.1:1)  — Success, confirmation
Red:      #DC2626 (4.5:1)  — Errors, warnings
Gray:     #4B5563 (7.5:1)  — Body text, secondary info
Yellow:   #B45309 (4.6:1)  — Caution (not pure yellow)
```

### Font Pairing Recommendations

| Context | Header Font | Body Font |
|---------|-------------|-----------|
| Professional/Corporate | Arial Black | Arial |
| Modern/Tech | Montserrat | Open Sans |
| Traditional/Legal | Georgia Bold | Georgia |
| Friendly/Startup | Poppins | Roboto |

### Content Density Guidelines

| Content Type | Optimal Density |
|--------------|-----------------|
| Slides | 1 idea per slide, <40 words |
| Documents | 150-200 words per page equivalent |
| Emails | <200 words for quick reads |
| Spreadsheets | 1 purpose per sheet |

---

## Quick Reference: Common Patterns

### Creating a Report

1. Start with purpose and audience
2. Outline structure (Exec Summary → Sections → Conclusion)
3. Write body sections first, summary last
4. Add visual hierarchy with headings
5. Include charts/tables where data tells the story
6. Review for scannability and white space

### Creating a Presentation

1. Define the one key message
2. Outline the story arc (problem → solution → future)
3. Create slides for each major beat
4. Apply visual hierarchy (title dominant)
5. Add visuals that reinforce, not decorate
6. Reduce text to absolute minimum
7. Practice the narrative flow

### Creating a Data Dashboard (Sheets)

1. Define the questions the data should answer
2. Structure raw data in tall format on a hidden sheet
3. Create summary calculations
4. Build charts with clear titles and labels
5. Apply consistent formatting and colors
6. Add context (date ranges, data sources)
7. Test accessibility (color independence)

### Writing an Important Email

1. State purpose in subject line
2. Lead with the ask or decision needed
3. Provide context in 2-3 sentences
4. Use bullets for supporting details
5. End with explicit call to action and deadline
6. Proofread for tone and typos

---

## API Efficiency: Minimizing Calls and Maximizing Performance

Google Workspace APIs have rate limits and quotas. Efficient API usage reduces latency, avoids errors, and creates a better user experience.

### Core Principle: Read Before Modify

**Always read the document/sheet/presentation before making changes.**

This is critical because:
1. **Index accuracy**: Document indices change after each insertion/deletion
2. **Structure understanding**: Know what exists before adding/removing
3. **Conflict avoidance**: Detect concurrent modifications
4. **Error prevention**: Verify the target exists

```bash
# BAD: Blind modification
uv run gws docs insert <doc_id> "New text" --index 50  # What if doc is shorter?

# GOOD: Read first, then modify
uv run gws docs read <doc_id>        # Understand structure
uv run gws docs structure <doc_id>   # Get heading positions
uv run gws docs insert <doc_id> "New text" --index 50  # Informed decision
```

### Batching Strategies

#### Google Sheets: Batch Reads

**Instead of multiple reads:**
```bash
# INEFFICIENT: 3 API calls
uv run gws sheets read <id> "A1:B10"
uv run gws sheets read <id> "C1:D10"
uv run gws sheets read <id> "E1:F10"

# EFFICIENT: 1 API call
uv run gws sheets batch-get <id> "A1:B10,C1:D10,E1:F10"
```

#### Google Sheets: Write Once

**Collect all data, then write:**
```bash
# INEFFICIENT: 5 API calls (one per row)
uv run gws sheets write <id> "A1:C1" --values '[["Header1","Header2","Header3"]]'
uv run gws sheets write <id> "A2:C2" --values '[["Row1","Data","Here"]]'
uv run gws sheets write <id> "A3:C3" --values '[["Row2","More","Data"]]'
# ... and so on

# EFFICIENT: 1 API call (all data at once)
uv run gws sheets write <id> "A1:C4" --values '[
  ["Header1","Header2","Header3"],
  ["Row1","Data","Here"],
  ["Row2","More","Data"],
  ["Row3","Even","More"]
]'
```

#### Google Docs: Strategic Formatting

**Apply formatting in a single pass with large ranges when possible:**
```bash
# INEFFICIENT: Format paragraph by paragraph
uv run gws docs format-paragraph <doc_id> 1 50 --align LEFT
uv run gws docs format-paragraph <doc_id> 51 100 --align LEFT
uv run gws docs format-paragraph <doc_id> 101 150 --align LEFT

# EFFICIENT: Format entire range at once
uv run gws docs format-paragraph <doc_id> 1 150 --align LEFT
```

### Operation Ordering for Docs

When modifying documents, **work from the end toward the beginning**:

```bash
# Problem: Inserting at index 10 shifts everything after it
# If you then insert at index 50, your actual target has moved

# SOLUTION: Work backwards
uv run gws docs insert <doc_id> "Section 3" --index 150  # Last position first
uv run gws docs insert <doc_id> "Section 2" --index 100  # Second last
uv run gws docs insert <doc_id> "Section 1" --index 50   # First position last
```

**For deletions, same principle:**
```bash
# Delete from highest index to lowest
uv run gws docs delete <doc_id> 150 200  # Delete later content first
uv run gws docs delete <doc_id> 100 140  # Then earlier content
uv run gws docs delete <doc_id> 50 90    # Preserves earlier indices
```

### Slides: Efficient Presentation Building

**Build slides in logical batches:**

```bash
# Step 1: Create all slides first
uv run gws slides add-slide <pres_id> --layout TITLE
uv run gws slides add-slide <pres_id> --layout TITLE_AND_BODY
uv run gws slides add-slide <pres_id> --layout TITLE_AND_BODY
uv run gws slides add-slide <pres_id> --layout SECTION_HEADER

# Step 2: Read to get all slide IDs
uv run gws slides read <pres_id>  # Get slide and element IDs

# Step 3: Populate content using IDs from step 2
# (Now you know exact IDs without re-reading)
```

### Sheets: Formatting Efficiency

**Apply formatting to ranges, not individual cells:**

```bash
# INEFFICIENT: Cell-by-cell formatting
for row in {1..100}; do
  uv run gws sheets format <id> <sheet_id> $row $((row+1)) 0 1 --bold
done

# EFFICIENT: Range formatting
uv run gws sheets format <id> <sheet_id> 1 100 0 1 --bold
```

### Caching Patterns

**Store IDs and metadata for reuse:**

```bash
# Read once at the start
SHEET_DATA=$(uv run gws sheets metadata <spreadsheet_id>)
SHEET_ID=$(echo "$SHEET_DATA" | jq -r '.sheets[0].sheet_id')

# Reuse the sheet_id for multiple operations
uv run gws sheets format <spreadsheet_id> $SHEET_ID 0 10 0 5 --bold
uv run gws sheets set-borders <spreadsheet_id> $SHEET_ID 0 10 0 5 --all
uv run gws sheets freeze-rows <spreadsheet_id> $SHEET_ID 1
```

### Rate Limit Awareness

Google Workspace APIs have these approximate limits:

| Service | Quota (per minute) | Strategy |
|---------|-------------------|----------|
| Docs | 300 read, 60 write | Batch content before writing |
| Sheets | 300 read, 60 write | Use batch-get, write ranges |
| Slides | 300 read, 60 write | Create structure first, populate second |
| Drive | 1000 queries | Use search with specific queries |
| Gmail | 250 send | Batch sends are not recommended |

**When hitting limits:**
1. Wait and retry (exponential backoff)
2. Combine operations where possible
3. Pre-plan the sequence to minimize calls

### Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Read-modify-read-modify loops | Doubles API calls | Read once, plan changes, apply all |
| Cell-by-cell writes | N API calls instead of 1 | Write entire range at once |
| Formatting before content | May need re-formatting | Add content first, format last |
| Blind insertions/deletions | Index errors | Always read structure first |
| Polling for changes | Wastes quota | Use Drive watch/push notifications |

### Efficient Workflows

#### Creating a Formatted Spreadsheet

```bash
# 1. Create the spreadsheet (1 call)
RESULT=$(uv run gws sheets create "Report" --sheets "Data,Summary")
SPREADSHEET_ID=$(echo "$RESULT" | jq -r '.spreadsheet_id')

# 2. Get sheet IDs (1 call)
META=$(uv run gws sheets metadata "$SPREADSHEET_ID")
DATA_SHEET=$(echo "$META" | jq -r '.sheets[0].sheet_id')

# 3. Write all data at once (1 call)
uv run gws sheets write "$SPREADSHEET_ID" "Data!A1:D100" --values '[...]'

# 4. Apply formatting in ranges (3 calls instead of 100+)
uv run gws sheets format-extended "$SPREADSHEET_ID" $DATA_SHEET 0 1 0 4 --bold --bg-color "#E3F2FD"
uv run gws sheets set-borders "$SPREADSHEET_ID" $DATA_SHEET 0 100 0 4 --all
uv run gws sheets freeze-rows "$SPREADSHEET_ID" $DATA_SHEET 1

# Total: 6 API calls instead of potentially 200+
```

#### Building a Multi-Slide Presentation

```bash
# 1. Create presentation (1 call)
RESULT=$(uv run gws slides create "Quarterly Review")
PRES_ID=$(echo "$RESULT" | jq -r '.presentation_id')

# 2. Add all slides at once (4 calls, but could batch if API supported)
for layout in TITLE TITLE_AND_BODY TITLE_AND_BODY SECTION_HEADER TITLE_AND_BODY; do
  uv run gws slides add-slide "$PRES_ID" --layout $layout
done

# 3. Single read to get all IDs (1 call)
SLIDES=$(uv run gws slides read "$PRES_ID")

# 4. Now populate using known IDs (minimize reads)
SLIDE1_ID=$(echo "$SLIDES" | jq -r '.slides[0].object_id')
# ... populate content
```

### Template-First Workflow (Recommended)

The most efficient approach is to **start from a template** rather than formatting from scratch. Templates provide:
- Pre-configured fonts, colors, and spacing
- Headers, footers, and page numbers already set
- Consistent branding with zero API calls
- Professional design without design expertise

#### Using Templates via Drive Copy

```bash
# Step 1: Identify template ID (store this once, reuse forever)
# User creates a styled template document and shares the ID
TEMPLATE_DOC_ID="1abc123..."  # Your corporate template
TEMPLATE_SLIDES_ID="1xyz789..."  # Your presentation template

# Step 2: Copy template to create new document (1 API call)
RESULT=$(uv run gws drive copy "$TEMPLATE_DOC_ID" --name "Q4 Analysis Report")
NEW_DOC_ID=$(echo "$RESULT" | jq -r '.file_id')

# Step 3: Replace placeholder content (minimal calls)
uv run gws docs replace "$NEW_DOC_ID" "{{TITLE}}" "Q4 Analysis Report"
uv run gws docs replace "$NEW_DOC_ID" "{{DATE}}" "January 2025"
uv run gws docs replace "$NEW_DOC_ID" "{{AUTHOR}}" "Analytics Team"

# Step 4: Insert actual content at designated locations
uv run gws docs read "$NEW_DOC_ID"  # Find insertion points
uv run gws docs insert "$NEW_DOC_ID" "Your analysis content here..." --index <position>

# Total: ~5 API calls vs. 20+ for format-from-scratch
```

#### Template Design Recommendations

Create templates with **placeholder tokens** that are easy to find-and-replace:

| Placeholder | Purpose |
|-------------|---------|
| `{{TITLE}}` | Document/presentation title |
| `{{SUBTITLE}}` | Subtitle or tagline |
| `{{DATE}}` | Creation or report date |
| `{{AUTHOR}}` | Author name or team |
| `{{CONTENT_START}}` | Marker for main content insertion |
| `{{SECTION_1}}` | First section content |

**Template structure example (Google Doc):**
```
[Header: Company Logo | {{TITLE}} | Page #]

{{TITLE}}
{{SUBTITLE}}

Prepared by: {{AUTHOR}}
Date: {{DATE}}

---

Executive Summary
{{EXECUTIVE_SUMMARY}}

1. Introduction
{{SECTION_1}}

2. Analysis
{{SECTION_2}}

3. Recommendations
{{SECTION_3}}

[Footer: Confidential | {{DATE}}]
```

#### Template Library Organization

Store templates in a dedicated Drive folder:

```bash
# Create templates folder
RESULT=$(uv run gws drive create-folder "Document Templates")
TEMPLATES_FOLDER=$(echo "$RESULT" | jq -r '.folder_id')

# Organize by type
uv run gws drive create-folder "Reports" --parent "$TEMPLATES_FOLDER"
uv run gws drive create-folder "Presentations" --parent "$TEMPLATES_FOLDER"
uv run gws drive create-folder "Spreadsheets" --parent "$TEMPLATES_FOLDER"
```

**Recommended template types:**
- `Report - Executive Brief` (1-2 pages, executive summary focus)
- `Report - Technical` (detailed, with appendices)
- `Presentation - Strategy` (10-15 slides, narrative arc)
- `Presentation - Status Update` (5-7 slides, metrics focus)
- `Spreadsheet - Data Tracker` (formatted table with headers)
- `Spreadsheet - Dashboard` (charts and summary cells pre-configured)

#### Google's Public Templates

Google Workspace also offers public templates accessible via the template gallery. While these can't be accessed directly via API, users can:

1. Browse templates at [docs.google.com/templates](https://docs.google.com/templates)
2. Select and open a template
3. Save a copy to their Drive
4. Use that copy as a reusable template via the Drive copy method above

**Tip:** When users mention wanting a "professional report" or "clean presentation," ask if they have a template or suggest they pick one from Google's gallery first.

#### When to Use Templates vs. Format-from-Scratch

| Scenario | Approach |
|----------|----------|
| Recurring reports (weekly, monthly) | **Template** — set up once, reuse forever |
| Brand-consistent documents | **Template** — ensures compliance |
| One-off quick document | **Format-from-scratch** — if simple enough |
| Converting existing markdown | **Hybrid** — convert, then apply template styling |
| User has no template | **Create one** — invest time upfront, save time forever |

### Conversion + Theming Workflow

When templates aren't available and you're converting markdown to Google Docs/Slides, conversion is just step one. Apply corporate theming afterward:

#### Complete Document Conversion Workflow

```bash
# Step 1: Convert markdown to Google Doc (1 call)
RESULT=$(uv run gws convert md-to-doc report.md --title "Q4 Analysis Report")
DOC_ID=$(echo "$RESULT" | jq -r '.document_id')

# Step 2: Read structure to get heading indices (1 call)
STRUCTURE=$(uv run gws docs structure "$DOC_ID")

# Step 3: Apply document-level styling (1 call)
uv run gws docs document-style "$DOC_ID" \
  --margin-top 72 --margin-bottom 72 \
  --margin-left 90 --margin-right 72

# Step 4: Create header with company branding (2 calls)
HEADER=$(uv run gws docs create-header "$DOC_ID" --type DEFAULT)
HEADER_ID=$(echo "$HEADER" | jq -r '.header_id')
uv run gws docs insert-segment-text "$DOC_ID" "$HEADER_ID" "ACME Corp | Confidential" --index 0

# Step 5: Create footer with page numbers (2 calls)
FOOTER=$(uv run gws docs create-footer "$DOC_ID" --type DEFAULT)
FOOTER_ID=$(echo "$FOOTER" | jq -r '.footer_id')
uv run gws docs insert-segment-text "$DOC_ID" "$FOOTER_ID" "Page " --index 0

# Step 6: Apply heading styles (batch by heading level)
# Extract H1 ranges from structure, apply consistent styling
H1_RANGES=$(echo "$STRUCTURE" | jq -r '.headings[] | select(.level==1)')
# Apply formatting to each H1 range...
uv run gws docs format-text-extended "$DOC_ID" <start> <end> \
  --font "Arial" --size 18 --color "#1A365D"

# Step 7: Style body text ranges
uv run gws docs format-text-extended "$DOC_ID" 1 <end_of_doc> \
  --font "Georgia" --size 11

# Total: ~10 API calls for a fully themed document
```

#### Complete Presentation Conversion Workflow

```bash
# Step 1: Convert markdown to slides (1 call)
RESULT=$(uv run gws convert md-to-slides presentation.md --title "Strategy Update")
PRES_ID=$(echo "$RESULT" | jq -r '.presentation_id')

# Step 2: Read to get all element IDs (1 call)
SLIDES=$(uv run gws slides read "$PRES_ID")

# Step 3: Apply consistent text formatting to all text boxes
# Loop through each text element and apply brand styling:
for ELEMENT_ID in $(echo "$SLIDES" | jq -r '.slides[].elements[] | select(.type=="TEXT_BOX") | .object_id'); do
  uv run gws slides format-text-extended "$PRES_ID" "$ELEMENT_ID" \
    --font "Montserrat" --color "#1A365D"
done

# Step 4: Style title slides differently
TITLE_SLIDE=$(echo "$SLIDES" | jq -r '.slides[0].object_id')
# Apply title-specific formatting...

# Step 5: Add company logo to each slide (create shape or insert image)
for SLIDE_ID in $(echo "$SLIDES" | jq -r '.slides[].object_id'); do
  uv run gws slides insert-image "$PRES_ID" "$SLIDE_ID" "https://example.com/logo.png" \
    --x 620 --y 10 --width 80 --height 40
done
```

### Brand Theme Templates

Define reusable theme constants for consistency:

**Document Theme (Corporate Blue):**
```bash
# Typography
FONT_HEADING="Arial"
FONT_BODY="Georgia"
SIZE_H1=18
SIZE_H2=14
SIZE_BODY=11

# Colors
COLOR_PRIMARY="#1A365D"    # Navy headings
COLOR_ACCENT="#2B6CB0"     # Links, emphasis
COLOR_BODY="#2D3748"       # Body text (softer than black)

# Margins (points, 72pt = 1 inch)
MARGIN_TOP=72
MARGIN_BOTTOM=72
MARGIN_LEFT=90    # Slightly wider for binding
MARGIN_RIGHT=72
```

**Presentation Theme (Modern):**
```bash
# Typography
FONT_TITLE="Montserrat"
FONT_BODY="Open Sans"
SIZE_TITLE=44
SIZE_SUBTITLE=28
SIZE_BODY=18

# Colors
COLOR_TITLE="#1A202C"
COLOR_BODY="#4A5568"
COLOR_ACCENT="#3182CE"
BG_DARK="#1A202C"      # For section headers
BG_LIGHT="#F7FAFC"     # For content slides
```

### Monitoring Your Usage

Check your actual API usage in the Google Cloud Console:
- Navigate to: APIs & Services → Dashboard
- Select the specific API (Docs, Sheets, etc.)
- View quotas and current usage

If you're building automated workflows, implement:
1. Request counting
2. Exponential backoff on 429 errors
3. Queue management for bulk operations

---

## Sources and Further Reading

### Presentation Design
- [Nancy Duarte: Resonate](https://www.duarte.com/resources/books/resonate/)
- [The Golden Rules of Presentation Design](https://blog.thenounproject.com/the-golden-rules-of-presentation-design/)
- [Design Principles for Effective Presentations](https://www.inkppt.com/guides/complete-guide-on-presentation-design-training/the-art-of-presentation-design/design-principles-for-effective-presentations/)

### Document Design
- [Best Practices for Formatting Business Documents](https://www.nobledesktop.com/learn/business-writing/best-practices-for-formatting-business-documents)
- [Four Principles of Document Design (CRAP)](https://odp.library.tamu.edu/howdyorhello/chapter/four-principles-of-document-design/)
- [Technical Report Writing Best Practices](https://www.csescienceeditor.org/article/best-practices-for-writing-and-editing-technical-reports/)

### Data Visualization
- [Edward Tufte's Data Visualization Principles](https://www.geeksforgeeks.org/data-visualization/mastering-tuftes-data-visualization-principles/)
- [Accessibility Standards for Chart Design](https://www.smashingmagazine.com/2024/02/accessibility-standards-empower-better-chart-visual-design/)
- [18 Best Practices for Working with Data in Google Sheets](https://www.benlcollins.com/spreadsheets/data-best-practices/)

### Email Communication
- [28 Email Etiquette Rules for the Workplace](https://www.indeed.com/career-advice/career-development/email-etiquette)
- [Best Practices for Email Subject Lines](https://mailchimp.com/help/best-practices-for-email-subject-lines/)

### Meeting Management
- [Meeting Invite Etiquette & Best Practices](https://www.flowtrace.co/collaboration-blog/meeting-invite-etiquette-best-practices)
- [Fellow.app Meeting Best Practices](https://fellow.app/blog/meetings/meeting-invite-etiquette-best-practices/)

### Accessibility
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Harvard: Data Visualizations, Charts, and Graphs Accessibility](https://accessibility.huit.harvard.edu/data-viz-charts-graphs)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

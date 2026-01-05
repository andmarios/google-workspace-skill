# Advanced Google Workspace Skill Guide

This guide covers content strategy and API efficiency for Google Workspace.

> **Documentation Structure**: This skill uses modular documentation:
> - [SKILL.md](SKILL.md) — Core reference (auth, overview, navigation)
> - [SKILL-typesetting.md](SKILL-typesetting.md) — Document formatting standards (fonts, tables, images, pagination)
> - [reference/](reference/) — Service-specific API docs
> - This file — Content strategy and API efficiency

---

## Philosophy: Audience-Centric Content

> "The audience is the hero, not the presenter." — Nancy Duarte

Every document, presentation, or email exists to serve someone. Before creating content:

1. **Identify the audience** — Who will consume this? What do they need?
2. **Define the outcome** — What should they know, feel, or do afterward?
3. **Respect their time** — Busy professionals scan; design for skimming.

---

## Google Slides: Content Strategy

### The Duarte Storytelling Structure

Great presentations follow a narrative arc that alternates between "what is" (today) and "what could be" (tomorrow):

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

### The One Idea Rule

Each slide should convey exactly one concept. If you need "and" to describe what a slide covers, split it into two slides.

### Content Limits

| Content Type | Limit |
|--------------|-------|
| Bullets per slide | Maximum 6 |
| Words per bullet | Maximum 6 |
| Total words per slide | Under 40 |
| Ideas per slide | Exactly 1 |

### Speaker Notes

Speaker notes are essential, especially for investor/executive presentations. They contain:
- Talking points and statistics
- Context not shown on slides
- Transitions to next slide

Always add speaker notes after creating slides:
```bash
uv run gws slides set-speaker-notes $PRES_ID $SLIDE_ID "Key talking points..."
```

---

## Google Docs: Content Structure

### Executive Summary Best Practices

For documents over 3 pages, include an executive summary that is:

- **Length**: 5-10% of the document (max 2 pages for 50+ page reports)
- **Standalone**: Readable without the full document
- **Structure**: Purpose → Key Findings → Recommendations → Next Steps
- **Audience-aware**: Written for decision-makers who may read only this section

### Lists and Bullet Points

**Use bullets when:**
- Order doesn't matter
- Items are relatively equal in importance

**Use numbers when:**
- Sequence matters (steps, priority)
- You'll reference items later ("see item 3")

**Best practices:**
- Parallel structure (all start with verbs OR all are nouns)
- 3-7 items per list (split longer lists)

---

## Google Sheets: Data Organization

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

---

## Gmail: Effective Communication

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
- Front-load important words
- Use brackets: [Urgent], [FYI], [Review]

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

---

## Google Calendar: Meeting Excellence

### Meeting Invitation Essentials

Every calendar invite should include:

1. **Clear title**: Descriptive, not generic
   - Good: "Q4 Planning: Marketing Budget Review"
   - Bad: "Meeting" or "Quick sync"

2. **Agenda in description**:
   ```
   Purpose: [One sentence]

   Agenda:
   1. [Topic] — 10 min
   2. [Topic] — 15 min
   3. [Topic] — 5 min

   Pre-work: [Any materials to review]
   ```

3. **Appropriate duration**:
   - Use 25 or 50 minutes (not 30/60) to allow transition time

4. **Location/link**: Clear join instructions

### Attendee Selection

**Limit attendees to those who:**
- Need to make decisions present in the meeting
- Have essential information to contribute
- Are directly responsible for outcomes

**Rule of thumb**: If someone doesn't need to speak, they can receive notes instead.

---

## API Efficiency: Minimizing Calls

Google Workspace APIs have rate limits and quotas. Efficient API usage reduces latency and avoids errors.

### Core Principle: Read Before Modify

**Always read the document/sheet/presentation before making changes.**

This is critical because:
1. **Index accuracy**: Document indices change after each insertion/deletion
2. **Structure understanding**: Know what exists before adding/removing
3. **Error prevention**: Verify the target exists

```bash
# GOOD: Read first, then modify
uv run gws docs read <doc_id>        # Understand structure
uv run gws docs insert <doc_id> "New text" --index 50  # Informed decision
```

### Batching Strategies

#### Google Sheets: Batch Reads

```bash
# INEFFICIENT: 3 API calls
uv run gws sheets read <id> "A1:B10"
uv run gws sheets read <id> "C1:D10"
uv run gws sheets read <id> "E1:F10"

# EFFICIENT: 1 API call
uv run gws sheets batch-get <id> "A1:B10,C1:D10,E1:F10"
```

#### Google Sheets: Write Once

```bash
# INEFFICIENT: 5 API calls (one per row)
uv run gws sheets write <id> "A1:C1" --values '[["Header1","Header2","Header3"]]'
uv run gws sheets write <id> "A2:C2" --values '[["Row1","Data","Here"]]'
# ... and so on

# EFFICIENT: 1 API call (all data at once)
uv run gws sheets write <id> "A1:C4" --values '[
  ["Header1","Header2","Header3"],
  ["Row1","Data","Here"],
  ["Row2","More","Data"]
]'
```

### Operation Ordering for Docs

When modifying documents, **work from the end toward the beginning**:

```bash
# Problem: Inserting at index 10 shifts everything after it

# SOLUTION: Work backwards
uv run gws docs insert <doc_id> "Section 3" --index 150  # Last position first
uv run gws docs insert <doc_id> "Section 2" --index 100  # Second last
uv run gws docs insert <doc_id> "Section 1" --index 50   # First position last
```

### Slides: Efficient Presentation Building

```bash
# Step 1: Create all slides first
uv run gws slides add-slide <pres_id> --layout TITLE
uv run gws slides add-slide <pres_id> --layout TITLE_AND_BODY

# Step 2: Read to get all slide IDs
uv run gws slides read <pres_id>

# Step 3: Populate content using IDs from step 2
```

### Rate Limit Awareness

| Service | Quota (per minute) | Strategy |
|---------|-------------------|----------|
| Docs | 300 read, 60 write | Batch content before writing |
| Sheets | 300 read, 60 write | Use batch-get, write ranges |
| Slides | 300 read, 60 write | Create structure first, populate second |
| Drive | 1000 queries | Use search with specific queries |

### Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Read-modify-read-modify loops | Doubles API calls | Read once, plan changes, apply all |
| Cell-by-cell writes | N API calls instead of 1 | Write entire range at once |
| Blind insertions/deletions | Index errors | Always read structure first |

### Template-First Workflow (Recommended)

The most efficient approach is to **start from a template** rather than building from scratch:

```bash
# Copy template to create new document (1 API call)
RESULT=$(uv run gws drive copy "$TEMPLATE_DOC_ID" --name "Q4 Analysis Report")
NEW_DOC_ID=$(echo "$RESULT" | jq -r '.file_id')

# Replace placeholder content
uv run gws docs replace "$NEW_DOC_ID" "{{TITLE}}" "Q4 Analysis Report"
uv run gws docs replace "$NEW_DOC_ID" "{{DATE}}" "January 2025"
```

**Template placeholders:**

| Placeholder | Purpose |
|-------------|---------|
| `{{TITLE}}` | Document/presentation title |
| `{{DATE}}` | Creation or report date |
| `{{AUTHOR}}` | Author name or team |
| `{{CONTENT_START}}` | Marker for main content insertion |

---

## Quick Reference: Common Patterns

### Creating a Report

1. Start with purpose and audience
2. Outline structure (Exec Summary → Sections → Conclusion)
3. Write body sections first, summary last
4. Include charts/tables where data tells the story

### Creating a Presentation

1. Define the one key message
2. Outline the story arc (problem → solution → future)
3. Create slides for each major beat
4. Add visuals that reinforce, not decorate
5. Reduce text to absolute minimum
6. Add speaker notes with talking points and context
7. Practice the narrative flow

### Writing an Important Email

1. State purpose in subject line
2. Lead with the ask or decision needed
3. Provide context in 2-3 sentences
4. Use bullets for supporting details
5. End with explicit call to action and deadline

---

## Sources

### Presentation Design
- [Nancy Duarte: Resonate](https://www.duarte.com/resources/books/resonate/)

### Email Communication
- [28 Email Etiquette Rules for the Workplace](https://www.indeed.com/career-advice/career-development/email-etiquette)

### Meeting Management
- [Meeting Invite Etiquette & Best Practices](https://www.flowtrace.co/collaboration-blog/meeting-invite-etiquette-best-practices)

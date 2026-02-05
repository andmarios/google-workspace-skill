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

## API Performance Fundamentals

Google Workspace APIs have rate limits and quotas. Efficient API usage reduces latency, avoids errors, and improves reliability.

### The Fields Parameter (Partial Responses)

Request only the data you need. The `fields` parameter can reduce payload size by up to 80%.

**Syntax:**
- Comma-separated fields: `fields=id,name,mimeType`
- Nested fields with `/`: `fields=permissions/role`
- Sub-selections with `()`: `fields=files(id,name,parents)`

**Note:** The `fields` parameter is used at the API level. The `gws` CLI automatically optimizes field selection for most operations, returning only relevant data.

**Required for some endpoints (API-level):**
- Drive: `about`, `comments`, and `replies` resources require explicit `fields`
- Without `fields`, some methods return empty responses

When building custom integrations, always specify `fields` in your API requests.

### PATCH vs PUT Semantics

| Method | Behavior | Use Case |
|--------|----------|----------|
| `PUT` | Replaces entire resource; unspecified fields are cleared | Full resource replacement |
| `PATCH` | Updates only specified fields; others unchanged | Partial updates |

**Always prefer PATCH** for updates to avoid accidentally clearing fields:
```bash
# GOOD: Only updates the name
uv run gws drive update $FILE_ID --name "New Name"

# BAD (conceptually): PUT would clear description, starred, etc.
```

### Read-Before-Modify Pattern

**Always read the document/sheet/presentation before making changes.**

This is critical because:
1. **Index accuracy**: Document indices change after each insertion/deletion
2. **Structure understanding**: Know what exists before adding/removing
3. **Revision tracking**: Capture `revisionId` for optimistic concurrency
4. **Error prevention**: Verify the target exists

```bash
# GOOD: Read first, then modify
uv run gws docs read <doc_id>        # Understand structure
uv run gws docs insert <doc_id> "New text" --index 50  # Informed decision
```

### Compression

Enable gzip compression to reduce bandwidth by 60-80%:
- Set `Accept-Encoding: gzip` header
- Include "gzip" in User-Agent string
- Trade-off: CPU for decompression (usually worthwhile)

The `gws` CLI handles this automatically.

---

## Service-Specific API Tips

### Google Docs: Edit Backwards

**Order requests in descending index order** within a single `batchUpdate` call. This eliminates the need to recalculate indices after each insertion/deletion.

```bash
# Problem: Inserting at index 10 shifts everything after it

# SOLUTION: Work backwards
uv run gws docs insert <doc_id> "Section 3" --index 150  # Last position first
uv run gws docs insert <doc_id> "Section 2" --index 100  # Second last
uv run gws docs insert <doc_id> "Section 1" --index 50   # First position last
```

**WriteControl for Concurrent Edits:**
- `requiredRevisionId`: Blocks writes if document changed since reading
- `targetRevisionId`: Merges changes with collaborator updates

```bash
# Read document and capture revision
RESULT=$(uv run gws docs read $DOC_ID)
REVISION=$(echo "$RESULT" | jq -r '.revision_id')

# Use revision to detect conflicts (handled internally by gws)
```

**Tabs Handling:**
- Set `includeTabsContent=true` to retrieve all tab content (not returned by default)
- Specify tab ID for each request; unspecified requests target the first tab

### Google Sheets: Explicit Ranges

**Specify exact ranges** for up to 45% performance improvement:

```bash
# INEFFICIENT: Reads entire sheet
uv run gws sheets read <id> "Sheet1"

# EFFICIENT: Reads only needed range
uv run gws sheets read <id> "Sheet1!A1:D100"
```

**Batch Reads:**
```bash
# INEFFICIENT: 3 API calls
uv run gws sheets read <id> "A1:B10"
uv run gws sheets read <id> "C1:D10"
uv run gws sheets read <id> "E1:F10"

# EFFICIENT: 1 API call
uv run gws sheets batch-get <id> "A1:B10,C1:D10,E1:F10"
```

**Write Once Pattern:**
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

**Avoid Write-Read-Write Cycles:**
```bash
# BAD: Write, read back, write more
uv run gws sheets write <id> "A1:B2" --values '[...]'
uv run gws sheets read <id> "A1:B2"  # Unnecessary
uv run gws sheets write <id> "A3:B4" --values '[...]'

# GOOD: Plan all writes, execute once
uv run gws sheets write <id> "A1:B4" --values '[all data]'
```

### Google Slides: Two-Pass Building

Build presentations in two passes:

```bash
# Pass 1: Create all slides first
uv run gws slides add-slide <pres_id> --layout TITLE
uv run gws slides add-slide <pres_id> --layout TITLE_AND_BODY
uv run gws slides add-slide <pres_id> --layout TITLE_AND_BODY

# Pass 2: Read to get all slide IDs
RESULT=$(uv run gws slides read <pres_id>)
SLIDE_IDS=$(echo "$RESULT" | jq -r '.slides[].object_id')

# Pass 3: Populate content using IDs from pass 2
for SLIDE_ID in $SLIDE_IDS; do
  uv run gws slides replace-text <pres_id> "{{TITLE}}" "Actual Title"
done
```

**Why two passes?**
- Slide IDs are server-generated; you can't predict them
- Creating structure first lets you batch content updates
- Reduces total API calls vs. create-then-read-per-slide

### Google Drive: Batch Limits

| Constraint | Limit |
|------------|-------|
| Calls per batch | 100 maximum |
| URL length per inner request | 8,000 characters |
| Media operations | Not allowed in batches |

**Important:** Each call in a batch counts individually toward quotas. A batch of 50 requests uses 50 quota units, not 1.

```bash
# For bulk operations, use search + iteration
uv run gws drive search "name contains 'report'"
```

### Gmail: Batch Recommendations

**Recommended batch size: 50 requests** (max is 100, but larger batches trigger rate limiting)

**Three causes of 429 errors:**
1. **Sending quota**: Too many emails sent
2. **Bandwidth quota**: Too much data transferred
3. **Concurrent request limit**: Too many parallel requests

```bash
# For bulk email operations, process in batches of 50
# The gws CLI handles batching internally for list operations
uv run gws gmail list --max-results 100  # Internally batched
```

### Google Calendar: Event ID Strategy

**Client-side event IDs** (API-level concept):

At the API level, providing an event ID prevents duplicate events if a network request fails after successful server-side execution. The `gws` CLI uses server-generated IDs for simplicity.

```bash
# Standard event creation with gws
uv run gws calendar create "Team Standup" \
  "2025-01-15T09:00:00" "2025-01-15T09:30:00" \
  --calendar primary
```

**For idempotent operations** (custom integrations):
- Generate a client-side ID (UUID without dashes, lowercase)
- Include it in the `id` field of your API request
- Retries with the same ID won't create duplicates

**Push Notifications vs Polling:**
| Approach | Pros | Cons |
|----------|------|------|
| Push notifications | Real-time, no wasted calls | ~1% message drop rate |
| Polling | Reliable, simple | Wastes quota, latency |

**Best practice:** Use push notifications with periodic sync as backup.

### Google Contacts: Sequential Mutations

**Critical:** Mutations to the same user must be sequential, not parallel.

```bash
# BAD: Parallel mutations to same contact
uv run gws contacts update $RESOURCE_NAME --email "new@example.com" &
uv run gws contacts update $RESOURCE_NAME --phone "+1234567890" &
wait  # Race condition!

# GOOD: Sequential mutations
uv run gws contacts update $RESOURCE_NAME --email "new@example.com"
uv run gws contacts update $RESOURCE_NAME --phone "+1234567890"

# BEST: Single mutation with all changes
uv run gws contacts update $RESOURCE_NAME \
  --email "new@example.com" \
  --phone "+1234567890"
```

**ETags for Updates:**
Always use the `etag` from the previous response to avoid conflicts:
```bash
# Read contact to get current etag
RESULT=$(uv run gws contacts get $RESOURCE_NAME)
# gws internally uses etag for subsequent updates
```

**Search Warmup:**
The first search query after authentication may be slower. Subsequent queries use cached indices.

---

## Error Handling & Recovery

### HTTP Status Code Reference

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check request syntax, missing fields, invalid parameters |
| 401 | Unauthorized | Refresh access token or re-authenticate |
| 403 | Forbidden | Check permissions, quotas, or domain policies |
| 404 | Not Found | Verify resource ID exists and is accessible |
| 429 | Too Many Requests | Implement exponential backoff |
| 500 | Internal Server Error | Retry with exponential backoff |
| 502 | Bad Gateway | Retry with exponential backoff |
| 503 | Service Unavailable | Retry with exponential backoff |
| 504 | Gateway Timeout | Retry with exponential backoff |

### 403 Reason Field Meanings

When you receive a 403 error, check the `reason` field in the response:

| Reason | Meaning | Resolution |
|--------|---------|------------|
| `dailyLimitExceeded` | Project's daily quota exhausted | Request quota increase in API Console |
| `userRateLimitExceeded` | Per-user rate limit hit | Reduce request frequency, add backoff |
| `rateLimitExceeded` | Maximum request rate exceeded | Implement exponential backoff |
| `quotaExceeded` | Resource quota exceeded | Check quota usage in Console |
| `domainPolicy` | Domain admin blocked access | Contact Google Workspace admin |
| `forbidden` | No permission for resource | Check sharing settings, request access |

### Exponential Backoff Strategy

The standard retry formula:

```
wait_time = min(((2^n) + random_milliseconds), max_backoff)
```

**Implementation:**

| Retry | Base Wait | With Jitter (0-1000ms) | Cumulative |
|-------|-----------|------------------------|------------|
| 1 | 1s | 1.0-2.0s | ~1.5s |
| 2 | 2s | 2.0-3.0s | ~4s |
| 3 | 4s | 4.0-5.0s | ~8.5s |
| 4 | 8s | 8.0-9.0s | ~17s |
| 5 | 16s | 16.0-17.0s | ~33s |
| 6 | 32s | 32.0-33.0s (cap) | ~65s |

**Key principles:**
- **Start at 1 second** minimum after first failure
- **Double each retry** (exponential growth)
- **Add random jitter** (0-1000ms) to prevent thundering herd
- **Cap at 32-64 seconds** to avoid excessive waits
- **Limit total retries** (typically 5-7 attempts)

The `gws` CLI implements exponential backoff with jitter automatically via `BaseService.execute()`.

### Rate Limit Recovery Patterns

**For `dailyLimitExceeded`:**
1. Check current quota usage in [Google Cloud Console](https://console.cloud.google.com/apis/dashboard)
2. Request quota increase if legitimately needed
3. Consider spreading operations across multiple days

**For `userRateLimitExceeded` / `rateLimitExceeded`:**
1. Implement exponential backoff (automatic in `gws`)
2. Reduce parallel request count
3. Batch operations where possible
4. Add delays between operations

**For `domainPolicy`:**
1. Contact Google Workspace administrator
2. Request API access for your application
3. Verify OAuth consent screen configuration

---

## Rate Limits Reference

### Per-Service Quotas

| Service | Read (per min) | Write (per min) | Notes |
|---------|----------------|-----------------|-------|
| Docs | 300 | 60 | Per-user limits |
| Sheets | 300 | 60 | Per-user limits |
| Slides | 300 | 60 | Per-user limits |
| Drive | 1,000 | 1,000 | Queries; uploads have separate limits |
| Gmail | 250 | 250 | Varies by operation type |
| Calendar | 500 | 100 | Shared calendar limits may be lower |
| Contacts | 90 | 90 | Per-user, 10 QPS max |

**Note:** These are default quotas. Enterprise accounts may have higher limits.

### Batch Operation Limits

| Service | Max per Batch | Constraints |
|---------|---------------|-------------|
| Drive | 100 | 8,000 char URL limit; no media |
| Gmail | 100 (rec. 50) | Larger batches trigger rate limiting |
| Sheets | Unlimited | Atomic `batchUpdate`; single range |
| Docs | Unlimited | Atomic `batchUpdate` |
| Slides | Unlimited | Atomic `batchUpdate` |
| Contacts | 200 | Per `batchUpdateContacts` request |

### Quota-Efficient Patterns

```bash
# GOOD: Use batch operations
uv run gws sheets batch-get <id> "A1:B10,C1:D10,E1:F10"  # 1 call

# GOOD: Use search instead of list + filter
uv run gws drive search "mimeType='application/pdf'"  # Server-side filter

# GOOD: Specify explicit ranges
uv run gws sheets read <id> "Sheet1!A1:D100"  # Not entire sheet
```

---

## Anti-Patterns to Avoid

### General Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Read-modify-read-modify loops | Doubles API calls | Read once, plan changes, apply all |
| Cell-by-cell writes | N API calls instead of 1 | Write entire range at once |
| Blind insertions/deletions | Index errors, overwrites | Always read structure first |
| Polling for changes | Wastes quota | Use push notifications + incremental sync |
| PUT for partial updates | Clears unspecified fields | Use PATCH instead |
| Fetching all fields | Excessive bandwidth | Use `fields` parameter |
| Ignoring rate limits | 429 errors, account suspension | Implement exponential backoff |

### Service-Specific Anti-Patterns

**Google Docs:**
| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Forward-order insertions | Index recalculation errors | Edit backwards (descending index) |
| Ignoring tabs | Missing content | Set `includeTabsContent=true` |
| No revision tracking | Lost updates in collaboration | Use `WriteControl` with `revisionId` |

**Google Sheets:**
| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Reading entire sheets | Slow, memory-heavy | Specify exact ranges |
| Individual row writes | N API calls | Write full range at once |
| Write-read-write cycles | Unnecessary round trips | Plan all writes, execute once |

**Gmail:**
| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Batches > 50 requests | Rate limiting | Keep batches at 50 or fewer |
| Ignoring 429 reasons | Can't fix root cause | Check `reason` field for specific issue |
| Polling for new messages | Quota waste | Use push notifications |

**Google Calendar:**
| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Server-generated event IDs | Duplicate events on retry | Generate client-side IDs |
| Frequent polling | Wastes quota | Use push notifications with sync backup |
| No attendee limits | Slow operations | Batch attendee updates |

**Google Contacts:**
| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Parallel mutations | Race conditions, failures | Sequential updates only |
| Ignoring etags | Conflict errors | Use etag from previous response |
| Cold search queries | Slow first query | Expect warmup time |

---

## Template-First Workflow (Recommended)

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

### Content Strategy
- [Nancy Duarte: Resonate](https://www.duarte.com/resources/books/resonate/)
- [28 Email Etiquette Rules for the Workplace](https://www.indeed.com/career-advice/career-development/email-etiquette)
- [Meeting Invite Etiquette & Best Practices](https://www.flowtrace.co/collaboration-blog/meeting-invite-etiquette-best-practices)

### Google API Documentation
- [Google Docs API Best Practices](https://developers.google.com/workspace/docs/api/how-tos/best-practices)
- [Google Sheets API Performance](https://developers.google.com/workspace/sheets/api/guides/performance)
- [Google Drive API Performance](https://developers.google.com/workspace/drive/api/guides/performance)
- [Google Calendar API Performance](https://developers.google.com/workspace/calendar/api/guides/performance)
- [Gmail API Error Handling](https://developers.google.com/workspace/gmail/api/guides/handle-errors)
- [Gmail API Batch Requests](https://developers.google.com/workspace/gmail/api/guides/batch)
- [Google Calendar Push Notifications](https://developers.google.com/workspace/calendar/api/guides/push)
- [Google Calendar Create Events](https://developers.google.com/workspace/calendar/api/guides/create-events)
- [Google People API](https://developers.google.com/people)

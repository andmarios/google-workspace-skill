# Google Gmail Operations

## Contents
- [Basic Operations](#basic-operations)
- [Labels](#labels)
- [Drafts](#drafts)
- [Attachments](#attachments)
- [Threads](#threads)
- [Settings](#settings)
- [Filters](#filters)

## Basic Operations

```bash
# List recent messages
uv run gws gmail list --max 10

# Read message
uv run gws gmail read <message_id>

# Search messages
uv run gws gmail search "is:unread from:user@example.com" --max 5

# Send email (HTML by default)
uv run gws gmail send "recipient@example.com" "Subject" "Email body"

# Send plain text email
uv run gws gmail send "recipient@example.com" "Subject" "Plain text" --plain

# Send with display name and signature
uv run gws gmail send "recipient@example.com" "Subject" "Body" \
    --from-name "John Doe" --signature "Best regards,\nJohn"

# Reply to message
uv run gws gmail reply <message_id> "Reply body"

# Mark as read/unread
uv run gws gmail mark-read <message_id>
uv run gws gmail mark-unread <message_id>

# Delete message (moves to trash)
uv run gws gmail delete <message_id>
```

**Gmail search operators**: `is:unread`, `from:`, `to:`, `subject:`, `has:attachment`, `after:`, `before:`

## Labels

```bash
# List all labels
uv run gws gmail labels

# Create a new label
uv run gws gmail create-label "Project X" --visibility labelShow

# Delete a label
uv run gws gmail delete-label <label_id>

# Add labels to a message
uv run gws gmail add-labels <message_id> "Label1_ID,Label2_ID"

# Remove labels from a message
uv run gws gmail remove-labels <message_id> "UNREAD,Label_ID"
```

## Drafts

```bash
# List drafts
uv run gws gmail drafts --max 10

# Read a draft
uv run gws gmail get-draft <draft_id>

# Create a draft (HTML by default)
uv run gws gmail create-draft "recipient@example.com" "Subject" "Draft body"

# Create plain text draft
uv run gws gmail create-draft "recipient@example.com" "Subject" "Body" --plain

# Update a draft
uv run gws gmail update-draft <draft_id> --subject "New Subject" --body "Updated body"

# Send a draft
uv run gws gmail send-draft <draft_id>

# Delete a draft
uv run gws gmail delete-draft <draft_id>
```

## Attachments

```bash
# Send email with attachments
uv run gws gmail send-with-attachment "recipient@example.com" "Subject" "Body" \
    "/path/to/file1.pdf,/path/to/file2.xlsx"

# List attachments in a message
uv run gws gmail list-attachments <message_id>

# Download an attachment
uv run gws gmail download-attachment <message_id> <attachment_id> /path/to/output.pdf
```

## Threads

```bash
# List threads
uv run gws gmail threads --max 10

# Read a thread (all messages in conversation)
uv run gws gmail get-thread <thread_id>

# Move thread to trash
uv run gws gmail trash-thread <thread_id>

# Restore thread from trash
uv run gws gmail untrash-thread <thread_id>

# Add/remove labels from entire thread
uv run gws gmail modify-thread-labels <thread_id> --add "IMPORTANT" --remove "UNREAD"
```

## Settings

```bash
# Get vacation responder settings
uv run gws gmail get-vacation

# Enable vacation responder
uv run gws gmail set-vacation \
    --subject "Out of Office" \
    --body "I'm currently out of the office and will return on Monday." \
    --enable

# Disable vacation responder
uv run gws gmail set-vacation --disable

# Vacation with date range
uv run gws gmail set-vacation \
    --subject "On Vacation" \
    --body "I'll be back soon!" \
    --start-time "2025-12-20T00:00:00Z" \
    --end-time "2025-12-31T00:00:00Z" \
    --contacts-only

# Get email signature
uv run gws gmail get-signature

# Set email signature (HTML)
uv run gws gmail set-signature "<p><b>John Doe</b><br>Software Engineer</p>"
```

## Filters

```bash
# List all mail filters
uv run gws gmail filters

# Get filter details
uv run gws gmail get-filter <filter_id>

# Create filter to archive emails from a sender
uv run gws gmail create-filter --from "newsletter@example.com" --archive

# Create filter to label emails and skip inbox
uv run gws gmail create-filter --from "team@company.com" --add-labels "Label_123" --archive

# Create filter matching a query with multiple actions
uv run gws gmail create-filter --query "subject:urgent" --star --important

# Create filter to never send to spam
uv run gws gmail create-filter --from "important@partner.com" --never-spam

# Create filter to auto-delete (trash)
uv run gws gmail create-filter --from "spam@example.com" --trash

# Delete a filter
uv run gws gmail delete-filter <filter_id>
```

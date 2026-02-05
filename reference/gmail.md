# Google Gmail Operations

## Contents
- [Basic Operations](#basic-operations)
- [Labels](#labels)
- [Batch Operations](#batch-operations)
- [Drafts](#drafts)
- [Attachments](#attachments)
- [Threads](#threads)
- [Settings](#settings)
- [Filters](#filters)
- [History/Sync](#historysync)

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

# Multi-line body via stdin (required when piping content)
cat <<'EOF' | uv run gws gmail send "recipient@example.com" "Meeting Notes" --stdin
Hi Team,

Here are the key points from today's meeting:

1. Project deadline moved to Friday
2. Review the updated spec document
3. Schedule follow-up for next week

Best regards
EOF

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

# Restore message from trash
uv run gws gmail untrash <message_id>
```

**Gmail search operators**: `is:unread`, `from:`, `to:`, `subject:`, `has:attachment`, `after:`, `before:`

## Labels

```bash
# List all labels
uv run gws gmail labels

# Get details of a specific label
uv run gws gmail get-label <label_id>

# Create a new label
uv run gws gmail create-label "Project X" --visibility labelShow

# Update label name
uv run gws gmail update-label <label_id> --name "New Name"

# Update label visibility
uv run gws gmail update-label <label_id> --label-visibility labelHide

# Update label colors
uv run gws gmail update-label <label_id> --text-color "#ffffff" --background-color "#4285f4"

# Update multiple label properties at once
uv run gws gmail update-label <label_id> \
    --name "Important Projects" \
    --message-visibility show \
    --label-visibility labelShow \
    --text-color "#000000" \
    --background-color "#fad165"

# Delete a label
uv run gws gmail delete-label <label_id>

# Add labels to a message
uv run gws gmail add-labels <message_id> "Label1_ID,Label2_ID"

# Remove labels from a message
uv run gws gmail remove-labels <message_id> "UNREAD,Label_ID"
```

**Label visibility options:**
- `--message-visibility`: `show` or `hide` (controls visibility in message list)
- `--label-visibility`: `labelShow`, `labelShowIfUnread`, or `labelHide` (controls visibility in label list)

## Batch Operations

```bash
# Add a label to multiple messages at once
uv run gws gmail batch-modify "msg_id1,msg_id2,msg_id3" --add-labels "Label_ID"

# Remove labels from multiple messages
uv run gws gmail batch-modify "msg_id1,msg_id2,msg_id3" --remove-labels "UNREAD,INBOX"

# Add and remove labels in one operation
uv run gws gmail batch-modify "msg_id1,msg_id2" \
    --add-labels "Label_ID,STARRED" \
    --remove-labels "UNREAD"

# Archive multiple messages (remove INBOX label)
uv run gws gmail batch-modify "msg_id1,msg_id2,msg_id3" --remove-labels "INBOX"

# Mark multiple messages as read
uv run gws gmail batch-modify "msg_id1,msg_id2" --remove-labels "UNREAD"
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

# Create draft with multi-line body via stdin
cat <<'EOF' | uv run gws gmail create-draft "recipient@example.com" "Draft Subject" --stdin
Draft content here
spanning multiple lines.

Add formatting as needed.
EOF

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

# Permanently delete a thread (cannot be undone)
uv run gws gmail delete-thread <thread_id>
```

**Warning:** `delete-thread` permanently deletes all messages in the thread. This action cannot be undone. Use `trash-thread` if you want to be able to recover the messages.

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

## History/Sync

The history API enables incremental synchronization by tracking mailbox changes since a specific history ID. This is useful for keeping a local cache in sync without fetching all messages.

```bash
# Get changes since a history ID
uv run gws gmail history <start_history_id>

# Limit the number of history records returned
uv run gws gmail history <start_history_id> --max 50

# Filter by specific change types
uv run gws gmail history <start_history_id> --types "messageAdded,messageDeleted"

# Only get changes for messages with a specific label
uv run gws gmail history <start_history_id> --label "INBOX"

# Combine options for targeted sync
uv run gws gmail history <start_history_id> \
    --max 200 \
    --types "labelAdded,labelRemoved" \
    --label "Label_ID"
```

**History types:**
- `messageAdded` - New messages added to the mailbox
- `messageDeleted` - Messages permanently deleted
- `labelAdded` - Labels added to messages
- `labelRemoved` - Labels removed from messages

**Sync workflow:**
1. On initial sync, use `list` or `search` to get messages and note the `historyId` from the response
2. On subsequent syncs, call `history` with the last known history ID
3. Process the returned changes to update your local state
4. Store the new `historyId` for the next sync

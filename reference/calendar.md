# Google Calendar Operations

## Contents
- [Basic Operations](#basic-operations)
- [Recurring Events](#recurring-events)
- [Attendees](#attendees)
- [Free/Busy](#freebusy)
- [Calendar Sharing (ACL)](#calendar-sharing-acl)
- [Reminders](#reminders)

## Basic Operations

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

# Create all-day event
uv run gws calendar create "Company Holiday" "2025-12-25" "2025-12-26" --all-day

# Quick add (natural language)
uv run gws calendar quick-add "Meeting tomorrow at 3pm"
uv run gws calendar quick-add "Lunch with Bob on Friday at noon"

# Update event
uv run gws calendar update <event_id> --summary "Updated Meeting" --location "Room B"

# Delete event
uv run gws calendar delete <event_id>
```

## Recurring Events

```bash
# Create recurring event with RRULE
uv run gws calendar create-recurring "Team Standup" "2025-01-15T09:30:00" "2025-01-15T09:45:00" \
    "FREQ=WEEKLY;BYDAY=MO,WE,FR" --timezone "America/New_York"

# Common RRULE patterns
# FREQ=DAILY - Every day
# FREQ=WEEKLY;BYDAY=MO,WE,FR - Monday, Wednesday, Friday
# FREQ=MONTHLY;BYMONTHDAY=15 - 15th of each month
# FREQ=YEARLY - Yearly
# FREQ=WEEKLY;COUNT=10 - Weekly for 10 occurrences
# FREQ=DAILY;UNTIL=20251231 - Daily until December 31, 2025

# List instances of a recurring event
uv run gws calendar instances <recurring_event_id> --max 10

# List instances in a date range
uv run gws calendar instances <event_id> --from "2025-01-01T00:00:00Z" --to "2025-03-01T00:00:00Z"
```

## Attendees

```bash
# Add attendees to an event
uv run gws calendar add-attendees <event_id> "alice@example.com,bob@example.com"

# Add attendees without sending notifications
uv run gws calendar add-attendees <event_id> "alice@example.com" --no-notify

# Remove attendees
uv run gws calendar remove-attendees <event_id> "bob@example.com"

# List attendees and RSVP status
uv run gws calendar attendees <event_id>

# RSVP to an event
uv run gws calendar rsvp <event_id> accepted
uv run gws calendar rsvp <event_id> declined
uv run gws calendar rsvp <event_id> tentative
```

## Free/Busy

```bash
# Query free/busy information
uv run gws calendar freebusy "2025-01-15T00:00:00Z" "2025-01-16T00:00:00Z"

# Query multiple calendars
uv run gws calendar freebusy "2025-01-15T00:00:00Z" "2025-01-16T00:00:00Z" \
    --calendars "primary,calendar_id_2"

# Query with timezone
uv run gws calendar freebusy "2025-01-15T09:00:00" "2025-01-15T18:00:00" \
    --timezone "America/New_York"
```

## Calendar Sharing (ACL)

```bash
# List who has access to a calendar
uv run gws calendar list-acl --calendar <calendar_id>

# Share calendar with a user (read-only)
uv run gws calendar add-acl user "alice@example.com" reader

# Share calendar with a user (can edit)
uv run gws calendar add-acl user "bob@example.com" writer

# Share with everyone in a domain (free/busy only)
uv run gws calendar add-acl domain "example.com" freeBusyReader

# Update access level
uv run gws calendar update-acl <rule_id> writer

# Remove access
uv run gws calendar remove-acl <rule_id>
```

**Scope types**: user, group, domain, default
**Roles**: reader, writer, owner, freeBusyReader

## Reminders

```bash
# Get reminders for an event
uv run gws calendar get-reminders <event_id>

# Set custom reminders (popup 10 min, email 1 hour before)
uv run gws calendar set-reminders <event_id> --reminders "popup:10,email:60"

# Use calendar's default reminders
uv run gws calendar set-reminders <event_id> --use-default

# Remove all reminders from an event
uv run gws calendar clear-reminders <event_id>

# Get calendar's default reminders
uv run gws calendar get-default-reminders

# Set calendar's default reminders
uv run gws calendar set-default-reminders "popup:10,email:30"
```

**Reminder methods**: popup (browser notification), email
**Minutes**: Time before event (e.g., 10 = 10 minutes before)

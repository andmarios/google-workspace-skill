"""Calendar CLI commands."""

import typer
from typing import Annotated, Optional

from gws.services.calendar import CalendarService

app = typer.Typer(
    name="calendar",
    help="Google Calendar event operations.",
    no_args_is_help=True,
)


@app.command("calendars")
def list_calendars() -> None:
    """List all accessible calendars."""
    service = CalendarService()
    service.list_calendars()


@app.command("list")
def list_events(
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
    time_min: Annotated[
        Optional[str],
        typer.Option("--from", help="Start time (ISO 8601 format)."),
    ] = None,
    time_max: Annotated[
        Optional[str],
        typer.Option("--to", help="End time (ISO 8601 format)."),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum events to return."),
    ] = 10,
    query: Annotated[
        Optional[str],
        typer.Option("--query", "-q", help="Free text search."),
    ] = None,
) -> None:
    """List upcoming events."""
    service = CalendarService()
    service.list_events(
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
        query=query,
    )


@app.command("get")
def get_event(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Get a specific event by ID."""
    service = CalendarService()
    service.get_event(event_id=event_id, calendar_id=calendar_id)


@app.command("create")
def create_event(
    summary: Annotated[str, typer.Argument(help="Event title.")],
    start: Annotated[str, typer.Argument(help="Start time (ISO 8601 or YYYY-MM-DD for all-day).")],
    end: Annotated[str, typer.Argument(help="End time (ISO 8601 or YYYY-MM-DD for all-day).")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Event description."),
    ] = None,
    location: Annotated[
        Optional[str],
        typer.Option("--location", "-l", help="Event location."),
    ] = None,
    attendees: Annotated[
        Optional[str],
        typer.Option("--attendees", "-a", help="Comma-separated attendee emails."),
    ] = None,
    all_day: Annotated[
        bool,
        typer.Option("--all-day", help="Create as all-day event."),
    ] = False,
) -> None:
    """Create a new event."""
    attendee_list = attendees.split(",") if attendees else None

    service = CalendarService()
    service.create_event(
        summary=summary,
        start=start,
        end=end,
        calendar_id=calendar_id,
        description=description,
        location=location,
        attendees=attendee_list,
        all_day=all_day,
    )


@app.command("update")
def update_event(
    event_id: Annotated[str, typer.Argument(help="Event ID to update.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
    summary: Annotated[
        Optional[str],
        typer.Option("--summary", "-s", help="New event title."),
    ] = None,
    start: Annotated[
        Optional[str],
        typer.Option("--start", help="New start time."),
    ] = None,
    end: Annotated[
        Optional[str],
        typer.Option("--end", help="New end time."),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="New description."),
    ] = None,
    location: Annotated[
        Optional[str],
        typer.Option("--location", "-l", help="New location."),
    ] = None,
) -> None:
    """Update an existing event."""
    service = CalendarService()
    service.update_event(
        event_id=event_id,
        calendar_id=calendar_id,
        summary=summary,
        start=start,
        end=end,
        description=description,
        location=location,
    )


@app.command("delete")
def delete_event(
    event_id: Annotated[str, typer.Argument(help="Event ID to delete.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Delete an event."""
    service = CalendarService()
    service.delete_event(event_id=event_id, calendar_id=calendar_id)


# ===== Recurring Events =====


@app.command("create-recurring")
def create_recurring_event(
    summary: Annotated[str, typer.Argument(help="Event title.")],
    start: Annotated[str, typer.Argument(help="Start time (ISO 8601 format).")],
    end: Annotated[str, typer.Argument(help="End time (ISO 8601 format).")],
    rrule: Annotated[str, typer.Argument(help="RRULE recurrence rule (e.g., 'FREQ=WEEKLY;BYDAY=MO,WE,FR').")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
    timezone_str: Annotated[
        str,
        typer.Option("--timezone", "-tz", help="Timezone for the event (default: UTC)."),
    ] = "UTC",
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Event description."),
    ] = None,
    location: Annotated[
        Optional[str],
        typer.Option("--location", "-l", help="Event location."),
    ] = None,
    attendees: Annotated[
        Optional[str],
        typer.Option("--attendees", "-a", help="Comma-separated attendee emails."),
    ] = None,
) -> None:
    """Create a recurring event.

    Common RRULE examples:
        FREQ=DAILY (every day)
        FREQ=WEEKLY;BYDAY=MO,WE,FR (Mon, Wed, Fri)
        FREQ=MONTHLY;BYMONTHDAY=15 (15th of each month)
        FREQ=YEARLY (yearly)
    """
    attendee_list = [a.strip() for a in attendees.split(",")] if attendees else None

    service = CalendarService()
    service.create_recurring_event(
        summary=summary,
        start=start,
        end=end,
        rrule=rrule,
        calendar_id=calendar_id,
        timezone_str=timezone_str,
        description=description,
        location=location,
        attendees=attendee_list,
    )


@app.command("instances")
def get_instances(
    event_id: Annotated[str, typer.Argument(help="Recurring event ID.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
    time_min: Annotated[
        Optional[str],
        typer.Option("--from", help="Start time (ISO 8601 format)."),
    ] = None,
    time_max: Annotated[
        Optional[str],
        typer.Option("--to", help="End time (ISO 8601 format)."),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum instances to return."),
    ] = 25,
) -> None:
    """List instances of a recurring event."""
    service = CalendarService()
    service.get_instances(
        event_id=event_id,
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
    )


# ===== Attendee Management =====


@app.command("add-attendees")
def add_attendees(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    emails: Annotated[str, typer.Argument(help="Comma-separated email addresses to add.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
    no_notify: Annotated[
        bool,
        typer.Option("--no-notify", help="Don't send email notifications."),
    ] = False,
) -> None:
    """Add attendees to an event."""
    email_list = [e.strip() for e in emails.split(",")]

    service = CalendarService()
    service.add_attendees(
        event_id=event_id,
        emails=email_list,
        calendar_id=calendar_id,
        send_notifications=not no_notify,
    )


@app.command("remove-attendees")
def remove_attendees(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    emails: Annotated[str, typer.Argument(help="Comma-separated email addresses to remove.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
    no_notify: Annotated[
        bool,
        typer.Option("--no-notify", help="Don't send email notifications."),
    ] = False,
) -> None:
    """Remove attendees from an event."""
    email_list = [e.strip() for e in emails.split(",")]

    service = CalendarService()
    service.remove_attendees(
        event_id=event_id,
        emails=email_list,
        calendar_id=calendar_id,
        send_notifications=not no_notify,
    )


@app.command("attendees")
def get_attendees(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """List attendees and their RSVP status for an event."""
    service = CalendarService()
    service.get_attendees(event_id=event_id, calendar_id=calendar_id)


@app.command("rsvp")
def respond_to_event(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    response: Annotated[str, typer.Argument(help="Response: accepted, declined, or tentative.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Respond to an event invitation (RSVP)."""
    service = CalendarService()
    service.respond_to_event(
        event_id=event_id,
        response=response,
        calendar_id=calendar_id,
    )


@app.command("quick-add")
def quick_add(
    text: Annotated[str, typer.Argument(help="Natural language event description.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Create an event from natural language.

    Examples:
        "Meeting tomorrow at 3pm"
        "Lunch with Bob on Friday at noon"
        "Team standup every weekday at 9:30am"
    """
    service = CalendarService()
    service.quick_add(text=text, calendar_id=calendar_id)


# ===== Free/Busy =====


@app.command("freebusy")
def get_freebusy(
    time_min: Annotated[str, typer.Argument(help="Start time (ISO 8601 format).")],
    time_max: Annotated[str, typer.Argument(help="End time (ISO 8601 format).")],
    calendar_ids: Annotated[
        Optional[str],
        typer.Option("--calendars", "-c", help="Comma-separated calendar IDs (default: primary)."),
    ] = None,
    timezone_str: Annotated[
        str,
        typer.Option("--timezone", "-tz", help="Timezone for the query."),
    ] = "UTC",
) -> None:
    """Query free/busy information for calendars."""
    cal_ids = [c.strip() for c in calendar_ids.split(",")] if calendar_ids else None

    service = CalendarService()
    service.get_freebusy(
        time_min=time_min,
        time_max=time_max,
        calendar_ids=cal_ids,
        timezone_str=timezone_str,
    )


# ===== Calendar Sharing (ACL) =====


@app.command("list-acl")
def list_acl(
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """List access control rules (who has access to the calendar)."""
    service = CalendarService()
    service.list_acl(calendar_id=calendar_id)


@app.command("add-acl")
def add_acl(
    scope_type: Annotated[str, typer.Argument(help="Scope type (user, group, domain, default).")],
    scope_value: Annotated[str, typer.Argument(help="Email address or domain.")],
    role: Annotated[str, typer.Argument(help="Role (reader, writer, owner, freeBusyReader).")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Add an access control rule to share a calendar."""
    service = CalendarService()
    service.add_acl(
        scope_type=scope_type,
        scope_value=scope_value,
        role=role,
        calendar_id=calendar_id,
    )


@app.command("remove-acl")
def remove_acl(
    rule_id: Annotated[str, typer.Argument(help="ACL rule ID to remove.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Remove an access control rule from a calendar."""
    service = CalendarService()
    service.remove_acl(rule_id=rule_id, calendar_id=calendar_id)


@app.command("update-acl")
def update_acl(
    rule_id: Annotated[str, typer.Argument(help="ACL rule ID to update.")],
    role: Annotated[str, typer.Argument(help="New role (reader, writer, owner, freeBusyReader).")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Update an access control rule's role."""
    service = CalendarService()
    service.update_acl(rule_id=rule_id, role=role, calendar_id=calendar_id)


# ===== Reminders =====


@app.command("get-reminders")
def get_event_reminders(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Get reminders for an event."""
    service = CalendarService()
    service.get_event_reminders(event_id=event_id, calendar_id=calendar_id)


@app.command("set-reminders")
def set_event_reminders(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    reminders: Annotated[
        Optional[str],
        typer.Option(
            "--reminders", "-r",
            help="Comma-separated reminders (format: method:minutes, e.g., 'popup:10,email:60').",
        ),
    ] = None,
    use_default: Annotated[
        bool,
        typer.Option("--use-default", help="Use calendar's default reminders."),
    ] = False,
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Set reminders for an event.

    Examples:
        Set a popup 10 minutes before and email 1 hour before:
            gws calendar set-reminders EVENT_ID --reminders "popup:10,email:60"

        Use calendar's default reminders:
            gws calendar set-reminders EVENT_ID --use-default
    """
    reminder_list = None
    if reminders and not use_default:
        reminder_list = []
        for r in reminders.split(","):
            parts = r.strip().split(":")
            if len(parts) == 2:
                method, minutes = parts
                reminder_list.append({
                    "method": method.strip(),
                    "minutes": int(minutes.strip()),
                })

    service = CalendarService()
    service.set_event_reminders(
        event_id=event_id,
        reminders=reminder_list,
        use_default=use_default,
        calendar_id=calendar_id,
    )


@app.command("clear-reminders")
def clear_event_reminders(
    event_id: Annotated[str, typer.Argument(help="Event ID.")],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Remove all reminders from an event."""
    service = CalendarService()
    service.clear_event_reminders(event_id=event_id, calendar_id=calendar_id)


@app.command("get-default-reminders")
def get_default_reminders(
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Get default reminders for a calendar."""
    service = CalendarService()
    service.get_default_reminders(calendar_id=calendar_id)


@app.command("set-default-reminders")
def set_default_reminders(
    reminders: Annotated[
        str,
        typer.Argument(help="Comma-separated reminders (format: method:minutes, e.g., 'popup:10,email:60')."),
    ],
    calendar_id: Annotated[
        str,
        typer.Option("--calendar", "-c", help="Calendar ID (default: primary)."),
    ] = "primary",
) -> None:
    """Set default reminders for a calendar.

    Example:
        Set popup 10 minutes and email 30 minutes before as defaults:
            gws calendar set-default-reminders "popup:10,email:30"
    """
    reminder_list = []
    for r in reminders.split(","):
        parts = r.strip().split(":")
        if len(parts) == 2:
            method, minutes = parts
            reminder_list.append({
                "method": method.strip(),
                "minutes": int(minutes.strip()),
            })

    service = CalendarService()
    service.set_default_reminders(reminders=reminder_list, calendar_id=calendar_id)

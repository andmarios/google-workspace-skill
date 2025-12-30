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

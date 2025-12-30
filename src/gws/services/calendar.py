"""Google Calendar service operations."""

from datetime import datetime, timezone
from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode


class CalendarService(BaseService):
    """Google Calendar operations."""

    SERVICE_NAME = "calendar"
    VERSION = "v3"

    def list_calendars(self) -> dict[str, Any]:
        """List all accessible calendars."""
        try:
            result = self.service.calendarList().list().execute()

            calendars = [
                {
                    "id": cal["id"],
                    "summary": cal.get("summary", ""),
                    "primary": cal.get("primary", False),
                    "access_role": cal.get("accessRole", ""),
                    "background_color": cal.get("backgroundColor", ""),
                }
                for cal in result.get("items", [])
            ]

            output_success(
                operation="calendar.list_calendars",
                calendar_count=len(calendars),
                calendars=calendars,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.list_calendars",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 10,
        query: str | None = None,
    ) -> dict[str, Any]:
        """List events from a calendar."""
        try:
            params: dict[str, Any] = {
                "calendarId": calendar_id,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }

            if time_min:
                params["timeMin"] = time_min
            else:
                # Default to now
                params["timeMin"] = datetime.now(timezone.utc).isoformat()

            if time_max:
                params["timeMax"] = time_max

            if query:
                params["q"] = query

            result = self.service.events().list(**params).execute()

            events = []
            for event in result.get("items", []):
                start = event.get("start", {})
                end = event.get("end", {})

                events.append({
                    "id": event["id"],
                    "summary": event.get("summary", "(no title)"),
                    "start": start.get("dateTime", start.get("date", "")),
                    "end": end.get("dateTime", end.get("date", "")),
                    "location": event.get("location", ""),
                    "description": event.get("description", "")[:200] if event.get("description") else "",
                    "status": event.get("status", ""),
                    "html_link": event.get("htmlLink", ""),
                })

            output_success(
                operation="calendar.list",
                calendar_id=calendar_id,
                event_count=len(events),
                events=events,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.list",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Get a specific event by ID."""
        try:
            event = (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            start = event.get("start", {})
            end = event.get("end", {})

            output_success(
                operation="calendar.get",
                event_id=event["id"],
                summary=event.get("summary", "(no title)"),
                start=start.get("dateTime", start.get("date", "")),
                end=end.get("dateTime", end.get("date", "")),
                location=event.get("location", ""),
                description=event.get("description", ""),
                status=event.get("status", ""),
                attendees=[
                    {"email": a["email"], "response": a.get("responseStatus", "")}
                    for a in event.get("attendees", [])
                ],
                html_link=event.get("htmlLink", ""),
            )
            return event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.get",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        calendar_id: str = "primary",
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        all_day: bool = False,
    ) -> dict[str, Any]:
        """Create a new event."""
        try:
            event_body: dict[str, Any] = {
                "summary": summary,
            }

            if all_day:
                # All-day events use date format (YYYY-MM-DD)
                event_body["start"] = {"date": start}
                event_body["end"] = {"date": end}
            else:
                # Timed events use dateTime format
                event_body["start"] = {"dateTime": start}
                event_body["end"] = {"dateTime": end}

            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location
            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]

            event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=event_body)
                .execute()
            )

            output_success(
                operation="calendar.create",
                event_id=event["id"],
                summary=summary,
                start=start,
                end=end,
                html_link=event.get("htmlLink", ""),
            )
            return event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.create",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        summary: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing event."""
        try:
            # Get existing event
            event = (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            # Update fields if provided
            if summary is not None:
                event["summary"] = summary
            if description is not None:
                event["description"] = description
            if location is not None:
                event["location"] = location
            if start is not None:
                if "date" in event.get("start", {}):
                    event["start"] = {"date": start}
                else:
                    event["start"] = {"dateTime": start}
            if end is not None:
                if "date" in event.get("end", {}):
                    event["end"] = {"date": end}
                else:
                    event["end"] = {"dateTime": end}

            updated_event = (
                self.service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=event)
                .execute()
            )

            output_success(
                operation="calendar.update",
                event_id=updated_event["id"],
                summary=updated_event.get("summary", ""),
                html_link=updated_event.get("htmlLink", ""),
            )
            return updated_event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.update",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Delete an event."""
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()

            output_success(
                operation="calendar.delete",
                event_id=event_id,
                calendar_id=calendar_id,
            )
            return {"id": event_id, "deleted": True}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.delete",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

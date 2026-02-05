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
            result = self.execute(
                self.service.calendarList().list(
                    fields="items(id,summary,primary,accessRole,backgroundColor),nextPageToken"
                )
            )

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

            result = self.execute(self.service.events().list(**params))

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
            event = self.execute(
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
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

            event = self.execute(
                self.service.events()
                .insert(calendarId=calendar_id, body=event_body)
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
            event = self.execute(
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
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

            updated_event = self.execute(
                self.service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=event)
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
            self.execute(self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ))

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

    # ===== Recurring Events =====

    def create_recurring_event(
        self,
        summary: str,
        start: str,
        end: str,
        rrule: str,
        calendar_id: str = "primary",
        timezone_str: str = "UTC",
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a recurring event.

        Args:
            summary: Event title.
            start: Start time (ISO format or HH:MM for time only).
            end: End time (ISO format or HH:MM for time only).
            rrule: RRULE recurrence rule (e.g., "FREQ=WEEKLY;BYDAY=MO,WE,FR").
            calendar_id: Calendar ID.
            timezone_str: Timezone for the event.
            description: Event description.
            location: Event location.
            attendees: List of attendee email addresses.
        """
        try:
            event_body: dict[str, Any] = {
                "summary": summary,
                "start": {"dateTime": start, "timeZone": timezone_str},
                "end": {"dateTime": end, "timeZone": timezone_str},
                "recurrence": [f"RRULE:{rrule}"],
            }

            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location
            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]

            event = self.execute(
                self.service.events()
                .insert(calendarId=calendar_id, body=event_body)
            )

            output_success(
                operation="calendar.create_recurring",
                event_id=event["id"],
                summary=summary,
                start=start,
                end=end,
                rrule=rrule,
                html_link=event.get("htmlLink", ""),
            )
            return event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.create_recurring",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_instances(
        self,
        event_id: str,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 25,
    ) -> dict[str, Any]:
        """Get instances of a recurring event.

        Args:
            event_id: The recurring event ID.
            calendar_id: Calendar ID.
            time_min: Lower bound for instances (ISO format).
            time_max: Upper bound for instances (ISO format).
            max_results: Maximum number of instances to return.
        """
        try:
            params: dict[str, Any] = {
                "calendarId": calendar_id,
                "eventId": event_id,
                "maxResults": max_results,
            }

            if time_min:
                params["timeMin"] = time_min
            else:
                params["timeMin"] = datetime.now(timezone.utc).isoformat()

            if time_max:
                params["timeMax"] = time_max

            result = self.execute(self.service.events().instances(**params))

            instances = []
            for event in result.get("items", []):
                start = event.get("start", {})
                end = event.get("end", {})

                instances.append({
                    "id": event["id"],
                    "summary": event.get("summary", "(no title)"),
                    "start": start.get("dateTime", start.get("date", "")),
                    "end": end.get("dateTime", end.get("date", "")),
                    "status": event.get("status", ""),
                })

            output_success(
                operation="calendar.get_instances",
                event_id=event_id,
                instance_count=len(instances),
                instances=instances,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.get_instances",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # ===== Attendee Management =====

    def add_attendees(
        self,
        event_id: str,
        emails: list[str],
        calendar_id: str = "primary",
        send_notifications: bool = True,
    ) -> dict[str, Any]:
        """Add attendees to an event.

        Args:
            event_id: The event ID.
            emails: List of email addresses to add.
            calendar_id: Calendar ID.
            send_notifications: Whether to send email notifications.
        """
        try:
            # Get existing event
            event = self.execute(
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
            )

            # Add new attendees
            existing_attendees = event.get("attendees", [])
            existing_emails = {a["email"] for a in existing_attendees}

            for email in emails:
                if email not in existing_emails:
                    existing_attendees.append({"email": email})

            event["attendees"] = existing_attendees

            # Update event
            send_updates = "all" if send_notifications else "none"
            updated_event = self.execute(
                self.service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event,
                    sendUpdates=send_updates,
                )
            )

            output_success(
                operation="calendar.add_attendees",
                event_id=event_id,
                added_emails=emails,
                attendee_count=len(updated_event.get("attendees", [])),
            )
            return updated_event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.add_attendees",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def remove_attendees(
        self,
        event_id: str,
        emails: list[str],
        calendar_id: str = "primary",
        send_notifications: bool = True,
    ) -> dict[str, Any]:
        """Remove attendees from an event.

        Args:
            event_id: The event ID.
            emails: List of email addresses to remove.
            calendar_id: Calendar ID.
            send_notifications: Whether to send email notifications.
        """
        try:
            # Get existing event
            event = self.execute(
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
            )

            # Filter out specified attendees
            emails_to_remove = set(emails)
            event["attendees"] = [
                a for a in event.get("attendees", [])
                if a["email"] not in emails_to_remove
            ]

            # Update event
            send_updates = "all" if send_notifications else "none"
            updated_event = self.execute(
                self.service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event,
                    sendUpdates=send_updates,
                )
            )

            output_success(
                operation="calendar.remove_attendees",
                event_id=event_id,
                removed_emails=emails,
                attendee_count=len(updated_event.get("attendees", [])),
            )
            return updated_event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.remove_attendees",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_attendees(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Get attendees and their RSVP status for an event.

        Args:
            event_id: The event ID.
            calendar_id: Calendar ID.
        """
        try:
            event = self.execute(
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
            )

            attendees = [
                {
                    "email": a["email"],
                    "display_name": a.get("displayName", ""),
                    "response_status": a.get("responseStatus", "needsAction"),
                    "organizer": a.get("organizer", False),
                    "optional": a.get("optional", False),
                }
                for a in event.get("attendees", [])
            ]

            output_success(
                operation="calendar.get_attendees",
                event_id=event_id,
                summary=event.get("summary", ""),
                attendee_count=len(attendees),
                attendees=attendees,
            )
            return {"event_id": event_id, "attendees": attendees}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.get_attendees",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def respond_to_event(
        self,
        event_id: str,
        response: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Respond to an event invitation (RSVP).

        Args:
            event_id: The event ID.
            response: Response status (accepted, declined, tentative).
            calendar_id: Calendar ID.
        """
        try:
            valid_responses = {"accepted", "declined", "tentative"}
            if response.lower() not in valid_responses:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="calendar.respond",
                    message=f"Response must be one of: {valid_responses}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # Get event and find self in attendees
            event = self.execute(
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
            )

            # Update self's response status
            for attendee in event.get("attendees", []):
                if attendee.get("self", False):
                    attendee["responseStatus"] = response.lower()
                    break

            updated_event = self.execute(
                self.service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event,
                )
            )

            output_success(
                operation="calendar.respond",
                event_id=event_id,
                response=response.lower(),
                summary=updated_event.get("summary", ""),
            )
            return updated_event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.respond",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def quick_add(
        self,
        text: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Create an event from natural language text.

        Args:
            text: Natural language description (e.g., "Meeting tomorrow at 3pm").
            calendar_id: Calendar ID.
        """
        try:
            event = self.execute(
                self.service.events()
                .quickAdd(calendarId=calendar_id, text=text)
            )

            start = event.get("start", {})
            end = event.get("end", {})

            output_success(
                operation="calendar.quick_add",
                event_id=event["id"],
                summary=event.get("summary", ""),
                start=start.get("dateTime", start.get("date", "")),
                end=end.get("dateTime", end.get("date", "")),
                html_link=event.get("htmlLink", ""),
            )
            return event
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.quick_add",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # FREE/BUSY QUERIES
    # =========================================================================

    def get_freebusy(
        self,
        time_min: str,
        time_max: str,
        calendar_ids: list[str] | None = None,
        timezone_str: str = "UTC",
    ) -> dict[str, Any]:
        """Query free/busy information for calendars.

        Args:
            time_min: Start time (ISO 8601 format).
            time_max: End time (ISO 8601 format).
            calendar_ids: List of calendar IDs to query (default: primary).
            timezone_str: Timezone for the query.
        """
        try:
            if not calendar_ids:
                calendar_ids = ["primary"]

            items = [{"id": cal_id} for cal_id in calendar_ids]

            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "timeZone": timezone_str,
                "items": items,
            }

            result = self.execute(self.service.freebusy().query(body=body))

            calendars = {}
            for cal_id, cal_data in result.get("calendars", {}).items():
                busy_times = []
                for busy in cal_data.get("busy", []):
                    busy_times.append({
                        "start": busy.get("start"),
                        "end": busy.get("end"),
                    })
                calendars[cal_id] = {
                    "busy": busy_times,
                    "errors": cal_data.get("errors", []),
                }

            output_success(
                operation="calendar.get_freebusy",
                time_min=time_min,
                time_max=time_max,
                calendars=calendars,
            )
            return {"calendars": calendars}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.get_freebusy",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # CALENDAR SHARING (ACL)
    # =========================================================================

    def list_acl(
        self,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """List access control rules for a calendar.

        Args:
            calendar_id: Calendar ID.
        """
        try:
            result = self.execute(self.service.acl().list(calendarId=calendar_id))

            rules = []
            for rule in result.get("items", []):
                rules.append({
                    "rule_id": rule.get("id"),
                    "scope_type": rule.get("scope", {}).get("type"),
                    "scope_value": rule.get("scope", {}).get("value"),
                    "role": rule.get("role"),
                })

            output_success(
                operation="calendar.list_acl",
                calendar_id=calendar_id,
                rule_count=len(rules),
                rules=rules,
            )
            return {"rules": rules}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.list_acl",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_acl(
        self,
        scope_type: str,
        scope_value: str,
        role: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Add an access control rule to a calendar.

        Args:
            scope_type: Scope type (user, group, domain, default).
            scope_value: Email address or domain.
            role: Role to grant (reader, writer, owner, freeBusyReader, none).
            calendar_id: Calendar ID.
        """
        try:
            valid_scope_types = {"user", "group", "domain", "default"}
            if scope_type.lower() not in valid_scope_types:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="calendar.add_acl",
                    message=f"scope_type must be one of: {valid_scope_types}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            valid_roles = {"reader", "writer", "owner", "freeBusyReader", "none"}
            if role.lower() not in {r.lower() for r in valid_roles}:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="calendar.add_acl",
                    message=f"role must be one of: {valid_roles}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            body = {
                "scope": {
                    "type": scope_type.lower(),
                    "value": scope_value,
                },
                "role": role,
            }

            result = self.execute(self.service.acl().insert(calendarId=calendar_id, body=body))

            output_success(
                operation="calendar.add_acl",
                calendar_id=calendar_id,
                rule_id=result.get("id"),
                scope_type=scope_type,
                scope_value=scope_value,
                role=role,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.add_acl",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def remove_acl(
        self,
        rule_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Remove an access control rule from a calendar.

        Args:
            rule_id: The ACL rule ID to remove.
            calendar_id: Calendar ID.
        """
        try:
            self.execute(self.service.acl().delete(calendarId=calendar_id, ruleId=rule_id))

            output_success(
                operation="calendar.remove_acl",
                calendar_id=calendar_id,
                rule_id=rule_id,
            )
            return {"rule_id": rule_id, "status": "removed"}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.remove_acl",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_acl(
        self,
        rule_id: str,
        role: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Update an access control rule.

        Args:
            rule_id: The ACL rule ID to update.
            role: New role (reader, writer, owner, freeBusyReader, none).
            calendar_id: Calendar ID.
        """
        try:
            valid_roles = {"reader", "writer", "owner", "freeBusyReader", "none"}
            if role.lower() not in {r.lower() for r in valid_roles}:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="calendar.update_acl",
                    message=f"role must be one of: {valid_roles}",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            # First get the existing rule to preserve scope
            existing = self.execute(self.service.acl().get(calendarId=calendar_id, ruleId=rule_id))

            body = {
                "scope": existing.get("scope"),
                "role": role,
            }

            result = self.execute(self.service.acl().update(
                calendarId=calendar_id, ruleId=rule_id, body=body
            ))

            output_success(
                operation="calendar.update_acl",
                calendar_id=calendar_id,
                rule_id=rule_id,
                role=role,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.update_acl",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # REMINDERS
    # =========================================================================

    def get_event_reminders(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Get reminders for an event.

        Args:
            event_id: The event ID.
            calendar_id: Calendar ID.
        """
        try:
            event = self.execute(self.service.events().get(
                calendarId=calendar_id, eventId=event_id
            ))

            reminders = event.get("reminders", {})

            output_success(
                operation="calendar.get_event_reminders",
                calendar_id=calendar_id,
                event_id=event_id,
                event_title=event.get("summary", ""),
                use_default=reminders.get("useDefault", True),
                overrides=reminders.get("overrides", []),
            )
            return reminders
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.get_event_reminders",
                    message=f"Event not found: {event_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.get_event_reminders",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_event_reminders(
        self,
        event_id: str,
        reminders: list[dict[str, Any]] | None = None,
        use_default: bool = False,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Set reminders for an event.

        Args:
            event_id: The event ID.
            reminders: List of reminders [{method: "email"|"popup", minutes: int}].
            use_default: Use calendar's default reminders.
            calendar_id: Calendar ID.
        """
        try:
            body: dict[str, Any] = {
                "reminders": {
                    "useDefault": use_default,
                }
            }

            if not use_default and reminders:
                body["reminders"]["overrides"] = reminders

            result = self.execute(self.service.events().patch(
                calendarId=calendar_id,
                eventId=event_id,
                body=body,
            ))

            output_success(
                operation="calendar.set_event_reminders",
                calendar_id=calendar_id,
                event_id=event_id,
                use_default=use_default,
                reminders=reminders if not use_default else "using defaults",
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.set_event_reminders",
                    message=f"Event not found: {event_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.set_event_reminders",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_default_reminders(
        self,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Get default reminders for a calendar.

        Args:
            calendar_id: Calendar ID.
        """
        try:
            calendar = self.execute(self.service.calendarList().get(
                calendarId=calendar_id
            ))

            reminders = calendar.get("defaultReminders", [])

            output_success(
                operation="calendar.get_default_reminders",
                calendar_id=calendar_id,
                calendar_summary=calendar.get("summary", ""),
                default_reminders=reminders,
            )
            return {"default_reminders": reminders}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.get_default_reminders",
                    message=f"Calendar not found: {calendar_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.get_default_reminders",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def set_default_reminders(
        self,
        reminders: list[dict[str, Any]],
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Set default reminders for a calendar.

        Args:
            reminders: List of reminders [{method: "email"|"popup", minutes: int}].
            calendar_id: Calendar ID.
        """
        try:
            result = self.execute(self.service.calendarList().patch(
                calendarId=calendar_id,
                body={"defaultReminders": reminders},
            ))

            output_success(
                operation="calendar.set_default_reminders",
                calendar_id=calendar_id,
                default_reminders=reminders,
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.set_default_reminders",
                    message=f"Calendar not found: {calendar_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.set_default_reminders",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def clear_event_reminders(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Remove all reminders from an event.

        Args:
            event_id: The event ID.
            calendar_id: Calendar ID.
        """
        try:
            body = {
                "reminders": {
                    "useDefault": False,
                    "overrides": [],
                }
            }

            result = self.execute(self.service.events().patch(
                calendarId=calendar_id,
                eventId=event_id,
                body=body,
            ))

            output_success(
                operation="calendar.clear_event_reminders",
                calendar_id=calendar_id,
                event_id=event_id,
                cleared=True,
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.clear_event_reminders",
                    message=f"Event not found: {event_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.clear_event_reminders",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # CALENDAR MANAGEMENT
    # =========================================================================

    def create_calendar(
        self,
        summary: str,
        description: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any]:
        """Create a new calendar.

        Args:
            summary: Calendar name/title.
            description: Calendar description.
            timezone: Timezone (e.g., 'America/New_York'). Uses user default if not specified.
        """
        try:
            body: dict[str, Any] = {"summary": summary}
            if description:
                body["description"] = description
            if timezone:
                body["timeZone"] = timezone

            result = self.execute(
                self.service.calendars().insert(body=body)
            )

            output_success(
                operation="calendar.create_calendar",
                calendar_id=result.get("id"),
                summary=result.get("summary"),
                timezone=result.get("timeZone"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.create_calendar",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_calendar(self, calendar_id: str) -> dict[str, Any]:
        """Delete a secondary calendar.

        Args:
            calendar_id: The calendar ID to delete. Cannot delete primary calendar.
        """
        try:
            self.execute(self.service.calendars().delete(calendarId=calendar_id))

            output_success(
                operation="calendar.delete_calendar",
                calendar_id=calendar_id,
                deleted=True,
            )
            return {"deleted": True, "calendar_id": calendar_id}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.delete_calendar",
                    message=f"Calendar not found: {calendar_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.delete_calendar",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def clear_calendar(self, calendar_id: str) -> dict[str, Any]:
        """Clear all events from a calendar.

        Args:
            calendar_id: The calendar ID to clear. Only works on primary calendar.
        """
        try:
            self.execute(self.service.calendars().clear(calendarId=calendar_id))

            output_success(
                operation="calendar.clear_calendar",
                calendar_id=calendar_id,
                cleared=True,
            )
            return {"cleared": True, "calendar_id": calendar_id}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.clear_calendar",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # EVENT OPERATIONS (extended)
    # =========================================================================

    def move_event(
        self,
        event_id: str,
        source_calendar_id: str,
        destination_calendar_id: str,
    ) -> dict[str, Any]:
        """Move an event to a different calendar.

        Args:
            event_id: The event ID to move.
            source_calendar_id: The source calendar ID.
            destination_calendar_id: The destination calendar ID.
        """
        try:
            result = self.execute(
                self.service.events().move(
                    calendarId=source_calendar_id,
                    eventId=event_id,
                    destination=destination_calendar_id,
                )
            )

            output_success(
                operation="calendar.move_event",
                event_id=event_id,
                source_calendar_id=source_calendar_id,
                destination_calendar_id=destination_calendar_id,
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.move_event",
                    message=f"Event not found: {event_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.move_event",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # COLORS
    # =========================================================================

    def get_colors(self) -> dict[str, Any]:
        """Get the color definitions for calendars and events."""
        try:
            result = self.execute(self.service.colors().get())

            output_success(
                operation="calendar.get_colors",
                calendar_color_count=len(result.get("calendar", {})),
                event_color_count=len(result.get("event", {})),
                calendar_colors=result.get("calendar"),
                event_colors=result.get("event"),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="calendar.get_colors",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # CALENDAR LIST (subscriptions)
    # =========================================================================

    def subscribe_calendar(self, calendar_id: str) -> dict[str, Any]:
        """Subscribe to (add) a public calendar to the user's calendar list.

        Args:
            calendar_id: The calendar ID to subscribe to.
        """
        try:
            result = self.execute(
                self.service.calendarList().insert(body={"id": calendar_id})
            )

            output_success(
                operation="calendar.subscribe",
                calendar_id=calendar_id,
                summary=result.get("summary"),
            )
            return result
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.subscribe",
                    message=f"Calendar not found: {calendar_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.subscribe",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def unsubscribe_calendar(self, calendar_id: str) -> dict[str, Any]:
        """Unsubscribe from (remove) a calendar from the user's calendar list.

        Args:
            calendar_id: The calendar ID to unsubscribe from.
        """
        try:
            self.execute(
                self.service.calendarList().delete(calendarId=calendar_id)
            )

            output_success(
                operation="calendar.unsubscribe",
                calendar_id=calendar_id,
                unsubscribed=True,
            )
            return {"unsubscribed": True, "calendar_id": calendar_id}
        except HttpError as e:
            if e.resp.status == 404:
                output_error(
                    error_code="NOT_FOUND",
                    operation="calendar.unsubscribe",
                    message=f"Calendar not found in list: {calendar_id}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)
            output_error(
                error_code="API_ERROR",
                operation="calendar.unsubscribe",
                message=f"Calendar API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

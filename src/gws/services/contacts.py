"""Google Contacts (People API) service operations."""

from typing import Any

from googleapiclient.errors import HttpError

from gws.services.base import BaseService
from gws.output import output_success, output_error
from gws.exceptions import ExitCode


class ContactsService(BaseService):
    """Google Contacts operations via People API."""

    SERVICE_NAME = "people"
    VERSION = "v1"

    def list_contacts(
        self,
        max_results: int = 10,
        query: str | None = None,
    ) -> dict[str, Any]:
        """List contacts."""
        try:
            if query:
                result = (
                    self.service.people()
                    .searchContacts(
                        query=query,
                        readMask="names,emailAddresses,phoneNumbers,organizations",
                        pageSize=max_results,
                    )
                    .execute()
                )
                people = [r.get("person", {}) for r in result.get("results", [])]
            else:
                result = (
                    self.service.people()
                    .connections()
                    .list(
                        resourceName="people/me",
                        pageSize=max_results,
                        personFields="names,emailAddresses,phoneNumbers,organizations",
                    )
                    .execute()
                )
                people = result.get("connections", [])

            contacts = []
            for person in people:
                contact = {
                    "resource_name": person.get("resourceName", ""),
                    "name": self._get_name(person),
                    "emails": [
                        e.get("value", "") for e in person.get("emailAddresses", [])
                    ],
                    "phones": [
                        p.get("value", "") for p in person.get("phoneNumbers", [])
                    ],
                    "organization": self._get_organization(person),
                }
                contacts.append(contact)

            output_success(
                operation="contacts.list",
                contact_count=len(contacts),
                contacts=contacts,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.list",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def _get_name(self, person: dict) -> str:
        """Extract display name from person."""
        names = person.get("names", [])
        if names:
            return names[0].get("displayName", "")
        return ""

    def _get_organization(self, person: dict) -> str:
        """Extract organization from person."""
        orgs = person.get("organizations", [])
        if orgs:
            org = orgs[0]
            name = org.get("name", "")
            title = org.get("title", "")
            if name and title:
                return f"{title} at {name}"
            return name or title
        return ""

    def get_contact(
        self,
        resource_name: str,
    ) -> dict[str, Any]:
        """Get a specific contact by resource name."""
        try:
            person = (
                self.service.people()
                .get(
                    resourceName=resource_name,
                    personFields="names,emailAddresses,phoneNumbers,organizations,addresses,birthdays,biographies",
                )
                .execute()
            )

            output_success(
                operation="contacts.get",
                resource_name=person.get("resourceName", ""),
                name=self._get_name(person),
                emails=[e.get("value", "") for e in person.get("emailAddresses", [])],
                phones=[p.get("value", "") for p in person.get("phoneNumbers", [])],
                organization=self._get_organization(person),
                addresses=[
                    a.get("formattedValue", "") for a in person.get("addresses", [])
                ],
            )
            return person
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.get",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_contact(
        self,
        given_name: str,
        family_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        organization: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Create a new contact."""
        try:
            person: dict[str, Any] = {
                "names": [
                    {
                        "givenName": given_name,
                    }
                ],
            }

            if family_name:
                person["names"][0]["familyName"] = family_name

            if email:
                person["emailAddresses"] = [{"value": email}]

            if phone:
                person["phoneNumbers"] = [{"value": phone}]

            if organization or title:
                org: dict[str, str] = {}
                if organization:
                    org["name"] = organization
                if title:
                    org["title"] = title
                person["organizations"] = [org]

            result = self.service.people().createContact(body=person).execute()

            output_success(
                operation="contacts.create",
                resource_name=result.get("resourceName", ""),
                name=f"{given_name} {family_name or ''}".strip(),
                email=email,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.create",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_contact(
        self,
        resource_name: str,
        given_name: str | None = None,
        family_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing contact."""
        try:
            # Get existing contact with etag
            existing = (
                self.service.people()
                .get(
                    resourceName=resource_name,
                    personFields="names,emailAddresses,phoneNumbers,metadata",
                )
                .execute()
            )

            # Build update
            update_fields = []

            if given_name is not None or family_name is not None:
                names = existing.get("names", [{}])
                if not names:
                    names = [{}]
                if given_name is not None:
                    names[0]["givenName"] = given_name
                if family_name is not None:
                    names[0]["familyName"] = family_name
                existing["names"] = names
                update_fields.append("names")

            if email is not None:
                existing["emailAddresses"] = [{"value": email}]
                update_fields.append("emailAddresses")

            if phone is not None:
                existing["phoneNumbers"] = [{"value": phone}]
                update_fields.append("phoneNumbers")

            if not update_fields:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="contacts.update",
                    message="At least one field to update required",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            result = (
                self.service.people()
                .updateContact(
                    resourceName=resource_name,
                    updatePersonFields=",".join(update_fields),
                    body=existing,
                )
                .execute()
            )

            output_success(
                operation="contacts.update",
                resource_name=result.get("resourceName", ""),
                name=self._get_name(result),
                updated_fields=update_fields,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.update",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_contact(
        self,
        resource_name: str,
    ) -> dict[str, Any]:
        """Delete a contact."""
        try:
            self.service.people().deleteContact(resourceName=resource_name).execute()

            output_success(
                operation="contacts.delete",
                resource_name=resource_name,
            )
            return {"resourceName": resource_name, "deleted": True}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.delete",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

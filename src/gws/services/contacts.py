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
                result = self.execute(
                    self.service.people()
                    .searchContacts(
                        query=query,
                        readMask="names,emailAddresses,phoneNumbers,organizations",
                        pageSize=max_results,
                    )
                )
                people = [r.get("person", {}) for r in result.get("results", [])]
            else:
                result = self.execute(
                    self.service.people()
                    .connections()
                    .list(
                        resourceName="people/me",
                        pageSize=max_results,
                        personFields="names,emailAddresses,phoneNumbers,organizations",
                    )
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
            person = self.execute(
                self.service.people()
                .get(
                    resourceName=resource_name,
                    personFields="names,emailAddresses,phoneNumbers,organizations,addresses,birthdays,biographies",
                )
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

            result = self.execute(self.service.people().createContact(body=person))

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
            existing = self.execute(
                self.service.people()
                .get(
                    resourceName=resource_name,
                    personFields="names,emailAddresses,phoneNumbers,metadata",
                )
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

            result = self.execute(
                self.service.people()
                .updateContact(
                    resourceName=resource_name,
                    updatePersonFields=",".join(update_fields),
                    body=existing,
                )
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
            self.execute(self.service.people().deleteContact(resourceName=resource_name))

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

    # =========================================================================
    # CONTACT GROUP OPERATIONS
    # =========================================================================

    def list_groups(self, max_results: int = 50) -> dict[str, Any]:
        """List all contact groups.

        Returns user-created groups and system groups (like 'My Contacts').
        """
        try:
            result = self.execute(
                self.service.contactGroups()
                .list(pageSize=max_results)
            )

            groups = []
            for group in result.get("contactGroups", []):
                groups.append({
                    "resource_name": group.get("resourceName", ""),
                    "name": group.get("name", ""),
                    "formatted_name": group.get("formattedName", ""),
                    "member_count": group.get("memberCount", 0),
                    "group_type": group.get("groupType", ""),
                })

            output_success(
                operation="contacts.list_groups",
                group_count=len(groups),
                groups=groups,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.list_groups",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def get_group(
        self,
        resource_name: str,
        include_members: bool = True,
    ) -> dict[str, Any]:
        """Get a contact group with optional member details.

        Args:
            resource_name: The group resource name (e.g., 'contactGroups/abc123').
            include_members: If True, includes member resource names.
        """
        try:
            max_members = 1000 if include_members else 0
            result = self.execute(
                self.service.contactGroups()
                .get(
                    resourceName=resource_name,
                    maxMembers=max_members,
                )
            )

            members = result.get("memberResourceNames", [])

            output_success(
                operation="contacts.get_group",
                resource_name=result.get("resourceName", ""),
                name=result.get("name", ""),
                formatted_name=result.get("formattedName", ""),
                member_count=result.get("memberCount", 0),
                members=members[:20],  # Limit output
                has_more_members=len(members) > 20,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.get_group",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def create_group(self, name: str) -> dict[str, Any]:
        """Create a new contact group.

        Args:
            name: The name for the new group.
        """
        try:
            result = self.execute(
                self.service.contactGroups()
                .create(body={"contactGroup": {"name": name}})
            )

            output_success(
                operation="contacts.create_group",
                resource_name=result.get("resourceName", ""),
                name=result.get("name", ""),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.create_group",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_group(
        self,
        resource_name: str,
        name: str,
    ) -> dict[str, Any]:
        """Update a contact group's name.

        Args:
            resource_name: The group resource name.
            name: The new name for the group.
        """
        try:
            result = self.execute(
                self.service.contactGroups()
                .update(
                    resourceName=resource_name,
                    body={
                        "contactGroup": {"name": name},
                        "updateGroupFields": "name",
                    },
                )
            )

            output_success(
                operation="contacts.update_group",
                resource_name=result.get("resourceName", ""),
                name=result.get("name", ""),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.update_group",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_group(
        self,
        resource_name: str,
        delete_contacts: bool = False,
    ) -> dict[str, Any]:
        """Delete a contact group.

        Args:
            resource_name: The group resource name.
            delete_contacts: If True, also deletes contacts in the group.
        """
        try:
            self.execute(self.service.contactGroups().delete(
                resourceName=resource_name,
                deleteContacts=delete_contacts,
            ))

            output_success(
                operation="contacts.delete_group",
                resource_name=resource_name,
                contacts_deleted=delete_contacts,
            )
            return {"resourceName": resource_name, "deleted": True}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.delete_group",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def add_to_group(
        self,
        group_resource_name: str,
        contact_resource_names: list[str],
    ) -> dict[str, Any]:
        """Add contacts to a group.

        Args:
            group_resource_name: The group resource name.
            contact_resource_names: List of contact resource names to add.
        """
        try:
            result = self.execute(
                self.service.contactGroups()
                .members()
                .modify(
                    resourceName=group_resource_name,
                    body={"resourceNamesToAdd": contact_resource_names},
                )
            )

            output_success(
                operation="contacts.add_to_group",
                group_resource_name=group_resource_name,
                added_count=len(contact_resource_names),
                not_found=result.get("notFoundResourceNames", []),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.add_to_group",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def remove_from_group(
        self,
        group_resource_name: str,
        contact_resource_names: list[str],
    ) -> dict[str, Any]:
        """Remove contacts from a group.

        Args:
            group_resource_name: The group resource name.
            contact_resource_names: List of contact resource names to remove.
        """
        try:
            result = self.execute(
                self.service.contactGroups()
                .members()
                .modify(
                    resourceName=group_resource_name,
                    body={"resourceNamesToRemove": contact_resource_names},
                )
            )

            output_success(
                operation="contacts.remove_from_group",
                group_resource_name=group_resource_name,
                removed_count=len(contact_resource_names),
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.remove_from_group",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # CONTACT PHOTO OPERATIONS
    # =========================================================================

    def get_contact_photo(
        self,
        resource_name: str,
    ) -> dict[str, Any]:
        """Get a contact's photo URL.

        Args:
            resource_name: The contact resource name.
        """
        try:
            person = self.execute(
                self.service.people()
                .get(
                    resourceName=resource_name,
                    personFields="photos,names",
                )
            )

            photos = person.get("photos", [])
            photo_url = None
            if photos:
                photo_url = photos[0].get("url")

            output_success(
                operation="contacts.get_photo",
                resource_name=resource_name,
                name=self._get_name(person),
                has_photo=photo_url is not None,
                photo_url=photo_url,
            )
            return {"photo_url": photo_url}
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.get_photo",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def update_contact_photo(
        self,
        resource_name: str,
        photo_path: str,
    ) -> dict[str, Any]:
        """Update a contact's photo from a local file.

        Args:
            resource_name: The contact resource name.
            photo_path: Path to the image file (JPEG or PNG, max 2MB).
        """
        import base64
        import os

        try:
            # Read and encode the photo
            if not os.path.exists(photo_path):
                output_error(
                    error_code="NOT_FOUND",
                    operation="contacts.update_photo",
                    message=f"Photo file not found: {photo_path}",
                )
                raise SystemExit(ExitCode.NOT_FOUND)

            with open(photo_path, "rb") as f:
                photo_data = f.read()

            # Check file size (max 2MB)
            if len(photo_data) > 2 * 1024 * 1024:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="contacts.update_photo",
                    message="Photo file exceeds 2MB limit",
                )
                raise SystemExit(ExitCode.INVALID_ARGS)

            photo_bytes = base64.urlsafe_b64encode(photo_data).decode("utf-8")

            result = self.execute(
                self.service.people()
                .updateContactPhoto(
                    resourceName=resource_name,
                    body={"photoBytes": photo_bytes},
                )
            )

            output_success(
                operation="contacts.update_photo",
                resource_name=resource_name,
                photo_path=photo_path,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.update_photo",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def delete_contact_photo(
        self,
        resource_name: str,
    ) -> dict[str, Any]:
        """Delete a contact's photo.

        Args:
            resource_name: The contact resource name.
        """
        try:
            result = self.execute(
                self.service.people()
                .deleteContactPhoto(resourceName=resource_name)
            )

            output_success(
                operation="contacts.delete_photo",
                resource_name=resource_name,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.delete_photo",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # DIRECTORY (Google Workspace domain)
    # =========================================================================

    def search_directory(
        self,
        query: str,
        max_results: int = 10,
        read_mask: str = "names,emailAddresses,organizations",
    ) -> dict[str, Any]:
        """Search for people in the Google Workspace directory.

        Args:
            query: Search query string.
            max_results: Maximum number of results.
            read_mask: Comma-separated list of fields to return.
        """
        try:
            result = self.execute(
                self.service.people()
                .searchDirectoryPeople(
                    query=query,
                    pageSize=max_results,
                    readMask=read_mask,
                    sources=["DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE"],
                )
            )

            people = []
            for person in result.get("people", []):
                names = person.get("names", [{}])
                emails = person.get("emailAddresses", [{}])
                orgs = person.get("organizations", [{}])

                people.append({
                    "resource_name": person.get("resourceName"),
                    "name": names[0].get("displayName") if names else None,
                    "email": emails[0].get("value") if emails else None,
                    "organization": orgs[0].get("name") if orgs else None,
                    "title": orgs[0].get("title") if orgs else None,
                })

            output_success(
                operation="contacts.search_directory",
                query=query,
                count=len(people),
                people=people,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.search_directory",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    def list_directory(
        self,
        max_results: int = 100,
        read_mask: str = "names,emailAddresses,organizations",
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List all people in the Google Workspace directory.

        Args:
            max_results: Maximum number of results per page.
            read_mask: Comma-separated list of fields to return.
            page_token: Token for pagination.
        """
        try:
            params: dict[str, Any] = {
                "pageSize": max_results,
                "readMask": read_mask,
                "sources": ["DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE"],
            }
            if page_token:
                params["pageToken"] = page_token

            result = self.execute(
                self.service.people()
                .listDirectoryPeople(**params)
            )

            people = []
            for person in result.get("people", []):
                names = person.get("names", [{}])
                emails = person.get("emailAddresses", [{}])

                people.append({
                    "resource_name": person.get("resourceName"),
                    "name": names[0].get("displayName") if names else None,
                    "email": emails[0].get("value") if emails else None,
                })

            output_success(
                operation="contacts.list_directory",
                count=len(people),
                next_page_token=result.get("nextPageToken"),
                people=people,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.list_directory",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def batch_get_contacts(
        self,
        resource_names: list[str],
        read_mask: str = "names,emailAddresses,phoneNumbers,organizations",
    ) -> dict[str, Any]:
        """Get multiple contacts in a single request.

        Args:
            resource_names: List of contact resource names.
            read_mask: Comma-separated list of fields to return.
        """
        try:
            result = self.execute(
                self.service.people()
                .getBatchGet(
                    resourceNames=resource_names,
                    personFields=read_mask,
                )
            )

            contacts = []
            for response in result.get("responses", []):
                person = response.get("person", {})
                names = person.get("names", [{}])
                emails = person.get("emailAddresses", [{}])
                phones = person.get("phoneNumbers", [{}])

                contacts.append({
                    "resource_name": person.get("resourceName"),
                    "name": names[0].get("displayName") if names else None,
                    "email": emails[0].get("value") if emails else None,
                    "phone": phones[0].get("value") if phones else None,
                })

            output_success(
                operation="contacts.batch_get",
                count=len(contacts),
                contacts=contacts,
            )
            return result
        except HttpError as e:
            output_error(
                error_code="API_ERROR",
                operation="contacts.batch_get",
                message=f"People API error: {e.reason}",
            )
            raise SystemExit(ExitCode.API_ERROR)

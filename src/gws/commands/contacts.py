"""Contacts CLI commands."""

import typer
from typing import Annotated, Optional

from gws.commands._account import account_callback
from gws.services.contacts import ContactsService

app = typer.Typer(
    name="contacts",
    help="Google Contacts operations.",
    no_args_is_help=True,
    callback=account_callback,
)


@app.command("list")
def list_contacts(
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum contacts to return."),
    ] = 10,
    query: Annotated[
        Optional[str],
        typer.Option("--query", "-q", help="Search query."),
    ] = None,
) -> None:
    """List contacts."""
    service = ContactsService()
    service.list_contacts(max_results=max_results, query=query)


@app.command("get")
def get_contact(
    resource_name: Annotated[str, typer.Argument(help="Contact resource name (e.g., people/c123).")],
) -> None:
    """Get a specific contact."""
    service = ContactsService()
    service.get_contact(resource_name=resource_name)


@app.command("create")
def create_contact(
    given_name: Annotated[str, typer.Argument(help="First name.")],
    family_name: Annotated[
        Optional[str],
        typer.Option("--family", "-f", help="Last name."),
    ] = None,
    email: Annotated[
        Optional[str],
        typer.Option("--email", "-e", help="Email address."),
    ] = None,
    phone: Annotated[
        Optional[str],
        typer.Option("--phone", "-p", help="Phone number."),
    ] = None,
    organization: Annotated[
        Optional[str],
        typer.Option("--org", "-o", help="Organization name."),
    ] = None,
    title: Annotated[
        Optional[str],
        typer.Option("--title", "-t", help="Job title."),
    ] = None,
) -> None:
    """Create a new contact."""
    service = ContactsService()
    service.create_contact(
        given_name=given_name,
        family_name=family_name,
        email=email,
        phone=phone,
        organization=organization,
        title=title,
    )


@app.command("update")
def update_contact(
    resource_name: Annotated[str, typer.Argument(help="Contact resource name.")],
    given_name: Annotated[
        Optional[str],
        typer.Option("--given", "-g", help="New first name."),
    ] = None,
    family_name: Annotated[
        Optional[str],
        typer.Option("--family", "-f", help="New last name."),
    ] = None,
    email: Annotated[
        Optional[str],
        typer.Option("--email", "-e", help="New email address."),
    ] = None,
    phone: Annotated[
        Optional[str],
        typer.Option("--phone", "-p", help="New phone number."),
    ] = None,
) -> None:
    """Update an existing contact."""
    service = ContactsService()
    service.update_contact(
        resource_name=resource_name,
        given_name=given_name,
        family_name=family_name,
        email=email,
        phone=phone,
    )


@app.command("delete")
def delete_contact(
    resource_name: Annotated[str, typer.Argument(help="Contact resource name to delete.")],
) -> None:
    """Delete a contact."""
    service = ContactsService()
    service.delete_contact(resource_name=resource_name)


# ===== Contact Groups =====


@app.command("groups")
def list_groups(
    max_results: Annotated[
        int,
        typer.Option("--max", "-n", help="Maximum groups to return."),
    ] = 50,
) -> None:
    """List all contact groups."""
    service = ContactsService()
    service.list_groups(max_results=max_results)


@app.command("get-group")
def get_group(
    resource_name: Annotated[str, typer.Argument(help="Group resource name (e.g., contactGroups/abc123).")],
    no_members: Annotated[
        bool,
        typer.Option("--no-members", help="Don't include member list."),
    ] = False,
) -> None:
    """Get a contact group with its members."""
    service = ContactsService()
    service.get_group(resource_name=resource_name, include_members=not no_members)


@app.command("create-group")
def create_group(
    name: Annotated[str, typer.Argument(help="Name for the new group.")],
) -> None:
    """Create a new contact group."""
    service = ContactsService()
    service.create_group(name=name)


@app.command("update-group")
def update_group(
    resource_name: Annotated[str, typer.Argument(help="Group resource name.")],
    name: Annotated[str, typer.Argument(help="New name for the group.")],
) -> None:
    """Rename a contact group."""
    service = ContactsService()
    service.update_group(resource_name=resource_name, name=name)


@app.command("delete-group")
def delete_group(
    resource_name: Annotated[str, typer.Argument(help="Group resource name to delete.")],
    delete_contacts: Annotated[
        bool,
        typer.Option("--delete-contacts", help="Also delete contacts in the group."),
    ] = False,
) -> None:
    """Delete a contact group."""
    service = ContactsService()
    service.delete_group(resource_name=resource_name, delete_contacts=delete_contacts)


@app.command("add-to-group")
def add_to_group(
    group_resource_name: Annotated[str, typer.Argument(help="Group resource name.")],
    contacts: Annotated[str, typer.Argument(help="Comma-separated contact resource names to add.")],
) -> None:
    """Add contacts to a group."""
    contact_list = [c.strip() for c in contacts.split(",")]
    service = ContactsService()
    service.add_to_group(
        group_resource_name=group_resource_name,
        contact_resource_names=contact_list,
    )


@app.command("remove-from-group")
def remove_from_group(
    group_resource_name: Annotated[str, typer.Argument(help="Group resource name.")],
    contacts: Annotated[str, typer.Argument(help="Comma-separated contact resource names to remove.")],
) -> None:
    """Remove contacts from a group."""
    contact_list = [c.strip() for c in contacts.split(",")]
    service = ContactsService()
    service.remove_from_group(
        group_resource_name=group_resource_name,
        contact_resource_names=contact_list,
    )


# ===== Contact Photos =====


@app.command("get-photo")
def get_photo(
    resource_name: Annotated[str, typer.Argument(help="Contact resource name.")],
) -> None:
    """Get a contact's photo URL."""
    service = ContactsService()
    service.get_contact_photo(resource_name=resource_name)


@app.command("set-photo")
def set_photo(
    resource_name: Annotated[str, typer.Argument(help="Contact resource name.")],
    photo_path: Annotated[str, typer.Argument(help="Path to photo file (JPEG or PNG, max 2MB).")],
) -> None:
    """Set a contact's photo from a local file."""
    service = ContactsService()
    service.update_contact_photo(resource_name=resource_name, photo_path=photo_path)


@app.command("delete-photo")
def delete_photo(
    resource_name: Annotated[str, typer.Argument(help="Contact resource name.")],
) -> None:
    """Delete a contact's photo."""
    service = ContactsService()
    service.delete_contact_photo(resource_name=resource_name)

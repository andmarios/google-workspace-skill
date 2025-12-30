"""Contacts CLI commands."""

import typer
from typing import Annotated, Optional

from gws.services.contacts import ContactsService

app = typer.Typer(
    name="contacts",
    help="Google Contacts operations.",
    no_args_is_help=True,
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

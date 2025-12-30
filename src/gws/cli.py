"""Main CLI application for Google Workspace."""

import typer
from typing import Annotated, Optional

from gws import __version__
from gws.auth.oauth import AuthManager
from gws.config import Config
from gws.output import output_json, output_success, output_error
from gws.exceptions import ExitCode, AuthError

# Main app
app = typer.Typer(
    name="gws",
    help="Google Workspace CLI - Unified management for Google services.",
    no_args_is_help=True,
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        output_json({"version": __version__})
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Google Workspace CLI - Manage Docs, Sheets, Slides, Drive, Gmail, Calendar, and Contacts."""
    pass


# Auth command group
auth_app = typer.Typer(help="Authentication management.")
app.add_typer(auth_app, name="auth")


@auth_app.callback(invoke_without_command=True)
def auth_default(
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force re-authentication by deleting existing token."),
    ] = False,
) -> None:
    """Authenticate with Google services."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        auth_manager = AuthManager()

        if force:
            deleted = auth_manager.delete_token()
            if deleted:
                typer.echo("Deleted existing token. Starting fresh authentication...", err=True)

        credentials = auth_manager.get_credentials(force_refresh=force)

        if credentials and credentials.valid:
            output_success(
                operation="auth",
                message="Authentication successful. Token is valid and stored.",
                token_path=str(auth_manager.TOKEN_PATH),
            )
        else:
            output_error(
                error_code="AUTH_FAILED",
                operation="auth",
                message="Failed to obtain valid credentials.",
            )
            raise typer.Exit(ExitCode.AUTH_ERROR)

    except AuthError as e:
        output_error(
            error_code="AUTH_ERROR",
            operation="auth",
            message=str(e),
            details=e.details if hasattr(e, "details") else None,
        )
        raise typer.Exit(ExitCode.AUTH_ERROR)


@auth_app.command("status")
def auth_status() -> None:
    """Check authentication status (non-interactive)."""
    auth_manager = AuthManager()

    is_valid, status_msg, credentials = auth_manager.check_credentials()

    if is_valid:
        output_json({
            "status": "authenticated",
            "message": f"Token is valid ({status_msg}).",
            "token_path": str(auth_manager.TOKEN_PATH),
        })
    else:
        output_json({
            "status": "not_authenticated",
            "message": f"Authentication required: {status_msg}",
            "token_path": str(auth_manager.TOKEN_PATH),
            "hint": "Run 'gws auth' to authenticate.",
        })
        raise typer.Exit(ExitCode.AUTH_ERROR)


@auth_app.command("logout")
def auth_logout() -> None:
    """Remove stored authentication token."""
    auth_manager = AuthManager()

    if auth_manager.delete_token():
        output_success(
            operation="auth.logout",
            message="Token deleted successfully.",
        )
    else:
        output_json({
            "status": "success",
            "operation": "auth.logout",
            "message": "No token to delete.",
        })


# Config command group
config_app = typer.Typer(help="Service configuration management.")
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_default(ctx: typer.Context) -> None:
    """Manage service configuration."""
    if ctx.invoked_subcommand is None:
        # Default: show current config
        config = Config.load()
        output_json({
            "status": "success",
            "operation": "config",
            "enabled_services": config.enabled_services,
            "all_services": Config.ALL_SERVICES,
        })


@config_app.command("list")
def config_list() -> None:
    """List all services and their status."""
    config = Config.load()
    services = {
        service: service in config.enabled_services
        for service in Config.ALL_SERVICES
    }
    output_json({
        "status": "success",
        "operation": "config.list",
        "services": services,
        "enabled_count": len(config.enabled_services),
        "total_count": len(Config.ALL_SERVICES),
    })


@config_app.command("enable")
def config_enable(
    service: Annotated[str, typer.Argument(help="Service name to enable.")],
) -> None:
    """Enable a service."""
    config = Config.load()

    if service not in Config.ALL_SERVICES:
        output_error(
            error_code="INVALID_SERVICE",
            operation="config.enable",
            message=f"Unknown service: {service}",
            details={"valid_services": Config.ALL_SERVICES},
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    if config.enable_service(service):
        output_success(
            operation="config.enable",
            message=f"Service '{service}' enabled.",
            enabled_services=config.enabled_services,
        )
    else:
        output_json({
            "status": "success",
            "operation": "config.enable",
            "message": f"Service '{service}' was already enabled.",
            "enabled_services": config.enabled_services,
        })


@config_app.command("disable")
def config_disable(
    service: Annotated[str, typer.Argument(help="Service name to disable.")],
) -> None:
    """Disable a service."""
    config = Config.load()

    if service not in Config.ALL_SERVICES:
        output_error(
            error_code="INVALID_SERVICE",
            operation="config.disable",
            message=f"Unknown service: {service}",
            details={"valid_services": Config.ALL_SERVICES},
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    if config.disable_service(service):
        output_success(
            operation="config.disable",
            message=f"Service '{service}' disabled.",
            enabled_services=config.enabled_services,
        )
    else:
        output_json({
            "status": "success",
            "operation": "config.disable",
            "message": f"Service '{service}' was already disabled.",
            "enabled_services": config.enabled_services,
        })


@config_app.command("reset")
def config_reset() -> None:
    """Reset configuration to defaults (all services enabled)."""
    config = Config.load()
    config.enabled_services = list(Config.ALL_SERVICES)
    config.save()

    output_success(
        operation="config.reset",
        message="Configuration reset to defaults. All services enabled.",
        enabled_services=config.enabled_services,
    )


# Register service command groups
from gws.commands import drive, docs, sheets, slides, gmail, calendar, contacts, convert

app.add_typer(drive.app, name="drive")
app.add_typer(docs.app, name="docs")
app.add_typer(sheets.app, name="sheets")
app.add_typer(slides.app, name="slides")
app.add_typer(gmail.app, name="gmail")
app.add_typer(calendar.app, name="calendar")
app.add_typer(contacts.app, name="contacts")
app.add_typer(convert.app, name="convert")


if __name__ == "__main__":
    app()

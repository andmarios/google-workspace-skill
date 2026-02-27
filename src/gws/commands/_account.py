"""Shared Typer callback for --account flag."""

from typing import Annotated, Optional

import typer

from gws.config import Config
from gws.context import set_active_account
from gws.exceptions import AuthError, ExitCode
from gws.output import output_error


def account_callback(
    ctx: typer.Context,
    account: Annotated[
        Optional[str],
        typer.Option(
            "--account",
            "-a",
            envvar="GWS_ACCOUNT",
            help="Named account to use (overrides default).",
        ),
    ] = None,
) -> None:
    """Resolve and set the active account for this command invocation."""
    config = Config.load()
    try:
        resolved = config.resolve_account(account)
    except AuthError as e:
        output_error(
            error_code="INVALID_ARGS",
            operation="account",
            message=str(e),
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)
    set_active_account(resolved)

    # Enforce allowed_operations from per-account config
    if resolved:
        overrides = config.load_account_config(resolved)
        allowed = overrides.get("allowed_operations")
        if allowed is not None:
            service = ctx.info_name
            command = ctx.invoked_subcommand
            if command and (service not in allowed or command not in allowed[service]):
                allowed_cmds = allowed.get(service, [])
                output_error(
                    error_code="OPERATION_NOT_ALLOWED",
                    operation=f"{service}.{command}",
                    message=(
                        f"Operation '{command}' is not allowed for account '{resolved}'."
                        + (f" Allowed: {', '.join(allowed_cmds)}" if allowed_cmds else "")
                    ),
                )
                raise typer.Exit(ExitCode.INVALID_ARGS)

"""Auth command group for gws-cli (login, status, logout, server relay)."""

import os
from typing import Annotated, Any, Optional

import typer

from gws.auth.provider import resolve_auth_provider
from gws.config import Config
from gws.exceptions import AuthError, ExitCode
from gws.output import output_error, output_json, output_success

app = typer.Typer(
    help=(
        "Authentication management. Running 'gws-cli auth' with no subcommand "
        "logs you in using the configured mode: local OAuth (default) or the "
        "server relay. Run 'gws-cli auth status' to see the current mode, or "
        "'gws-cli config set-mode local|server' to change it."
    )
)


@app.callback(invoke_without_command=True)
def auth_default(
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force re-authentication by deleting existing token."),
    ] = False,
    headless: Annotated[
        bool,
        typer.Option(
            "--headless",
            help="Do not launch a local browser; use the provider's headless flow.",
        ),
    ] = False,
    account: Annotated[
        Optional[str],
        typer.Option(
            "--account",
            "-a",
            envvar="GWS_ACCOUNT",
            help="Named account to authenticate.",
        ),
    ] = None,
) -> None:
    """Authenticate with Google services."""
    if ctx.invoked_subcommand is not None:
        return

    # Note: this bare `auth` command logs in using the configured mode
    # (local OAuth or server relay), resolved per-account by
    # resolve_auth_provider(). See `auth status` to inspect the active mode.
    try:
        provider = resolve_auth_provider(account=account)

        if force:
            deleted = provider.delete_token()
            if deleted:
                typer.echo("Deleted existing token. Starting fresh authentication...", err=True)

        credentials = provider.get_credentials(force_refresh=force, headless=headless)

        if credentials and credentials.valid:
            result: dict[str, Any] = {
                "operation": "auth",
                "message": "Authentication successful. Token is valid and stored.",
            }
            result["token_path"] = str(provider.TOKEN_PATH)
            if provider.account_name:
                result["account"] = provider.account_name
            output_success(**result)
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


@app.command("status")
def auth_status(
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account to check."),
    ] = None,
) -> None:
    """Check authentication status (non-interactive)."""
    provider = resolve_auth_provider(account=account)

    # Resolve the effective auth mode so it is always visible in the output
    # (this is the question 'will auth go local or relay?' — see #UX).
    config = Config.load()
    resolved = config.resolve_account(account)
    effective = config.load_effective_config(resolved)

    auth_info: dict[str, Any] = {"mode": effective.mode}
    if effective.mode == "server":
        server_url = os.environ.get("GWS_SERVER_URL") or effective.server_url
        if server_url:
            auth_info["server_url"] = server_url
        if effective.server_provider:
            auth_info["provider"] = effective.server_provider

    is_valid, status_msg, credentials = provider.check_credentials()

    if is_valid:
        result: dict[str, Any] = {
            "status": "authenticated",
            "message": f"Token is valid ({status_msg}).",
        }
        result["token_path"] = str(provider.TOKEN_PATH)
        if provider.account_name:
            result["account"] = provider.account_name
        result.update(auth_info)
        output_json(result)
    else:
        hint = "Run 'gws-cli auth' to authenticate."
        if effective.mode == "server":
            hint = (
                "Run 'gws-cli auth' (server mode) or 'gws-cli auth server-login' "
                "to authenticate."
            )
        result = {
            "status": "not_authenticated",
            "message": f"Authentication required: {status_msg}",
            "hint": hint,
        }
        result["token_path"] = str(provider.TOKEN_PATH)
        if provider.account_name:
            result["account"] = provider.account_name
        result.update(auth_info)
        output_json(result)
        raise typer.Exit(ExitCode.AUTH_ERROR)


@app.command("logout")
def auth_logout(
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account to log out."),
    ] = None,
) -> None:
    """Remove stored authentication token."""
    provider = resolve_auth_provider(account=account)

    if provider.delete_token():
        result: dict[str, Any] = {
            "operation": "auth.logout",
            "message": "Token deleted successfully.",
        }
        if provider.account_name:
            result["account"] = provider.account_name
        output_success(**result)
    else:
        result = {
            "status": "success",
            "operation": "auth.logout",
            "message": "No token to delete.",
        }
        if provider.account_name:
            result["account"] = provider.account_name
        output_json(result)


@app.command("server-login")
def auth_server_login(
    device: Annotated[
        bool,
        typer.Option("--device", help="Use device flow (for headless/SSH environments)."),
    ] = False,
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account."),
    ] = None,
) -> None:
    """Authenticate to the oauth-token-relay server.

    Uses OAuth 2.1 PKCE flow by default.
    Use --device for headless/SSH environments.
    """
    from gws.auth.server import ServerAuthProvider

    config = Config.load()
    resolved_account = config.resolve_account(account)
    effective = config.load_effective_config(resolved_account)
    server_url = os.environ.get("GWS_SERVER_URL") or effective.server_url
    if not server_url:
        output_error(
            error_code="NOT_CONFIGURED",
            operation="auth.server-login",
            message="No server URL configured.",
            details="Run 'gws-cli config set-mode server --url <url>' first.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    try:
        provider = ServerAuthProvider(
            server_url=server_url,
            account=resolved_account,
            config=effective,
        )
        provider.server_login(device_flow=device)
        output_success(
            operation="auth.server-login",
            message="Server authentication successful.",
            server_url=server_url,
        )
    except AuthError as e:
        output_error(
            error_code="AUTH_ERROR",
            operation="auth.server-login",
            message=str(e),
            details=e.details if hasattr(e, "details") else None,
        )
        raise typer.Exit(ExitCode.AUTH_ERROR)


@app.command("server-status")
def auth_server_status(
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account."),
    ] = None,
) -> None:
    """Check connection and auth status with the relay server."""
    from gws.auth.server import ServerAuthProvider

    config = Config.load()
    resolved_account = config.resolve_account(account)
    effective = config.load_effective_config(resolved_account)
    server_url = os.environ.get("GWS_SERVER_URL") or effective.server_url
    if not server_url:
        output_error(
            error_code="NOT_CONFIGURED",
            operation="auth.server-status",
            message="No server URL configured. Mode is 'local'.",
            details="Run 'gws-cli config set-mode server --url <url>' to switch to server mode.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    provider = ServerAuthProvider(server_url=server_url, account=resolved_account, config=effective)
    status = provider.server_status()
    output_json({"status": "success", "operation": "auth.server-status", **status})


@app.command("server-logout")
def auth_server_logout(
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account."),
    ] = None,
) -> None:
    """Revoke server authentication and remove server token."""
    from gws.auth.server import ServerAuthProvider

    config = Config.load()
    resolved_account = config.resolve_account(account)
    effective = config.load_effective_config(resolved_account)
    server_url = os.environ.get("GWS_SERVER_URL") or effective.server_url
    if not server_url:
        output_error(
            error_code="NOT_CONFIGURED",
            operation="auth.server-logout",
            message="No server URL configured.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    provider = ServerAuthProvider(server_url=server_url, account=resolved_account, config=effective)
    provider.server_logout()
    output_success(
        operation="auth.server-logout",
        message="Server token revoked and removed.",
    )


@app.command("import-credentials")
def auth_import_credentials(
    path: Annotated[
        str,
        typer.Argument(help="Path to client_secret.json from Google Cloud Console."),
    ],
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account."),
    ] = None,
) -> None:
    """Import OAuth client credentials and encrypt them for secure storage."""
    import json
    from pathlib import Path

    from gws.auth.oauth import LocalAuthProvider
    from gws.crypto import save_encrypted

    source = Path(path).expanduser()
    if not source.exists():
        output_error(
            error_code="NOT_FOUND",
            operation="auth.import-credentials",
            message=f"File not found: {source}",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    try:
        with open(source) as f:
            client_config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        output_error(
            error_code="INVALID_FILE",
            operation="auth.import-credentials",
            message=f"Cannot read file: {e}",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    # Validate structure
    if "installed" not in client_config and "web" not in client_config:
        output_error(
            error_code="INVALID_FORMAT",
            operation="auth.import-credentials",
            message="File must contain 'installed' or 'web' key (Google OAuth client config).",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    config = Config.load()
    key = config.get_encryption_key()
    dest = LocalAuthProvider.CREDENTIALS_PATH
    save_encrypted(dest, client_config, key)

    output_success(
        operation="auth.import-credentials",
        message="Client credentials imported and encrypted.",
        credentials_path=str(dest.parent / (dest.name + ".enc")) if key else str(dest),
    )

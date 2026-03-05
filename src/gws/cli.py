"""Main CLI application for Google Workspace."""

import os

import typer
from typing import Annotated, Any, Optional

from gws import __version__
from gws.auth.provider import resolve_auth_provider
from gws.config import Config
from gws.output import output_json, output_success, output_error
from gws.exceptions import ExitCode, AuthError

# Main app
app = typer.Typer(
    name="gws-cli",
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


# ── Auth command group ─────────────────────────────────────────────────
auth_app = typer.Typer(help="Authentication management.")
app.add_typer(auth_app, name="auth")


@auth_app.callback(invoke_without_command=True)
def auth_default(
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force re-authentication by deleting existing token."),
    ] = False,
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account to authenticate."),
    ] = None,
) -> None:
    """Authenticate with Google services."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        provider = resolve_auth_provider(account=account)

        if force:
            deleted = provider.delete_token()
            if deleted:
                typer.echo("Deleted existing token. Starting fresh authentication...", err=True)

        credentials = provider.get_credentials(force_refresh=force)

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


@auth_app.command("status")
def auth_status(
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", envvar="GWS_ACCOUNT", help="Named account to check."),
    ] = None,
) -> None:
    """Check authentication status (non-interactive)."""
    provider = resolve_auth_provider(account=account)

    is_valid, status_msg, credentials = provider.check_credentials()

    if is_valid:
        result: dict[str, Any] = {
            "status": "authenticated",
            "message": f"Token is valid ({status_msg}).",
        }
        result["token_path"] = str(provider.TOKEN_PATH)
        if provider.account_name:
            result["account"] = provider.account_name
        output_json(result)
    else:
        result = {
            "status": "not_authenticated",
            "message": f"Authentication required: {status_msg}",
            "hint": "Run 'gws-cli auth' to authenticate.",
        }
        result["token_path"] = str(provider.TOKEN_PATH)
        if provider.account_name:
            result["account"] = provider.account_name
        output_json(result)
        raise typer.Exit(ExitCode.AUTH_ERROR)


@auth_app.command("logout")
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


@auth_app.command("server-login")
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
        provider = ServerAuthProvider(server_url=server_url, account=resolved_account, config=effective)
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


@auth_app.command("server-status")
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


@auth_app.command("server-logout")
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


@auth_app.command("import-credentials")
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


# ── Account command group ──────────────────────────────────────────────
account_app = typer.Typer(help="Multi-account management.")
app.add_typer(account_app, name="account")


@account_app.command("add")
def account_add(
    name: Annotated[str, typer.Argument(help="Account name (e.g., 'work', 'personal').")],
    display_name: Annotated[
        Optional[str],
        typer.Option("--name", help="Display name for From field in emails."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing account."),
    ] = False,
    no_auth: Annotated[
        bool,
        typer.Option("--no-auth", help="Register account without triggering authentication."),
    ] = False,
) -> None:
    """Register and authenticate a new named account."""
    config = Config.load()

    if config.accounts and name in config.accounts.entries and not force:
        output_error(
            error_code="ACCOUNT_EXISTS",
            operation="account.add",
            message=f"Account '{name}' already exists. Use --force to overwrite.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    try:
        Config.validate_account_name(name)
    except ValueError as e:
        output_error(
            error_code="INVALID_ARGS",
            operation="account.add",
            message=str(e),
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    config.add_account(name, display_name=display_name or "")

    if no_auth:
        output_success(
            operation="account.add",
            message=f"Account '{name}' registered (authentication deferred).",
            account=name,
            is_default=config.accounts.default_account == name if config.accounts else False,
            hint="Run 'gws-cli auth -a {name}' or use any command with '-a {name}' to authenticate.".format(name=name),
        )
        return

    # Trigger authentication for the new account
    try:
        provider = resolve_auth_provider(account=name, config=config)
        credentials = provider.get_credentials()

        if credentials and credentials.valid:
            result: dict[str, Any] = {
                "operation": "account.add",
                "message": f"Account '{name}' added and authenticated.",
                "account": name,
                "is_default": config.accounts.default_account == name if config.accounts else False,
            }
            result["token_path"] = str(provider.TOKEN_PATH)
            output_success(**result)
        else:
            # Auth didn't produce valid credentials — keep account, warn user
            output_success(
                operation="account.add",
                message=f"Account '{name}' registered but authentication incomplete.",
                account=name,
                is_default=config.accounts.default_account == name if config.accounts else False,
                hint=f"Authenticate later with 'gws-cli auth -a {name}' or any command with '-a {name}'.",
            )
    except AuthError as e:
        # Auth failed — keep account registered, warn user
        output_success(
            operation="account.add",
            message=f"Account '{name}' registered (authentication skipped: {e}).",
            account=name,
            is_default=config.accounts.default_account == name if config.accounts else False,
            hint=f"Authenticate later with 'gws-cli auth -a {name}' or any command with '-a {name}'.",
        )


@account_app.command("update")
def account_update(
    name: Annotated[str, typer.Argument(help="Account name to update.")],
    display_name: Annotated[
        Optional[str],
        typer.Option("--name", help="Display name for From field in emails."),
    ] = None,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email address metadata."),
    ] = None,
) -> None:
    """Update account metadata (display name, email)."""
    config = Config.load()

    if display_name is None and email is None:
        output_error(
            error_code="INVALID_ARGS",
            operation="account.update",
            message="Provide at least one of --name or --email.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    if config.update_account(name, display_name=display_name, email=email):
        updated = {}
        if display_name is not None:
            updated["name"] = display_name
        if email is not None:
            updated["email"] = email
        output_success(
            operation="account.update",
            message=f"Account '{name}' updated.",
            account=name,
            **updated,
        )
    else:
        output_error(
            error_code="NOT_FOUND",
            operation="account.update",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)


@account_app.command("remove")
def account_remove(
    name: Annotated[str, typer.Argument(help="Account name to remove.")],
) -> None:
    """Remove a named account and its credentials."""
    config = Config.load()

    if config.remove_account(name):
        output_success(
            operation="account.remove",
            message=f"Account '{name}' removed.",
            account=name,
        )
    else:
        output_error(
            error_code="NOT_FOUND",
            operation="account.remove",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)


@account_app.command("list")
def account_list() -> None:
    """List all configured accounts."""
    config = Config.load()
    accounts = config.list_accounts()

    output_json({
        "status": "success",
        "operation": "account.list",
        "accounts": accounts,
        "count": len(accounts),
        "default": config.accounts.default_account if config.accounts else None,
    })


@account_app.command("default")
def account_default(
    name: Annotated[str, typer.Argument(help="Account name to set as default.")],
) -> None:
    """Set the default account."""
    config = Config.load()

    if config.set_default_account(name):
        output_success(
            operation="account.default",
            message=f"Default account set to '{name}'.",
            account=name,
        )
    else:
        output_error(
            error_code="NOT_FOUND",
            operation="account.default",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)


@account_app.command("config")
def account_config_show(
    name: Annotated[str, typer.Argument(help="Account name.")],
) -> None:
    """Show effective configuration for an account."""
    config = Config.load()
    if not config.accounts or name not in config.accounts.entries:
        output_error(
            error_code="NOT_FOUND",
            operation="account.config",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)

    effective = config.load_effective_config(name)
    overrides = config.load_account_config(name)

    output_json({
        "status": "success",
        "operation": "account.config",
        "account": name,
        "effective_config": {
            "enabled_services": effective.enabled_services,
            "kroki_url": effective.kroki_url,
            "security_enabled": effective.security_enabled,
        },
        "has_overrides": bool(overrides),
        "overrides": overrides if overrides else None,
    })


@account_app.command("config-enable")
def account_config_enable(
    name: Annotated[str, typer.Argument(help="Account name.")],
    service: Annotated[str, typer.Argument(help="Service to enable for this account.")],
) -> None:
    """Enable a service for a specific account (override)."""
    config = Config.load()

    if not config.accounts or name not in config.accounts.entries:
        output_error(
            error_code="NOT_FOUND",
            operation="account.config.enable",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)

    if service not in Config.ALL_SERVICES:
        output_error(
            error_code="INVALID_SERVICE",
            operation="account.config.enable",
            message=f"Unknown service: {service}",
            details={"valid_services": Config.ALL_SERVICES},
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    overrides = config.load_account_config(name)
    services = overrides.get("enabled_services", config.enabled_services.copy())
    if service not in services:
        services.append(service)
    overrides["enabled_services"] = services
    config.save_account_config(name, overrides)

    output_success(
        operation="account.config.enable",
        account=name,
        message=f"Service '{service}' enabled for account '{name}'.",
        enabled_services=services,
    )


@account_app.command("config-disable")
def account_config_disable(
    name: Annotated[str, typer.Argument(help="Account name.")],
    service: Annotated[str, typer.Argument(help="Service to disable for this account.")],
) -> None:
    """Disable a service for a specific account (override)."""
    config = Config.load()

    if not config.accounts or name not in config.accounts.entries:
        output_error(
            error_code="NOT_FOUND",
            operation="account.config.disable",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)

    if service not in Config.ALL_SERVICES:
        output_error(
            error_code="INVALID_SERVICE",
            operation="account.config.disable",
            message=f"Unknown service: {service}",
            details={"valid_services": Config.ALL_SERVICES},
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    overrides = config.load_account_config(name)
    services = overrides.get("enabled_services", config.enabled_services.copy())
    if service in services:
        services.remove(service)
    overrides["enabled_services"] = services
    config.save_account_config(name, overrides)

    output_success(
        operation="account.config.disable",
        account=name,
        message=f"Service '{service}' disabled for account '{name}'.",
        enabled_services=services,
    )


@account_app.command("set-readonly")
def account_set_readonly(
    name: Annotated[str, typer.Argument(help="Account name.")],
) -> None:
    """Restrict an account to read-only operations."""
    config = Config.load()

    if not config.accounts or name not in config.accounts.entries:
        output_error(
            error_code="NOT_FOUND",
            operation="account.set-readonly",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)

    overrides = config.load_account_config(name)
    overrides["allowed_operations"] = Config.READ_ONLY_OPS
    overrides["read_only"] = True
    config.save_account_config(name, overrides)

    from gws.crypto import delete_encrypted
    token_path = config.get_account_dir(name) / "token.json"
    delete_encrypted(token_path)

    output_success(
        operation="account.set-readonly",
        account=name,
        message=f"Account '{name}' is now read-only.",
        allowed_operations=Config.READ_ONLY_OPS,
        note="Token cleared — next API call will re-authenticate with read-only scopes.",
    )


@account_app.command("unset-readonly")
def account_unset_readonly(
    name: Annotated[str, typer.Argument(help="Account name.")],
) -> None:
    """Remove read-only restriction from an account."""
    config = Config.load()

    if not config.accounts or name not in config.accounts.entries:
        output_error(
            error_code="NOT_FOUND",
            operation="account.unset-readonly",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)

    overrides = config.load_account_config(name)
    if "allowed_operations" in overrides:
        del overrides["allowed_operations"]
    if "read_only" in overrides:
        del overrides["read_only"]
    if overrides:
        config.save_account_config(name, overrides)
    else:
        config.clear_account_config(name)

    from gws.crypto import delete_encrypted
    token_path = config.get_account_dir(name) / "token.json"
    delete_encrypted(token_path)

    output_success(
        operation="account.unset-readonly",
        account=name,
        message=f"Account '{name}' is no longer read-only. All operations allowed.",
        note="Token cleared — next API call will re-authenticate with full scopes.",
    )


@account_app.command("config-reset")
def account_config_reset(
    name: Annotated[str, typer.Argument(help="Account name.")],
) -> None:
    """Remove all per-account overrides (inherit global config)."""
    config = Config.load()

    if not config.accounts or name not in config.accounts.entries:
        output_error(
            error_code="NOT_FOUND",
            operation="account.config.reset",
            message=f"Account '{name}' not found.",
        )
        raise typer.Exit(ExitCode.NOT_FOUND)

    config.clear_account_config(name)

    output_success(
        operation="account.config.reset",
        account=name,
        message=f"Per-account overrides cleared for '{name}'. Using global config.",
    )


# ── Config command group ───────────────────────────────────────────────
config_app = typer.Typer(help="Service configuration management.")
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_default(ctx: typer.Context) -> None:
    """Manage service configuration."""
    if ctx.invoked_subcommand is None:
        # Default: show current config
        config = Config.load()
        result: dict[str, Any] = {
            "status": "success",
            "operation": "config",
            "mode": config.mode,
            "enabled_services": config.enabled_services,
            "all_services": Config.ALL_SERVICES,
            "kroki_url": config.kroki_url,
            "security_enabled": config.security_enabled,
            "allowlisted_documents": config.allowlisted_documents,
            "allowlisted_emails": config.allowlisted_emails,
            "disabled_security_services": config.disabled_security_services,
            "disabled_security_operations": config.disabled_security_operations,
        }
        if config.server_url:
            result["server_url"] = config.server_url
        if config.is_multi_account:
            result["accounts"] = config.list_accounts()
            result["default_account"] = config.accounts.default_account if config.accounts else None
        output_json(result)


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
    config.kroki_url = Config.DEFAULT_KROKI_URL
    config.save()

    output_success(
        operation="config.reset",
        message="Configuration reset to defaults.",
        enabled_services=config.enabled_services,
        kroki_url=config.kroki_url,
    )


@config_app.command("set-kroki")
def config_set_kroki(
    url: Annotated[str, typer.Argument(help="Kroki server URL (e.g., http://localhost:8000).")],
) -> None:
    """Set the Kroki server URL for diagram rendering.

    Default is https://kroki.io (public server).
    Set a custom URL if you run a local Kroki instance.
    """
    config = Config.load()
    config.kroki_url = url.rstrip("/")
    config.save()

    output_success(
        operation="config.set-kroki",
        message=f"Kroki URL set to: {config.kroki_url}",
        kroki_url=config.kroki_url,
    )


@config_app.command("allowlist-add")
def config_allowlist_add(
    type_: Annotated[str, typer.Argument(help="Type: 'docs' or 'email'.", metavar="TYPE")],
    id_: Annotated[str, typer.Argument(help="Document ID or email message ID.", metavar="ID")],
) -> None:
    """Add an ID to the security allowlist.

    Allowlisted documents and emails skip security wrapping.

    Examples:
        gws-cli config allowlist-add docs 1abc2def3ghi
        gws-cli config allowlist-add email 18fd9a8b2c3d4e5f
    """
    config = Config.load()

    if type_ == "docs":
        if id_ not in config.allowlisted_documents:
            config.allowlisted_documents.append(id_)
            config.save()
            output_success(
                operation="config.allowlist-add",
                type="docs",
                id=id_,
                message=f"Document {id_} added to allowlist.",
                allowlisted_documents=config.allowlisted_documents,
            )
        else:
            output_json({
                "status": "success",
                "operation": "config.allowlist-add",
                "message": f"Document {id_} already in allowlist.",
            })
    elif type_ == "email":
        if id_ not in config.allowlisted_emails:
            config.allowlisted_emails.append(id_)
            config.save()
            output_success(
                operation="config.allowlist-add",
                type="email",
                id=id_,
                message=f"Email {id_} added to allowlist.",
                allowlisted_emails=config.allowlisted_emails,
            )
        else:
            output_json({
                "status": "success",
                "operation": "config.allowlist-add",
                "message": f"Email {id_} already in allowlist.",
            })
    else:
        output_error(
            error_code="INVALID_TYPE",
            operation="config.allowlist-add",
            message=f"Unknown type: {type_}. Use 'docs' or 'email'.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)


@config_app.command("allowlist-remove")
def config_allowlist_remove(
    type_: Annotated[str, typer.Argument(help="Type: 'docs' or 'email'.", metavar="TYPE")],
    id_: Annotated[str, typer.Argument(help="Document ID or email message ID.", metavar="ID")],
) -> None:
    """Remove an ID from the security allowlist.

    Examples:
        gws-cli config allowlist-remove docs 1abc2def3ghi
        gws-cli config allowlist-remove email 18fd9a8b2c3d4e5f
    """
    config = Config.load()

    if type_ == "docs":
        if id_ in config.allowlisted_documents:
            config.allowlisted_documents.remove(id_)
            config.save()
            output_success(
                operation="config.allowlist-remove",
                type="docs",
                id=id_,
                message=f"Document {id_} removed from allowlist.",
                allowlisted_documents=config.allowlisted_documents,
            )
        else:
            output_json({
                "status": "success",
                "operation": "config.allowlist-remove",
                "message": f"Document {id_} was not in allowlist.",
            })
    elif type_ == "email":
        if id_ in config.allowlisted_emails:
            config.allowlisted_emails.remove(id_)
            config.save()
            output_success(
                operation="config.allowlist-remove",
                type="email",
                id=id_,
                message=f"Email {id_} removed from allowlist.",
                allowlisted_emails=config.allowlisted_emails,
            )
        else:
            output_json({
                "status": "success",
                "operation": "config.allowlist-remove",
                "message": f"Email {id_} was not in allowlist.",
            })
    else:
        output_error(
            error_code="INVALID_TYPE",
            operation="config.allowlist-remove",
            message=f"Unknown type: {type_}. Use 'docs' or 'email'.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)


@config_app.command("allowlist-list")
def config_allowlist_list() -> None:
    """List all IDs in the security allowlist."""
    config = Config.load()
    output_success(
        operation="config.allowlist-list",
        allowlisted_documents=config.allowlisted_documents,
        allowlisted_emails=config.allowlisted_emails,
        total_count=len(config.allowlisted_documents) + len(config.allowlisted_emails),
    )


@config_app.command("set-mode")
def config_set_mode(
    mode: Annotated[str, typer.Argument(help="Auth mode: 'local' or 'server'.")],
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="Server URL (required for server mode)."),
    ] = None,
    provider: Annotated[
        Optional[str],
        typer.Option("--provider", help="Relay provider name (e.g. 'google-workspace'). Required when server has multiple providers."),
    ] = None,
    account: Annotated[
        Optional[str],
        typer.Option("--account", "-a", help="Set mode for a specific account only."),
    ] = None,
) -> None:
    """Switch authentication mode between local and server.

    Local mode: uses client_secret.json for direct OAuth.
    Server mode: delegates auth to an oauth-token-relay server.

    When --account is specified, the mode is stored as a per-account override.
    Without --account, it sets the global default for all accounts.

    Examples:
        gws-cli config set-mode server --url https://auth.company.com
        gws-cli config set-mode server --url https://auth.company.com -a work --provider google-work
        gws-cli config set-mode local -a personal
    """
    if mode not in ("local", "server"):
        output_error(
            error_code="INVALID_ARGS",
            operation="config.set-mode",
            message=f"Invalid mode: {mode}. Use 'local' or 'server'.",
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    if mode == "server" and not url:
        # Check if there's already a global server_url to inherit
        config = Config.load()
        if not config.server_url:
            output_error(
                error_code="INVALID_ARGS",
                operation="config.set-mode",
                message="Server mode requires --url (no global server_url to inherit).",
            )
            raise typer.Exit(ExitCode.INVALID_ARGS)

    config = Config.load()

    if account:
        # Auto-create account if it doesn't exist (convenience for setup)
        if account not in (config.accounts.entries if config.accounts else {}):
            try:
                Config.validate_account_name(account)
            except ValueError as e:
                output_error(
                    error_code="INVALID_ARGS",
                    operation="config.set-mode",
                    message=str(e),
                )
                raise typer.Exit(ExitCode.INVALID_ARGS)
            config.add_account(account)

        overrides = config.load_account_config(account)
        overrides["mode"] = mode
        if url:
            overrides["server_url"] = url.rstrip("/")
        elif mode == "local":
            overrides.pop("server_url", None)
        if provider is not None:
            overrides["server_provider"] = provider
        elif mode == "local":
            overrides.pop("server_provider", None)
        config.save_account_config(account, overrides)
    else:
        # Global config
        config.mode = mode
        config.server_url = url.rstrip("/") if url else None
        config.server_provider = provider
        config.save()

    result: dict[str, Any] = {
        "operation": "config.set-mode",
        "message": f"Auth mode set to '{mode}'.",
        "mode": mode,
    }
    if account:
        result["account"] = account
        result["scope"] = "per-account"
    else:
        result["scope"] = "global"
    if url:
        result["server_url"] = url.rstrip("/") if url else None
    if provider:
        result["server_provider"] = provider
    output_success(**result)


# Register service command groups
from gws.commands import drive, docs, sheets, slides, gmail, calendar, contacts, convert  # noqa: E402

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

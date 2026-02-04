# Claude Code Development Guide

This file provides context for Claude when working on this codebase.

## Project Overview

This is a **Claude Code skill** that provides Google Workspace integration. The skill exposes a CLI (`gws`) that Claude invokes to interact with Google APIs.

**Key distinction:**
- `SKILL.md` - Instructions for Claude when **using** the skill (overview, navigation)
- `reference/*.md` - Service-specific API documentation (docs, sheets, slides, etc.)
- `SKILL-advanced.md` - Design best practices, content creation, API efficiency
- `CLAUDE.md` - Instructions for Claude when **developing** the skill (this file)

## Architecture

```
src/gws/
├── cli.py              # Main Typer app, auth/config/account commands
├── config.py           # Service config + multi-account registry
├── context.py          # Runtime active account state
├── output.py           # JSON output formatting (output_success, output_error)
├── exceptions.py       # Exit codes (0-4)
├── auth/
│   ├── oauth.py        # OAuth loopback flow (ports 8080-8099), account-aware token paths
│   └── scopes.py       # Per-service Google API scopes
├── services/
│   ├── base.py         # BaseService class (handles auth, builds API client, account context)
│   ├── drive.py        # Google Drive operations
│   ├── docs.py         # Google Docs operations
│   ├── sheets.py       # Google Sheets operations
│   ├── slides.py       # Google Slides operations
│   ├── gmail.py        # Gmail operations
│   ├── calendar.py     # Google Calendar operations
│   ├── contacts.py     # People API operations
│   └── convert.py      # Markdown → Docs/Slides/PDF converter
├── commands/
│   ├── _account.py     # Shared --account/-a Typer callback for all service commands
│   ├── docs.py         # Typer CLI commands (mirror services/)
│   └── ...
└── utils/
    ├── colors.py       # Hex color → RGB conversion for Sheets/Slides
    ├── diagrams.py     # Kroki API diagram rendering
    └── markdown.py     # Markdown parser for slides conversion
```

## Key Patterns

### Service Structure

Each service follows this pattern:

```python
class SomeService(BaseService):
    SERVICE_NAME = "some_api"  # Google API name
    VERSION = "v1"             # API version

    def operation(self, ...) -> dict[str, Any]:
        try:
            result = self.service.resource().method(...).execute()
            output_success(operation="service.op", ...)
            return result
        except HttpError as e:
            output_error(error_code="API_ERROR", operation="service.op", message=...)
            raise SystemExit(ExitCode.API_ERROR)
```

### Output Format

All commands output JSON via `output_success()` or `output_error()`:

```python
# Success
output_success(operation="docs.read", document_id=doc_id, content=text)

# Error
output_error(error_code="NOT_FOUND", operation="docs.read", message="Document not found")
```

### CLI Commands

Commands are thin wrappers that parse args and call service methods:

```python
@app.command("read")
def read_document(document_id: Annotated[str, typer.Argument(...)]) -> None:
    service = DocsService()
    service.read_document(document_id=document_id)
```

## Running and Testing

```bash
# Run CLI directly
uv run gws --help
uv run gws docs read <doc_id>

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check .
```

## Credentials

Stored in `~/.claude/.google-workspace/`:
- `client_secret.json` - OAuth client credentials (user provides, shared across accounts)
- `token.json` - Access token (auto-generated, legacy single-account mode)
- `gws_config.json` - Configuration (enabled services, Kroki URL, accounts registry)

### Multi-Account Storage

When multi-account mode is active, per-account data is stored under `accounts/`:

```
~/.claude/.google-workspace/
├── client_secret.json              # Shared OAuth client (unchanged)
├── token.json                      # Legacy token (kept, used when no accounts)
├── gws_config.json                 # Global config + accounts registry
└── accounts/
    ├── work/
    │   ├── token.json              # Account-specific token
    │   └── config.json             # Per-account overrides (optional)
    └── personal/
        └── token.json
```

## Multi-Account Architecture

Multi-account is opt-in. When no accounts are configured, the CLI behaves exactly as before (legacy mode).

### Key concepts

- **Accounts registry**: Stored in `gws_config.json` under the `accounts` key. When `None`/absent, legacy mode is active.
- **Account resolution priority**: `--account` flag > `GWS_ACCOUNT` env var > default account > None (legacy)
- **Per-account config**: Optional `config.json` in account directory. Fields override global config (e.g., `enabled_services`).
- **Context module** (`context.py`): Module-level `_active_account` state. The `account_callback` in `_account.py` resolves the active account at command invocation and stores it. Both `BaseService` and `output_external_content` read it.
- **Account name validation**: Names must match `^[a-zA-Z0-9_-]+$` to prevent path traversal.

### CLI commands

```bash
# Account management
gws account add <name> [--force]     # Register + authenticate
gws account remove <name>            # Delete account + credentials
gws account list                     # Show all accounts with default marker
gws account default <name>           # Change default account

# Per-account config overrides
gws account config <name>            # Show effective config
gws account config-enable <name> <service>   # Enable service for account
gws account config-disable <name> <service>  # Disable service for account
gws account config-reset <name>      # Remove all overrides (inherit global)

# Using accounts with any command
gws docs read <id> --account personal
GWS_ACCOUNT=personal gws docs read <id>

# Auth commands support --account
gws auth --account work
gws auth status --account work
gws auth logout --account work
```

## Common Tasks

### Adding a New Operation

1. Add method to service class in `src/gws/services/<service>.py`
2. Add CLI command in `src/gws/commands/<service>.py`
3. Document in the appropriate reference file (`reference/<service>.md`)

### Adding a New Service

1. Create `src/gws/services/newservice.py` extending `BaseService`
2. Create `src/gws/commands/newservice.py` with Typer app
3. Register in `src/gws/cli.py`: `app.add_typer(newservice.app, name="newservice")`
4. Add scopes to `src/gws/auth/scopes.py`
5. Add to `Config.ALL_SERVICES` in `src/gws/config.py`
6. Create `reference/newservice.md` with API documentation
7. Add navigation entry in `SKILL.md` Services Reference table

## Important Notes

- **Exit codes**: Use `ExitCode` enum (0=success, 1=auth, 2=API, 3=args, 4=not found)
- **Shell escaping**: Claude Code sandbox escapes `!` as `\!`. Use `_unescape_text()` for user content.
- **HTML email default**: Gmail sends HTML by default (`--plain` for plain text)
- **Diagram rendering**: Uses Kroki API. Mermaid gets `default` theme injected automatically (configurable via `--mermaid-theme`).
- **Image sizing**: Docs converter limits images to 450pt width, 600pt height

## Dependencies

Key packages:
- `typer` - CLI framework
- `google-api-python-client` - Google API client
- `google-auth-oauthlib` - OAuth flow
- `httpx` - HTTP client (for Kroki API)

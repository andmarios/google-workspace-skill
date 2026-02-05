"""Configuration management for GWS CLI."""

import copy
import json
import os
import re
import shutil
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from typing import Any, ClassVar

# Account names must be alphanumeric, hyphens, or underscores
_VALID_ACCOUNT_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


@dataclass
class AccountEntry:
    """Metadata for a named account."""

    name: str = ""
    email: str = ""
    created_at: str = ""


@dataclass
class AccountsRegistry:
    """Registry of all named accounts."""

    default_account: str = ""
    entries: dict[str, AccountEntry] = field(default_factory=dict)


@dataclass
class Config:
    """CLI configuration with enabled services and security settings."""

    BASE_DIR: ClassVar[Path] = Path.home() / ".claude" / ".google-workspace"
    CONFIG_PATH: ClassVar[Path] = BASE_DIR / "gws_config.json"

    ALL_SERVICES: ClassVar[list[str]] = [
        "docs",
        "sheets",
        "slides",
        "drive",
        "gmail",
        "calendar",
        "contacts",
        "convert",
    ]

    DEFAULT_KROKI_URL: ClassVar[str] = "https://kroki.io"

    # Read-only operations per service (used by `account set-readonly`)
    READ_ONLY_OPS: ClassVar[dict[str, list[str]]] = {
        "gmail": [
            "list", "read", "search", "labels", "drafts", "get-draft",
            "list-attachments", "download-attachment", "threads", "get-thread",
            "get-vacation", "get-signature", "filters", "get-filter",
            "get-label", "history",
        ],
        "docs": [
            "list-tabs", "read", "structure", "list-tables",
            "list-headers-footers", "find-text", "list-named-ranges",
            "list-footnotes", "suggestions", "get-page-format", "document-mode",
        ],
        "sheets": [
            "metadata", "read", "batch-get", "list-filter-views",
            "list-pivot-tables", "list-protected-ranges", "list-named-ranges",
        ],
        "slides": ["metadata", "read", "get-speaker-notes"],
        "drive": [
            "list", "search", "get", "download", "export", "list-comments",
            "list-revisions", "get-revision", "list-trash", "list-permissions",
            "get-permission", "list-replies", "get-reply", "changes-token",
            "list-changes", "list-shared-drives", "get-shared-drive", "generate-ids",
        ],
        "calendar": [
            "calendars", "list", "get", "instances", "attendees", "freebusy",
            "list-acl", "get-reminders", "get-default-reminders", "colors",
        ],
        "contacts": [
            "list", "get", "groups", "get-group", "get-photo",
            "search-directory", "list-directory", "batch-get",
        ],
        "convert": [],
    }

    enabled_services: list[str] = field(default_factory=lambda: Config.ALL_SERVICES.copy())
    kroki_url: str = field(default_factory=lambda: Config.DEFAULT_KROKI_URL)
    security_enabled: bool = True  # Prompt injection protection enabled by default

    # Service-specific security settings
    allowlisted_documents: list[str] = field(default_factory=list)  # Docs/Sheets/Slides IDs
    allowlisted_emails: list[str] = field(default_factory=list)  # Gmail message IDs
    disabled_security_services: list[str] = field(default_factory=list)  # Services to skip
    disabled_security_operations: dict[str, bool] = field(default_factory=dict)  # e.g., {"gmail.send": True}

    # Multi-account support (None = legacy single-account mode)
    accounts: AccountsRegistry | None = None

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file or create default."""
        if cls.CONFIG_PATH.exists():
            try:
                with open(cls.CONFIG_PATH) as f:
                    data = json.load(f)
                return cls._from_dict(data)
            except (json.JSONDecodeError, TypeError):
                # Invalid config, return default
                return cls()
        return cls()

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Config":
        """Deserialize config from dict, handling nested accounts structure."""
        accounts_data = data.pop("accounts", None)
        # Filter to known fields to avoid TypeError on future/unknown keys
        known_fields = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        config = cls(**filtered)

        if accounts_data is not None:
            entries = {}
            for name, entry_data in accounts_data.get("entries", {}).items():
                entries[name] = AccountEntry(**entry_data)
            config.accounts = AccountsRegistry(
                default_account=accounts_data.get("default_account", ""),
                entries=entries,
            )

        return config

    def save(self) -> None:
        """Save configuration to file."""
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        # Omit accounts key entirely in legacy mode for clean JSON
        if self.accounts is None:
            data.pop("accounts", None)
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def is_service_enabled(self, service: str) -> bool:
        """Check if a service is enabled."""
        return service in self.enabled_services

    def enable_service(self, service: str) -> bool:
        """Enable a service. Returns True if changed."""
        if service in self.ALL_SERVICES and service not in self.enabled_services:
            self.enabled_services.append(service)
            self.save()
            return True
        return False

    def disable_service(self, service: str) -> bool:
        """Disable a service. Returns True if changed."""
        if service in self.enabled_services:
            self.enabled_services.remove(service)
            self.save()
            return True
        return False

    def is_allowlisted(self, source_type: str, source_id: str) -> bool:
        """Check if a source is in the allowlist."""
        if source_type in ("email", "message"):
            return source_id in self.allowlisted_emails
        elif source_type in ("document", "docs", "spreadsheet", "sheets", "slides"):
            return source_id in self.allowlisted_documents
        return False

    def is_security_enabled_for_operation(self, operation: str) -> bool:
        """Check if security is enabled for an operation (e.g., 'gmail.read')."""
        if not self.security_enabled:
            return False
        # Check if explicitly disabled
        if operation in self.disabled_security_operations:
            return not self.disabled_security_operations[operation]
        # Check if service is disabled
        service = operation.split(".")[0] if "." in operation else operation
        return service not in self.disabled_security_services

    # ── Multi-account methods ──────────────────────────────────────────

    @property
    def is_multi_account(self) -> bool:
        """Check if multi-account mode is active."""
        return self.accounts is not None and len(self.accounts.entries) > 0

    @staticmethod
    def validate_account_name(name: str) -> None:
        """Validate account name is safe for filesystem use."""
        if not _VALID_ACCOUNT_NAME.match(name):
            raise ValueError(
                f"Invalid account name '{name}'. "
                "Use only letters, numbers, hyphens, and underscores."
            )

    def get_account_dir(self, name: str) -> Path:
        """Get the directory for a named account."""
        self.validate_account_name(name)
        return self.BASE_DIR / "accounts" / name

    def resolve_account(self, account: str | None = None) -> str | None:
        """Resolve which account to use.

        Priority: explicit arg > GWS_ACCOUNT env > default > None (legacy).
        """
        if account:
            return account
        env_account = os.environ.get("GWS_ACCOUNT")
        if env_account:
            return env_account
        if self.accounts and self.accounts.default_account:
            return self.accounts.default_account
        return None

    def load_effective_config(self, account: str | None) -> "Config":
        """Return a config with per-account overrides applied.

        Deep-copies self, then overlays fields from per-account config.json.
        """
        if not account:
            return self
        overrides = self.load_account_config(account)
        if not overrides:
            return self
        effective = copy.deepcopy(self)
        # Overlay supported fields
        if "enabled_services" in overrides:
            effective.enabled_services = overrides["enabled_services"]
        if "kroki_url" in overrides:
            effective.kroki_url = overrides["kroki_url"]
        if "security_enabled" in overrides:
            effective.security_enabled = overrides["security_enabled"]
        if "disabled_security_services" in overrides:
            effective.disabled_security_services = overrides["disabled_security_services"]
        if "disabled_security_operations" in overrides:
            effective.disabled_security_operations = overrides["disabled_security_operations"]
        return effective

    def add_account(self, name: str, display_name: str = "", email: str = "") -> None:
        """Register a new named account."""
        from datetime import datetime, timezone

        if self.accounts is None:
            self.accounts = AccountsRegistry()

        self.accounts.entries[name] = AccountEntry(
            name=display_name,
            email=email,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # First account becomes default
        if not self.accounts.default_account:
            self.accounts.default_account = name

        # Create account directory
        account_dir = self.get_account_dir(name)
        account_dir.mkdir(parents=True, exist_ok=True)

        self.save()

    def remove_account(self, name: str) -> bool:
        """Remove a named account and its files. Returns True if removed."""
        if not self.accounts or name not in self.accounts.entries:
            return False

        del self.accounts.entries[name]

        # Clean up account directory
        account_dir = self.get_account_dir(name)
        if account_dir.exists():
            shutil.rmtree(account_dir)

        # Reassign default if needed
        if self.accounts.default_account == name:
            if self.accounts.entries:
                self.accounts.default_account = next(iter(self.accounts.entries))
            else:
                self.accounts.default_account = ""

        # Revert to legacy mode if no accounts left
        if not self.accounts.entries:
            self.accounts = None

        self.save()
        return True

    def set_default_account(self, name: str) -> bool:
        """Set the default account. Returns True if changed."""
        if not self.accounts or name not in self.accounts.entries:
            return False
        self.accounts.default_account = name
        self.save()
        return True

    def list_accounts(self) -> dict[str, Any]:
        """Return all accounts with metadata and default flag."""
        if not self.accounts:
            return {}
        result = {}
        for name, entry in self.accounts.entries.items():
            result[name] = {
                "name": entry.name,
                "email": entry.email,
                "created_at": entry.created_at,
                "is_default": name == self.accounts.default_account,
            }
        return result

    def get_account_display_name(self, account: str | None) -> str:
        """Get the display name for an account, or empty string."""
        if not account or not self.accounts:
            return ""
        entry = self.accounts.entries.get(account)
        return entry.name if entry else ""

    def update_account(self, account: str, display_name: str | None = None, email: str | None = None) -> bool:
        """Update account metadata fields. Returns True if changed."""
        if not self.accounts or account not in self.accounts.entries:
            return False
        entry = self.accounts.entries[account]
        changed = False
        if display_name is not None:
            entry.name = display_name
            changed = True
        if email is not None:
            entry.email = email
            changed = True
        if changed:
            self.save()
        return changed

    def save_account_config(self, name: str, overrides: dict[str, Any]) -> None:
        """Save per-account config overrides."""
        account_dir = self.get_account_dir(name)
        account_dir.mkdir(parents=True, exist_ok=True)
        config_path = account_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(overrides, f, indent=2)

    def load_account_config(self, name: str) -> dict[str, Any]:
        """Load per-account config overrides."""
        config_path = self.get_account_dir(name) / "config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data: dict[str, Any] = json.load(f)
                    return data
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def clear_account_config(self, name: str) -> None:
        """Remove per-account config (full inheritance from global)."""
        config_path = self.get_account_dir(name) / "config.json"
        if config_path.exists():
            config_path.unlink()

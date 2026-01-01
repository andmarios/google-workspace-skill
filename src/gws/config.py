"""Configuration management for GWS CLI."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import ClassVar


@dataclass
class Config:
    """CLI configuration with enabled services."""

    CONFIG_PATH: ClassVar[Path] = Path.home() / ".claude" / ".google-workspace" / "gws_config.json"

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

    enabled_services: list[str] = field(default_factory=lambda: Config.ALL_SERVICES.copy())
    kroki_url: str = field(default_factory=lambda: Config.DEFAULT_KROKI_URL)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file or create default."""
        if cls.CONFIG_PATH.exists():
            try:
                with open(cls.CONFIG_PATH) as f:
                    data = json.load(f)
                    return cls(**data)
            except (json.JSONDecodeError, TypeError):
                # Invalid config, return default
                return cls()
        return cls()

    def save(self) -> None:
        """Save configuration to file."""
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(asdict(self), f, indent=2)

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

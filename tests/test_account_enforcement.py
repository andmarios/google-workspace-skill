"""Tests for account_callback allowed_operations enforcement."""

import pytest
from unittest.mock import patch, MagicMock

import typer

from gws.commands._account import account_callback
from gws.config import Config, AccountsRegistry, AccountEntry


class TestAccountEnforcement:

    def _make_context(self, info_name: str, invoked_subcommand: str | None) -> MagicMock:
        """Create a mock typer.Context."""
        ctx = MagicMock(spec=typer.Context)
        ctx.info_name = info_name
        ctx.invoked_subcommand = invoked_subcommand
        return ctx

    def _make_config_with_account(self, account_name: str) -> Config:
        """Create a Config with a registered account."""
        config = Config()
        config.accounts = AccountsRegistry(
            default_account=account_name,
            entries={account_name: AccountEntry(name=account_name)},
        )
        return config

    def test_allowed_command_passes(self):
        """Command in allowed_operations should not raise."""
        ctx = self._make_context("gmail", "read")
        config = self._make_config_with_account("readonly")

        account_overrides = {
            "allowed_operations": {
                "gmail": ["read", "list", "search"],
            }
        }

        with patch("gws.commands._account.Config.load", return_value=config), \
             patch.object(config, "load_account_config", return_value=account_overrides), \
             patch("gws.commands._account.set_active_account"):
            # Should not raise
            account_callback(ctx, account=None)

    def test_blocked_command_raises(self):
        """Command NOT in allowed_operations should raise typer.Exit."""
        ctx = self._make_context("gmail", "send")
        config = self._make_config_with_account("readonly")

        account_overrides = {
            "allowed_operations": {
                "gmail": ["read", "list"],
            }
        }

        with patch("gws.commands._account.Config.load", return_value=config), \
             patch.object(config, "load_account_config", return_value=account_overrides), \
             patch("gws.commands._account.set_active_account"), \
             patch("gws.commands._account.output_error"):
            with pytest.raises(typer.Exit):
                account_callback(ctx, account=None)

    def test_default_deny_missing_service(self):
        """If service not in allowed_operations at all, should block (default-deny)."""
        ctx = self._make_context("drive", "delete")
        config = self._make_config_with_account("readonly")

        account_overrides = {
            "allowed_operations": {
                "gmail": ["read"],
                # drive is NOT listed - should be denied
            }
        }

        with patch("gws.commands._account.Config.load", return_value=config), \
             patch.object(config, "load_account_config", return_value=account_overrides), \
             patch("gws.commands._account.set_active_account"), \
             patch("gws.commands._account.output_error"):
            with pytest.raises(typer.Exit):
                account_callback(ctx, account=None)

    def test_no_restrictions_allows_all(self):
        """When allowed_operations is None, all commands pass."""
        ctx = self._make_context("gmail", "send")
        config = self._make_config_with_account("unrestricted")

        account_overrides = {}  # No allowed_operations key at all

        with patch("gws.commands._account.Config.load", return_value=config), \
             patch.object(config, "load_account_config", return_value=account_overrides), \
             patch("gws.commands._account.set_active_account"):
            # Should not raise
            account_callback(ctx, account=None)

    def test_invalid_account_name_exits(self):
        """Invalid account name (path traversal) should exit with error."""
        ctx = self._make_context("gmail", "read")
        config = Config()

        with patch("gws.commands._account.Config.load", return_value=config), \
             patch("gws.commands._account.output_error"):
            with pytest.raises(typer.Exit):
                account_callback(ctx, account="../../../etc/passwd")

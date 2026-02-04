"""Runtime context for the active account."""

_active_account: str | None = None


def get_active_account() -> str | None:
    """Get the currently active account name."""
    return _active_account


def set_active_account(account: str | None) -> None:
    """Set the active account name for this invocation."""
    global _active_account
    _active_account = account

"""OAuth scope definitions per service."""

SCOPES: dict[str, list[str]] = {
    "docs": ["https://www.googleapis.com/auth/documents"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "slides": ["https://www.googleapis.com/auth/presentations"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "gmail": ["https://www.googleapis.com/auth/gmail.modify"],
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "contacts": [
        "https://www.googleapis.com/auth/contacts",
        "https://www.googleapis.com/auth/directory.readonly",
    ],
    "convert": [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/presentations",
    ],
}

READONLY_SCOPES: dict[str, list[str]] = {
    "docs": ["https://www.googleapis.com/auth/documents.readonly"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets.readonly"],
    "slides": ["https://www.googleapis.com/auth/presentations.readonly"],
    "drive": ["https://www.googleapis.com/auth/drive.readonly"],
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly"],
    "calendar": ["https://www.googleapis.com/auth/calendar.readonly"],
    "contacts": [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/directory.readonly",
    ],
    "convert": [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/presentations.readonly",
    ],
}


def get_scopes_for_services(services: list[str], read_only: bool = False) -> list[str]:
    """Get combined OAuth scopes for a list of services."""
    scope_map = READONLY_SCOPES if read_only else SCOPES
    scopes: set[str] = set()
    for service in services:
        if service in scope_map:
            scopes.update(scope_map[service])
    return list(scopes)

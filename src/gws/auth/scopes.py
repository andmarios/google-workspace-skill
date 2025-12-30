"""OAuth scope definitions per service."""

SCOPES: dict[str, list[str]] = {
    "docs": ["https://www.googleapis.com/auth/documents"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "slides": ["https://www.googleapis.com/auth/presentations"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "gmail": ["https://www.googleapis.com/auth/gmail.modify"],
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "contacts": ["https://www.googleapis.com/auth/contacts"],
    "convert": [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/presentations",
    ],
}


def get_scopes_for_services(services: list[str]) -> list[str]:
    """Get combined OAuth scopes for a list of services."""
    scopes: set[str] = set()
    for service in services:
        if service in SCOPES:
            scopes.update(SCOPES[service])
    return list(scopes)

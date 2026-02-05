# Google Contacts Operations

## Contents
- [Basic Operations](#basic-operations)
- [Contact Groups](#contact-groups)
- [Photos](#photos)
- [Directory (Google Workspace)](#directory-google-workspace)
- [Batch Operations](#batch-operations)

## Basic Operations

```bash
# List contacts (default 10)
uv run gws contacts list

# List more contacts
uv run gws contacts list --max 50

# Search contacts by name or email
uv run gws contacts list --query "john"

# Get a specific contact
uv run gws contacts get people/c1234567890

# Create a new contact (first name required)
uv run gws contacts create "John"

# Create contact with full details
uv run gws contacts create "John" \
    --family "Doe" \
    --email "john.doe@example.com" \
    --phone "+1-555-123-4567" \
    --org "Acme Corp" \
    --title "Software Engineer"

# Update a contact
uv run gws contacts update people/c1234567890 --given "Jonathan" --family "Smith"

# Update contact email or phone
uv run gws contacts update people/c1234567890 --email "new.email@example.com"
uv run gws contacts update people/c1234567890 --phone "+1-555-987-6543"

# Delete a contact
uv run gws contacts delete people/c1234567890
```

**Resource names**: Contacts use `people/cXXX` format (e.g., `people/c1234567890`).

## Contact Groups

```bash
# List all contact groups
uv run gws contacts groups

# List more groups
uv run gws contacts groups --max 100

# Get group details with members
uv run gws contacts get-group contactGroups/abc123

# Get group without member list
uv run gws contacts get-group contactGroups/abc123 --no-members

# Create a new group
uv run gws contacts create-group "Work Colleagues"

# Rename a group
uv run gws contacts update-group contactGroups/abc123 "Team Members"

# Delete a group (keeps contacts)
uv run gws contacts delete-group contactGroups/abc123

# Delete a group AND its contacts
uv run gws contacts delete-group contactGroups/abc123 --delete-contacts

# Add contacts to a group
uv run gws contacts add-to-group contactGroups/abc123 "people/c111,people/c222"

# Remove contacts from a group
uv run gws contacts remove-from-group contactGroups/abc123 "people/c111,people/c222"
```

**Group types**: USER_CONTACT_GROUP (user-created), SYSTEM_CONTACT_GROUP (like "My Contacts", "Starred").

## Photos

```bash
# Get a contact's photo URL
uv run gws contacts get-photo people/c1234567890

# Set a contact's photo from a file
uv run gws contacts set-photo people/c1234567890 /path/to/photo.jpg

# Delete a contact's photo
uv run gws contacts delete-photo people/c1234567890
```

**Photo requirements**: JPEG or PNG format, maximum 2MB file size.

## Directory (Google Workspace)

These commands require a Google Workspace account and search the organization's directory.

```bash
# Search directory by name or email
uv run gws contacts search-directory "john"

# Search with more results
uv run gws contacts search-directory "engineering" --max 25

# Search with custom fields
uv run gws contacts search-directory "john" \
    --fields "names,emailAddresses,phoneNumbers,organizations"

# List all directory members
uv run gws contacts list-directory

# List with pagination
uv run gws contacts list-directory --max 100
uv run gws contacts list-directory --page-token "TOKEN_FROM_PREVIOUS_RESPONSE"

# List with custom fields
uv run gws contacts list-directory --fields "names,emailAddresses,phoneNumbers"
```

**Available fields**: names, emailAddresses, phoneNumbers, organizations, photos, addresses, birthdays, biographies.

**Note**: Directory commands only work with Google Workspace accounts. Personal Gmail accounts will receive an error.

## Batch Operations

```bash
# Get multiple contacts in one request
uv run gws contacts batch-get "people/c111,people/c222,people/c333"

# Get with custom fields
uv run gws contacts batch-get "people/c111,people/c222" \
    --fields "names,emailAddresses,phoneNumbers,addresses"
```

**Batch limits**: Up to 200 resource names per request.

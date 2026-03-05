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
uvx gws-cli contacts list

# List more contacts
uvx gws-cli contacts list --max 50

# Search contacts by name or email
uvx gws-cli contacts list --query "john"

# Get a specific contact
uvx gws-cli contacts get people/c1234567890

# Create a new contact (first name required)
uvx gws-cli contacts create "John"

# Create contact with full details
uvx gws-cli contacts create "John" \
    --family "Doe" \
    --email "john.doe@example.com" \
    --phone "+1-555-123-4567" \
    --org "Acme Corp" \
    --title "Software Engineer"

# Update a contact
uvx gws-cli contacts update people/c1234567890 --given "Jonathan" --family "Smith"

# Update contact email or phone
uvx gws-cli contacts update people/c1234567890 --email "new.email@example.com"
uvx gws-cli contacts update people/c1234567890 --phone "+1-555-987-6543"

# Delete a contact
uvx gws-cli contacts delete people/c1234567890
```

**Resource names**: Contacts use `people/cXXX` format (e.g., `people/c1234567890`).

## Contact Groups

```bash
# List all contact groups
uvx gws-cli contacts groups

# List more groups
uvx gws-cli contacts groups --max 100

# Get group details with members
uvx gws-cli contacts get-group contactGroups/abc123

# Get group without member list
uvx gws-cli contacts get-group contactGroups/abc123 --no-members

# Create a new group
uvx gws-cli contacts create-group "Work Colleagues"

# Rename a group
uvx gws-cli contacts update-group contactGroups/abc123 "Team Members"

# Delete a group (keeps contacts)
uvx gws-cli contacts delete-group contactGroups/abc123

# Delete a group AND its contacts
uvx gws-cli contacts delete-group contactGroups/abc123 --delete-contacts

# Add contacts to a group
uvx gws-cli contacts add-to-group contactGroups/abc123 "people/c111,people/c222"

# Remove contacts from a group
uvx gws-cli contacts remove-from-group contactGroups/abc123 "people/c111,people/c222"
```

**Group types**: USER_CONTACT_GROUP (user-created), SYSTEM_CONTACT_GROUP (like "My Contacts", "Starred").

## Photos

```bash
# Get a contact's photo URL
uvx gws-cli contacts get-photo people/c1234567890

# Set a contact's photo from a file
uvx gws-cli contacts set-photo people/c1234567890 /path/to/photo.jpg

# Delete a contact's photo
uvx gws-cli contacts delete-photo people/c1234567890
```

**Photo requirements**: JPEG or PNG format, maximum 2MB file size.

## Directory (Google Workspace)

These commands require a Google Workspace account and search the organization's directory.

```bash
# Search directory by name or email
uvx gws-cli contacts search-directory "john"

# Search with more results
uvx gws-cli contacts search-directory "engineering" --max 25

# Search with custom fields
uvx gws-cli contacts search-directory "john" \
    --fields "names,emailAddresses,phoneNumbers,organizations"

# List all directory members
uvx gws-cli contacts list-directory

# List with pagination
uvx gws-cli contacts list-directory --max 100
uvx gws-cli contacts list-directory --page-token "TOKEN_FROM_PREVIOUS_RESPONSE"

# List with custom fields
uvx gws-cli contacts list-directory --fields "names,emailAddresses,phoneNumbers"
```

**Available fields**: names, emailAddresses, phoneNumbers, organizations, photos, addresses, birthdays, biographies.

**Note**: Directory commands only work with Google Workspace accounts. Personal Gmail accounts will receive an error.

## Batch Operations

```bash
# Get multiple contacts in one request
uvx gws-cli contacts batch-get "people/c111,people/c222,people/c333"

# Get with custom fields
uvx gws-cli contacts batch-get "people/c111,people/c222" \
    --fields "names,emailAddresses,phoneNumbers,addresses"
```

**Batch limits**: Up to 200 resource names per request.

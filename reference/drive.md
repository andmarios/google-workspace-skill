# Google Drive Operations

## Contents
- [Basic Operations](#basic-operations)
- [Response Structure](#response-structure)
- [Comments](#comments)
- [Replies](#replies)
- [Revisions](#revisions)
- [Changes API](#changes-api)
- [Shared Drives](#shared-drives)
- [Trash Management](#trash-management)
- [Permissions](#permissions)
- [Utilities](#utilities)

## Basic Operations

```bash
# List files (default: 10)
uvx gws-cli drive list --max 20

# Search files
uvx gws-cli drive search "name contains 'report'"

# Get file metadata
uvx gws-cli drive get <file_id>

# Download file
uvx gws-cli drive download <file_id> /path/to/output.pdf

# Upload file
uvx gws-cli drive upload /path/to/file.pdf --folder <folder_id>

# Create folder
uvx gws-cli drive create-folder "New Folder" --parent <parent_id>

# Copy file
uvx gws-cli drive copy <file_id> --name "Copy of File"

# Move file
uvx gws-cli drive move <file_id> <target_folder_id>

# Share file
uvx gws-cli drive share <file_id> --role reader  # anyone with link
uvx gws-cli drive share <file_id> --email user@example.com --role writer
uvx gws-cli drive share <file_id> --domain company.com --role reader  # anyone at domain

# Update file content
uvx gws-cli drive update <file_id> /path/to/new-content.pdf

# Delete file (moves to trash)
uvx gws-cli drive delete <file_id>

# Export Google file format (pass MIME type via --format)
uvx gws-cli drive export <file_id> /path/to/output.pdf
uvx gws-cli drive export <file_id> output.docx --format "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
uvx gws-cli drive export <file_id> output.md --format "text/markdown"
```

**Tip**: For exporting Google Docs specifically, use `gws-cli docs export` which accepts friendly format names (`markdown`, `pdf`, `docx`, etc.) instead of raw MIME types.

## Response Structure

Commands return JSON with different structures depending on the operation:

**File operations** (upload, get, copy) return file data in a `file` object:
```json
{
  "status": "success",
  "operation": "drive.upload",
  "file": {
    "id": "14mGid9UpxOIG-ALG8D-NQkOaC3TEJQuu",
    "name": "report.pdf",
    "mimeType": "application/pdf",
    "webViewLink": "https://drive.google.com/file/d/.../view"
  }
}
```

**Important**: Access the file ID via `file.id`, not `file_id` at the top level.

**List operations** return data in arrays:
```json
{
  "status": "success",
  "operation": "drive.list",
  "files": [{"id": "...", "name": "..."}, ...]
}
```

## Comments

```bash
# List comments on a file
uvx gws-cli drive list-comments <file_id> --max 20

# Include deleted comments
uvx gws-cli drive list-comments <file_id> --include-deleted

# Add a comment
uvx gws-cli drive add-comment <file_id> "This needs review"

# Reply to a comment
uvx gws-cli drive reply-to-comment <file_id> <comment_id> "Good point, fixed."

# Resolve a comment
uvx gws-cli drive resolve-comment <file_id> <comment_id>

# Delete a comment
uvx gws-cli drive delete-comment <file_id> <comment_id>
```

## Replies

Replies are responses to comments on a file.

```bash
# List replies to a comment
uvx gws-cli drive list-replies <file_id> <comment_id> --max 20

# Get a specific reply
uvx gws-cli drive get-reply <file_id> <comment_id> <reply_id>

# Update a reply's content
uvx gws-cli drive update-reply <file_id> <comment_id> <reply_id> "Updated reply text"

# Delete a reply
uvx gws-cli drive delete-reply <file_id> <comment_id> <reply_id>
```

## Revisions

```bash
# List file revisions
uvx gws-cli drive list-revisions <file_id> --max 20

# Get revision metadata
uvx gws-cli drive get-revision <file_id> <revision_id>

# Delete a revision (cannot delete the last remaining revision)
uvx gws-cli drive delete-revision <file_id> <revision_id>

# Update revision metadata
uvx gws-cli drive update-revision <file_id> <revision_id> --keep-forever

# Publish a revision (for web-published files)
uvx gws-cli drive update-revision <file_id> <revision_id> --published

# Enable auto-publish for future revisions
uvx gws-cli drive update-revision <file_id> <revision_id> --publish-auto
```

## Changes API

Track changes to files over time. Useful for syncing or monitoring file activity.

```bash
# Get a start token for tracking future changes
uvx gws-cli drive changes-token

# List changes since a token
uvx gws-cli drive list-changes <page_token> --max 100

# Exclude removed files from results
uvx gws-cli drive list-changes <page_token> --no-removed
```

**Workflow**: First call `changes-token` to get a starting point. Store the returned token. Later, call `list-changes` with that token to get all changes since then. The response includes a new token for the next poll.

## Shared Drives

Shared drives (formerly Team Drives) are shared spaces where teams can store files.

```bash
# List shared drives you have access to
uvx gws-cli drive list-shared-drives --max 100

# Get shared drive metadata
uvx gws-cli drive get-shared-drive <drive_id>

# Create a new shared drive
uvx gws-cli drive create-shared-drive "Team Projects"

# Delete a shared drive (must be empty)
uvx gws-cli drive delete-shared-drive <drive_id>
```

**Note**: To work with files in a shared drive, use the standard file commands (list, upload, etc.) with the shared drive ID as the folder.

## Trash Management

```bash
# List files in trash
uvx gws-cli drive list-trash --max 20

# Restore a file from trash
uvx gws-cli drive restore <file_id>

# Permanently delete all files in trash
uvx gws-cli drive empty-trash
```

## Permissions

```bash
# List all permissions on a file (who has access)
uvx gws-cli drive list-permissions <file_id>

# Get details of a specific permission
uvx gws-cli drive get-permission <file_id> <permission_id>

# Update a permission's role
uvx gws-cli drive update-permission <file_id> <permission_id> writer

# Set permission with expiration
uvx gws-cli drive update-permission <file_id> <permission_id> reader \
    --expiration "2025-12-31T23:59:59Z"

# Remove a permission (unshare)
uvx gws-cli drive delete-permission <file_id> <permission_id>

# Transfer file ownership to another user
uvx gws-cli drive transfer-ownership <file_id> "newowner@example.com"
```

**Roles**: reader, commenter, writer, organizer (shared drives only), owner

### Sharing Options

```bash
# Share with anyone (public link)
uvx gws-cli drive share <file_id> --role reader

# Share with specific user
uvx gws-cli drive share <file_id> --email user@example.com --role writer

# Share with anyone at a domain (domain-restricted)
uvx gws-cli drive share <file_id> --domain company.com --role reader

# Share with a group
uvx gws-cli drive share <file_id> --email group@example.com --type group --role reader
```

**Share types**: user, group, domain, anyone (auto-detected from options)

## Utilities

```bash
# Pre-generate file IDs for use with create operations
uvx gws-cli drive generate-ids --count 10

# Generate IDs for appDataFolder space
uvx gws-cli drive generate-ids --count 5 --space appDataFolder
```

**Use case**: Pre-generating IDs allows you to know a file's ID before creating it, useful for setting up references between files or for resumable uploads.

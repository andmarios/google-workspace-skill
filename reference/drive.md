# Google Drive Operations

## Contents
- [Basic Operations](#basic-operations)
- [Response Structure](#response-structure)
- [Comments](#comments)
- [Revisions](#revisions)
- [Trash Management](#trash-management)
- [Permissions](#permissions)

## Basic Operations

```bash
# List files (default: 10)
uv run gws drive list --max 20

# Search files
uv run gws drive search "name contains 'report'"

# Get file metadata
uv run gws drive get <file_id>

# Download file
uv run gws drive download <file_id> /path/to/output.pdf

# Upload file
uv run gws drive upload /path/to/file.pdf --folder <folder_id>

# Create folder
uv run gws drive create-folder "New Folder" --parent <parent_id>

# Copy file
uv run gws drive copy <file_id> --name "Copy of File"

# Move file
uv run gws drive move <file_id> <target_folder_id>

# Share file
uv run gws drive share <file_id> --role reader  # anyone with link
uv run gws drive share <file_id> --email user@example.com --role writer
uv run gws drive share <file_id> --domain company.com --role reader  # anyone at domain

# Update file content
uv run gws drive update <file_id> /path/to/new-content.pdf

# Delete file (moves to trash)
uv run gws drive delete <file_id>

# Export Google file format
uv run gws drive export <file_id> /path/to/output.pdf --format pdf
```

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
uv run gws drive list-comments <file_id> --max 20

# Include deleted comments
uv run gws drive list-comments <file_id> --include-deleted

# Add a comment
uv run gws drive add-comment <file_id> "This needs review"

# Reply to a comment
uv run gws drive reply-to-comment <file_id> <comment_id> "Good point, fixed."

# Resolve a comment
uv run gws drive resolve-comment <file_id> <comment_id>

# Delete a comment
uv run gws drive delete-comment <file_id> <comment_id>
```

## Revisions

```bash
# List file revisions
uv run gws drive list-revisions <file_id> --max 20

# Get revision metadata
uv run gws drive get-revision <file_id> <revision_id>

# Delete a revision (cannot delete the last remaining revision)
uv run gws drive delete-revision <file_id> <revision_id>
```

## Trash Management

```bash
# List files in trash
uv run gws drive list-trash --max 20

# Restore a file from trash
uv run gws drive restore <file_id>

# Permanently delete all files in trash
uv run gws drive empty-trash
```

## Permissions

```bash
# List all permissions on a file (who has access)
uv run gws drive list-permissions <file_id>

# Get details of a specific permission
uv run gws drive get-permission <file_id> <permission_id>

# Update a permission's role
uv run gws drive update-permission <file_id> <permission_id> writer

# Set permission with expiration
uv run gws drive update-permission <file_id> <permission_id> reader \
    --expiration "2025-12-31T23:59:59Z"

# Remove a permission (unshare)
uv run gws drive delete-permission <file_id> <permission_id>

# Transfer file ownership to another user
uv run gws drive transfer-ownership <file_id> "newowner@example.com"
```

**Roles**: reader, commenter, writer, organizer (shared drives only), owner

### Sharing Options

```bash
# Share with anyone (public link)
uv run gws drive share <file_id> --role reader

# Share with specific user
uv run gws drive share <file_id> --email user@example.com --role writer

# Share with anyone at a domain (domain-restricted)
uv run gws drive share <file_id> --domain company.com --role reader

# Share with a group
uv run gws drive share <file_id> --email group@example.com --type group --role reader
```

**Share types**: user, group, domain, anyone (auto-detected from options)

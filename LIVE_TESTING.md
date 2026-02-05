# Live Testing Log

This document records manual testing of endpoints against real Google Workspace accounts.

---

## 2026-02-05

### Read-Only Tests

| Endpoint | Command | Result | Notes |
|----------|---------|--------|-------|
| Drive changes-token | `gws drive changes-token` | ✓ Pass | Returns start page token |
| Drive list-shared-drives | `gws drive list-shared-drives --max 5` | ✓ Pass | Lists shared drives |
| Drive generate-ids | `gws drive generate-ids --count 3` | ✓ Pass | Generates unique file IDs |
| Gmail get-label | `gws gmail get-label INBOX` | ✓ Pass | Returns label details with counts |
| Gmail history | `gws gmail history <id> --max 5` | ✓ Pass | Returns history with sync point |
| Contacts search-directory | `gws contacts search-directory "name"` | ✓ Pass | Searches Workspace directory |
| Contacts list-directory | `gws contacts list-directory --max 5` | ✓ Pass | Lists directory with pagination |
| Contacts batch-get | `gws contacts batch-get "people/...,people/..."` | ✓ Pass | Batch retrieves contacts |
| Calendar colors | `gws calendar colors` | ✓ Pass | Returns color definitions |

### Create/Delete Tests

| Endpoint | Command | Result | Notes |
|----------|---------|--------|-------|
| Calendar create-calendar | `gws calendar create-calendar "Test"` | ✓ Pass | Creates secondary calendar |
| Calendar delete-calendar | `gws calendar delete-calendar <id>` | ✓ Pass | Deletes calendar |
| Drive list-comments | `gws drive list-comments <file_id>` | ✓ Pass | Lists file comments |
| Drive list-replies | `gws drive list-replies <file_id> <comment_id>` | ✓ Pass | Lists comment replies |

### Modification Tests

| Endpoint | Command | Result | Notes |
|----------|---------|--------|-------|
| Sheets move-rows | `gws sheets move-rows <id> 0 1 3 4` | ✓ Pass | Moves rows; verified reordering |
| Slides transform-element | `gws slides transform-element <id> <obj> --scale-x 1.5` | ✓ Pass | Applies transformation |
| Docs replace-named-range | `gws docs replace-named-range <id> "text" --name "range"` | ✓ Pass | Replaces named range content |

### Bugs Found

| Bug | Fix Applied |
|-----|-------------|
| `supportsAllDrives` invalid for comments/replies API | Removed from 9 methods |
| `history_id` missing from Gmail read output | Added to output |
| `colorId` missing from Calendar event list | Added conditional field |

---

## Endpoints Not Yet Tested

### Drive
- `get-reply`, `update-reply`, `delete-reply`
- `update-revision`, `list-changes`
- `get-shared-drive`, `create-shared-drive`, `delete-shared-drive`

### Gmail
- `untrash`, `update-label`, `batch-modify`, `delete-thread`

### Calendar
- `clear-calendar`, `move-event`, `subscribe`, `unsubscribe`

### Sheets
- `update-chart`, `move-columns`, `copy-paste`, `auto-fill`
- `trim-whitespace`, `text-to-columns`, `update-banding`, `update-filter-view`

### Slides
- `update-image`, `group`, `ungroup`
- `replace-shapes-with-image`, `set-alt-text`, `insert-sheets-chart`

### Docs
- `replace-image`, `delete-positioned-object`

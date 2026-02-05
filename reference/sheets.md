# Google Sheets Operations

## Contents
- [Basic Operations](#basic-operations)
- [Sheet Management](#sheet-management)
- [Cell Formatting](#cell-formatting)
- [Cell Borders](#cell-borders)
- [Merge and Unmerge Cells](#merge-and-unmerge-cells)
- [Row and Column Sizing](#row-and-column-sizing)
- [Freeze Panes](#freeze-panes)
- [Conditional Formatting](#conditional-formatting)
- [Row and Column Manipulation](#row-and-column-manipulation)
- [Data Manipulation](#data-manipulation)
- [Sorting and Data Operations](#sorting-and-data-operations)
- [Data Validation](#data-validation)
- [Charts](#charts)
- [Banding (Alternating Row Colors)](#banding-alternating-row-colors)
- [Filters](#filters)
- [Pivot Tables](#pivot-tables)
- [Protected Ranges](#protected-ranges)
- [Named Ranges](#named-ranges)

## Basic Operations

```bash
# Get spreadsheet metadata
uv run gws sheets metadata <spreadsheet_id>

# Read cell range (returns displayed values)
uv run gws sheets read <spreadsheet_id> "A1:C10"
uv run gws sheets read <spreadsheet_id> "Sheet2!A1:B5"

# Read formulas instead of computed values
uv run gws sheets read <spreadsheet_id> "A1:C10" --formulas

# Create new spreadsheet
uv run gws sheets create "Spreadsheet Title" --sheets "Data,Summary"

# Write to cells
uv run gws sheets write <spreadsheet_id> "A1:C2" --values '[["A","B","C"],["1","2","3"]]'

# Write complex data via stdin (avoids shell escaping issues)
cat <<'EOF' | uv run gws sheets write <spreadsheet_id> "A1:C4" --stdin
[
  ["Product", "Revenue", "Units"],
  ["Widget A", 15000, 500],
  ["Widget B", 22000, 440],
  ["Widget C", 8500, 170]
]
EOF

# Pipe JSON from another command
jq -n '[["Name","Score"],["Alice",95],["Bob",87]]' | \
    uv run gws sheets write <spreadsheet_id> "A1:B3" --stdin

# Append rows
uv run gws sheets append <spreadsheet_id> "A1:C1" --values '[["New","Row","Data"]]'

# Clear range
uv run gws sheets clear <spreadsheet_id> "A1:C10"

# Batch get multiple ranges
uv run gws sheets batch-get <spreadsheet_id> "A1:B5,C1:D5"
```

## Sheet Management

```bash
# Add new sheet
uv run gws sheets add-sheet <spreadsheet_id> "New Sheet"

# Rename sheet
uv run gws sheets rename-sheet <spreadsheet_id> <sheet_id> "Renamed Sheet"

# Delete sheet
uv run gws sheets delete-sheet <spreadsheet_id> <sheet_id>
```

## Cell Formatting

```bash
# Basic formatting (bold, background color)
uv run gws sheets format <spreadsheet_id> <sheet_id> 0 5 0 3 --bold --bg-color "#FFE0B2"

# Extended formatting (full typography and alignment control)
uv run gws sheets format-extended <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --bold --italic --font "Arial" --size 12 \
    --color "#000000" --bg-color "#E3F2FD" \
    --h-align CENTER --v-align MIDDLE --wrap WRAP

# Number formatting
uv run gws sheets format-extended <spreadsheet_id> <sheet_id> 1 10 2 3 \
    --number-format "#,##0.00"      # Currency style
uv run gws sheets format-extended <spreadsheet_id> <sheet_id> 1 10 4 5 \
    --number-format "0%"             # Percentage style
```

**Horizontal alignment**: LEFT, CENTER, RIGHT
**Vertical alignment**: TOP, MIDDLE, BOTTOM
**Text wrap**: OVERFLOW_CELL, CLIP, WRAP
**Number formats**: Use spreadsheet pattern syntax (e.g., `#,##0.00`, `0%`, `yyyy-mm-dd`)

## Cell Borders

```bash
# Add borders to all sides of a range
uv run gws sheets set-borders <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --all --color "#000000" --style SOLID --width 1

# Custom border configuration
uv run gws sheets set-borders <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --top --bottom --left --right \
    --color "#0000FF" --style DASHED --width 2

# Grid lines (inner borders)
uv run gws sheets set-borders <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --all --inner-horizontal --inner-vertical
```

**Border styles**: SOLID, DOTTED, DASHED, SOLID_MEDIUM, SOLID_THICK, DOUBLE

## Merge and Unmerge Cells

```bash
# Merge all cells in range
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4

# Merge types
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4 --type MERGE_ALL
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4 --type MERGE_COLUMNS
uv run gws sheets merge-cells <spreadsheet_id> <sheet_id> 0 3 0 4 --type MERGE_ROWS

# Unmerge cells
uv run gws sheets unmerge-cells <spreadsheet_id> <sheet_id> 0 3 0 4
```

**Merge types**: MERGE_ALL (single cell), MERGE_COLUMNS (merge within columns), MERGE_ROWS (merge within rows)

## Row and Column Sizing

```bash
# Set column width (pixels)
uv run gws sheets set-column-width <spreadsheet_id> <sheet_id> 0 3 150

# Set row height (pixels)
uv run gws sheets set-row-height <spreadsheet_id> <sheet_id> 0 5 30

# Auto-resize columns to fit content
uv run gws sheets auto-resize-columns <spreadsheet_id> <sheet_id> 0 5
```

## Freeze Panes

```bash
# Freeze header rows (first N rows stay visible when scrolling)
uv run gws sheets freeze-rows <spreadsheet_id> <sheet_id> 1

# Freeze columns (first N columns stay visible)
uv run gws sheets freeze-columns <spreadsheet_id> <sheet_id> 2

# Unfreeze (set to 0)
uv run gws sheets freeze-rows <spreadsheet_id> <sheet_id> 0
uv run gws sheets freeze-columns <spreadsheet_id> <sheet_id> 0
```

## Conditional Formatting

```bash
# Highlight cells greater than a value
uv run gws sheets add-conditional-format <spreadsheet_id> <sheet_id> 1 100 2 3 \
    --condition NUMBER_GREATER --values 100 --bg-color "#FFCDD2"

# Highlight cells containing text
uv run gws sheets add-conditional-format <spreadsheet_id> <sheet_id> 1 100 0 1 \
    --condition TEXT_CONTAINS --values "urgent" \
    --bg-color "#FFEB3B" --color "#000000" --bold

# Highlight blank cells
uv run gws sheets add-conditional-format <spreadsheet_id> <sheet_id> 1 100 0 5 \
    --condition BLANK --bg-color "#E0E0E0"

# Color scale (gradient from min to max)
uv run gws sheets add-color-scale <spreadsheet_id> <sheet_id> 1 100 2 3 \
    --min-color "#FFFFFF" --max-color "#4CAF50"

# Three-color scale (with midpoint)
uv run gws sheets add-color-scale <spreadsheet_id> <sheet_id> 1 100 2 3 \
    --min-color "#F44336" --mid-color "#FFEB3B" --max-color "#4CAF50"

# Clear all conditional formatting from sheet
uv run gws sheets clear-conditional-formats <spreadsheet_id> <sheet_id>
```

**Condition types**: NUMBER_GREATER, NUMBER_LESS, NUMBER_EQ, NUMBER_BETWEEN, TEXT_CONTAINS, TEXT_NOT_CONTAINS, TEXT_STARTS_WITH, TEXT_ENDS_WITH, BLANK, NOT_BLANK, DATE_BEFORE, DATE_AFTER

## Row and Column Manipulation

```bash
# Insert rows at index (0-indexed)
uv run gws sheets insert-rows <spreadsheet_id> <sheet_id> 5 3  # Insert 3 rows at index 5
uv run gws sheets insert-rows <spreadsheet_id> <sheet_id> 0 2 --inherit-after  # Inherit formatting from row below

# Insert columns
uv run gws sheets insert-columns <spreadsheet_id> <sheet_id> 2 1  # Insert 1 column at index 2

# Delete rows
uv run gws sheets delete-rows <spreadsheet_id> <sheet_id> 5 8  # Delete rows 5-7 (end exclusive)

# Delete columns
uv run gws sheets delete-columns <spreadsheet_id> <sheet_id> 0 2  # Delete columns 0-1
```

## Data Manipulation

```bash
# Move rows to a new position (0-indexed)
uv run gws sheets move-rows <spreadsheet_id> <sheet_id> 5 8 15  # Move rows 5-7 to row 15

# Move columns to a new position
uv run gws sheets move-columns <spreadsheet_id> <sheet_id> 2 4 0  # Move columns 2-3 to column 0

# Copy a range and paste to another location
uv run gws sheets copy-paste <spreadsheet_id> \
    --source-sheet 0 --source-start-row 0 --source-end-row 10 \
    --source-start-col 0 --source-end-col 3 \
    --dest-sheet 0 --dest-start-row 20 --dest-start-col 0

# Paste values only (without formatting)
uv run gws sheets copy-paste <spreadsheet_id> \
    --source-sheet 0 --source-start-row 0 --source-end-row 10 \
    --source-start-col 0 --source-end-col 3 \
    --dest-sheet 1 --dest-start-row 0 --dest-start-col 0 \
    --paste-type PASTE_VALUES

# Paste formatting only
uv run gws sheets copy-paste <spreadsheet_id> \
    --source-sheet 0 --source-start-row 0 --source-end-row 5 \
    --source-start-col 0 --source-end-col 3 \
    --dest-sheet 0 --dest-start-row 10 --dest-start-col 0 \
    --paste-type PASTE_FORMAT

# Auto-fill a range based on source data patterns (like dragging fill handle)
uv run gws sheets auto-fill <spreadsheet_id> <sheet_id> \
    --source-start-row 0 --source-end-row 2 --source-start-col 0 --source-end-col 1 \
    --fill-start-row 0 --fill-end-row 10 --fill-start-col 0 --fill-end-col 1

# Auto-fill with alternate series (e.g., Jan/Feb pattern instead of incrementing)
uv run gws sheets auto-fill <spreadsheet_id> <sheet_id> \
    --source-start-row 0 --source-end-row 2 --source-start-col 0 --source-end-col 1 \
    --fill-start-row 0 --fill-end-row 20 --fill-start-col 0 --fill-end-col 1 \
    --alternate-series

# Trim whitespace from cells (entire sheet)
uv run gws sheets trim-whitespace <spreadsheet_id> <sheet_id>

# Trim whitespace from specific range
uv run gws sheets trim-whitespace <spreadsheet_id> <sheet_id> \
    --start-row 0 --end-row 100 --start-col 0 --end-col 5

# Split text into columns by delimiter (comma by default)
uv run gws sheets text-to-columns <spreadsheet_id> <sheet_id> 1 100 0

# Split by semicolon
uv run gws sheets text-to-columns <spreadsheet_id> <sheet_id> 1 100 0 -d SEMICOLON

# Split by custom delimiter
uv run gws sheets text-to-columns <spreadsheet_id> <sheet_id> 1 100 0 -d CUSTOM --custom "|"

# Auto-detect delimiter
uv run gws sheets text-to-columns <spreadsheet_id> <sheet_id> 1 100 0 -d AUTODETECT
```

**Paste types**: PASTE_NORMAL (values and formatting), PASTE_VALUES (values only), PASTE_FORMAT (formatting only)
**Delimiter types**: COMMA, SEMICOLON, PERIOD, SPACE, CUSTOM, AUTODETECT

## Sorting and Data Operations

```bash
# Sort range by column (ascending by default)
uv run gws sheets sort <spreadsheet_id> <sheet_id> 1 100 0 5 2  # Sort rows 1-99 by column 2

# Sort descending
uv run gws sheets sort <spreadsheet_id> <sheet_id> 1 100 0 5 2 --descending

# Find and replace text
uv run gws sheets find-replace <spreadsheet_id> "old text" "new text"

# Find-replace options
uv run gws sheets find-replace <spreadsheet_id> "pattern" "replacement" \
    --sheet-id 0 --match-case --match-entire-cell --use-regex

# Duplicate a sheet
uv run gws sheets duplicate-sheet <spreadsheet_id> <sheet_id> --name "Copy of Sheet1"
```

## Data Validation

```bash
# Dropdown list from values
uv run gws sheets set-validation <spreadsheet_id> <sheet_id> 1 10 2 3 \
    --type ONE_OF_LIST --values "Option1,Option2,Option3"

# Number validation (greater than)
uv run gws sheets set-validation <spreadsheet_id> <sheet_id> 1 10 0 1 \
    --type NUMBER_GREATER --values "0"

# Custom formula validation
uv run gws sheets set-validation <spreadsheet_id> <sheet_id> 1 10 0 5 \
    --type CUSTOM_FORMULA --formula "=A1>0"

# Clear validation
uv run gws sheets clear-validation <spreadsheet_id> <sheet_id> 1 10 2 3
```

**Validation types**: ONE_OF_LIST, ONE_OF_RANGE, NUMBER_GREATER, NUMBER_LESS, NUMBER_BETWEEN, NUMBER_EQ, NUMBER_NOT_EQ, DATE_BEFORE, DATE_AFTER, DATE_BETWEEN, TEXT_CONTAINS, TEXT_NOT_CONTAINS, CUSTOM_FORMULA, BOOLEAN

## Charts

```bash
# Create a basic column chart
uv run gws sheets add-chart <spreadsheet_id> <sheet_id> COLUMN "A1:C10" 0 5 \
    --title "Sales Report"

# Create line chart
uv run gws sheets add-chart <spreadsheet_id> <sheet_id> LINE "Sheet1!A1:B20" 0 5

# Create pie chart
uv run gws sheets add-chart <spreadsheet_id> <sheet_id> PIE "A1:B5" 5 0

# Delete chart
uv run gws sheets delete-chart <spreadsheet_id> <chart_id>

# Update chart title
uv run gws sheets update-chart <spreadsheet_id> <chart_id> --title "New Chart Title"

# Change chart type
uv run gws sheets update-chart <spreadsheet_id> <chart_id> --type BAR

# Change legend position
uv run gws sheets update-chart <spreadsheet_id> <chart_id> --legend BOTTOM

# Update multiple properties at once
uv run gws sheets update-chart <spreadsheet_id> <chart_id> \
    --title "Monthly Sales" --type LINE --legend RIGHT
```

**Chart types**: COLUMN, BAR, LINE, AREA, PIE, SCATTER
**Legend positions**: TOP, BOTTOM, LEFT, RIGHT, NONE

## Banding (Alternating Row Colors)

```bash
# Add alternating colors to a range
uv run gws sheets add-banding <spreadsheet_id> <sheet_id> 0 20 0 5 \
    --header-color "#1565C0" --first-color "#E3F2FD" --second-color "#FFFFFF"

# Update banding colors
uv run gws sheets update-banding <spreadsheet_id> <banded_range_id> \
    --header-color "#4285F4" --first-color "#E8F0FE" --second-color "#FFFFFF"

# Update banding with footer color
uv run gws sheets update-banding <spreadsheet_id> <banded_range_id> \
    --first-color "#FFF3E0" --second-color "#FFFFFF" --footer-color "#FFE0B2"

# Delete banding
uv run gws sheets delete-banding <spreadsheet_id> <banding_id>
```

## Filters

```bash
# Set a basic filter on a range (enables filter dropdowns)
uv run gws sheets set-filter <spreadsheet_id> <sheet_id> 0 100 0 5

# Clear basic filter
uv run gws sheets clear-filter <spreadsheet_id> <sheet_id>

# Create a filter view (saved view with specific filters)
uv run gws sheets create-filter-view <spreadsheet_id> <sheet_id> 0 100 0 5 "My Filter"

# List filter views
uv run gws sheets list-filter-views <spreadsheet_id> <sheet_id>

# Update filter view title
uv run gws sheets update-filter-view <spreadsheet_id> <filter_view_id> --title "Updated Filter"

# Update filter view range
uv run gws sheets update-filter-view <spreadsheet_id> <filter_view_id> \
    --start-row 0 --end-row 200 --start-col 0 --end-col 10

# Update filter view title and range together
uv run gws sheets update-filter-view <spreadsheet_id> <filter_view_id> \
    --title "Extended Data View" --start-row 0 --end-row 500

# Delete filter view
uv run gws sheets delete-filter-view <spreadsheet_id> <filter_view_id>
```

## Pivot Tables

```bash
# Create a pivot table from source data
uv run gws sheets create-pivot-table <spreadsheet_id> <source_sheet_id> 0 100 0 5 \
    <target_sheet_id> 0 0 --row-source 0 --column-source 1 --value-source 2 \
    --summarize SUM

# List pivot tables in a sheet
uv run gws sheets list-pivot-tables <spreadsheet_id> <sheet_id>
```

**Summarize functions**: SUM, COUNTA, COUNT, COUNTUNIQUE, AVERAGE, MAX, MIN, MEDIAN, PRODUCT, STDEV, STDEVP, VAR, VARP

## Protected Ranges

```bash
# Protect a range (only you can edit)
uv run gws sheets protect-range <spreadsheet_id> <sheet_id> 0 10 0 5 \
    --description "Header row - do not edit"

# Protect entire sheet
uv run gws sheets protect-sheet <spreadsheet_id> <sheet_id> --description "Locked sheet"

# List protected ranges
uv run gws sheets list-protected-ranges <spreadsheet_id>

# Unprotect a range
uv run gws sheets unprotect-range <spreadsheet_id> <protected_range_id>
```

## Named Ranges

```bash
# Create a named range
uv run gws sheets create-named-range <spreadsheet_id> <sheet_id> 0 10 0 3 "SalesData"

# List named ranges
uv run gws sheets list-named-ranges <spreadsheet_id>

# Delete named range
uv run gws sheets delete-named-range <spreadsheet_id> <named_range_id>
```

## Working with Sheet Names and Formulas

### Reading Formulas

By default, `sheets read` returns computed/displayed values. Use `--formulas` to see the actual formulas:

```bash
# See computed value (e.g., "$18,463.64")
uv run gws sheets read <spreadsheet_id> "A1"

# See actual formula (e.g., "=SUM(B1:B10)")
uv run gws sheets read <spreadsheet_id> "A1" --formulas
```

### Sheet Names and Special Characters

Sheet names with spaces and formulas with `!` or `$` work correctly with double quotes:

```bash
# Ranges with sheet names containing spaces
uv run gws sheets read <spreadsheet_id> "My Sheet!A1:B10"
uv run gws sheets write <spreadsheet_id> "Costs FY26!A1:C10" --values '[["Q1","Q2","Q3"]]'

# Formulas with absolute references ($)
uv run gws sheets write <spreadsheet_id> "A1" --values '[["=SUM($B$1:$B$10)"]]'

# Formulas referencing other sheets (!)
uv run gws sheets write <spreadsheet_id> "A1" --values '[["=OtherSheet!B2"]]'

# Complex formulas - use --stdin to avoid JSON escaping
cat <<'EOF' | uv run gws sheets write <spreadsheet_id> "A1:A3" --stdin
[
  ["=SUM($B$1:$B$10)"],
  ["=IF(A1>100, \"Yes\", \"No\")"],
  ["='Data Sheet'!A1"]
]
EOF
```

**Tips:**
- Use double quotes (`"..."`) for ranges with spaces or `!`
- Use single quotes for `--values` JSON to preserve `$` in formulas
- Use `--stdin` for complex multi-cell formula writes

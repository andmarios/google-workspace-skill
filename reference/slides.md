# Google Slides Operations

## Contents
- [Basic Operations](#basic-operations)
- [Text Boxes and Content](#text-boxes-and-content)
- [Text Formatting](#text-formatting)
- [Paragraph Formatting](#paragraph-formatting)
- [Shapes](#shapes)
- [Tables](#tables)
- [Slide Backgrounds](#slide-backgrounds)
- [Bullet Lists](#bullet-lists)
- [Lines and Arrows](#lines-and-arrows)
- [Slide Reordering](#slide-reordering)
- [Speaker Notes](#speaker-notes)
- [Videos](#videos)

## Basic Operations

```bash
# Get presentation metadata
uv run gws slides metadata <presentation_id>

# Read all slides with elements
uv run gws slides read <presentation_id>

# Create new presentation
uv run gws slides create "Presentation Title"

# Add slide
uv run gws slides add-slide <presentation_id> --layout TITLE_AND_BODY

# Delete slide
uv run gws slides delete-slide <presentation_id> <slide_id>

# Duplicate slide
uv run gws slides duplicate-slide <presentation_id> <slide_id>
```

**Slide layouts**: BLANK, TITLE, TITLE_AND_BODY, TITLE_AND_TWO_COLUMNS, TITLE_ONLY, SECTION_HEADER, CAPTION_ONLY, BIG_NUMBER

## Text Boxes and Content

```bash
# Create textbox
uv run gws slides create-textbox <presentation_id> <slide_id> "Text content" \
    --x 100 --y 100 --width 400 --height 50

# Insert text into element
uv run gws slides insert-text <presentation_id> <element_id> "Text to insert" --index 0

# Replace text in presentation
uv run gws slides replace-text <presentation_id> "{{placeholder}}" "Replacement"

# Insert image
uv run gws slides insert-image <presentation_id> <slide_id> "https://example.com/image.png" \
    --x 100 --y 100 --width 300 --height 200

# Delete element
uv run gws slides delete-element <presentation_id> <element_id>
```

## Text Formatting

```bash
# Basic formatting
uv run gws slides format-text <presentation_id> <element_id> --bold --font-size 24

# Extended formatting (full typography control)
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --bold --italic --underline --strikethrough \
    --font "Arial" --weight 700 --size 18 \
    --color "#1A237E" --bg-color "#E3F2FD"

# Format specific text range (start_index to end_index)
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 0 --end 10 --bold --color "#FF0000"

# Superscript/subscript
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 5 --end 7 --baseline SUPERSCRIPT
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 10 --end 12 --baseline SUBSCRIPT

# Add hyperlink
uv run gws slides format-text-extended <presentation_id> <element_id> \
    --start 0 --end 15 --link "https://example.com"

# Small caps
uv run gws slides format-text-extended <presentation_id> <element_id> --small-caps
```

**Baseline offsets**: SUPERSCRIPT, SUBSCRIPT, NONE
**Font weights**: 100 (thin) to 900 (black), 400 is normal, 700 is bold

## Paragraph Formatting

```bash
# Paragraph alignment
uv run gws slides format-paragraph <presentation_id> <element_id> --align CENTER

# Line spacing and paragraph spacing (points)
uv run gws slides format-paragraph <presentation_id> <element_id> \
    --line-spacing 150 --space-above 12 --space-below 6

# Indentation (points)
uv run gws slides format-paragraph <presentation_id> <element_id> \
    --indent-first 36 --indent-start 18 --indent-end 0

# Format specific paragraph range
uv run gws slides format-paragraph <presentation_id> <element_id> \
    --start 0 --end 100 --align JUSTIFIED
```

**Alignments**: START, CENTER, END, JUSTIFIED

## Shapes

```bash
# Create shape
uv run gws slides create-shape <presentation_id> <slide_id> RECTANGLE \
    --x 100 --y 100 --width 200 --height 100

# Create other shape types
uv run gws slides create-shape <presentation_id> <slide_id> ELLIPSE \
    --x 350 --y 100 --width 150 --height 150
uv run gws slides create-shape <presentation_id> <slide_id> ROUND_RECTANGLE \
    --x 100 --y 250 --width 200 --height 80

# Format shape appearance
uv run gws slides format-shape <presentation_id> <shape_id> \
    --fill-color "#4CAF50" --outline-color "#2E7D32" \
    --outline-weight 2 --outline-dash SOLID

# Dashed outline
uv run gws slides format-shape <presentation_id> <shape_id> \
    --outline-dash DASH --outline-weight 3
```

**Shape types**: RECTANGLE, ROUND_RECTANGLE, ELLIPSE, TRIANGLE, RIGHT_TRIANGLE, PARALLELOGRAM, TRAPEZOID, PENTAGON, HEXAGON, HEPTAGON, OCTAGON, STAR_4, STAR_5, STAR_6, ARROW_EAST, ARROW_NORTH, PLUS, and many more

**Outline dash styles**: SOLID, DASH, DOT, DASH_DOT, LONG_DASH, LONG_DASH_DOT

## Tables

```bash
# Insert table
uv run gws slides insert-table <presentation_id> <slide_id> 4 3 \
    --x 100 --y 150 --width 500 --height 200

# Insert text into table cell
uv run gws slides insert-table-text <presentation_id> <table_id> 0 0 "Header 1"
uv run gws slides insert-table-text <presentation_id> <table_id> 0 1 "Header 2"
uv run gws slides insert-table-text <presentation_id> <table_id> 1 0 "Row 1 Data"

# Style table cell (background color)
uv run gws slides style-table-cell <presentation_id> <table_id> 0 0 \
    --bg-color "#1565C0"

# Style header row
uv run gws slides style-table-cell <presentation_id> <table_id> 0 0 --bg-color "#E3F2FD"
uv run gws slides style-table-cell <presentation_id> <table_id> 0 1 --bg-color "#E3F2FD"
uv run gws slides style-table-cell <presentation_id> <table_id> 0 2 --bg-color "#E3F2FD"

# Insert row (below specified row index)
uv run gws slides insert-table-row <presentation_id> <table_id> 2

# Insert row above
uv run gws slides insert-table-row <presentation_id> <table_id> 0 --above

# Insert column (right of specified column index)
uv run gws slides insert-table-column <presentation_id> <table_id> 1

# Insert column to the left
uv run gws slides insert-table-column <presentation_id> <table_id> 0 --left

# Delete row
uv run gws slides delete-table-row <presentation_id> <table_id> 3

# Delete column
uv run gws slides delete-table-column <presentation_id> <table_id> 2

# Merge table cells
uv run gws slides merge-table-cells <presentation_id> <table_id> 0 0 2 2

# Unmerge table cells
uv run gws slides unmerge-table-cells <presentation_id> <table_id> 0 0 2 2

# Style table borders
uv run gws slides style-table-borders <presentation_id> <table_id> 0 0 \
    --rows 3 --cols 3 --color "#000000" --weight 2 --style SOLID --position ALL
```

**Border positions**: ALL, INNER, OUTER, INNER_HORIZONTAL, INNER_VERTICAL, LEFT, RIGHT, TOP, BOTTOM

## Slide Backgrounds

```bash
# Set solid color background
uv run gws slides set-background <presentation_id> <slide_id> --color "#1565C0"

# Set image background
uv run gws slides set-background <presentation_id> <slide_id> \
    --image "https://example.com/background.jpg"
```

## Bullet Lists

```bash
# Add bullet formatting to text
uv run gws slides create-bullets <presentation_id> <element_id> \
    --preset BULLET_DISC_CIRCLE_SQUARE

# Apply bullets to specific text range
uv run gws slides create-bullets <presentation_id> <element_id> \
    --start 0 --end 100 --preset NUMBERED_DIGIT_ALPHA_ROMAN

# Remove bullets
uv run gws slides remove-bullets <presentation_id> <element_id>
```

**Bullet presets**: BULLET_DISC_CIRCLE_SQUARE, BULLET_DIAMONDX_ARROW3D_SQUARE, BULLET_CHECKBOX, BULLET_ARROW_DIAMOND_DISC, NUMBERED_DIGIT_ALPHA_ROMAN, NUMBERED_DIGIT_NESTED

## Lines and Arrows

```bash
# Create a line
uv run gws slides create-line <presentation_id> <slide_id> \
    --start-x 100 --start-y 100 --end-x 400 --end-y 100

# Create an arrow
uv run gws slides create-line <presentation_id> <slide_id> \
    --start-x 100 --start-y 200 --end-x 400 --end-y 200 \
    --end-arrow FILL_ARROW --color "#FF0000" --weight 2

# Create a dashed line
uv run gws slides create-line <presentation_id> <slide_id> \
    --start-x 100 --start-y 300 --end-x 400 --end-y 400 \
    --style DASH --category STRAIGHT
```

**Line categories**: STRAIGHT, BENT, CURVED
**Arrow types**: NONE, FILL_ARROW, STEALTH_ARROW, FILL_CIRCLE, FILL_SQUARE, FILL_DIAMOND, OPEN_ARROW, OPEN_CIRCLE, OPEN_SQUARE, OPEN_DIAMOND

## Slide Reordering

```bash
# Move slides to a new position
uv run gws slides reorder-slides <presentation_id> "slide_id1,slide_id2" 0
```

## Speaker Notes

```bash
# Get speaker notes for a slide
uv run gws slides get-speaker-notes <presentation_id> <slide_id>

# Set speaker notes for a slide
uv run gws slides set-speaker-notes <presentation_id> <slide_id> "Notes for this slide"
```

## Videos

```bash
# Insert a YouTube video
uv run gws slides insert-video <presentation_id> <slide_id> "dQw4w9WgXcQ" \
    --x 100 --y 100 --width 400 --height 225

# Update video properties (autoplay, mute, start/end times)
uv run gws slides update-video-properties <presentation_id> <video_id> \
    --autoplay --mute --start 10 --end 60
```

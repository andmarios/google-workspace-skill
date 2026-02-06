# Live Testing Log

Manual testing of all CLI operations against real Google Workspace accounts.

---

## Summary

| Metric | Count | Notes |
|--------|-------|-------|
| Pass | 210 | |
| Skip | 6 | Destructive or require external setup (e.g. target email, ownership transfer) |
| Expected fail | 1 | API correctly rejects the operation (e.g. unsubscribe from owned calendar) |
| **Total** | **217** | |

---

## All Tests

| # | Service | Command | Status | Date | Notes |
|---|---------|---------|--------|------|-------|
| 1 | Infra |`gws --version`|PASS| 2026-02-05 |Returns `{"version": "1.0.0"}`|
| 2 | Infra |`gws --help`|PASS| 2026-02-05 |Lists all 8 services|
| 3 | Infra |`gws auth status`|PASS| 2026-02-05 |Token valid|
| 4 | Infra |`gws config`|PASS| 2026-02-05 |Shows all config including multi-account|
| 5 | Infra |`gws config list`|PASS| 2026-02-05 |8/8 services enabled|
| 6 | Drive |`drive list --max 5`|PASS| 2026-02-05 |Pagination works|
| 7 | Drive |`drive search "name contains 'GWS-Test'"`|PASS| 2026-02-05 |Query works|
| 8 | Drive |`drive get <file_id>`|PASS| 2026-02-05 |Full metadata|
| 9 | Drive |`drive download <file_id> /tmp/...`|PASS| 2026-02-05 |File downloaded|
| 10 | Drive |`drive export <doc_id> --format "application/pdf"`|PASS| 2026-02-05 |PDF exported|
| 11 | Drive |`drive changes-token`|PASS| 2026-02-05 |Returns start_page_token|
| 12 | Drive |`drive list-changes <token>`|PASS| 2026-02-05 |Lists changes|
| 13 | Drive |`drive list-trash --max 5`|PASS| 2026-02-05 |Shows trashed files|
| 14 | Drive |`drive list-shared-drives --max 5`|PASS| 2026-02-05 |Lists 5 shared drives|
| 15 | Drive |`drive generate-ids --count 3`|PASS| 2026-02-05 |Returns 3 IDs|
| 16 | Drive |`drive list-permissions <file_id>`|PASS| 2026-02-05 |Shows owner permission|
| 17 | Drive |`drive list-revisions <file_id>`|FIXED| 2026-02-05 |Bug: `supportsAllDrives` not valid for revisions API|
| 18 | Drive |`drive list-comments <file_id>`|PASS| 2026-02-05 |Works|
| 19 | Drive |`drive list-replies <file_id> <comment_id>`|PASS| 2026-02-05 |Lists comment replies|
| 20 | Drive |`drive create-folder "..."`|PASS| 2026-02-05 |Created test folder|
| 21 | Drive |`drive upload <path> --folder <id>`|PASS| 2026-02-05 |File uploaded|
| 22 | Drive |`drive copy <id> --name "..."`|PASS| 2026-02-05 |File copied|
| 23 | Drive |`drive move <id> <folder_id>`|PASS| 2026-02-05 |File moved|
| 24 | Drive |`drive update <id> <path>`|PASS| 2026-02-05 |Content updated|
| 25 | Drive |`drive add-comment <id> "..."`|PASS| 2026-02-05 |Comment added|
| 26 | Drive |`drive reply-to-comment <id> <cid> "..."`|PASS| 2026-02-05 |Reply created|
| 27 | Drive |`drive resolve-comment <id> <cid>`|FIXED| 2026-02-05 |Bug: was using `comments().update()`, fixed to `replies().create()` with `action: "resolve"`|
| 28 | Drive |`drive delete-comment <id> <cid>`|PASS| 2026-02-05 |Comment deleted|
| 29 | Drive |`drive delete <id>`|PASS| 2026-02-05 |File trashed|
| 30 | Drive |`drive restore <id>`|PASS| 2026-02-05 |File restored|
| 31 | Drive |`drive share`|SKIP| 2026-02-05 |Requires target email|
| 32 | Drive |`drive update-permission`|SKIP| 2026-02-05 |Requires target email|
| 33 | Drive |`drive delete-permission`|SKIP| 2026-02-05 |Requires target email|
| 34 | Drive |`drive transfer-ownership`|SKIP| 2026-02-05 |Risky on real account|
| 35 | Drive |`drive empty-trash`|SKIP| 2026-02-05 |Destructive|
| 36 | Docs |`docs read <id>`|PASS| 2026-02-05 |Returns content with security wrapper|
| 37 | Docs |`docs structure <id>`|PASS| 2026-02-05 |Lists headings|
| 38 | Docs |`docs list-tabs <id>`|PASS| 2026-02-05 |Shows tab info|
| 39 | Docs |`docs list-tables <id>`|PASS| 2026-02-05 |Shows table info|
| 40 | Docs |`docs list-named-ranges <id>`|PASS| 2026-02-05 |Lists ranges|
| 41 | Docs |`docs list-footnotes <id>`|PASS| 2026-02-05 |Lists footnotes|
| 42 | Docs |`docs list-headers-footers <id>`|PASS| 2026-02-05 |Lists headers/footers|
| 43 | Docs |`docs get-page-format <id>`|PASS| 2026-02-05 |Returns PAGES/PAGELESS|
| 44 | Docs |`docs suggestions <id>`|PASS| 2026-02-05 |Lists suggestions|
| 45 | Docs |`docs find-text <id> "test"`|PASS| 2026-02-05 |Finds position and count|
| 46 | Docs |`docs create "Title" --content "..."`|PASS| 2026-02-05 |Creates doc|
| 47 | Docs |`docs insert <id> "text" --index 1`|PASS| 2026-02-05 |Inserts at index|
| 48 | Docs |`docs append <id> "text"`|PASS| 2026-02-05 |Appends text|
| 49 | Docs |`docs insert-markdown <id> "**bold**" --index 1`|PASS| 2026-02-05 |Markdown converted|
| 50 | Docs |`docs replace <id> "old" "new"`|PASS| 2026-02-05 |Replace works (0 matches OK)|
| 51 | Docs |`docs format <id> 1 8 --bold`|PASS| 2026-02-05 |Bold formatting|
| 52 | Docs |`docs format-text-extended <id> 1 20 --size 14`|PASS| 2026-02-05 |Font size change|
| 53 | Docs |`docs format-paragraph <id> 1 25 --align CENTER`|PASS| 2026-02-05 |Center alignment|
| 54 | Docs |`docs paragraph-border <id> 1 18 --top`|FIXED| 2026-02-05 |Bug: missing required `padding` field in border style|
| 55 | Docs |`docs insert-link <id> 10 20 "url"`|PASS| 2026-02-05 |Hyperlink added|
| 56 | Docs |`docs insert-table <id> 3 3 --index 83`|PASS| 2026-02-05 |Table inserted|
| 57 | Docs |`docs insert-table-column <id> 0 2`|PASS| 2026-02-05 |Column added|
| 58 | Docs |`docs merge-cells <id> 0 0 0 1 1`|PASS| 2026-02-05 |Cells merged|
| 59 | Docs |`docs unmerge-cells <id> 0 0 0 1 1`|PASS| 2026-02-05 |Cells unmerged|
| 60 | Docs |`docs style-table-cell <id> 0 0 0 --bg-color "#f0f0f0"`|PASS| 2026-02-05 |Cell styled|
| 61 | Docs |`docs set-table-column-widths <id> 0 '{"0":100,...}'`|PASS| 2026-02-05 |Widths set|
| 62 | Docs |`docs pin-table-header <id> 0`|PASS| 2026-02-05 |Header pinned|
| 63 | Docs |`docs create-header <id>`|PASS| 2026-02-05 |Header created|
| 64 | Docs |`docs create-footer <id>`|PASS| 2026-02-05 |Footer created|
| 65 | Docs |`docs insert-segment-text <id> <hdr_id> "text"`|PASS| 2026-02-05 |Text in header|
| 66 | Docs |`docs delete-header <id> <hdr_id>`|PASS| 2026-02-05 |Header deleted|
| 67 | Docs |`docs create-named-range <id> "name" 10 30`|PASS| 2026-02-05 |Range created|
| 68 | Docs |`docs replace-named-range <id> "text" --name "range"`|PASS| 2026-02-05 |Replaces named range content|
| 69 | Docs |`docs create-bullets <id> 50 80`|PASS| 2026-02-05 |Bullet list|
| 70 | Docs |`docs create-numbered <id> 22 40`|PASS| 2026-02-05 |Numbered list|
| 71 | Docs |`docs remove-bullets <id> 22 40`|PASS| 2026-02-05 |Bullets removed|
| 72 | Docs |`docs insert-section-break <id> 20`|PASS| 2026-02-05 |Section break|
| 73 | Docs |`docs page-break <id> 30`|PASS| 2026-02-05 |Page break|
| 74 | Docs |`docs document-style <id> --margin-top 72`|PASS| 2026-02-05 |Margins updated|
| 75 | Docs |`docs set-page-format <id> PAGELESS`|PASS| 2026-02-05 |Pageless mode|
| 76 | Docs |`docs insert-footnote <id> 10`|PASS| 2026-02-05 |Footnote added|
| 77 | Docs |`docs create-tab <id> "TestTab"`|PASS| 2026-02-05 |Tab created|
| 78 | Docs |`docs rename-tab <id> <tab_id> "New"`|FIXED| 2026-02-05 |Bug: `tabId` placed outside `tabProperties`|
| 79 | Docs |`docs reorder-tab <id> <tab_id> 0`|FIXED| 2026-02-05 |Bug: same `tabId` placement issue|
| 80 | Docs |`docs delete-tab <id> <tab_id>`|PASS| 2026-02-05 |Tab deleted|
| 81 | Sheets |`sheets metadata <id>`|PASS| 2026-02-05 |Full metadata|
| 82 | Sheets |`sheets read <id> "Sheet1\!A1:C5"`|PASS| 2026-02-05 |Read range|
| 83 | Sheets |`sheets batch-get <id> "A1:B2,C1:D2"`|PASS| 2026-02-05 |Batch read|
| 84 | Sheets |`sheets create "Title" --sheets "S1,S2"`|PASS| 2026-02-05 |Creates spreadsheet|
| 85 | Sheets |`sheets write <id> "A1:C3" --values '[...]'`|PASS| 2026-02-05 |Write values|
| 86 | Sheets |`sheets append <id> "A:C" --values '[...]'`|PASS| 2026-02-05 |Append values|
| 87 | Sheets |`sheets clear <id> "A10:C10"`|PASS| 2026-02-05 |Clear range|
| 88 | Sheets |`sheets add-sheet <id> "NewSheet"`|PASS| 2026-02-05 |Add sheet|
| 89 | Sheets |`sheets rename-sheet <id> <sheet_id> "Renamed"`|PASS| 2026-02-05 |Rename sheet|
| 90 | Sheets |`sheets duplicate-sheet <id> <sheet_id>`|PASS| 2026-02-05 |Duplicate sheet|
| 91 | Sheets |`sheets delete-sheet <id> <sheet_id>`|PASS| 2026-02-05 |Delete sheet|
| 92 | Sheets |`sheets format <id> <sid> 0 3 0 3 --bold`|PASS| 2026-02-05 |Bold format|
| 93 | Sheets |`sheets format-extended <id> <sid> 0 3 0 3 --font-size 12`|PASS| 2026-02-05 |Extended format|
| 94 | Sheets |`sheets set-borders <id> <sid> 0 3 0 3 --style SOLID`|PASS| 2026-02-05 |Borders|
| 95 | Sheets |`sheets merge-cells <id> <sid> 5 6 0 2`|PASS| 2026-02-05 |Merge cells|
| 96 | Sheets |`sheets unmerge-cells <id> <sid> 5 6 0 2`|PASS| 2026-02-05 |Unmerge cells|
| 97 | Sheets |`sheets set-column-width <id> <sid> 0 150`|PASS| 2026-02-05 |Column width|
| 98 | Sheets |`sheets set-row-height <id> <sid> 0 30`|PASS| 2026-02-05 |Row height|
| 99 | Sheets |`sheets auto-resize-columns <id> <sid> 0 3`|PASS| 2026-02-05 |Auto resize|
| 100 | Sheets |`sheets freeze-rows <id> <sid> 1`|PASS| 2026-02-05 |Freeze rows|
| 101 | Sheets |`sheets freeze-columns <id> <sid> 1`|PASS| 2026-02-05 |Freeze columns|
| 102 | Sheets |`sheets insert-rows <id> <sid> 5 2`|PASS| 2026-02-05 |Insert rows|
| 103 | Sheets |`sheets insert-columns <id> <sid> 3 2`|PASS| 2026-02-05 |Insert columns|
| 104 | Sheets |`sheets delete-rows <id> <sid> 5 2`|PASS| 2026-02-05 |Delete rows|
| 105 | Sheets |`sheets delete-columns <id> <sid> 3 2`|PASS| 2026-02-05 |Delete columns|
| 106 | Sheets |`sheets sort <id> <sid> 0 10 0 --ascending`|PASS| 2026-02-05 |Sort range|
| 107 | Sheets |`sheets find-replace <id> "old" "new"`|PASS| 2026-02-05 |Find/replace|
| 108 | Sheets |`sheets move-rows <id> <sid> 1 3 4`|PASS| 2026-02-05 |Move rows|
| 109 | Sheets |`sheets move-columns <id> <sid> 0 1 3`|PASS| 2026-02-05 |Move columns|
| 110 | Sheets |`sheets copy-paste <id> <sid> 0 2 0 2 5 0`|PASS| 2026-02-05 |Copy/paste|
| 111 | Sheets |`sheets auto-fill <id> <sid> 0 1 0 1 0 5 0 1`|PASS| 2026-02-05 |Auto-fill|
| 112 | Sheets |`sheets trim-whitespace <id> <sid> 0 10 0 3`|PASS| 2026-02-05 |Trim whitespace|
| 113 | Sheets |`sheets set-validation <id> <sid> 0 5 0 1 --type NUMBER_GREATER`|PASS| 2026-02-05 |Data validation|
| 114 | Sheets |`sheets clear-validation <id> <sid> 0 5 0 1`|PASS| 2026-02-05 |Clear validation|
| 115 | Sheets |`sheets add-conditional-format <id> <sid> 0 10 0 3 --type NUMBER_GREATER`|PASS| 2026-02-05 |Conditional format|
| 116 | Sheets |`sheets clear-conditional-formats <id> <sid>`|PASS| 2026-02-05 |Clear conditional formats|
| 117 | Sheets |`sheets add-chart <id> <sid> "A1:B5" --type COLUMN`|PASS| 2026-02-05 |Add chart|
| 118 | Sheets |`sheets delete-chart <id> <chart_id>`|PASS| 2026-02-05 |Delete chart|
| 119 | Sheets |`sheets add-banding <id> <sid> 0 10 0 3`|PASS| 2026-02-05 |Add banding|
| 120 | Sheets |`sheets delete-banding <id> <banding_id>`|PASS| 2026-02-05 |Delete banding|
| 121 | Sheets |`sheets set-basic-filter <id> <sid> 0 10 0 3`|PASS| 2026-02-05 |Set filter|
| 122 | Sheets |`sheets clear-basic-filter <id> <sid>`|PASS| 2026-02-05 |Clear filter|
| 123 | Sheets |`sheets create-filter-view <id> <sid> "MyView" 0 10 0 3`|PASS| 2026-02-05 |Create filter view|
| 124 | Sheets |`sheets delete-filter-view <id> <view_id>`|PASS| 2026-02-05 |Delete filter view|
| 125 | Sheets |`sheets protect-range <id> <sid> 0 5 0 3 "Protected"`|PASS| 2026-02-05 |Protect range|
| 126 | Sheets |`sheets unprotect-range <id> <protected_id>`|PASS| 2026-02-05 |Unprotect range|
| 127 | Sheets |`sheets create-named-range <id> <sid> "myrange" 0 5 0 3`|PASS| 2026-02-05 |Named range|
| 128 | Sheets |`sheets delete-named-range <id> <range_id>`|PASS| 2026-02-05 |Delete named range|
| 129 | Sheets |`sheets list-named-ranges <id>`|PASS| 2026-02-05 |List named ranges|
| 130 | Sheets |`sheets list-protected-ranges <id>`|PASS| 2026-02-05 |List protected ranges|
| 131 | Slides |`slides metadata <id>`|PASS| 2026-02-05 |Full metadata|
| 132 | Slides |`slides read <id>`|PASS| 2026-02-05 |Full content|
| 133 | Slides |`slides create "Title"`|PASS| 2026-02-05 |Creates presentation|
| 134 | Slides |`slides add-slide <id> --layout TITLE_AND_BODY`|PASS| 2026-02-05 |Add slide|
| 135 | Slides |`slides duplicate-slide <id> <slide_id>`|PASS| 2026-02-05 |Duplicate slide|
| 136 | Slides |`slides reorder-slides <id> <slide_id> 0`|PASS| 2026-02-05 |Reorder slide|
| 137 | Slides |`slides delete-slide <id> <slide_id>`|PASS| 2026-02-05 |Delete slide|
| 138 | Slides |`slides create-textbox <id> <slide_id> "Content"`|PASS| 2026-02-05 |Textbox created|
| 139 | Slides |`slides insert-text <id> <elem_id> "Text" --index 0`|PASS| 2026-02-05 |Insert text|
| 140 | Slides |`slides replace-text <id> "old" "new"`|PASS| 2026-02-05 |Replace text|
| 141 | Slides |`slides format-text <id> <elem_id> 0 10 --bold`|PASS| 2026-02-05 |Format text|
| 142 | Slides |`slides format-text-extended <id> <elem_id> 0 10 --font-size 24`|PASS| 2026-02-05 |Extended format|
| 143 | Slides |`slides format-paragraph <id> <elem_id> 0 --alignment CENTER`|PASS| 2026-02-05 |Paragraph format|
| 144 | Slides |`slides delete-element <id> <elem_id>`|PASS| 2026-02-05 |Delete element|
| 145 | Slides |`slides insert-image <id> <slide_id> <url>`|PASS| 2026-02-05 |Image inserted|
| 146 | Slides |`slides create-shape <id> <slide_id> RECTANGLE`|PASS| 2026-02-05 |Shape created|
| 147 | Slides |`slides format-shape <id> <elem_id> --fill-color "#ff0000"`|PASS| 2026-02-05 |Shape formatted|
| 148 | Slides |`slides transform-element <id> <elem_id> --scale-x 1.5`|FIXED| 2026-02-05 |Bug: non-invertible matrix when only scaleX set; defaulted scaleY to 1.0|
| 149 | Slides |`slides set-alt-text <id> <elem_id> "Alt text"`|PASS| 2026-02-05 |Alt text set|
| 150 | Slides |`slides create-line <id> <slide_id>`|PASS| 2026-02-05 |Line created|
| 151 | Slides |`slides set-background <id> <slide_id> --color "#ffffff"`|PASS| 2026-02-05 |Background set|
| 152 | Slides |`slides create-bullets <id> <elem_id> 0 50`|PASS| 2026-02-05 |Bullets created|
| 153 | Slides |`slides remove-bullets <id> <elem_id> 0 50`|PASS| 2026-02-05 |Bullets removed|
| 154 | Slides |`slides insert-table <id> <slide_id> 3 3`|PASS| 2026-02-05 |Table inserted|
| 155 | Slides |`slides insert-table-row <id> <table_id> 1`|PASS| 2026-02-05 |Row added|
| 156 | Slides |`slides insert-table-column <id> <table_id> 1`|PASS| 2026-02-05 |Column added|
| 157 | Slides |`slides delete-table-row <id> <table_id> 1`|PASS| 2026-02-05 |Row deleted|
| 158 | Slides |`slides delete-table-column <id> <table_id> 1`|PASS| 2026-02-05 |Column deleted|
| 159 | Slides |`slides insert-table-text <id> <table_id> 0 0 "Cell"`|PASS| 2026-02-05 |Cell text added|
| 160 | Slides |`slides style-table-cell <id> <table_id> 0 0 --bg-color "#f0f0f0"`|PASS| 2026-02-05 |Cell styled|
| 161 | Slides |`slides merge-table-cells <id> <table_id> 0 0 2 2`|PASS| 2026-02-05 |Cells merged|
| 162 | Slides |`slides unmerge-table-cells <id> <table_id> 0 0`|PASS| 2026-02-05 |Cells unmerged|
| 163 | Slides |`slides get-speaker-notes <id> <slide_id>`|PASS| 2026-02-05 |Returns notes|
| 164 | Slides |`slides set-speaker-notes <id> <slide_id> "Notes"`|FIXED| 2026-02-05 |Bug: `deleteText` fails on empty notes; added existence check|
| 165 | Slides |`slides group-objects <id> <elem1> <elem2>`|PASS| 2026-02-05 |Objects grouped|
| 166 | Slides |`slides ungroup-objects <id> <group_id>`|PASS| 2026-02-05 |Objects ungrouped|
| 167 | Gmail |`gmail list --max 5`|PASS| 2026-02-05 |Lists messages|
| 168 | Gmail |`gmail read <message_id>`|FIXED| 2026-02-05 |Bug: case-sensitive header lookup failed on API-sent messages|
| 169 | Gmail |`gmail search "subject:GWS-Test"`|PASS| 2026-02-05 |Search works|
| 170 | Gmail |`gmail get-label INBOX`|PASS| 2026-02-05 |Returns label details with counts|
| 171 | Gmail |`gmail history <history_id> --max 5`|PASS| 2026-02-05 |Returns history|
| 172 | Gmail |`gmail send <to> "Subject" "Body"`|PASS| 2026-02-05 |Email sent|
| 173 | Gmail |`gmail reply <message_id> "Reply body"`|FIXED| 2026-02-05 |Bug: case-insensitive headers + format="full" needed|
| 174 | Gmail |`gmail mark-read <message_id>`|PASS| 2026-02-05 |Marked read|
| 175 | Gmail |`gmail mark-unread <message_id>`|PASS| 2026-02-05 |Marked unread|
| 176 | Gmail |`gmail add-star <message_id>`|PASS| 2026-02-05 |Starred|
| 177 | Gmail |`gmail remove-star <message_id>`|PASS| 2026-02-05 |Unstarred|
| 178 | Gmail |`gmail create-label "GWS-Test-Label"`|PASS| 2026-02-05 |Label created|
| 179 | Gmail |`gmail batch-modify <ids> --add-labels STARRED`|PASS| 2026-02-05 |Batch modify|
| 180 | Gmail |`gmail delete <message_id>`|PASS| 2026-02-05 |Trashed|
| 181 | Gmail |`gmail untrash <message_id>`|PASS| 2026-02-05 |Untrashed|
| 182 | Gmail |`gmail delete-label <label_id>`|PASS| 2026-02-05 |Label deleted|
| 183 | Calendar |`calendar calendars`|PASS| 2026-02-06 |Lists all calendars|
| 184 | Calendar |`calendar create-calendar "GWS-Test-Calendar"`|PASS| 2026-02-06 |Created secondary calendar|
| 185 | Calendar |`calendar create "Meeting" <start> <end> -c <cal>`|PASS| 2026-02-06 |Event created|
| 186 | Calendar |`calendar list -c <cal>`|PASS| 2026-02-06 |Lists events|
| 187 | Calendar |`calendar get <event_id> -c <cal>`|PASS| 2026-02-06 |Gets event|
| 188 | Calendar |`calendar colors`|PASS| 2026-02-06 |Returns color definitions|
| 189 | Calendar |`calendar update <event_id> --summary "New" -c <cal>`|PASS| 2026-02-06 |Event updated|
| 190 | Calendar |`calendar quick-add "Lunch tomorrow at noon" -c <cal>`|PASS| 2026-02-06 |NLP event created|
| 191 | Calendar |`calendar freebusy <start> <end> -c <cal>`|PASS| 2026-02-06 |Free/busy info|
| 192 | Calendar |`calendar create-recurring "Weekly" <start> <end> <rrule> -c <cal>`|PASS| 2026-02-06 |Recurring event created|
| 193 | Calendar |`calendar instances <event_id> -c <cal>`|PASS| 2026-02-06 |Lists 3 instances|
| 194 | Calendar |`calendar rsvp <event_id> accepted -c <cal>`|PASS| 2026-02-06 |RSVP accepted|
| 195 | Calendar |`calendar attendees <event_id> -c <cal>`|PASS| 2026-02-06 |Lists attendees|
| 196 | Calendar |`calendar move-event <event_id> primary -f <cal>`|PASS| 2026-02-06 |Event moved|
| 197 | Calendar |`calendar list-acl -c <cal>`|PASS| 2026-02-06 |Lists ACL rules|
| 198 | Calendar |`calendar add-acl user <email> reader -c <cal>`|PASS| 2026-02-06 |ACL rule added|
| 199 | Calendar |`calendar update-acl <rule_id> writer -c <cal>`|PASS| 2026-02-06 |ACL role updated|
| 200 | Calendar |`calendar remove-acl <rule_id> -c <cal>`|PASS| 2026-02-06 |ACL rule removed|
| 201 | Calendar |`calendar subscribe <cal>`|PASS| 2026-02-06 |Calendar subscribed|
| 202 | Calendar |`calendar unsubscribe <cal>`|EXPECTED| 2026-02-06 |Cannot unsubscribe from owned calendar|
| 203 | Calendar |`calendar delete <event_id>`|PASS| 2026-02-06 |Event deleted|
| 204 | Calendar |`calendar delete <recurring_id> -c <cal>`|PASS| 2026-02-06 |Recurring event deleted|
| 205 | Calendar |`calendar clear-calendar <cal>`|SKIP| 2026-02-06 |Only works on primary; hangs/risky|
| 206 | Calendar |`calendar delete-calendar <cal>`|PASS| 2026-02-06 |Calendar deleted|
| 207 | Contacts |`contacts create "Name" -f "Last" -e "x@y.com"`|PASS| 2026-02-06 |Contact created|
| 208 | Contacts |`contacts list --max 5`|PASS| 2026-02-06 |Lists contacts|
| 209 | Contacts |`contacts get <resource_name>`|PASS| 2026-02-06 |Gets contact|
| 210 | Contacts |`contacts batch-get <res1>,<res2>`|PASS| 2026-02-06 |Batch retrieves contacts|
| 211 | Contacts |`contacts search-directory "marios"`|PASS| 2026-02-06 |Searches Workspace directory|
| 212 | Contacts |`contacts list-directory --max 5`|PASS| 2026-02-06 |Lists directory with pagination|
| 213 | Contacts |`contacts update <resource_name> -e "new@x.com"`|PASS| 2026-02-06 |Contact updated|
| 214 | Contacts |`contacts delete <resource_name>`|PASS| 2026-02-06 |Contact deleted|
| 215 | Convert |`convert md-to-doc /tmp/test.md -t "Title"`|PASS| 2026-02-06 |Markdown to Google Doc|
| 216 | Convert |`convert md-to-pdf /tmp/test.md /tmp/out.pdf`|PASS| 2026-02-06 |Markdown to PDF (35KB)|
| 217 | Convert |`convert md-to-slides /tmp/test.md -t "Title"`|PASS| 2026-02-06 |Markdown to Slides|

---

## All Bugs Found & Fixed

| # | Service | Operation | Issue | Fix |
|---|---------|-----------|-------|-----|
| 1 | Drive | list-revisions | `supportsAllDrives` not valid for revisions API | Removed parameter |
| 2 | Drive | get-revision | `supportsAllDrives` not valid for revisions API | Removed parameter |
| 3 | Drive | resolve-comment | Wrong API method (`comments().update()`) | Changed to `replies().create()` with `action: "resolve"` |
| 4 | Drive | comments/replies | `supportsAllDrives` invalid for these endpoints | Removed parameter |
| 5 | Gmail | read | Case-sensitive header lookup fails on API-sent messages | Case-insensitive `{k.lower(): v}` lookup |
| 6 | Gmail | reply | Same case-sensitive header bug + `format="metadata"` insufficient | Case-insensitive headers + `format="full"` |
| 7 | Calendar | list events | `colorId` missing from event output | Added `colorId` to output |
| 8 | Docs | rename-tab | `tabId` placed outside `tabProperties` dict | Moved `tabId` inside `tabProperties` |
| 9 | Docs | reorder-tab | Same `tabId` placement bug | Moved `tabId` inside `tabProperties` |
| 10 | Docs | paragraph-border | Missing required `padding` field in border style | Added `padding: {magnitude: 6.0, unit: "PT"}` |
| 11 | Slides | set-speaker-notes | `deleteText` fails when notes are empty | Check text existence before deleting |
| 12 | Slides | transform-element | Non-invertible matrix when only `scaleX` set | Default unset `scaleX`/`scaleY` to 1.0 |

---

## Test Environment

- Platform: Linux 6.8.0-90-generic
- Python: 3.12 (via uv)
- GWS Version: 1.0.0
- Auth: OAuth (multi-account mode)

---

## Changelog

| Date | Description |
|------|-------------|
| 2026-02-05 | Initial test run: Infra, Drive, Docs, Sheets, Slides, Gmail. Fixed 10 bugs. |
| 2026-02-06 | Completed: Calendar, Contacts, Convert. Fixed 2 bugs (Slides). All 217 tests done. |

# Google Workspace Skill for Claude Code

A Claude Code skill that enables Claude to manage your Google Workspace: Docs, Sheets, Slides, Drive, Gmail, Calendar, and Contacts.

## What Claude Can Do

With this skill installed, Claude can:

- **Documents**: Read, create, edit, and format Google Docs
- **Spreadsheets**: Read/write data, format cells, manage sheets
- **Presentations**: Create slides, add text and images, format content
- **Drive**: Upload, download, search, share, and organize files
- **Email**: Read, send, reply to, and search Gmail messages
- **Calendar**: View and create events, manage schedules
- **Contacts**: List and manage your contacts
- **Convert**: Transform Markdown files to Docs, Slides, or PDF (with diagram support)

## Installation

### 1. Clone to your skills directory

```bash
git clone https://github.com/your-username/google-workspace ~/.claude/skills/google-workspace
```

### 2. Set up Google Cloud OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable these APIs:
   - Google Drive API
   - Google Docs API
   - Google Sheets API
   - Google Slides API
   - Gmail API
   - Google Calendar API
   - People API
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Select **Desktop application**
6. Download the JSON file
7. Save it as `~/.claude/.google/client_secret.json`

### 3. Authenticate

Run any command or ask Claude to use the skill. A browser window will open for Google sign-in. Grant access to the requested services and authentication completes automatically.

## Usage

Once installed, simply ask Claude to work with your Google Workspace:

> "Read my latest Google Doc and summarize it"

> "Create a spreadsheet with this data..."

> "Send an email to john@example.com about the meeting"

> "Convert this markdown report to a PDF"

> "What's on my calendar tomorrow?"

Claude will use the skill automatically when your request involves Google Workspace services.

## Configuration

### Enable/Disable Services

For security, you can disable services you don't need:

```bash
# Disable Gmail access
uv run gws config disable gmail

# Re-enable later
uv run gws config enable gmail

# See what's enabled
uv run gws config list
```

### Custom Kroki Server

For diagram rendering, the skill uses [Kroki](https://kroki.io) (public server by default). To use a self-hosted instance:

```bash
# Set custom Kroki URL
uv run gws config set-kroki http://localhost:8000

# Or use environment variable
export GWS_KROKI_URL=http://localhost:8000
```

## Requirements

- [uv](https://docs.astral.sh/uv/) package manager
- Google Cloud OAuth credentials (see Installation)
- Claude Code CLI

## Credential Storage

All credentials are stored in `~/.claude/.google/`:

| File | Purpose |
|------|---------|
| `client_secret.json` | OAuth client credentials (you provide) |
| `token.json` | Access token (auto-generated on first auth) |
| `gws_config.json` | Service enable/disable settings |

## Skill Documentation

For detailed command reference and examples, see [SKILL.md](SKILL.md).

## License

MIT License - See [LICENSE](LICENSE) for details.

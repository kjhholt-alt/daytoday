# DayToDay

A daily productivity tool that aggregates your Outlook meetings, Teams transcripts, OneNote pages, and Word documents into a searchable, indexed living document.

Run it once a day and DayToDay collects everything into a summary you can reference back to anytime.

## Features

- **Outlook Calendar Integration** - Pulls all meetings for the day with attendees, agendas, and details
- **Teams Transcript Support** - Retrieves meeting transcripts when available
- **OneNote References** - Captures recently modified OneNote pages
- **Word Document Tracking** - Scans configured directories for modified `.docx` files and extracts content
- **Searchable History** - Full-text search across all meetings, notes, and documents
- **Daily Summaries** - Auto-generated markdown summaries indexed by date
- **One-Click Launch** - Run via a `.bat` file on your desktop

## Prerequisites

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** - [Download](https://nodejs.org/)
- **Microsoft Azure App Registration** (see setup below)

## Quick Start

### 1. First-Time Setup

```
scripts\setup.bat
```

This creates the virtual environment, installs dependencies, and prepares the database.

### 2. Azure App Registration

You need to register an application in Azure to access Microsoft 365 data:

1. Go to [Azure Portal](https://portal.azure.com) > **Microsoft Entra ID** > **App registrations** > **New registration**
2. Name: `DayToDay App`
3. Supported account types: **Accounts in any organizational directory**
4. Redirect URI: Select **Public client/native (mobile & desktop)**, set to `http://localhost`
5. Click **Register**
6. Copy the **Application (client) ID**
7. Go to **API permissions** > **Add a permission** > **Microsoft Graph** > **Delegated permissions**
8. Add these permissions:
   - `Calendars.Read`
   - `Notes.Read`
   - `OnlineMeetingTranscript.Read.All`
   - `User.Read`
9. Click **Grant admin consent** (if you are an admin, or ask your admin)

### 3. Configure

Edit `config/config.json`:

```json
{
    "azure_client_id": "paste-your-client-id-here",
    "azure_authority": "https://login.microsoftonline.com/common",
    "graph_scopes": [
        "Calendars.Read",
        "Notes.Read",
        "OnlineMeetingTranscript.Read.All",
        "User.Read"
    ],
    "word_doc_directories": [
        "C:\\Users\\YourName\\Documents"
    ],
    "token_cache_path": "./config/token_cache.bin"
}
```

- **azure_client_id**: Your Application (client) ID from step 6 above
- **azure_authority**: Use `https://login.microsoftonline.com/common` for multi-tenant, or replace `common` with your tenant ID
- **word_doc_directories**: List of folders to scan for Word documents
- **token_cache_path**: Where to store the authentication token (encrypted on Windows)

### 4. Run

```
scripts\daytoday.bat
```

This will:
1. Authenticate with Microsoft (browser popup on first run)
2. Collect today's meetings, transcripts, notes, and documents
3. Start the backend and frontend servers
4. Open the app in your browser at `http://localhost:3000`

## Usage

- **Today** - View the current day's summary with all meetings, notes, and docs
- **History** - Browse past daily summaries
- **Search** - Search across all collected data
- **Settings** - Manage your Microsoft account connection
- **Run Collection** button - Re-collect data for the current day at any time

## Architecture

```
scripts/daytoday.bat
  -> python manage.py collect_today    (collects data from Microsoft Graph API)
  -> python manage.py runserver        (Django REST API on port 8000)
  -> npm start                         (React frontend on port 3000)
```

- **Backend**: Django 4.2 + Django REST Framework
- **Frontend**: React 18 + Material UI
- **Database**: SQLite (portable, zero-config)
- **Auth**: MSAL Python (Microsoft Authentication Library)
- **APIs**: Microsoft Graph API v1.0

## Project Structure

```
daytoday/
├── backend/                    Django project
│   ├── core/                   Main app (models, views, services)
│   │   ├── services/           Business logic layer
│   │   │   ├── auth_service.py     MSAL authentication
│   │   │   ├── calendar_service.py Outlook calendar
│   │   │   ├── teams_service.py    Teams transcripts
│   │   │   ├── onenote_service.py  OneNote pages
│   │   │   ├── word_service.py     Word document reader
│   │   │   └── summary_service.py  Orchestrator
│   │   └── management/commands/
│   │       └── collect_today.py    CLI collection command
│   └── tests/                  Backend test suite
├── frontend/                   React application
│   └── src/
│       ├── components/         Reusable UI components
│       ├── pages/              Page views
│       └── services/           API client
├── scripts/
│   ├── daytoday.bat            Main launcher
│   └── setup.bat               First-time setup
├── config/
│   ├── config.template.json    Config template
│   └── config.json             Your config (gitignored)
└── README.md
```

## Running Tests

```bash
# Activate virtual environment
venv\Scripts\activate

# Run backend tests
python backend\manage.py test tests -v 2
```

## Troubleshooting

**"Config created from template" error**
- Edit `config/config.json` with your Azure Client ID

**"Authentication failed" error**
- Verify your Azure App Registration has the correct redirect URI (`http://localhost`)
- Ensure the required API permissions are granted
- Try deleting `config/token_cache.bin` and re-authenticating

**"No summary for today" on the frontend**
- Click the "Run Collection" button or run `scripts\daytoday.bat`

**Teams transcripts not showing**
- `OnlineMeetingTranscript.Read.All` may require admin consent in your organization
- Only scheduled (calendar-backed) Teams meetings expose transcripts
- The app works fully without transcript permissions

**Word documents not appearing**
- Check that `word_doc_directories` in config.json points to valid folders
- Only `.docx` files modified today are collected

## Sharing with Others

To share this app with another person:

1. Give them the project folder (or have them clone from git)
2. They run `scripts\setup.bat`
3. They register their own Azure App or you add them to yours
4. They edit `config/config.json` with their settings
5. They run `scripts\daytoday.bat`

## License

Proprietary - All rights reserved.

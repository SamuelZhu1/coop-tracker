# Co-op Application Tracker

Automated pipeline that reads co-op response emails from Gmail, extracts structured data using the Claude Haiku API, and logs it to a Google Sheet — running on a GitHub Actions cron every 6 hours.

## Problem

Applying to 30+ co-op positions means losing track of where things stand. Rejections, interview invites, and acknowledgements all look similar in your inbox. This project eliminates manual tracking.

## Architecture

```
Gmail (unprocessed co-op emails)
        │
        ▼
  gmail_client.py   ← fetches emails matching keyword search
        │
        ▼
  claude_client.py  ← sends email to Claude Haiku, gets back JSON
        │               { company, role, status, deadline }
        ▼
  sheets_client.py  ← appends a row to Google Sheet
        │
        ▼
  gmail_client.py   ← labels email "coop-tracker-processed"
                        (prevents reprocessing on next run)

GitHub Actions cron fires every 6 hours → runs src/main.py
```

## Google Sheet columns

| Date Received | Company | Role | Status | Deadline | Email Subject | Email Snippet |
|---|---|---|---|---|---|---|

Status values: `rejection`, `interview_invite`, `received`, `other`

## Setup

### 1. Clone and install

```bash
git clone https://github.com/SamuelZhu1/coop-tracker
cd coop-tracker
pip install -r requirements.txt
```

### 2. Get API credentials

**Anthropic API key**
- Go to [console.anthropic.com](https://console.anthropic.com), create a key, set a $5 spend cap.
- Set environment variable: `ANTHROPIC_API_KEY=your-key`

**Google OAuth (Gmail + Sheets)**
- Go to [console.cloud.google.com](https://console.cloud.google.com), create a project.
- Enable **Gmail API** and **Google Sheets API**.
- Create OAuth credentials: *APIs & Services → Credentials → Create → OAuth client ID → Desktop app*
- Download the JSON and save as `credentials.json` in the repo root.

**First run (local)**
```bash
ANTHROPIC_API_KEY=your-key SPREADSHEET_ID=your-sheet-id python src/main.py
```
A browser will open for Google OAuth consent. After you click Allow, `token.json` is saved automatically — subsequent runs don't need a browser.

### 3. Set GitHub Actions secrets

In your repo: *Settings → Secrets and variables → Actions → New repository secret*

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `GOOGLE_TOKEN` | full contents of `token.json` |
| `GOOGLE_CREDENTIALS` | full contents of `credentials.json` |
| `SPREADSHEET_ID` | the ID from your Sheet's URL (`/d/<ID>/edit`) |

### 4. Trigger manually

Go to *Actions → Run Co-op Tracker → Run workflow* to test it immediately without waiting for the cron.

## Extraction prompt

```
Extract the following from this co-op application email.
Respond ONLY with valid JSON. No markdown fences, no explanation, no other text.

Fields:
- company (string)
- role (string)
- status: one of "rejection", "interview_invite", "received", "other"
- deadline: YYYY-MM-DD string or null
```

The prompt asks for JSON-only output. A post-processing step strips markdown fences in case the model wraps the response anyway (it sometimes does).

## Error handling

Each email is processed inside a `try/except` block. If one email fails (malformed body, API error, bad JSON from Claude), it's logged and skipped — the rest of the run continues. Emails are only labelled `coop-tracker-processed` after successful logging, so a failed email will be retried on the next run.

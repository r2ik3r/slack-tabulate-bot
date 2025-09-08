# Tabulate Slack Bot

A Slack app that detects pasted tabular text (CSV/TSV/semicolon/pipe/multi‑space), cleans it, and posts a scrollable CSV snippet in the same conversation (channel, DM, thread). No manual formatting required.


## 🗺️ Architecture Diagram

```mermaid
flowchart TD
  subgraph Slack
    A[User] -- "/csv, mention, paste" --> B[Slack Workspace]
  end
  B -- Event/API --> C[Slack App (Tabulate)]
  C -- Socket Mode or HTTP --> D[tabulate.bot.handlers]
  D -- Table Detection --> E[tabulate.utils.table_formatter]
  D -- CSV Snippet --> F[Slack API: files_upload]
  F -- Snippet Link --> B
```

***

## ⚡ Quickstart (Under 60 Seconds)

1) Clone & install
```sh
git clone https://github.com/r2ik3r/slack-tabulate-bot.git
cd slack-tabulate-bot
poetry install
```

2) Add environment variables (.env)
```env
# Socket Mode (local dev)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...   # must include connections:write

# HTTP/OAuth (prod)
SLACK_SIGNING_SECRET=...
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
```

3) Run locally (Socket Mode)
```sh
PYTHONPATH=./src poetry run python -m tabulate.bot.run_dev
```

4) Expose HTTP (optional, for OAuth/events)
```sh
ngrok http 3000
```
Update Slack App settings to use the ngrok HTTPS URL for OAuth, Events, Interactivity, and the /csv command.

***

## 🚀 How It Works

Tabulate listens in channels, groups, DMs, and threads. When a table is detected, it:
1. Isolates the table from surrounding text.  
2. Parses and cleans it (delimiters, uneven rows, spacing).  
3. Adds a row index if missing.  
4. Uploads a CSV snippet with a short summary while keeping before/after context intact.

All entry points behave the same and yield CSV snippets:
- /csv command
- @app_mention
- Auto-detection on message events

***

## ✨ Features

- CSV snippet uploads (v2 flow) for consistent, scrollable previews.  
- Robust detection across CSV/TSV/semicolon/pipe and multi‑space layouts.  
- Conservative heuristics to avoid false positives on normal prose.  
- Context preserved; small inter‑push delay minimizes out‑of‑order rendering in threads.

***

## 📂 Project Structure

```
slack-tabulate-bot/
├── .env
├── .gitignore
├── LICENSE
├── poetry.lock
├── pyproject.toml
├── README.md
└── src/
  └── tabulate/
    ├── __init__.py
    ├── bot/
    │   ├── __init__.py
    │   ├── app.py         # HTTP/OAuth server (Bolt + Flask)
    │   ├── handlers.py    # /csv, app_mention, message; uploads & context
    │   └── run_dev.py     # Socket Mode entry point
    └── utils/
      ├── __init__.py
      └── table_formatter.py  # detection, parsing, CSV rendering
```

***

## 🛠 Setup for Distribution

Tabulate is a public Slack App using OAuth 2.0; a public HTTPS URL is required for OAuth redirects, Events, and Interactivity.

***

## 1️⃣ Configure Your Slack App

- Create a new app (From scratch) and select your workspace.  
- Bot Token Scopes (OAuth & Permissions):
  - app_mentions:read
  - chat:write
  - commands
  - files:write
- Create a Slash Command:
  - /csv (set Request URL after you have a public URL)
- Capture credentials from Basic Information:
  - Client ID, Client Secret, Signing Secret

***

## 2️⃣ Local Environment Setup

- Install Poetry; install dependencies (see Quickstart).  
- Create a .env with either Socket Mode tokens or HTTP/OAuth secrets.  
- Socket Mode: enable it and create an App‑Level token (connections:write), then run the dev entry point.

***

## 3️⃣ Deploy (HTTP/OAuth mode)

- Deploy anywhere (Render/Railway/your infra).  
- Start command:
```sh
poetry run gunicorn "tabulate.bot.app:server" --chdir ./src
```

- Configure your Slack App:
  - Redirect URL:
    ```
    https://<YOUR_PUBLIC_URL>/slack/oauth/callback
    ```
  - Events Request URL:
    ```
    https://<YOUR_PUBLIC_URL>/slack/events
    ```
  - Interactivity Request URL:
    ```
    https://<YOUR_PUBLIC_URL>/slack/events
    ```
  - Slash Command /csv → Request URL:
    ```
    https://<YOUR_PUBLIC_URL>/slack/events
    ```

- Subscribe to events:
  ```
  app_mention
  message.channels
  message.groups
  message.im
  message.mpim
  ```

***

## ☁ One‑Click Render (Optional)

- Build:
```sh
poetry install
```

- Start:
```sh
poetry run gunicorn "main.tabulate.bot.app:server" --chdir ./src
```

- Add env vars in the service settings, then update Slack App URLs to your Render domain.

***

## 4️⃣ Install & Run

Install to workspace:
```
https://<YOUR_PUBLIC_URL>/slack/install
```

Local testing:
```sh
PYTHONPATH=./src poetry run python -m tabulate.bot.run_dev

# HTTP mode (OAuth flow)
poetry run gunicorn "tabulate.bot.app:server" --chdir ./src
```

***

## 📦 Data Directory

For HTTP/OAuth mode, the app stores OAuth installations in ./data. Ensure it exists and is writable:
```sh
mkdir -p data
```

***

## 💡 Notes & Tips

- Large messages: auto‑detection is skipped above a conservative size cap; use /csv or upload a file.  
- Ordering: a tiny sleep is applied between consecutive uploads and before trailing context to minimize out‑of‑order rendering in busy threads.  
- Permissions: only app_mentions:read, chat:write, commands, files:write are required for core functionality.

***

## 🐞 Troubleshooting

- “Invalid Request URL”: verify your HTTPS endpoint and that it matches Slack App settings.  
- Not uploading: ensure files:write is granted and the app is a member of the destination channel/DM.  
- No response: check event subscriptions and that the bot is installed in the conversation.

***

## 🔐 Security

- Keep tokens (xoxb-/xapp-) in secrets; never commit .env.  
- Use least‑privilege scopes.  
- For production HTTP, ensure HTTPS and validate Slack request signatures.

***

## 📜 License

MIT — see LICENSE.

***
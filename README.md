# Tabulate Slack Bot

A Slack app that detects pasted tabular text (CSV/TSV/semicolon/pipe/multi‑space), cleans it, and posts a scrollable CSV snippet to the same conversation (channel, DM, thread). No manual formatting required.

## Quickstart

- Prerequisites: Python 3.9+, Poetry, a Slack workspace and a Slack App (created from scratch).
- Clone and install:
  - git clone https://github.com/r2ik3r/slack-tabulate-bot.git
  - cd slack-tabulate-bot
  - poetry install

- Environment variables:
  - Development (Socket Mode): SLACK_BOT_TOKEN, SLACK_APP_TOKEN (xapp-... with connections:write)
  - HTTP/OAuth: SLACK_SIGNING_SECRET, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET

- Run (Socket Mode, local):
  - PYTHONPATH=./src poetry run python -m main.tabulate.bot.run_dev

- Expose HTTP (optional, for OAuth/events):
  - ngrok http 3000, update Slack App URLs to use the ngrok HTTPS endpoint.

## What it does

- Listens to messages (channels, groups, DMs, threads). On detecting a table, it extracts, cleans headers/rows/columns, adds a row index if missing, and uploads a CSV snippet with a brief summary (rows/columns), preserving surrounding context.
- Unified outputs: /csv command, @app_mention, and auto-detection for normal messages all produce CSV snippet uploads via the same path.

## Features

- CSV snippet uploads (files_upload_v2 under the hood), not rich‑text messages, for consistent, scrollable previews.
- Robust detection: CSV/TSV/semicolon/pipe and multi‑space tables, with conservative heuristics to avoid false positives on prose.
- Context preservation before and after tables; minimal inter‑push delay to reduce out‑of‑order rendering in threads.

## Project layout

- src/main/tabulate/bot/app.py — HTTP/OAuth server (Bolt + Flask)
- src/main/tabulate/bot/run_dev.py — Socket Mode entry point
- src/main/tabulate/bot/handlers.py — listeners for /csv, app_mention, message; upload logic
- src/main/tabulate/utils/table_formatter.py — detection, parsing, CSV rendering

## Configure Slack app

- Create an app (From scratch) and install to workspace.
- Add Bot Token Scopes:
  - app_mentions:read
  - chat:write
  - commands
  - files:write
- Enable a Slash Command:
  - /csv (Request URL set to your events endpoint)
- Event Subscriptions (HTTP mode):
  - Request URL: https://<PUBLIC_URL>/slack/events
  - Subscribe to: app_mention, message.channels, message.groups, message.im, message.mpim
- Interactivity:
  - Request URL: https://<PUBLIC_URL>/slack/events
- OAuth v2:
  - Redirect URL: https://<PUBLIC_URL>/slack/oauth/callback

## Run locally (Socket Mode)

- Ensure:
  - SLACK_BOT_TOKEN = xoxb-...
  - SLACK_APP_TOKEN = xapp-... with connections:write
- Start:
  - PYTHONPATH=./src poetry run python -m main.tabulate.bot.run_dev
- No public URL is required for Socket Mode.

## Deploy (HTTP/OAuth)

- Host on Render/Railway/your platform. Environment:
  - SLACK_SIGNING_SECRET, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET
- Start command:
  - poetry run gunicorn "main.tabulate.bot.app:server" --chdir ./src
- Configure:
  - Redirect URL: https://<PUBLIC_URL>/slack/oauth/callback
  - Events URL: https://<PUBLIC_URL>/slack/events
  - Interactivity URL: https://<PUBLIC_URL>/slack/events
  - Slash command /csv → https://<PUBLIC_URL>/slack/events

## File uploads and v2 migration

- This app uses files_upload_v2 (SDK convenience) that wraps files.getUploadURLExternal + files.completeUploadExternal. New Slack apps cannot use files.upload; legacy deprecation ends Nov 12, 2025.
- v2 uploads are asynchronous server‑side; a short delay is applied between consecutive uploads and before trailing context to reduce apparent out‑of‑order rendering.

## Data directory

- A ./data directory is used for OAuth installation storage in HTTP mode; ensure it exists and is writable by the process.

## Tips and notes

- Large messages: auto‑detection is skipped beyond a conservative size cap; use /csv or upload a file.
- Ordering: a tiny sleep between pushes stabilizes ordering; all posts share thread_ts when applicable to keep conversation context intact.
- Permissions: chat:write, files:write, commands, app_mentions:read are required; add read scopes only if needed for your workflow.

## Troubleshooting

- Invalid Request URL: ensure the public URL is reachable over HTTPS and matches the configured endpoints.
- Not uploading: verify files:write scope and that the app is installed to the target channel; new apps must use files_upload_v2 via SDKs.
- No response: confirm the app is in the channel/DM and that event subscriptions are enabled.

## Security and compliance

- Tokens (xoxb-/xapp-) must be stored as secrets; do not commit .env. Restrict app scopes to the minimum required.
- Socket Mode eliminates inbound public endpoints for local development; for production, use HTTPS and validate signatures.

## License

MIT — see LICENSE.

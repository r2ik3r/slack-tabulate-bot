# Table Beautifier Slack Bot

A Slack app that detects pasted tabular text (CSV/TSV/semicolon/pipe/multi‑space), cleans it, and posts a scrollable CSV snippet to the same conversation (channel, DM, thread). No manual formatting required.[3][4]

## Quickstart

- Prerequisites: Python 3.9+, Poetry, a Slack workspace and a Slack App (created from scratch).[5]
- Clone and install:
  - git clone https://github.com/your-username/slack-table-beautifier-bot.git
  - cd slack-table-beautifier-bot
  - poetry install[5]

- Environment variables:
  - Development (Socket Mode): SLACK_BOT_TOKEN, SLACK_APP_TOKEN (xapp-... with connections:write)[6][7]
  - HTTP/OAuth: SLACK_SIGNING_SECRET, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET[8]

- Run (Socket Mode, local):
  - PYTHONPATH=./src poetry run python -m main.tablebeautifier.bot.run_dev[6]

- Expose HTTP (optional, for OAuth/events):
  - ngrok http 3000, update Slack App URLs to use the ngrok HTTPS endpoint.[5]

## What it does

- Listens to messages (channels, groups, DMs, threads). On detecting a table, it extracts, cleans headers/rows/columns, adds a row index if missing, and uploads a CSV snippet with a brief summary (rows/columns), preserving surrounding context.[9][3]
- Unified outputs: /csv command, @app_mention, and auto-detection for normal messages all produce CSV snippet uploads via the same path.[10]

## Features

- CSV snippet uploads (files_upload_v2 under the hood), not rich‑text messages, for consistent, scrollable previews.[2]
- Robust detection: CSV/TSV/semicolon/pipe and multi‑space tables, with conservative heuristics to avoid false positives on prose.[9]
- Context preservation before and after tables; minimal inter‑push delay to reduce out‑of‑order rendering in threads.[4]

## Project layout

- src/main/tablebeautifier/bot/app.py — HTTP/OAuth server (Bolt + Flask)[5]
- src/main/tablebeautifier/bot/run_dev.py — Socket Mode entry point[7]
- src/main/tablebeautifier/bot/handlers.py — listeners for /csv, app_mention, message; upload logic[5]
- src/main/tablebeautifier/utils/table_formatter.py — detection, parsing, CSV rendering[9]

## Configure Slack app

- Create an app (From scratch) and install to workspace.[5]
- Add Bot Token Scopes:
  - app_mentions:read
  - chat:write
  - commands
  - files:write[11][12]
- Enable a Slash Command:
  - /csv (Request URL set to your events endpoint)[13]
- Event Subscriptions (HTTP mode):
  - Request URL: https://<PUBLIC_URL>/slack/events
  - Subscribe to: app_mention, message.channels, message.groups, message.im, message.mpim[14]
- Interactivity:
  - Request URL: https://<PUBLIC_URL>/slack/events[5]
- OAuth v2:
  - Redirect URL: https://<PUBLIC_URL>/slack/oauth/callback[8]

## Run locally (Socket Mode)

- Ensure:
  - SLACK_BOT_TOKEN = xoxb-...
  - SLACK_APP_TOKEN = xapp-... with connections:write[7]
- Start:
  - PYTHONPATH=./src poetry run python -m main.tablebeautifier.bot.run_dev[7]
- No public URL is required for Socket Mode.[7]

## Deploy (HTTP/OAuth)

- Host on Render/Railway/your platform. Environment:
  - SLACK_SIGNING_SECRET, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET[8]
- Start command:
  - poetry run gunicorn "main.tablebeautifier.bot.app:server" --chdir ./src[5]
- Configure:
  - Redirect URL: https://<PUBLIC_URL>/slack/oauth/callback
  - Events URL: https://<PUBLIC_URL>/slack/events
  - Interactivity URL: https://<PUBLIC_URL>/slack/events
  - Slash command /csv → https://<PUBLIC_URL>/slack/events[5]

## File uploads and v2 migration

- This app uses files_upload_v2 (SDK convenience) that wraps files.getUploadURLExternal + files.completeUploadExternal. New Slack apps cannot use files.upload; legacy deprecation ends Nov 12, 2025.[2]
- v2 uploads are asynchronous server‑side; a short delay is applied between consecutive uploads and before trailing context to reduce apparent out‑of‑order rendering.[15]

## Data directory

- A ./data directory is used for OAuth installation storage in HTTP mode; ensure it exists and is writable by the process.[8]

## Tips and notes

- Large messages: auto‑detection is skipped beyond a conservative size cap; use /csv or upload a file.[9]
- Ordering: a tiny sleep between pushes stabilizes ordering; all posts share thread_ts when applicable to keep conversation context intact.[4]
- Permissions: chat:write, files:write, commands, app_mentions:read are required; add read scopes only if needed for your workflow.[12][11]

## Troubleshooting

- Invalid Request URL: ensure the public URL is reachable over HTTPS and matches the configured endpoints.[5]
- Not uploading: verify files:write scope and that the app is installed to the target channel; new apps must use files_upload_v2 via SDKs.[2]
- No response: confirm the app is in the channel/DM and that event subscriptions are enabled.[14]

## Security and compliance

- Tokens (xoxb-/xapp-) must be stored as secrets; do not commit .env. Restrict app scopes to the minimum required.[1]
- Socket Mode eliminates inbound public endpoints for local development; for production, use HTTPS and validate signatures.[7]

## License

MIT — see LICENSE.[5]

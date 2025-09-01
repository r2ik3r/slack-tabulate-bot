# /src/main/tabulate/bot/app.py

import os
import sys
import logging
import flask
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.oauth.installation_store.file import FileInstallationStore
from slack_sdk.oauth.state_store.file import FileOAuthStateStore

# Ensure project root is in sys.path for safe imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Import the handler registration function
from src.main.tabulate.bot.handlers import register_handlers

# --- Initialization ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Environment validation ---
required_vars = [
    "SLACK_CLIENT_ID",
    "SLACK_CLIENT_SECRET",
    "SLACK_SIGNING_SECRET"
]
missing_vars = [v for v in required_vars if not os.environ.get(v)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# --- OAuth & Installation Setup for Distribution ---
state_store = FileOAuthStateStore(expiration_seconds=300, base_dir="./data")
installation_store = FileInstallationStore(base_dir="./data")

oauth_settings = OAuthSettings(
    client_id=os.environ["SLACK_CLIENT_ID"],
    client_secret=os.environ["SLACK_CLIENT_SECRET"],
    scopes=["app_mentions:read", "chat:write", "commands", "files:write"],
    installation_store=installation_store,
    state_store=state_store,
)

# Initialize the Bolt App for production
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    oauth_settings=oauth_settings
)

# Register all the event handlers from the shared handlers.py file
register_handlers(app)

# --- Flask Web Server Setup ---
server = flask.Flask(__name__)
handler = SlackRequestHandler(app)

@server.route("/slack/install", methods=["GET"])
def install():
    return handler.handle_install_path(flask.request)

@server.route("/slack/oauth/callback", methods=["GET"])
def oauth_callback():
    return handler.handle_callback_path(flask.request)

@server.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(flask.request)

@server.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for production monitoring."""
    return {"status": "ok"}, 200

if __name__ == "__main__":
    logger.info("🤖 Tabulate bot (PROD) is starting...")
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

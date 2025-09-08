# /src/tabulate/bot/run_dev.py

import os
import sys
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Ensure project root is in sys.path for safe imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Import the handler registration function
from tabulate.bot.handlers import register_handlers

# --- Initialization ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Development Setup (Socket Mode) ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    logger.error("Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN for Socket Mode.")
    sys.exit(1)

# Initialize the Bolt App for development
app = App(token=SLACK_BOT_TOKEN)

# Register all the event handlers from the shared handlers.py file
register_handlers(app)

# --- Start the App in Socket Mode ---
if __name__ == "__main__":
    logger.info("🤖 Tabulate bot (DEV) is starting in Socket Mode...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

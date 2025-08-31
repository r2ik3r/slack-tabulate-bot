# src/main/tablebeautifier/bot/handlers.py

import re
import logging
from io import StringIO
import pandas as pd
import time

from tablebeautifier.utils.table_formatter import TableFormatter

logger = logging.getLogger(__name__)

HELP_TEXT = """Hi there! I'm the Table Beautifier bot. 🤖 You can:
1. Paste table-like data (CSV, TSV, etc.) to automatically create a scrollable CSV snippet.
2. Use the /csv command with your data to also create a CSV snippet.
3. Mention me (`@Table Beautifier`) with your data to format it as a text-based table.
"""

formatter = TableFormatter()

def register_handlers(app):
    """
    Register Bolt handlers on the given `app`.
    Improvements made:
    - cache bot_user_id at startup to avoid auth_test() on every message (performance).
    - skip auto-detection for messages that include files/attachments (don't interfere with uploads).
    - preserve thread_ts and DM handling (same semantics as your original).
    """
    # Cache bot user id to avoid calling auth_test repeatedly in hot path.
    bot_user_id = None
    try:
        auth_resp = app.client.auth_test()
        bot_user_id = auth_resp.get("user_id")
        logger.debug("Cached bot_user_id for TableBeautifier: %s", bot_user_id)
    except Exception:
        logger.debug("Could not fetch bot_user_id at startup; will tolerate per-message checks.")

    def _open_dm_if_needed(client, channel_id, user_id):
        if channel_id and channel_id.startswith("D"):
            if not user_id:
                raise RuntimeError("Missing user_id for DM channel.")
            resp = client.conversations_open(users=user_id)
            return resp["channel"]["id"]
        return channel_id

    def create_and_post_snippets(client, text, channel_id, user_id, thread_ts=None):
        """
        Main work: detect tables, post CSV files for each table, and post trailing context.
        Adds a tiny delay between pushes to stabilize ordering in Slack without noticeable latency.
        """
        try:
            post_channel_id = _open_dm_if_needed(client, channel_id, user_id)
            processed_tables, final_context = formatter.process_all_inputs(text)

            if not processed_tables:
                logger.debug("No tables found; nothing to upload.")
                return

            # Limit number of tables per message to avoid spam (safety)
            max_tables = 25
            if len(processed_tables) > max_tables:
                logger.warning("Message contains %d tables; truncating to %d.", len(processed_tables), max_tables)
                processed_tables = processed_tables[:max_tables]

            for context, csv_content, rows, cols in processed_tables:
                comment_parts = []
                if context:
                    comment_parts.append(context.strip())
                #comment_parts.append(f"📊 Rows: {rows} -  Columns: {cols}")
                comment_parts.append(f"• Rows: {rows} • Columns: {cols}")
                initial_comment = "\n\n".join(comment_parts)

                # upload CSV content
                try:
                    client.files_upload_v2(
                        channel=post_channel_id,
                        content=csv_content,
                        filename="data.csv",
                        initial_comment=initial_comment,
                        thread_ts=thread_ts,
                    )
                except AttributeError:
                    # older SDK fallback
                    client.files_upload(
                        channels=post_channel_id,
                        content=csv_content,
                        filename="data.csv",
                        initial_comment=initial_comment,
                        thread_ts=thread_ts,
                    )

                # minimal spacing to avoid interleaving/racey ordering
                time.sleep(0.12)

            # brief pause before trailing context so snippet previews render first
            if final_context:
                time.sleep(0.12)
                client.chat_postMessage(channel=post_channel_id, text=final_context, thread_ts=thread_ts)

        except Exception:
            logger.exception("Failed to create or post snippets.")
            raise

    def format_as_text_table(text: str) -> str:
        """
        Retained utility (not used by handlers anymore).
        """
        processed_tables, final_context = formatter.process_all_inputs(text)
        if not processed_tables:
            raise ValueError("No table-like content found in message.")

        parts = []
        for context, csv_content, rows, cols in processed_tables:
            if context:
                parts.append(context.strip())
            df = pd.read_csv(StringIO(csv_content))
            parts.append(formatter.format_as_text_table(df))

        if final_context:
            parts.append(final_context.strip())

        return "\n\n".join(parts)

    @app.command("/csv")
    def handle_csv_command(ack, respond, command, client):
        """
        Explicit command handler — ack quickly, then process.
        """
        ack()
        text = command.get("text", "")
        if not text or not text.strip():
            respond("Please provide table-like data after the `/csv` command.")
            return

        try:
            create_and_post_snippets(
                client=client,
                text=text,
                channel_id=command.get("channel_id"),
                user_id=command.get("user_id"),
                thread_ts=command.get("thread_ts"),
            )
        except Exception as e:
            logger.exception("Error handling /csv command")
            respond(f"😕 Oops! I couldn't process that. {str(e)}")

    @app.event("app_mention")
    def handle_app_mention_events(event, client):
        """
        Mention -> produce the same CSV snippet uploads as other paths.
        """
        text = event.get("text", "") or ""
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts")

        # strip mention(s)
        text_without_mention = re.sub(r'^<@[^>]+>\s*', '', text).strip()
        if not text_without_mention:
            return

        if "help" in text_without_mention.lower():
            client.chat_postMessage(channel=channel_id, text=HELP_TEXT, thread_ts=thread_ts)
            return

        if not formatter.is_table_like(text_without_mention):
            client.chat_postMessage(
                channel=channel_id,
                text="I couldn't detect table-like data. Paste a CSV/TSV or use /csv with your data.",
                thread_ts=thread_ts,
            )
            return

        try:
            create_and_post_snippets(
                client=client,
                text=text_without_mention,
                channel_id=channel_id,
                user_id=event.get("user"),
                thread_ts=thread_ts,
            )
        except Exception as e:
            logger.exception("Failed to create snippet for app_mention")
            client.chat_postMessage(
                channel=channel_id,
                text=f"😕 Sorry, I couldn't process that. {str(e)}",
                thread_ts=thread_ts,
            )

    @app.event("message")
    def handle_message_events(event, client):
        """
        Auto-detect pasted table-like snippets in normal messages.
        Safety/performance improvements:
        - Ignore bot messages and subtypes.
        - Skip messages with uploaded files/attachments (we don't parse file contents here).
        - Use cached bot_user_id to ignore messages that mention the bot (those handled elsewhere).
        - Quick is_table_like() check (very cheap).
        - Small hard size cap to avoid blocking on huge text; recommend /csv or uploads for huge data.
        """
        if event.get("subtype") or event.get("bot_id"):
            return

        if event.get("files") or event.get("attachments"):
            return

        text = event.get("text", "") or ""
        if not text.strip():
            return

        # Avoid processing explicit mentions here (they are handled in app_mention)
        try:
            if bot_user_id and f"<@{bot_user_id}>" in text:
                return
        except Exception:
            pass

        if not formatter.is_table_like(text):
            return

        max_chars = 250_000
        if len(text) > max_chars:
            logger.info("Message too large for auto-parsing (%d chars); skipping. Suggest /csv or file upload.", len(text))
            return

        try:
            create_and_post_snippets(client, text, event.get("channel"), event.get("user"), thread_ts=event.get("thread_ts"))
        except Exception as e:
            logger.info(f"Auto-detection skipped or failed: {e}")

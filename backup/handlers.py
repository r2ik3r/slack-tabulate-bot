import re
import logging
from io import StringIO
import pandas as pd

from tablebeautifier.utils.table_formatter import TableFormatter

logger = logging.getLogger(__name__)

HELP_TEXT = """Hi there! I'm the Table Beautifier bot. 🤖 You can:
1. Paste table-like data (CSV, TSV, etc.) to automatically create a scrollable CSV snippet.
2. Use the `/csv` command with your data to also create a CSV snippet.
3. Mention me (`@Table Beautifier`) with your data to format it as a text-based table.
"""

formatter = TableFormatter()

def register_handlers(app):
    def _open_dm_if_needed(client, channel_id, user_id):
        if channel_id and channel_id.startswith("D"):
            if not user_id:
                raise RuntimeError("Missing user_id for DM channel.")
            resp = client.conversations_open(users=user_id)
            return resp["channel"]["id"]
        return channel_id

    def create_and_post_snippets(client, text, channel_id, user_id, thread_ts=None):
        try:
            post_channel_id = _open_dm_if_needed(client, channel_id, user_id)
            processed_tables, final_context = formatter.process_all_inputs(text)

            if not processed_tables:
                logger.info("No tables found; nothing to upload.")
                return

            for context, csv_content, rows, cols in processed_tables:
                comment_parts = []
                if context:
                    comment_parts.append(context.strip())
                comment_parts.append(f"📊 Rows: {rows} • Columns: {cols}")
                initial_comment = "\n\n".join(comment_parts)

                try:
                    client.files_upload_v2(
                        channel=post_channel_id,
                        content=csv_content,
                        filename="data.csv",
                        initial_comment=initial_comment,
                        thread_ts=thread_ts,
                    )
                except AttributeError:
                    client.files_upload(
                        channels=post_channel_id,
                        content=csv_content,
                        filename="data.csv",
                        initial_comment=initial_comment,
                        thread_ts=thread_ts,
                    )

            if final_context:
                client.chat_postMessage(channel=post_channel_id, text=final_context, thread_ts=thread_ts)

        except Exception:
            logger.exception("Failed to create or post snippets.")
            raise

    def format_as_text_table(text: str) -> str:
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
        text = event.get("text", "") or ""
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts")

        text_without_mention = re.sub(r'^<@[^>]+>\s*', '', text).strip()

        if not text_without_mention:
            return

        if "help" in text_without_mention.lower():
            client.chat_postMessage(channel=channel_id, text=HELP_TEXT, thread_ts=thread_ts)
            return

        if not formatter.is_table_like(text_without_mention):
            client.chat_postMessage(channel=channel_id,
                                    text="I couldn't detect table-like data. Paste a CSV/TSV or mention me with data.",
                                    thread_ts=thread_ts)
            return

        try:
            msg = format_as_text_table(text_without_mention)
            client.chat_postMessage(channel=channel_id, text=msg, thread_ts=thread_ts)
        except Exception as e:
            logger.exception("Failed to format table for app_mention")
            client.chat_postMessage(channel=channel_id,
                                    text=f"😕 Sorry, I couldn't format that. {str(e)}",
                                    thread_ts=thread_ts)

    @app.event("message")
    def handle_message_events(event, client):
        if event.get("subtype") or event.get("bot_id"):
            return

        text = event.get("text", "") or ""
        channel_id = event.get("channel")
        user_id = event.get("user")
        thread_ts = event.get("thread_ts")

        try:
            auth = client.auth_test()
            bot_user_id = auth.get("user_id")
            if bot_user_id and f"<@{bot_user_id}>" in text:
                return
        except Exception:
            logger.debug("auth_test failed; skipping mention filtering.")

        if not formatter.is_table_like(text):
            return

        try:
            create_and_post_snippets(client, text, channel_id, user_id, thread_ts=thread_ts)
        except Exception as e:
            logger.info(f"Auto-detection skipped or failed: {e}")

"""
Stewie Telegram Bot — Remote command interface via Telegram.

Allows authorized users to send commands from their phone and receive
responses, screenshots, and status updates.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from loguru import logger

from config.settings import TelegramConfig
from core.exceptions import TelegramAuthError, TelegramError


class TelegramModule:
    """
    Telegram bot integration for remote Stewie control.

    Supports:
    - /status — Check if Stewie is online
    - /order <details> — Place an order
    - /run <command> — Execute a voice-style command
    - /screen — Get a screenshot of the current screen
    - /say <text> — Make Stewie speak aloud
    - /brightness <level> — Set screen brightness
    - /volume <level> — Set system volume
    - Natural language messages (processed by NLU)
    """

    def __init__(self, config: TelegramConfig, orchestrator, tts_engine=None, nlu=None):
        self.config = config
        self.orchestrator = orchestrator
        self.tts_engine = tts_engine
        self.nlu = nlu
        self._app = None
        self._is_configured = bool(
            config.bot_token and config.bot_token != "YOUR_TELEGRAM_BOT_TOKEN_HERE"
        )

    def _build_app(self):
        """Build the Telegram application with all handlers."""
        try:
            from telegram import Update
            from telegram.ext import (
                ApplicationBuilder,
                CommandHandler,
                ContextTypes,
                MessageHandler,
                filters,
            )
        except ImportError:
            logger.error(
                "python-telegram-bot not installed. "
                "Run: pip install python-telegram-bot"
            )
            return None

        app = ApplicationBuilder().token(self.config.bot_token).build()

        # Register command handlers
        app.add_handler(CommandHandler("start", self._handle_start))
        app.add_handler(CommandHandler("status", self._handle_status))
        app.add_handler(CommandHandler("order", self._handle_order))
        app.add_handler(CommandHandler("run", self._handle_run))
        app.add_handler(CommandHandler("screen", self._handle_screen))
        app.add_handler(CommandHandler("say", self._handle_say))
        app.add_handler(CommandHandler("brightness", self._handle_brightness))
        app.add_handler(CommandHandler("volume", self._handle_volume))
        app.add_handler(CommandHandler("help", self._handle_help))

        # Natural language handler (last, as catch-all)
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_natural_language,
            )
        )

        return app

    def _is_authorized(self, user_id: int) -> bool:
        """Check if a user is in the whitelist."""
        if not self.config.allowed_user_ids:
            # No whitelist configured — allow all
            logger.warning(
                "No Telegram user whitelist configured — "
                "allowing all users."
            )
            return True
        return user_id in self.config.allowed_user_ids

    async def _authorize(self, update) -> bool:
        """Check authorization and send denial if unauthorized."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await update.message.reply_text(
                "🔒 I'm sorry, but I don't recognize your credentials. "
                "Access denied."
            )
            logger.warning(
                f"Unauthorized Telegram access attempt by user {user_id}"
            )
            return False
        return True

    # --- Command Handlers ---

    async def _handle_start(self, update, context):
        """Handle /start command."""
        if not await self._authorize(update):
            return
        await update.message.reply_text(
            "🤖 *Stewie online.*\n\n"
            "Good to see you, sir. I'm ready to assist remotely.\n\n"
            "Use /help to see available commands.",
            parse_mode="Markdown",
        )

    async def _handle_status(self, update, context):
        """Handle /status command."""
        if not await self._authorize(update):
            return
        await update.message.reply_text(
            "✅ *Systems Nominal*\n\n"
            "All modules are operational, sir. "
            "Standing by for your instructions.",
            parse_mode="Markdown",
        )

    async def _handle_order(self, update, context):
        """Handle /order command — place an order."""
        if not await self._authorize(update):
            return

        order_text = " ".join(context.args) if context.args else ""
        if not order_text:
            await update.message.reply_text(
                "📋 Please specify what you'd like to order.\n"
                "Example: `/order 2 coffees from Starbucks`",
                parse_mode="Markdown",
            )
            return

        result = await self.orchestrator.execute(
            {
                "intent": "place_order",
                "action": "place_order",
                "params": {"order_details": order_text},
                "source": "telegram",
                "original_text": f"/order {order_text}",
            }
        )

        status_emoji = "✅" if result.status.value == "completed" else "❌"
        await update.message.reply_text(
            f"{status_emoji} *Order Processed*\n\n"
            f"📋 {order_text}\n\n"
            f"{result.summary}",
            parse_mode="Markdown",
        )

    async def _handle_run(self, update, context):
        """Handle /run command — execute a voice-style command."""
        if not await self._authorize(update):
            return

        command_text = " ".join(context.args) if context.args else ""
        if not command_text:
            await update.message.reply_text(
                "🎙️ Please specify a command to run.\n"
                "Example: `/run open Chrome`",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text("⚙️ Processing command...")

        if not self.nlu:
            await update.message.reply_text("❌ NLU module not loaded. Cannot process command.")
            return

        # Parse intent via NLU
        parsed = await self.nlu.parse(command_text)
        
        # Execute
        result = await self.orchestrator.execute(parsed)

        status_emoji = "✅" if result.status.value == "completed" else "❌"
        await update.message.reply_text(
            f"{status_emoji} {result.summary}",
            parse_mode="Markdown",
        )

    async def _handle_screen(self, update, context):
        """Handle /screen command — send a screenshot."""
        if not await self._authorize(update):
            return

        try:
            from execution.screen_reader import capture_screen_to_file

            screenshot_path = capture_screen_to_file()
            with open(screenshot_path, "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption="📸 Here's what's currently on screen, sir.",
                )
            # Clean up temp screenshot
            Path(screenshot_path).unlink(missing_ok=True)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Couldn't capture the screen: {e}"
            )

    async def _handle_say(self, update, context):
        """Handle /say command — speak text aloud."""
        if not await self._authorize(update):
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "🔊 What would you like me to say?"
            )
            return

        if self.tts_engine:
            await self.tts_engine.speak(text)
            await update.message.reply_text(f'🔊 Spoken: "{text}"')
        else:
            await update.message.reply_text(
                "⚠️ TTS engine is not available at the moment."
            )

    async def _handle_brightness(self, update, context):
        """Handle /brightness command."""
        if not await self._authorize(update):
            return

        if not context.args:
            await update.message.reply_text(
                "💡 Specify a brightness level (0-100).\n"
                "Example: `/brightness 70`",
                parse_mode="Markdown",
            )
            return

        try:
            level = int(context.args[0])
            result = await self.orchestrator.execute(
                {
                    "action": "set_brightness",
                    "params": {"level": level},
                    "source": "telegram",
                    "original_text": f"/brightness {level}",
                }
            )
            await update.message.reply_text(f"💡 Brightness set to {level}%.")
        except ValueError:
            await update.message.reply_text(
                "❌ Please provide a number between 0 and 100."
            )

    async def _handle_volume(self, update, context):
        """Handle /volume command."""
        if not await self._authorize(update):
            return

        if not context.args:
            await update.message.reply_text(
                "🔊 Specify a volume level (0-100).\n"
                "Example: `/volume 50`",
                parse_mode="Markdown",
            )
            return

        try:
            level = int(context.args[0])
            level_float = max(0.0, min(1.0, level / 100.0))
            result = await self.orchestrator.execute(
                {
                    "action": "set_volume",
                    "params": {"level": level_float},
                    "source": "telegram",
                    "original_text": f"/volume {level}",
                }
            )
            await update.message.reply_text(f"🔊 Volume set to {level}%.")
        except ValueError:
            await update.message.reply_text(
                "❌ Please provide a number between 0 and 100."
            )

    async def _handle_help(self, update, context):
        """Handle /help command."""
        if not await self._authorize(update):
            return

        help_text = (
            "🤖 *Stewie Remote Commands*\n\n"
            "/status — Check if I'm online\n"
            "/order `<details>` — Place an order\n"
            "/run `<command>` — Execute a command\n"
            "/screen — Get a screenshot\n"
            "/say `<text>` — Make me speak\n"
            "/brightness `<0-100>` — Set brightness\n"
            "/volume `<0-100>` — Set volume\n"
            "/help — Show this message\n\n"
            "You can also send natural language messages."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def _handle_natural_language(self, update, context):
        """Handle free-form text messages via NLU."""
        if not await self._authorize(update):
            return

        text = update.message.text
        logger.info(f"Telegram natural language: \"{text}\"")

        await update.message.reply_text("🧠 Processing...")

        if not self.nlu:
            await update.message.reply_text("❌ NLU module not loaded. Cannot process text.")
            return

        # Parse intent via NLU
        parsed = await self.nlu.parse(text)
        
        # Handle clarification responses
        if parsed.get("intent") == "clarification":
            response_msg = parsed.get("params", {}).get("message", "I didn't quite catch that.")
            await update.message.reply_text(f"🗣️ {response_msg}")
            return

        # Execute
        result = await self.orchestrator.execute(parsed)

        status_emoji = "✅" if result.status.value == "completed" else "❌"
        await update.message.reply_text(
            f"{status_emoji} {result.summary}"
        )

    async def start(self) -> None:
        """Start the Telegram bot (polling mode)."""
        if not self._is_configured:
            logger.warning(
                "Telegram bot token not configured — "
                "Telegram integration disabled. "
                "Set STEWIE_TG_BOT_TOKEN in .env to enable."
            )
            # Keep running but do nothing — allows the main loop to continue
            while True:
                await asyncio.sleep(3600)
            return

        self._app = self._build_app()
        if self._app is None:
            logger.error("Failed to build Telegram app.")
            return

        logger.info("Telegram bot starting (polling mode)...")
        try:
            await self._app.initialize()
            await self._app.start()
            await self._app.updater.start_polling()
            logger.info("Telegram bot is online and listening.")

            # Keep running
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            logger.info("Telegram bot stopped.")

"""
╔═══════════════════════════════════════════════════════════════╗
║                    S T E W I E                                ║
║         Voice-Controlled AI Assistant for Windows             ║
║              Inspired by JARVIS — Built for You               ║
╚═══════════════════════════════════════════════════════════════╝

Entry point for the Stewie AI Assistant.

Bootstraps all modules, initializes the voice pipeline and Telegram bot,
and runs the main event loop.

Usage:
    python main.py
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure the project root is in the Python path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

# ===================================
# LOGGING SETUP
# ===================================

logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    level="INFO",
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>"
    ),
)
logger.add(
    "logs/stewie_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)


# ===================================
# STARTUP BANNER
# ===================================

BANNER = r"""
  ____  _                  _      
 / ___|| |_ _____      __ (_) ___ 
 \___ \| __/ _ \ \ /\ / / | |/ _ \
  ___) | ||  __/\ V  V /  | |  __/
 |____/ \__\___| \_/\_/   |_|\___|
                                   
  Voice-Controlled AI Assistant v0.1.0
  "At your service, sir."
"""


async def main():
    """Main entry point -- bootstraps and runs Stewie."""
    print(BANNER)
    logger.info("Initializing Stewie...")

    # ── Load Configuration ──
    from config.settings import load_config

    try:
        config = load_config()
        logger.info("Configuration loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        logger.error("Please check your .env file. See .env.example for reference.")
        return

    # ── Initialize Core Components ──
    from core.event_bus import EventBus
    from core.context import ConversationContext
    from core.orchestrator import Orchestrator
    from core.learning import LearningEngine

    event_bus = EventBus()
    context = ConversationContext()
    orchestrator = Orchestrator(event_bus=event_bus, context=context)
    learning = LearningEngine()

    # ── Initialize Output ──
    from output.tts_engine import TTSEngine
    from output.response_formatter import JarvisFormatter

    tts = TTSEngine(voice=config.tts_voice)
    formatter = JarvisFormatter()

    # ── Register Execution Handlers ──
    from execution import system_control, app_manager, screen_reader
    from execution import research_engine, document_creator

    orchestrator.register_many(
        {
            # System Control
            "set_brightness": system_control.set_brightness,
            "adjust_brightness": system_control.adjust_brightness,
            "set_volume": system_control.set_volume,
            "toggle_mute": system_control.toggle_mute,
            "shutdown_pc": system_control.shutdown_pc,
            "restart_pc": system_control.restart_pc,
            "cancel_shutdown": system_control.cancel_shutdown,
            "lock_screen": system_control.lock_screen,
            "get_battery_level": system_control.get_battery_level,
            # App Management
            "open_application": app_manager.open_application,
            "close_application": app_manager.close_application,
            "type_text": app_manager.type_text,
            # Screen
            "read_screen": screen_reader.read_screen,
            "summarize_screen": screen_reader.summarize_screen,
            # Research
            "web_search": research_engine.web_search,
            "research_topic": research_engine.research_topic,
            # Documents
            "create_document": document_creator.create_document,
        }
    )

    # ── Register a "respond" action for clarifications ──
    async def respond_action(message: str = "", **kwargs) -> str:
        """Handle clarification/response actions from NLU."""
        return message

    orchestrator.register("respond", respond_action)

    # ── Register a placeholder "place_order" action ──
    async def place_order_action(order_details: str = "", **kwargs) -> str:
        """Handle order placement (placeholder — customize per your needs)."""
        logger.info(f"Order received: {order_details}")
        return f"Order recorded: {order_details}. I'll process this for you."

    orchestrator.register("place_order", place_order_action)

    # ── Register self-learning actions ──
    async def self_report_action(**kwargs) -> str:
        """Generate a self-analysis report of what Stewie has learned."""
        return learning.generate_self_report()

    async def learning_stats_action(**kwargs) -> str:
        """Get learning engine statistics."""
        stats = learning.get_stats()
        return (
            f"I've processed {stats['total_commands']} commands with a "
            f"{stats['success_rate']:.0%} success rate. "
            f"Average response time: {stats['avg_execution_time_ms']:.0f}ms. "
            f"I've learned {stats['learned_corrections']} corrections so far."
        )

    orchestrator.register("self_report", self_report_action)
    orchestrator.register("learning_stats", learning_stats_action)

    # ── Initialize NLU ──
    from nlu.intent_parser import IntentParser

    nlu = IntentParser(
        api_key=config.openai_api_key,
        model=config.openai_model,
        base_url=config.openai_base_url,
        context=context,
        learning_engine=learning,
    )

    # ── Initialize Input Layer ──
    from input.wake_word import WakeWordDetector
    from input.speech_recognition import SpeechRecognizer
    from input.telegram_bot import TelegramModule

    wake_detector = WakeWordDetector(
        event_bus=event_bus,
        wake_phrase=config.wake_phrase,
        sensitivity=config.wake_sensitivity,
    )

    speech_rec = SpeechRecognizer(model_size=config.whisper_model)

    telegram = TelegramModule(
        config=config.telegram,
        orchestrator=orchestrator,
        tts_engine=tts,
        nlu=nlu,
    )

    # ── Startup Complete ──
    logger.info("All modules initialized.")
    logger.info(f"Wake phrase: \"{config.wake_phrase}\"")
    logger.info(f"Whisper model: {config.whisper_model}")
    logger.info(f"TTS voice: {config.tts_voice}")
    logger.info(f"OpenAI model: {config.openai_model}")
    logger.info(
        f"Telegram: {'configured' if telegram._is_configured else 'not configured'}"
    )

    # Learning engine stats
    learning_stats = learning.get_stats()
    if learning_stats["total_commands"] > 0:
        logger.info(
            f"Learning engine: {learning_stats['total_commands']} past commands, "
            f"{learning_stats['success_rate']:.0%} success rate, "
            f"{learning_stats['learned_corrections']} corrections learned"
        )
    else:
        logger.info("Learning engine: fresh start — no prior history")

    # Speak greeting
    try:
        await tts.speak(formatter.greeting())
    except Exception as e:
        logger.warning(f"TTS greeting failed: {e}")

    logger.info("Stewie is online. Awaiting your command, sir.")

    # ── Main Voice Loop ──
    async def voice_loop():
        """Continuously listen for wake word → process commands."""
        while True:
            try:
                # Wait for wake word
                logger.debug("Waiting for wake word...")
                wake_detector.resume()
                await wake_detector.wait_for_wake_word()

                # Pause wake detection so STT/TTS don't re-trigger it
                wake_detector.pause()

                # Play listening chime
                await tts.play_sound("assets/sounds/listening.wav")

                # Record and transcribe
                transcript = await speech_rec.listen_and_transcribe()

                if not transcript:
                    await tts.speak(formatter.clarify())
                    continue

                logger.info(f"Command: \"{transcript}\"")

                # Acknowledge
                await tts.speak(formatter.acknowledge())

                # Parse intent via NLU
                parsed = await nlu.parse(transcript)
                logger.debug(f"Parsed intent: {parsed}")

                # Check for clarification responses
                if parsed.get("intent") == "clarification":
                    message = parsed.get("params", {}).get("message", "")
                    await tts.speak(message)
                    learning.record_command(
                        raw_text=transcript,
                        parsed_intent="clarification",
                        parsed_params={},
                        success=True,
                        source="voice",
                    )
                    continue

                # Execute with timing
                import time as _time
                start_time = _time.monotonic()
                result = await orchestrator.execute(parsed)
                exec_time_ms = (_time.monotonic() - start_time) * 1000

                # Record for learning
                learning.record_command(
                    raw_text=transcript,
                    parsed_intent=parsed.get("intent", "unknown"),
                    parsed_params=parsed.get("params", {}),
                    success=(result.status.value == "completed"),
                    execution_time_ms=exec_time_ms,
                    source="voice",
                )

                # Format and speak response
                if result.status.value == "completed":
                    response = formatter.complete(result.summary)
                else:
                    error_msg = result.error or result.summary
                    response = formatter.error(error_msg)

                await tts.speak(response)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in voice loop: {e}", exc_info=True)
                try:
                    await tts.speak(
                        formatter.error(f"An unexpected error occurred: {e}")
                    )
                except Exception:
                    pass

    # ── Run Voice Loop + Telegram Concurrently ──
    try:
        await asyncio.gather(
            voice_loop(),
            telegram.start(),
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")
    finally:
        # Cleanup
        await wake_detector.stop()
        await telegram.stop()
        learning.close()
        try:
            await tts.speak(formatter.farewell())
        except Exception:
            pass
        logger.info("Stewie offline. Goodbye, sir.")


# ═══════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStewie shutting down. Goodbye, sir.")

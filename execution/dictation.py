"""
Stewie Dictation Module — Voice-to-typing interface.

Provides a dedicated module for dictation mode where continuous
speech is typed into the active window.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger


class DictationMode:
    """
    Continuous dictation mode — listens and types in real-time.

    Activated by commands like "start dictation" and deactivated
    by "stop dictation" or the wake word.
    """

    def __init__(self, speech_recognizer, event_bus):
        self.speech_recognizer = speech_recognizer
        self.event_bus = event_bus
        self._active = False

    async def start(self) -> None:
        """Start continuous dictation mode."""
        from execution.app_manager import type_text

        self._active = True
        logger.info("Dictation mode activated")

        await self.event_bus.emit("dictation_started")

        while self._active:
            transcript = await self.speech_recognizer.listen_and_transcribe()

            if transcript:
                # Check for stop commands
                if self._is_stop_command(transcript):
                    break

                await type_text(transcript + " ")

        await self.stop()

    async def stop(self) -> None:
        """Stop dictation mode."""
        self._active = False
        logger.info("Dictation mode deactivated")
        await self.event_bus.emit("dictation_stopped")

    def _is_stop_command(self, text: str) -> bool:
        """Check if the text is a stop dictation command."""
        stop_phrases = [
            "stop dictation",
            "end dictation",
            "stop typing",
            "that's all",
            "hey stewie",
        ]
        return any(phrase in text.lower() for phrase in stop_phrases)

    @property
    def is_active(self) -> bool:
        return self._active

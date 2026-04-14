"""
Stewie Fallback Parser — Rule-based intent parsing for offline mode.

When the LLM API is unavailable, this module provides basic keyword
matching to handle essential commands like system control and app management.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger


class FallbackParser:
    """
    Keyword-based command parser — no network required.

    Handles a limited set of commands using pattern matching.
    For complex or ambiguous commands, returns a clarification request.
    """

    # Pattern → (action, param_extractor)
    PATTERNS = [
        # App management
        (
            r"(?:open|launch|start)\s+(.+)",
            lambda m: {
                "action": "open_application",
                "params": {"app_name": m.group(1).strip('.?! ')},
            },
        ),
        (
            r"(?:close|quit|exit|kill)\s+(.+)",
            lambda m: {
                "action": "close_application",
                "params": {"app_name": m.group(1).strip('.?! ')},
            },
        ),
        # Brightness
        (
            r"(?:set\s+)?brightness\s+(?:to\s+)?(\d+)",
            lambda m: {
                "action": "set_brightness",
                "params": {"level": int(m.group(1))},
            },
        ),
        (
            r"(?:increase|raise|up)\s+(?:the\s+)?brightness",
            lambda m: {
                "action": "adjust_brightness",
                "params": {"delta": 20},
            },
        ),
        (
            r"(?:decrease|lower|down|dim)\s+(?:the\s+)?brightness",
            lambda m: {
                "action": "adjust_brightness",
                "params": {"delta": -20},
            },
        ),
        # Volume
        (
            r"(?:set\s+)?volume\s+(?:to\s+)?(\d+)",
            lambda m: {
                "action": "set_volume",
                "params": {"level": int(m.group(1)) / 100},
            },
        ),
        (
            r"(?:increase|raise|up)\s+(?:the\s+)?volume",
            lambda m: {
                "action": "set_volume",
                "params": {"level": 0.8},
            },
        ),
        (
            r"(?:decrease|lower|down)\s+(?:the\s+)?volume",
            lambda m: {
                "action": "set_volume",
                "params": {"level": 0.3},
            },
        ),
        (
            r"(?:mute|unmute|toggle\s+mute)",
            lambda m: {
                "action": "toggle_mute",
                "params": {},
            },
        ),
        # Power
        (
            r"(?:shut\s*down|power\s+off)",
            lambda m: {
                "action": "shutdown_pc",
                "params": {"delay_seconds": 30},
            },
        ),
        (
            r"restart|reboot",
            lambda m: {
                "action": "restart_pc",
                "params": {"delay_seconds": 10},
            },
        ),
        (
            r"lock\s+(?:the\s+)?(?:screen|computer|pc)",
            lambda m: {
                "action": "lock_screen",
                "params": {},
            },
        ),
        # Screen
        (
            r"(?:read|show|what'?s?\s+on)\s+(?:the\s+)?screen",
            lambda m: {
                "action": "read_screen",
                "params": {},
            },
        ),
        (
            r"summarize\s+(?:the\s+)?screen",
            lambda m: {
                "action": "summarize_screen",
                "params": {},
            },
        ),
        # Search
        (
            r"(?:search|google|look\s+up)\s+(?:for\s+)?(.+)",
            lambda m: {
                "action": "web_search",
                "params": {"query": m.group(1).strip('.?! ')},
            },
        ),
        # Dictation
        (
            r"(?:type|write|dictate)\s+(.+)",
            lambda m: {
                "action": "type_text",
                "params": {"text": m.group(1).strip('.?! ')},
            },
        ),
    ]

    @classmethod
    def parse(cls, text: str) -> dict[str, Any]:
        """
        Parse a command using keyword/regex matching.

        Args:
            text: The command text to parse.

        Returns:
            Structured intent dict compatible with the Orchestrator.
        """
        text_lower = text.lower().strip()

        for pattern, extractor in cls.PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                result = extractor(match)
                logger.debug(
                    f"Fallback parser matched: '{pattern}' "
                    f"→ {result['action']}"
                )
                return {
                    "intent": result["action"],
                    "action": result["action"],
                    "params": result["params"],
                    "original_text": text,
                    "source": "voice",
                    "confidence": 0.7,  # Lower confidence than LLM
                    "parser": "fallback",
                }

        # No match found
        logger.warning(
            f"Fallback parser: no match for \"{text}\""
        )
        return {
            "intent": "unrecognized",
            "action": "respond",
            "params": {
                "message": (
                    "I'm operating in offline mode and couldn't "
                    "interpret that command, sir. Could you try a "
                    "simpler phrasing?"
                )
            },
            "original_text": text,
            "source": "voice",
            "confidence": 0.1,
            "parser": "fallback",
        }

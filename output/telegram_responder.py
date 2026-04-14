"""
Stewie Telegram Responder — Formats and sends rich Telegram replies.

Wraps orchestrator results in well-formatted Telegram messages
with emojis, markdown, and appropriate status indicators.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger


class TelegramResponder:
    """
    Formats execution results for Telegram delivery.

    Handles markdown formatting, emoji status indicators,
    and message length limits.
    """

    MAX_MESSAGE_LENGTH = 4096  # Telegram limit

    @staticmethod
    def format_result(result: Any, command: str = "") -> str:
        """
        Format an orchestrator result for Telegram.

        Args:
            result: TaskResult from the orchestrator.
            command: Original command text.

        Returns:
            Formatted message string.
        """
        status = getattr(result, "status", None)
        summary = getattr(result, "summary", str(result))
        error = getattr(result, "error", None)

        if status and status.value == "completed":
            emoji = "✅"
            header = "Task Complete"
        elif status and status.value == "failed":
            emoji = "❌"
            header = "Task Failed"
        else:
            emoji = "ℹ️"
            header = "Result"

        parts = [f"{emoji} *{header}*"]

        if command:
            parts.append(f"📝 Command: `{command}`")

        if summary:
            parts.append(f"\n{summary}")

        if error:
            parts.append(f"\n⚠️ Error: {error}")

        message = "\n".join(parts)

        # Truncate if necessary
        if len(message) > TelegramResponder.MAX_MESSAGE_LENGTH:
            message = (
                message[: TelegramResponder.MAX_MESSAGE_LENGTH - 20]
                + "\n\n... [truncated]"
            )

        return message

    @staticmethod
    def format_research(research: dict) -> str:
        """Format research results for Telegram."""
        parts = ["🔬 *Research Results*\n"]

        topic = research.get("topic", "Unknown")
        parts.append(f"📌 Topic: *{topic}*")

        source_count = research.get("source_count", 0)
        if source_count:
            parts.append(f"📚 Sources: {source_count}\n")

        # Key points
        key_points = research.get("key_points", [])
        if key_points:
            parts.append("*Key Findings:*")
            for i, point in enumerate(key_points[:10], 1):
                parts.append(f"  {i}. {point}")

        # Summary excerpt
        summary = research.get("summary", "")
        if summary:
            excerpt = summary[:500]
            if len(summary) > 500:
                excerpt += "..."
            parts.append(f"\n💬 *Summary:*\n{excerpt}")

        return "\n".join(parts)

    @staticmethod
    def format_error(error_message: str) -> str:
        """Format an error message for Telegram."""
        return (
            f"❌ *Error*\n\n"
            f"{error_message}\n\n"
            f"Please try again or use /help for available commands."
        )

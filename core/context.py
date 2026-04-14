"""
Stewie Conversation Context — Maintains state across interactions.

Tracks conversation history, user preferences, and provides context
to the NLU engine for better intent resolution.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Interaction:
    """A single user interaction record."""

    timestamp: str
    source: str  # "voice" or "telegram"
    command: str
    intent: str
    result_status: str
    result_summary: str


@dataclass
class ConversationContext:
    """
    Maintains state across multiple interactions for contextual awareness.

    Provides recent history to the LLM so Stewie can understand references
    like "do that again" or "also save it as PDF."
    """

    history: deque[Interaction] = field(
        default_factory=lambda: deque(maxlen=20)
    )
    session_start: datetime = field(default_factory=datetime.now)
    user_preferences: dict[str, Any] = field(default_factory=dict)
    active_tasks: dict[str, Any] = field(default_factory=dict)

    # Track last interaction for quick reference
    _last_command: str = ""
    _last_result: dict = field(default_factory=dict)

    def add_interaction(
        self,
        command: str,
        intent: str,
        result_status: str,
        result_summary: str,
        source: str = "voice",
    ) -> None:
        """Record a completed interaction."""
        interaction = Interaction(
            timestamp=datetime.now().isoformat(),
            source=source,
            command=command,
            intent=intent,
            result_status=result_status,
            result_summary=result_summary,
        )
        self.history.append(interaction)
        self._last_command = command
        self._last_result = {
            "status": result_status,
            "summary": result_summary,
        }

    def get_context_for_llm(self, max_recent: int = 5) -> str:
        """
        Build a context string for the LLM to understand conversation flow.

        Returns a formatted summary of recent interactions that helps
        the NLU resolve ambiguous references.
        """
        recent = list(self.history)[-max_recent:]
        if not recent:
            return "No previous interactions in this session."

        lines = ["Recent conversation history:"]
        for interaction in recent:
            lines.append(
                f"  [{interaction.source}] \"{interaction.command}\" "
                f"→ {interaction.intent} → {interaction.result_status}"
            )
        return "\n".join(lines)

    @property
    def last_command(self) -> str:
        """Get the most recent command text."""
        return self._last_command

    @property
    def last_result(self) -> dict:
        """Get the most recent result."""
        return dict(self._last_result)

    @property
    def session_duration_minutes(self) -> float:
        """How long this session has been active."""
        delta = datetime.now() - self.session_start
        return delta.total_seconds() / 60

    def set_preference(self, key: str, value: Any) -> None:
        """Store a user preference."""
        self.user_preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a user preference."""
        return self.user_preferences.get(key, default)

    def reset(self) -> None:
        """Clear all context (new session)."""
        self.history.clear()
        self.active_tasks.clear()
        self._last_command = ""
        self._last_result = {}
        self.session_start = datetime.now()

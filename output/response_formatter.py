"""
Stewie Response Formatter — JARVIS-style personality for all responses.

Wraps raw execution results in polished, personality-driven language
befitting of a sophisticated AI assistant.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger


class JarvisFormatter:
    """
    Formats responses with JARVIS-inspired personality.

    Loads templates from personas.yaml for variety and authenticity.
    Falls back to built-in templates if the config file is missing.
    """

    # Built-in fallback templates
    _DEFAULT_TITLE = "sir"

    _DEFAULT_ACKNOWLEDGMENTS = [
        "Right away, {title}.",
        "Consider it done.",
        "On it, {title}.",
        "As you wish.",
        "Certainly, {title}.",
        "Executing now.",
    ]

    _DEFAULT_COMPLETIONS = [
        "Task complete, {title}. {detail}",
        "All done. {detail}",
        "Finished, {title}. {detail}",
        "That's been taken care of. {detail}",
        "{detail} — will there be anything else, {title}?",
    ]

    _DEFAULT_ERRORS = [
        "I'm afraid I've encountered a complication, {title}. {error}",
        "We have a situation. {error}",
        "My apologies, {title}. {error} Shall I try an alternative approach?",
        "That didn't go as planned. {error}",
    ]

    _DEFAULT_CLARIFICATIONS = [
        "I didn't quite catch that, {title}. Could you repeat?",
        "My apologies, I couldn't make that out. Once more, please?",
    ]

    def __init__(self, config_path: Optional[str] = None):
        self.title = self._DEFAULT_TITLE
        self.acknowledgments = list(self._DEFAULT_ACKNOWLEDGMENTS)
        self.completions = list(self._DEFAULT_COMPLETIONS)
        self.errors = list(self._DEFAULT_ERRORS)
        self.clarifications = list(self._DEFAULT_CLARIFICATIONS)

        # Try to load from personas.yaml
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent / "config" / "personas.yaml"
            )

        self._load_config(Path(config_path))

    def _load_config(self, path: Path) -> None:
        """Load persona templates from YAML config."""
        if not path.exists():
            logger.debug("Personas config not found — using defaults.")
            return

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            persona = data.get("persona", {})
            self.title = persona.get("title", self._DEFAULT_TITLE)

            if "acknowledgments" in data:
                self.acknowledgments = data["acknowledgments"]
            if "completions" in data:
                self.completions = data["completions"]
            if "errors" in data:
                self.errors = data["errors"]
            if "clarifications" in data:
                self.clarifications = data["clarifications"]

            logger.debug("Loaded persona templates from config.")

        except Exception as e:
            logger.warning(f"Failed to load personas config: {e}")

    def acknowledge(self) -> str:
        """Generate a JARVIS-style acknowledgment."""
        template = random.choice(self.acknowledgments)
        return template.format(title=self.title)

    def complete(self, detail: str = "") -> str:
        """Generate a JARVIS-style completion message."""
        template = random.choice(self.completions)
        return template.format(title=self.title, detail=detail).strip()

    def error(self, error: str) -> str:
        """Generate a JARVIS-style error message."""
        template = random.choice(self.errors)
        return template.format(title=self.title, error=error)

    def clarify(self) -> str:
        """Generate a JARVIS-style clarification request."""
        template = random.choice(self.clarifications)
        return template.format(title=self.title)

    def greeting(self) -> str:
        """Generate the startup greeting."""
        return f"Systems are online. How may I assist you, {self.title}?"

    def farewell(self) -> str:
        """Generate a shutdown message."""
        return f"Going into standby, {self.title}. I'll be here if you need me."

    def status(self) -> str:
        """Generate a status response."""
        return f"All systems nominal, {self.title}. Running at full capacity."

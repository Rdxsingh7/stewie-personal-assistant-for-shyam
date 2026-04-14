"""
Stewie Global Settings — Pydantic-based configuration management.

All settings are loaded from environment variables (prefixed with STEWIE_)
or from a .env file in the project root.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class TelegramConfig(BaseSettings):
    """Telegram bot configuration."""

    bot_token: str = Field(default="", description="Bot token from @BotFather")
    allowed_user_ids: list[int] = Field(
        default_factory=list,
        description="Whitelist of authorized Telegram user IDs",
    )

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def parse_user_ids(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = {
        "env_prefix": "STEWIE_TG_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class StewieConfig(BaseSettings):
    """Master configuration for all Stewie subsystems."""

    # --- OpenAI / LLM ---
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model to use")
    openai_base_url: Optional[str] = Field(
        default=None, description="Custom base URL for the LLM API"
    )

    # --- Voice ---
    wake_phrase: str = Field(default="hey jarvis", description="Wake word phrase")
    wake_sensitivity: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Wake word sensitivity"
    )
    whisper_model: str = Field(
        default="base",
        description="Whisper model size: tiny, base, small, medium, large",
    )
    tts_voice: str = Field(
        default="en-US-GuyNeural", description="Edge TTS voice name"
    )

    # --- General ---
    log_level: str = Field(default="INFO", description="Logging level")
    save_path: str = Field(
        default="~/Desktop", description="Default save location for documents"
    )

    # --- Telegram (loaded separately to pick up STEWIE_TG_ env vars) ---
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)

    @property
    def resolved_save_path(self) -> Path:
        """Expand ~ and return a resolved Path."""
        return Path(self.save_path).expanduser().resolve()

    model_config = {
        "env_prefix": "STEWIE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def load_config() -> StewieConfig:
    """Load and validate the Stewie configuration."""
    # Load Telegram config separately (it has its own env_prefix)
    telegram_config = TelegramConfig()

    config = StewieConfig(telegram=telegram_config)

    # Ensure save path exists
    config.resolved_save_path.mkdir(parents=True, exist_ok=True)

    return config

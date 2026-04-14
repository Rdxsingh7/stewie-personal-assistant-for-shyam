"""
Stewie Custom Exceptions — A proper hierarchy for graceful error handling.
"""


class StewieError(Exception):
    """Base exception for all Stewie errors."""

    def __init__(self, message: str = "An unexpected error occurred.", *args):
        self.message = message
        super().__init__(self.message, *args)


# --- Input Layer Errors ---


class WakeWordError(StewieError):
    """Raised when wake word detection fails to initialize or operate."""
    pass


class SpeechRecognitionError(StewieError):
    """Raised when speech cannot be captured or transcribed."""
    pass


# --- NLU Errors ---


class IntentParsingError(StewieError):
    """Raised when the NLU engine cannot parse user intent."""
    pass


class LLMConnectionError(StewieError):
    """Raised when the LLM API is unreachable or returns an error."""
    pass


# --- Execution Errors ---


class CommandExecutionError(StewieError):
    """Raised when a command fails during execution."""
    pass


class ApplicationNotFoundError(CommandExecutionError):
    """Raised when a requested application cannot be found."""

    def __init__(self, app_name: str):
        self.app_name = app_name
        super().__init__(f"Application not found: '{app_name}'")


class SystemControlError(CommandExecutionError):
    """Raised when a system control operation fails (brightness, volume, etc.)."""
    pass


class ScreenReadError(CommandExecutionError):
    """Raised when screen reading or OCR fails."""
    pass


class DocumentCreationError(CommandExecutionError):
    """Raised when document creation or saving fails."""
    pass


class ResearchError(CommandExecutionError):
    """Raised when web research encounters an issue."""
    pass


# --- Telegram Errors ---


class TelegramError(StewieError):
    """Base error for Telegram integration issues."""
    pass


class TelegramAuthError(TelegramError):
    """Raised when a Telegram user is not authorized."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Unauthorized Telegram user: {user_id}")


# --- Configuration Errors ---


class ConfigurationError(StewieError):
    """Raised when configuration is missing or invalid."""
    pass

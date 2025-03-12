"""Custom exceptions for the langki package."""


class LangkiError(Exception):
    """Base exception for all langki errors."""

    pass


class AnkiConnectError(LangkiError):
    """Exception raised when there is an error communicating with AnkiConnect."""

    pass


class AnkiConnectionError(LangkiError):
    """Exception raised when there is an error connecting to Anki."""

    pass


class TranslationError(LangkiError):
    """Exception raised when there is an error with the translation service."""

    pass


class AudioGenerationError(LangkiError):
    """Exception raised when there is an error generating audio."""

    pass


class ConfigurationError(LangkiError):
    """Exception raised when there is a configuration error (e.g., missing API keys)."""

    pass

"""Custom exceptions for the add2anki package."""


class add2ankiError(Exception):
    """Base exception for all add2anki errors."""

    pass


class AnkiConnectError(add2ankiError):
    """Exception raised when there is an error communicating with AnkiConnect."""

    pass


class AnkiConnectionError(add2ankiError):
    """Exception raised when there is an error connecting to Anki."""

    pass


class TranslationError(add2ankiError):
    """Exception raised when there is an error with the translation service."""

    pass


class AudioGenerationError(add2ankiError):
    """Exception raised when there is an error generating audio."""

    pass


class ConfigurationError(add2ankiError):
    """Exception raised when there is a configuration error (e.g., missing API keys)."""

    pass


class LanguageDetectionError(add2ankiError):
    """Exception raised when language detection fails or is ambiguous."""

    pass

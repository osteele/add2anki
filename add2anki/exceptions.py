"""Custom exceptions for the add2anki package."""


class Add2ankiError(Exception):
    """Base exception for all add2anki errors."""

    pass


class AnkiConnectError(Add2ankiError):
    """Exception raised when there is an error communicating with AnkiConnect."""

    pass


class AnkiConnectionError(Add2ankiError):
    """Exception raised when there is an error connecting to Anki."""

    pass


class TranslationError(Add2ankiError):
    """Exception raised when there is an error with the translation service."""

    pass


class AudioGenerationError(Add2ankiError):
    """Exception raised when there is an error generating audio."""

    pass


class ConfigurationError(Add2ankiError):
    """Exception raised when there is a configuration error (e.g., missing API keys)."""

    pass


class LanguageDetectionError(Add2ankiError):
    """Exception raised when language detection fails or is ambiguous."""

    pass

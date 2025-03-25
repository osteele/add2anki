"""Language detection and processing for add2anki."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Dict, Sequence

import fast_langdetect

from add2anki.exceptions import LanguageDetectionError
from add2anki.translation import TranslationService


# Type aliases
class Language(str):
    """A two-or three-letter ISO 639-1 language code."""

    def __new__(cls, code: str) -> "Language":
        """Create a new Language instance with validation."""
        if not (2 <= len(code) <= 3) or not code.isalpha() or not code.islower():
            raise ValueError(f"Invalid language code: {code}. Must be a two-letter ISO 639-1 code.")
        return super().__new__(cls, code)


TranslationCallback = Callable[[str, str, str], None]


@dataclass
class DetectionResult:
    """Result of language detection including confidence."""

    language: Language
    confidence: float
    is_ambiguous: bool = False


@dataclass
class LanguageState:
    """State for language detection in REPL mode."""

    detected_language: Language | None = None
    language_history: Dict[Language, int] | None = None

    def __post_init__(self) -> None:
        """Initialize language history."""
        if self.language_history is None:
            self.language_history = {}

    def record_language(self, language: Language) -> None:
        """Record a detected language to build context."""
        if self.language_history is None:
            self.language_history = {}

        if language in self.language_history:
            self.language_history[language] += 1
        else:
            self.language_history[language] = 1

        # Update the detected language to the most frequent
        if self.language_history:
            self.detected_language = max(self.language_history.items(), key=lambda x: x[1])[0]


# Confidence threshold for language detection
CONFIDENCE_THRESHOLD = 0.70  # Adjust as needed based on empirical testing


def detect_language(text: str) -> DetectionResult:
    """Detect the language of the given text.

    Args:
        text: The text to detect the language of.

    Returns:
        DetectionResult with detected language and confidence score.

    Raises:
        LanguageDetectionError: If language detection fails completely.
    """
    try:
        result = fast_langdetect.detect(text)

        # Process result based on return type
        if isinstance(result, str):
            # Simple string result - assume high confidence
            return DetectionResult(language=Language(result), confidence=1.0, is_ambiguous=False)
        else:
            # Dictionary result with language and confidence
            lang = result.get("lang", "")
            confidence = float(result.get("score", 0.0))

            if not lang:
                raise LanguageDetectionError("No language detected")

            # Determine if the result is ambiguous based on confidence
            is_ambiguous = confidence < CONFIDENCE_THRESHOLD

            return DetectionResult(language=Language(str(lang)), confidence=confidence, is_ambiguous=is_ambiguous)

    except Exception as e:
        raise LanguageDetectionError(f"Language detection failed: {e}") from e


def process_sentence(
    sentence: str,
    target_lang: Language,
    translation_service: TranslationService,
    state: LanguageState | None = None,
    source_lang: Language | None = None,
    on_translation: TranslationCallback | None = None,
) -> None:
    """Process a single sentence, detecting its language and translating if needed.

    Args:
        sentence: The sentence to process.
        target_lang: The target language to translate to.
        translation_service: The translation service to use.
        state: Optional language state for REPL mode.
        source_lang: Optional explicit source language.
        on_translation: Optional callback for translation results.

    Raises:
        LanguageDetectionError: If language detection fails or is ambiguous and cannot be resolved.
    """
    # If source language is explicitly specified, use it for direction
    if source_lang:
        detection = detect_language(sentence)
        detected_lang = detection.language

        # Skip if the sentence is already in target language
        if detected_lang == target_lang:
            return

        # Verify the sentence is in the specified source language
        if detected_lang != source_lang:
            raise LanguageDetectionError(
                f"Sentence appears to be in {detected_lang} instead of specified source language {source_lang}"
            )

        # Translate from source to target
        result = translation_service.translate(sentence, style="conversational")
        if on_translation:
            on_translation(sentence, result.hanzi, result.pinyin)
        return

    # No explicit source language - detect and handle ambiguity
    detection = detect_language(sentence)
    detected_lang = detection.language

    # Skip if the sentence is already in target language
    if detected_lang == target_lang:
        return

    # Handle ambiguous detection
    if detection.is_ambiguous:
        # Try to use context from state in REPL mode
        if state and state.detected_language:
            detected_lang = state.detected_language
        else:
            # No context available - must ask user or fail
            raise LanguageDetectionError(
                f"Language detection is ambiguous (confidence: {detection.confidence:.2f}). "
                f"Detected '{detected_lang}' but confidence is low. "
                f"Please specify the source language explicitly with --source-lang."
            )

    # Record this detection in state for future context (REPL mode)
    if state and not detection.is_ambiguous:
        state.record_language(detected_lang)

    # Translate from detected language to target
    result = translation_service.translate(sentence, style="conversational")
    if on_translation:
        on_translation(sentence, result.hanzi, result.pinyin)


def process_batch(
    sentences: Sequence[str],
    target_lang: Language,
    translation_service: TranslationService,
    source_lang: Language | None = None,
    on_translation: TranslationCallback | None = None,
) -> None:
    """Process a batch of sentences, detecting languages and translating if needed.

    Args:
        sentences: The sentences to process.
        target_lang: The target language to translate to.
        translation_service: The translation service to use.
        source_lang: Optional explicit source language.
        on_translation: Optional callback for translation results.

    Raises:
        LanguageDetectionError: If language detection fails or is ambiguous and cannot be resolved.
    """
    # When source language is explicitly specified
    if source_lang:
        for sentence in sentences:
            detection = detect_language(sentence)
            detected_lang = detection.language

            # Skip if the sentence is already in target language
            if detected_lang == target_lang:
                continue

            # Verify the sentence is in the specified source language
            if detected_lang != source_lang:
                raise LanguageDetectionError(
                    f"Sentence appears to be in {detected_lang} instead of specified source language {source_lang}"
                )

            # Translate from source to target
            result = translation_service.translate(sentence, style="conversational")
            if on_translation:
                on_translation(sentence, result.hanzi, result.pinyin)
        return

    # No explicit source language - use two-pass approach with context

    # First pass: categorize sentences and collect language statistics
    unambiguous_sentences: list[tuple[str, Language]] = []  # (sentence, language)
    ambiguous_sentences: list[tuple[str, DetectionResult]] = []  # (sentence, detection_result)
    target_sentences: list[str] = []  # Sentences already in target language
    language_counts: Dict[Language, int] = {}  # Count of each detected language

    # First pass: categorize all sentences
    for sentence in sentences:
        detection = detect_language(sentence)

        # Skip sentences already in target language
        if detection.language == target_lang:
            target_sentences.append(sentence)
            continue

        # Sort into unambiguous and ambiguous categories
        if detection.is_ambiguous:
            ambiguous_sentences.append((sentence, detection))
        else:
            unambiguous_sentences.append((sentence, detection.language))

            # Update language statistics
            if detection.language in language_counts:
                language_counts[detection.language] += 1
            else:
                language_counts[detection.language] = 1

    # Process unambiguous sentences first
    for sentence, _ in unambiguous_sentences:
        result = translation_service.translate(sentence, style="conversational")
        if on_translation:
            on_translation(sentence, result.hanzi, result.pinyin)

    # Process ambiguous sentences using context from unambiguous ones
    if ambiguous_sentences:
        # Find the most common detected language as context
        predominant_language = None
        if language_counts:
            predominant_language = max(language_counts.items(), key=lambda x: x[1])[0]

        if not predominant_language:
            # Cannot determine language context - skip with warning
            sentences_preview = [s[:30] + "..." for s, _ in ambiguous_sentences[:3]]
            raise LanguageDetectionError(
                f"Cannot determine language for {len(ambiguous_sentences)} ambiguous sentences. "
                f"No unambiguous sentences found for context. "
                f"Examples: {', '.join(sentences_preview)}"
            )

        # Use the predominant language as context for ambiguous sentences
        for sentence, detection in ambiguous_sentences:
            # Override the ambiguous detection with predominant language
            result = translation_service.translate(sentence, style="conversational")
            if on_translation:
                on_translation(sentence, result.hanzi, result.pinyin)

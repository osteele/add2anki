"""Language detection and processing for add2anki."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Dict, List, Sequence

from contextual_langdetect import contextual_detect

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
class LanguageState:
    """State for language detection in REPL mode."""

    detected_language: Language | None = None
    language_history: Dict[Language, int] | None = None
    primary_languages: List[Language] | None = None

    def __post_init__(self) -> None:
        """Initialize language history."""
        if self.language_history is None:
            self.language_history = {}
        if self.primary_languages is None:
            self.primary_languages = []

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

            # Update primary languages (anything that appears >10% of the time)
            threshold = max(1, sum(self.language_history.values()) * 0.1)
            self.primary_languages = [lang for lang, count in self.language_history.items() if count >= threshold]


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
    # Skip empty sentences
    if not sentence.strip():
        return

    # If source language is explicitly specified, use it
    if source_lang:
        # Skip if the sentence is already in target language
        if source_lang == target_lang:
            return

        # Get expected languages list (to verify source_lang)
        expected_langs = [str(source_lang)]
        detected_langs = contextual_detect([sentence], languages=expected_langs)

        if not detected_langs or not detected_langs[0]:
            raise LanguageDetectionError(f"No language detected for: {sentence}")

        detected_lang = Language(detected_langs[0])

        # Verify detected language matches specified source language
        if detected_lang != source_lang:
            raise LanguageDetectionError(
                f"Sentence appears to be in {detected_lang} instead of specified source language {source_lang}"
            )

        # Translate from source to target
        result = translation_service.translate(sentence, style="conversational")
        if on_translation:
            on_translation(sentence, result.hanzi, result.pinyin)
        return

    # Handle context from state for improved detection
    expected_langs = None
    if state and state.primary_languages:
        expected_langs = [str(lang) for lang in state.primary_languages]

    # Detect language with context hints if available
    detected_langs = contextual_detect([sentence], languages=expected_langs)

    if not detected_langs or not detected_langs[0]:
        # If detection failed but we have state context, use that
        if state and state.detected_language:
            detected_lang = state.detected_language
        else:
            raise LanguageDetectionError(f"Failed to detect language for: {sentence}")
    else:
        detected_lang = Language(detected_langs[0])

    # Handle very short text (which may be ambiguous)
    is_ambiguous = len(sentence) < 6  # Short texts are considered potentially ambiguous

    # If text is potentially ambiguous but we have state context, use it
    if is_ambiguous and state and state.detected_language and not expected_langs:
        # Try again with expected languages hint based on state
        expected_langs = [str(lang) for lang in state.primary_languages] if state.primary_languages else []
        if state.detected_language:
            expected_langs.append(str(state.detected_language))

        if expected_langs:
            better_langs = contextual_detect([sentence], languages=expected_langs)
            if better_langs and better_langs[0]:
                detected_lang = Language(better_langs[0])

    # If ambiguous and no context available, warn the user
    if is_ambiguous and not state:
        # We'll continue with the detected language, but warn user they might want to use source_lang
        # This is a softer approach than raising an error
        print(f"Warning: '{sentence}' is short and language detection may be ambiguous.")

    # Skip if the sentence is already in target language
    if detected_lang == target_lang:
        return

    # Record this detection in state for future context (REPL mode)
    if state and not is_ambiguous:
        state.record_language(detected_lang)

    # Translate using the detected language
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
    # Filter out empty sentences
    valid_sentences = [s for s in sentences if s.strip()]
    if not valid_sentences:
        return

    # When source language is explicitly specified, process each sentence individually
    if source_lang:
        for sentence in valid_sentences:
            process_sentence(
                sentence,
                target_lang=target_lang,
                translation_service=translation_service,
                source_lang=source_lang,
                on_translation=on_translation,
            )
        return

    # No explicit source language - use contextual_langdetect for batch processing
    # The package automatically handles context-aware detection
    detected_languages = contextual_detect(valid_sentences)

    if len(detected_languages) != len(valid_sentences):
        raise LanguageDetectionError(
            "Language detection failed: Number of results doesn't match number of input sentences"
        )

    # Process each sentence with its detected language
    for sentence, language in zip(valid_sentences, detected_languages):
        # Skip sentences where language could not be detected
        if not language:
            continue

        detected_lang = Language(language)

        # Skip if the sentence is already in target language
        if detected_lang == target_lang:
            continue

        # Translate using the detected language
        result = translation_service.translate(sentence, style="conversational")
        if on_translation:
            on_translation(sentence, result.hanzi, result.pinyin)

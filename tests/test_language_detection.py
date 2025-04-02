"""Tests for the language detection module."""

from unittest.mock import MagicMock, patch

import pytest

from add2anki.language_detection import (
    Language,
    LanguageState,
    process_batch,
    process_sentence,
)


def test_language_validation() -> None:
    """Test Language class validation."""
    # Valid language codes
    assert Language("en") == "en"
    assert Language("zh") == "zh"
    assert Language("ja") == "ja"
    assert Language("spa") == "spa"  # 3-letter code

    # Invalid language codes
    with pytest.raises(ValueError):
        Language("INVALID")  # Not lowercase

    with pytest.raises(ValueError):
        Language("e")  # Too short

    with pytest.raises(ValueError):
        Language("12345")  # Too long and not alpha


def test_language_state_record_language() -> None:
    """Test LanguageState recording and history."""
    state = LanguageState()

    # Record languages
    state.record_language(Language("en"))
    state.record_language(Language("zh"))
    state.record_language(Language("zh"))
    state.record_language(Language("en"))
    state.record_language(Language("zh"))

    # Check language counts
    assert state.language_history is not None  # Ensure language_history is not None for type checking
    assert state.language_history[Language("en")] == 2
    assert state.language_history[Language("zh")] == 3

    # Most frequent should be set as detected language
    assert state.detected_language == Language("zh")

    # Primary languages should include both (as both appear >10% of the time)
    assert state.primary_languages is not None
    assert len(state.primary_languages) == 2
    assert Language("zh") in state.primary_languages
    assert Language("en") in state.primary_languages


def test_process_sentence_with_source_lang() -> None:
    """Test processing a sentence with explicit source language."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"
    mock_translation.english = "Hello"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    with patch("contextual_langdetect.contextual_detect") as mock_detect:
        mock_detect.return_value = ["zh"]  # Returns the language detection result
        process_sentence(
            "你好",
            target_lang=Language("en"),
            translation_service=mock_translation_service,
            source_lang=Language("zh"),
        )
        mock_translation_service.translate.assert_called_once_with("你好", style="conversational")


def test_process_sentence_with_empty_text() -> None:
    """Test processing an empty sentence."""
    mock_translation_service = MagicMock()

    # Process should skip empty text without error
    process_sentence(
        "",
        target_lang=Language("en"),
        translation_service=mock_translation_service,
    )

    # No translation should happen for empty text
    mock_translation_service.translate.assert_not_called()


def test_process_sentence_with_state() -> None:
    """Test processing a sentence with REPL state."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"
    mock_translation.english = "Hello"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    with patch("contextual_langdetect.contextual_detect") as mock_detect:
        # Return language detection results
        mock_detect.return_value = ["zh"]

        # Create a state with previous context
        state = LanguageState()
        state.record_language(Language("zh"))
        state.record_language(Language("zh"))

        # Ensure primary_languages is set
        state.primary_languages = [Language("zh")]

        # Process should succeed using state context
        process_sentence(
            "你好",
            target_lang=Language("en"),
            translation_service=mock_translation_service,
            state=state,
        )
        mock_translation_service.translate.assert_called_once_with("你好", style="conversational")


def test_process_batch() -> None:
    """Test batch processing with contextual detection."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    # Mix of Chinese and English sentences
    sentences = ["你好", "很好", "Hello", "Good day"]

    with patch("contextual_langdetect.contextual_detect") as mock_detect:
        # Mock the contextual detection
        mock_detect.return_value = ["zh", "zh", "en", "en"]

        # Process batch - target language is English
        process_batch(
            sentences,
            target_lang=Language("en"),
            translation_service=mock_translation_service,
        )

        # Only Chinese sentences should be translated to English
        assert mock_translation_service.translate.call_count == 2
        mock_translation_service.translate.assert_any_call("你好", style="conversational")
        mock_translation_service.translate.assert_any_call("很好", style="conversational")


def test_process_batch_with_source_lang() -> None:
    """Test processing a batch with explicit source language."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"
    mock_translation.english = "Hello"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    sentences = ["Hello", "Good morning", "Hi there"]

    with patch("contextual_langdetect.contextual_detect") as mock_detect:
        # Mock source language verification
        mock_detect.return_value = ["en", "en", "en"]

        process_batch(
            sentences,
            target_lang=Language("zh"),
            translation_service=mock_translation_service,
            source_lang=Language("en"),
        )

        # All sentences should be translated
        assert mock_translation_service.translate.call_count == 3
        for sentence in sentences:
            mock_translation_service.translate.assert_any_call(sentence, style="conversational")


def test_process_batch_with_empty_text() -> None:
    """Test batch processing with empty text."""
    mock_translation_service = MagicMock()

    # Empty input should be handled gracefully
    process_batch(
        ["", "   ", "\n"],
        target_lang=Language("en"),
        translation_service=mock_translation_service,
    )

    # No translation calls should happen
    mock_translation_service.translate.assert_not_called()


def test_process_batch_with_valid_detection() -> None:
    """Test batch processing with valid language detection."""
    mock_translation_service = MagicMock()

    with patch("contextual_langdetect.contextual_detect") as mock_detect:
        # Return English for all detections
        mock_detect.return_value = ["en", "en", "en"]

        # Process batch with various texts
        process_batch(
            ["Text1", "Hello", "Text3"],
            target_lang=Language("zh"),
            translation_service=mock_translation_service,
        )

        # All texts should be processed since they all have valid language detections
        assert mock_translation_service.translate.call_count == 3


def test_process_batch_with_target_language() -> None:
    """Test batch processing with texts already in target language."""
    mock_translation_service = MagicMock()

    with patch("contextual_langdetect.contextual_detect") as mock_detect:
        # Return target language for second sentence
        mock_detect.return_value = ["en", "zh", "en"]

        # Process batch with target language as Chinese
        process_batch(
            ["Hello1", "你好", "Hello2"],
            target_lang=Language("zh"),
            translation_service=mock_translation_service,
        )

        # Second sentence should be skipped as it's already in target language
        assert mock_translation_service.translate.call_count == 2
        mock_translation_service.translate.assert_any_call("Hello1", style="conversational")
        mock_translation_service.translate.assert_any_call("Hello2", style="conversational")

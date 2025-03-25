"""Tests for the language detection module."""

from unittest.mock import MagicMock, patch

import pytest

from add2anki.exceptions import LanguageDetectionError
from add2anki.language_detection import (
    DetectionResult,
    Language,
    LanguageState,
    detect_language,
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


def test_detect_language_with_high_confidence() -> None:
    """Test detection with high confidence score."""
    with patch("fast_langdetect.detect") as mock_detect:
        mock_detect.return_value = {"lang": "zh", "score": 0.95}
        result = detect_language("你好，最近怎么样？")
        assert result.language == Language("zh")
        assert result.confidence == 0.95
        assert not result.is_ambiguous


def test_detect_language_with_low_confidence() -> None:
    """Test detection with low confidence score."""
    with patch("fast_langdetect.detect") as mock_detect:
        mock_detect.return_value = {"lang": "zh", "score": 0.45}
        result = detect_language("我")  # Very short text
        assert result.language == Language("zh")
        assert result.confidence == 0.45
        assert result.is_ambiguous  # Should be ambiguous because confidence < threshold


def test_detect_language_string_result() -> None:
    """Test handling string result from langdetect."""
    with patch("fast_langdetect.detect") as mock_detect:
        mock_detect.return_value = "en"  # Simple string result
        result = detect_language("Hello")
        assert result.language == Language("en")
        assert result.confidence == 1.0  # Default high confidence
        assert not result.is_ambiguous


def test_detect_language_mixed_content() -> None:
    """Test detection of mixed language content."""
    with patch("fast_langdetect.detect") as mock_detect:
        # Low confidence for mixed content
        mock_detect.return_value = {"lang": "en", "score": 0.55}
        result = detect_language("Hello 你好")
        assert result.language == Language("en")
        assert result.confidence == 0.55
        assert result.is_ambiguous


def test_detect_language_very_short_text() -> None:
    """Test detection of very short text."""
    with patch("fast_langdetect.detect") as mock_detect:
        # Low confidence for very short text
        mock_detect.return_value = {"lang": "ja", "score": 0.60}
        result = detect_language("あ")  # Single character
        assert result.language == Language("ja")
        assert result.confidence == 0.60
        assert result.is_ambiguous


def test_detect_language_failure() -> None:
    """Test handling of detection failure."""
    with patch("fast_langdetect.detect") as mock_detect:
        mock_detect.side_effect = Exception("Detection failed")
        with pytest.raises(LanguageDetectionError):
            detect_language("Some text")


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


def test_process_sentence_with_source_lang() -> None:
    """Test processing a sentence with explicit source language."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"
    mock_translation.english = "Hello"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    with patch("add2anki.language_detection.detect_language") as mock_detect:
        mock_detect.return_value = DetectionResult(language=Language("zh"), confidence=0.95, is_ambiguous=False)
        process_sentence(
            "你好",
            target_lang=Language("en"),
            translation_service=mock_translation_service,
            source_lang=Language("zh"),
        )
        mock_translation_service.translate.assert_called_once_with("你好", style="conversational")


def test_process_sentence_ambiguous_with_state() -> None:
    """Test processing an ambiguous sentence with REPL state."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"
    mock_translation.english = "Hello"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    with patch("add2anki.language_detection.detect_language") as mock_detect:
        # Return ambiguous result
        mock_detect.return_value = DetectionResult(language=Language("zh"), confidence=0.55, is_ambiguous=True)

        # Create a state with previous context
        state = LanguageState()
        state.record_language(Language("zh"))
        state.record_language(Language("zh"))

        # Process should succeed using state context
        process_sentence(
            "你",  # Short, ambiguous text
            target_lang=Language("en"),
            translation_service=mock_translation_service,
            state=state,
        )
        mock_translation_service.translate.assert_called_once_with("你", style="conversational")


def test_process_sentence_ambiguous_without_state() -> None:
    """Test processing an ambiguous sentence without state context."""
    mock_translation = MagicMock()
    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    with patch("add2anki.language_detection.detect_language") as mock_detect:
        # Return ambiguous result
        mock_detect.return_value = DetectionResult(language=Language("zh"), confidence=0.55, is_ambiguous=True)

        # No state context provided - should raise error
        with pytest.raises(LanguageDetectionError):
            process_sentence(
                "你",  # Short, ambiguous text
                target_lang=Language("en"),
                translation_service=mock_translation_service,
            )


def test_process_batch_with_confidence_thresholds() -> None:
    """Test batch processing with different confidence thresholds."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    sentences = ["Hello world", "你好，世界", "こんにちは、世界"]

    with patch("add2anki.language_detection.detect_language") as mock_detect:
        # Return different confidence levels
        mock_detect.side_effect = [
            DetectionResult(language=Language("en"), confidence=0.95, is_ambiguous=False),
            DetectionResult(language=Language("zh"), confidence=0.85, is_ambiguous=False),
            DetectionResult(language=Language("ja"), confidence=0.75, is_ambiguous=False),
        ]

        process_batch(
            sentences,
            target_lang=Language("zh"),
            translation_service=mock_translation_service,
        )

        # English and Japanese should be translated to Chinese
        # (only Chinese sentence should be skipped as it's already in target language)
        assert mock_translation_service.translate.call_count == 2
        mock_translation_service.translate.assert_any_call("Hello world", style="conversational")
        mock_translation_service.translate.assert_any_call("こんにちは、世界", style="conversational")


def test_process_batch_with_mixed_confidence() -> None:
    """Test batch processing with mixed confidence levels."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    sentences = ["Hello", "你好", "안녕하세요", "短"]  # Last one is very short Chinese

    with patch("add2anki.language_detection.detect_language") as mock_detect:
        # Return different confidence levels
        mock_detect.side_effect = [
            DetectionResult(language=Language("en"), confidence=0.95, is_ambiguous=False),
            DetectionResult(language=Language("zh"), confidence=0.90, is_ambiguous=False),
            DetectionResult(language=Language("ko"), confidence=0.85, is_ambiguous=False),
            DetectionResult(language=Language("zh"), confidence=0.55, is_ambiguous=True),
        ]

        process_batch(
            sentences,
            target_lang=Language("zh"),
            translation_service=mock_translation_service,
        )

        # English and Korean should be translated (the ambiguous Chinese might not be processed
        # if there's not enough context)
        assert mock_translation_service.translate.call_count == 2
        mock_translation_service.translate.assert_any_call("Hello", style="conversational")
        mock_translation_service.translate.assert_any_call("안녕하세요", style="conversational")


def test_process_batch_with_source_lang() -> None:
    """Test processing a batch with explicit source language."""
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "ni3 hao3"
    mock_translation.english = "Hello"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    sentences = ["Hello", "Good morning", "Hi there"]
    with patch("add2anki.language_detection.detect_language") as mock_detect:
        # All sentences should be detected with high confidence
        mock_detect.side_effect = [
            DetectionResult(language=Language("en"), confidence=0.95, is_ambiguous=False),
            DetectionResult(language=Language("en"), confidence=0.92, is_ambiguous=False),
            DetectionResult(language=Language("en"), confidence=0.90, is_ambiguous=False),
        ]

        process_batch(
            sentences,
            target_lang=Language("zh"),
            translation_service=mock_translation_service,
            source_lang=Language("en"),
        )

        # All sentences should be translated
        assert mock_translation_service.translate.call_count == 3

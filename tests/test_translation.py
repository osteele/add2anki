"""Tests for the translation module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from langki.exceptions import ConfigurationError
from langki.translation import TranslationResult, TranslationService


def test_translation_result_model() -> None:
    """Test the TranslationResult model."""
    result = TranslationResult(
        hanzi="u4f60u597d",
        pinyin="nu01d0 hu01ceo",
        english="Hello",
        style="conversational",
    )
    assert result.hanzi == "u4f60u597d"
    assert result.pinyin == "nu01d0 hu01ceo"
    assert result.english == "Hello"
    assert result.style == "conversational"


def test_translation_service_init_no_api_key() -> None:
    """Test that TranslationService raises an error when no API key is provided."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfigurationError):
            TranslationService()


def test_translation_service_init_with_api_key() -> None:
    """Test that TranslationService can be initialized with an API key."""
    with patch.dict(os.environ, {}, clear=True):
        service = TranslationService(api_key="test_key")
        assert service.api_key == "test_key"


def test_translation_service_init_from_env() -> None:
    """Test that TranslationService can get the API key from the environment."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "env_key"}, clear=True):
        service = TranslationService()
        assert service.api_key == "env_key"


def test_translate_success() -> None:
    """Test successful translation."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"hanzi": "u4f60u597d", "pinyin": "nu01d0 hu01ceo", "english": "Hello", "style": "conversational"}'
            )
        )
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("langki.translation.OpenAI", return_value=mock_client):
        service = TranslationService(api_key="test_key")
        result = service.translate("Hello")

        assert result.hanzi == "u4f60u597d"
        assert result.pinyin == "nu01d0 hu01ceo"
        assert result.english == "Hello"
        assert result.style == "conversational"
        mock_client.chat.completions.create.assert_called_once()

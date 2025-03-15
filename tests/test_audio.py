"""Tests for the audio module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from langki.audio import (
    ElevenLabsAudioService,
    create_audio_service,
)
from langki.exceptions import AudioGenerationError, ConfigurationError


def test_elevenlabs_audio_service_init_no_api_key() -> None:
    """Test that ElevenLabsAudioService raises an error when no API key is provided."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfigurationError):
            ElevenLabsAudioService()


def test_elevenlabs_audio_service_init_with_api_key() -> None:
    """Test that ElevenLabsAudioService can be initialized with an API key."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("elevenlabs.client.ElevenLabs") as mock_eleven_labs:
            service = ElevenLabsAudioService(eleven_labs_api_key="test_key")
            assert service.eleven_labs_api_key == "test_key"
            mock_eleven_labs.assert_called_once_with(api_key="test_key")


def test_elevenlabs_audio_service_init_from_env() -> None:
    """Test that ElevenLabsAudioService can get the API key from the environment."""
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "env_key"}, clear=True):
        with patch("elevenlabs.client.ElevenLabs") as mock_eleven_labs:
            service = ElevenLabsAudioService()
            assert service.eleven_labs_api_key == "env_key"
            mock_eleven_labs.assert_called_once_with(api_key="env_key")


def test_get_mandarin_chinese_voice_success() -> None:
    """Test getting a Chinese voice successfully."""
    mock_voice = MagicMock()
    mock_voice.labels.languages = ["chinese"]
    mock_voice.voice_id = "voice_id_123"

    mock_response = MagicMock()
    mock_response.voices = [mock_voice]

    mock_client = MagicMock()
    mock_client.voices.get_all.return_value = mock_response

    with patch("langki.audio.ElevenLabs", return_value=mock_client):
        service = ElevenLabsAudioService(eleven_labs_api_key="test_key")
        # Mock the eleven_labs_client to avoid actual API calls
        service.eleven_labs_client = mock_client
        voice_id = service.get_mandarin_chinese_voice()
        assert voice_id == "voice_id_123"


def test_get_mandarin_chinese_voice_fallback_to_multilingual() -> None:
    """Test fallback to multilingual voice when no Chinese voice is found."""
    mock_voice = MagicMock()
    mock_voice.labels.languages = ["english"]
    mock_voice.labels.descriptions = ["multilingual"]
    mock_voice.voice_id = "voice_id_123"

    mock_response = MagicMock()
    mock_response.voices = [mock_voice]

    mock_client = MagicMock()
    mock_client.voices.get_all.return_value = mock_response

    with patch("langki.audio.ElevenLabs", return_value=mock_client):
        service = ElevenLabsAudioService(eleven_labs_api_key="test_key")
        # Mock the eleven_labs_client to avoid actual API calls
        service.eleven_labs_client = mock_client
        voice_id = service.get_mandarin_chinese_voice()
        assert voice_id == "voice_id_123"


def test_get_mandarin_chinese_voice_fallback_to_any() -> None:
    """Test fallback to any voice when no suitable voice is found."""
    mock_voice = MagicMock()
    mock_voice.labels.languages = ["english"]
    mock_voice.labels.descriptions = ["natural"]
    mock_voice.voice_id = "voice_id_123"

    mock_response = MagicMock()
    mock_response.voices = [mock_voice]

    mock_client = MagicMock()
    mock_client.voices.get_all.return_value = mock_response

    with patch("langki.audio.ElevenLabs", return_value=mock_client):
        service = ElevenLabsAudioService(eleven_labs_api_key="test_key")
        # Mock the eleven_labs_client to avoid actual API calls
        service.eleven_labs_client = mock_client
        voice_id = service.get_mandarin_chinese_voice()
        assert voice_id == "voice_id_123"


def test_elevenlabs_generate_audio_file_success() -> None:
    """Test successful audio generation with ElevenLabs."""
    mock_audio_data = b"audio_data"
    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = mock_audio_data

    with patch("langki.audio.ElevenLabs", return_value=mock_client):
        with patch("tempfile.gettempdir", return_value="/tmp"):
            with patch.object(Path, "mkdir"):
                with patch("builtins.open", MagicMock()):
                    service = ElevenLabsAudioService(eleven_labs_api_key="test_key")
                    # Directly mock both required attributes
                    service.eleven_labs_client = mock_client
                    # Skip the get_mandarin_chinese_voice call
                    with patch.object(
                        ElevenLabsAudioService,
                        "get_mandarin_chinese_voice",
                        return_value="voice_id_123",
                    ):
                        audio_path = service.generate_audio_file("你好")

                        assert isinstance(audio_path, str)
                        assert audio_path.endswith(".mp3")
                        mock_client.text_to_speech.convert.assert_called_once()


def test_elevenlabs_generate_audio_file_error() -> None:
    """Test audio generation when an error occurs with ElevenLabs."""
    service = ElevenLabsAudioService(eleven_labs_api_key="test_key")
    # Mock to avoid actual API calls
    with patch.object(
        ElevenLabsAudioService,
        "get_mandarin_chinese_voice",
        side_effect=AudioGenerationError("Test error"),
    ):
        with pytest.raises(AudioGenerationError, match="Audio generation failed"):
            service.generate_audio_file("你好")


def test_create_audio_service() -> None:
    """Test the create_audio_service factory function."""
    # Test with google-translate provider
    with patch("langki.audio.GoogleTranslateAudioService") as mock_google_translate:
        create_audio_service("google-translate")
        mock_google_translate.assert_called_once()

    # Test with google-cloud provider
    with patch("langki.audio.GoogleCloudAudioService") as mock_google_cloud:
        create_audio_service("google-cloud")
        mock_google_cloud.assert_called_once()

    # Test with elevenlabs provider
    with patch("langki.audio.ElevenLabsAudioService") as mock_elevenlabs:
        create_audio_service("elevenlabs")
        mock_elevenlabs.assert_called_once()

    # Test with invalid provider
    with pytest.raises(ConfigurationError):
        create_audio_service("invalid-provider")

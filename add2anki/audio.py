"""Audio generation services for text-to-speech."""

import abc
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

import elevenlabs.client

from add2anki.exceptions import AudioGenerationError, ConfigurationError

# Create an alias for the tests to mock
ElevenLabs = elevenlabs.client.ElevenLabs


class AudioGenerationService(abc.ABC):
    """Abstract base class for audio generation services."""

    @abc.abstractmethod
    def generate_audio_file(self, text: str) -> str:
        """Generate audio for the given text.

        Args:
            text: The text to generate audio for (in Mandarin).

        Returns:
            Path to the generated audio file.

        Raises:
            AudioGenerationError: If there is an error generating the audio.
        """
        pass


class GoogleTranslateAudioService(AudioGenerationService):
    """Service for generating audio using Google Translate's text-to-speech API.

    This service uses the free Google Translate TTS API and doesn't require authentication.
    """

    def __init__(self) -> None:
        """Initialize the Google Translate audio service."""
        pass

    def generate_audio_file(self, text: str) -> str:
        """Generate audio for the given text using Google Translate's TTS API.

        Args:
            text: The text to generate audio for (in Mandarin).

        Returns:
            Path to the generated audio file.

        Raises:
            AudioGenerationError: If there is an error generating the audio.
        """
        # Prepare the URL for Google Translate TTS
        # Using Mandarin Chinese (zh-CN) with a female voice
        base_url = "https://translate.google.com/translate_tts"
        params = {
            "ie": "UTF-8",
            "q": text,
            "tl": "zh-CN",  # Mandarin Chinese
            "client": "tw-ob",  # Required for the API to work
            "ttsspeed": "1.0",  # Normal speed
        }

        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        # Set up headers to mimic a browser request
        headers = {
            "Referer": "https://translate.google.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
        }

        # Create the request
        request = urllib.request.Request(url, headers=headers)

        # Save to a temporary file
        temp_dir = Path(tempfile.gettempdir()) / "add2anki"
        temp_dir.mkdir(exist_ok=True)
        audio_file_path = temp_dir / f"add2anki_{abs(hash(text))}.mp3"

        # Download the audio file
        with urllib.request.urlopen(request) as response, open(audio_file_path, "wb") as file:
            file.write(response.read())

        return str(audio_file_path)


class ElevenLabsAudioService(AudioGenerationService):
    """Service for generating audio using ElevenLabs API."""

    def __init__(self, eleven_labs_api_key: str | None = None) -> None:
        """Initialize the ElevenLabs audio service.

        Args:
            eleven_labs_api_key: ElevenLabs API key. If None, will try to get from environment.

        Raises:
            ConfigurationError: If no API key is provided or found in environment.
        """
        # Get API key from parameter or environment
        self.eleven_labs_api_key = eleven_labs_api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self.eleven_labs_api_key:
            raise ConfigurationError(
                "ElevenLabs API key is required. "
                "Either pass it as a parameter or set the ELEVENLABS_API_KEY environment variable."
            )
        # Initialize the ElevenLabs client
        self.eleven_labs_client = elevenlabs.client.ElevenLabs(api_key=self.eleven_labs_api_key)

    def get_mandarin_chinese_voice(self) -> str:
        """Get a voice that supports Mandarin Chinese.

        Returns:
            A voice ID that supports Mandarin Chinese.

        Raises:
            AudioGenerationError: If no suitable voice is found.
        """
        try:
            # Get all available voices
            response = self.eleven_labs_client.voices.get_all()
            available_voices = response.voices

            # Filter for voices that support Chinese
            chinese_voices: list[Any] = []
            for voice in available_voices:
                # Handle voice.labels.languages which should be a list of strings
                languages: list[str] = getattr(getattr(voice, "labels", {}), "languages", [])
                if any("chinese" in language.lower() for language in languages):
                    chinese_voices.append(voice)

            # If no Chinese voices found, try to find a multilingual voice
            if not chinese_voices:
                for voice in available_voices:
                    # Handle voice.labels.descriptions which should be a list of strings
                    descriptions: list[str] = getattr(getattr(voice, "labels", {}), "descriptions", [])
                    if any("multilingual" in description.lower() for description in descriptions):
                        chinese_voices.append(voice)

            # If still no suitable voice, use the first voice (better than nothing)
            if not chinese_voices and available_voices:
                return str(available_voices[0].voice_id)

            if not chinese_voices:
                raise AudioGenerationError("No voices found")

            # Cast to str to ensure type safety
            return str(chinese_voices[0].voice_id)

        except Exception as e:
            raise AudioGenerationError(f"Failed to get voice: {e}") from e

    def generate_audio_file(self, text: str) -> str:
        """Generate audio for the given text using ElevenLabs.

        Args:
            text: The text to generate audio for (in Mandarin).

        Returns:
            Path to the generated audio file.

        Raises:
            AudioGenerationError: If there is an error generating the audio.
        """
        try:
            voice_id = self.get_mandarin_chinese_voice()

            # Generate the audio
            audio = self.eleven_labs_client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",  # Best for language diversity
                output_format="mp3_44100_128",
            )

            # Save to a temporary file
            temp_dir = Path(tempfile.gettempdir()) / "add2anki"
            temp_dir.mkdir(exist_ok=True)
            audio_file_path = temp_dir / f"add2anki_{abs(hash(text))}.mp3"

            # Convert iterator to bytes if needed
            audio_bytes = b"".join(audio) if hasattr(audio, "__iter__") and not isinstance(audio, bytes) else audio

            with open(audio_file_path, "wb") as file:
                # Cast to bytes to ensure type safety
                file.write(cast(bytes, audio_bytes))

            return str(audio_file_path)

        except Exception as e:
            raise AudioGenerationError(f"Audio generation failed: {e}") from e


def create_audio_service(provider: str = "google-translate", **kwargs: Any) -> AudioGenerationService:
    """Create an audio service based on the specified provider.

    Args:
        provider: The audio service provider to use ('google-translate' or 'elevenlabs').
        **kwargs: Additional arguments to pass to the service constructor.
            - eleven_labs_api_key: API key for ElevenLabs (for 'elevenlabs' provider)

    Returns:
        An instance of AudioGenerationService.

    Raises:
        ConfigurationError: If the provider is not supported.
    """
    if provider.lower() == "elevenlabs":
        return ElevenLabsAudioService(**kwargs)
    elif provider.lower() == "google-translate":
        return GoogleTranslateAudioService(**kwargs)
    else:
        raise ConfigurationError(f"Unsupported audio provider: {provider}. Use 'google-translate' or 'elevenlabs'.")

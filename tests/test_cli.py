"""Tests for the CLI module."""

import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from langki.cli import check_environment, main, process_sentence


def test_check_environment_missing_vars() -> None:
    """Test check_environment when environment variables are missing."""
    with patch.dict(os.environ, {}, clear=True):
        status, message = check_environment(audio_provider="elevenlabs")
        assert status is False
        assert "Missing environment variables" in message
        assert "OPENAI_API_KEY" in message
        assert "ELEVENLABS_API_KEY" in message


def test_check_environment_all_vars_present() -> None:
    """Test check_environment when all environment variables are present."""
    with patch.dict(
        os.environ, {"OPENAI_API_KEY": "test_key", "ELEVENLABS_API_KEY": "test_key"}, clear=True
    ):
        status, message = check_environment(audio_provider="elevenlabs")
        assert status is True
        assert message == "All required environment variables are set"


def test_process_sentence() -> None:
    """Test process_sentence function."""
    # Mock the translation service
    mock_translation = MagicMock()
    mock_translation.hanzi = "u4f60u597d"
    mock_translation.pinyin = "nu01d0 hu01ceo"
    mock_translation.english = "Hello"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    # Mock the audio service
    mock_audio_service = MagicMock()
    mock_audio_service.generate_audio_file.return_value = "/tmp/audio.mp3"

    # Mock the Anki client
    mock_anki_client = MagicMock()
    mock_anki_client.add_note.return_value = 12345

    with patch("langki.cli.TranslationService", return_value=mock_translation_service):
        with patch("langki.cli.create_audio_service", return_value=mock_audio_service):
            # Call the function
            process_sentence("Hello", "Test Deck", mock_anki_client, audio_provider="google-translate")

            # Verify the calls
            mock_translation_service.translate.assert_called_once_with("Hello")
            mock_audio_service.generate_audio_file.assert_called_once_with("u4f60u597d")
            mock_anki_client.add_note.assert_called_once()


def test_main_no_sentences_no_file() -> None:
    """Test main function with no sentences and no file (interactive mode)."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with patch("langki.cli.check_environment", return_value=(True, "All good")):
        with patch("langki.cli.AnkiClient") as mock_anki_client_class:
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            mock_anki_client_class.return_value = mock_anki_client

            # Mock Prompt.ask to simulate user input and then exit
            with patch("rich.prompt.Prompt.ask", side_effect=["exit"]):
                result = runner.invoke(main, [])
                assert result.exit_code == 0


def test_main_with_sentences() -> None:
    """Test main function with sentences provided as arguments."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with patch("langki.cli.check_environment", return_value=(True, "All good")):
        with patch("langki.cli.AnkiClient") as mock_anki_client_class:
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            mock_anki_client_class.return_value = mock_anki_client

            # Mock process_sentence
            with patch("langki.cli.process_sentence") as mock_process_sentence:
                result = runner.invoke(main, ["Hello", "world"])
                assert result.exit_code == 0

                # Looking at the CLI implementation, if all arguments have no spaces,
                # they are joined together into a single sentence
                mock_process_sentence.assert_called_once_with(
                    "Helloworld", "Smalltalk", mock_anki_client, "google-translate"
                )


def test_main_with_file() -> None:
    """Test main function with a file input."""
    runner = CliRunner()

    # Create a temporary file with sentences
    with runner.isolated_filesystem():
        with open("sentences.txt", "w") as f:
            f.write("Hello\nWorld\n")

        # Mock environment and Anki checks to pass
        with patch("langki.cli.check_environment", return_value=(True, "All good")):
            with patch("langki.cli.AnkiClient") as mock_anki_client_class:
                mock_anki_client = MagicMock()
                mock_anki_client.check_connection.return_value = (True, "Connected")
                mock_anki_client_class.return_value = mock_anki_client

                # Mock process_sentence
                with patch("langki.cli.process_sentence") as mock_process_sentence:
                    result = runner.invoke(main, ["--file", "sentences.txt"])
                    assert result.exit_code == 0

                    # Check that process_sentence was called for each line in the file
                    assert mock_process_sentence.call_count == 2
                    mock_process_sentence.assert_any_call(
                        "Hello", "Smalltalk", mock_anki_client, "google-translate"
                    )
                    mock_process_sentence.assert_any_call(
                        "World", "Smalltalk", mock_anki_client, "google-translate"
                    )

"""Tests for the CLI module."""

import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from add2anki.cli import (
    check_environment,
    is_chinese_learning_table,
    main,
    process_sentence,
)


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
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "ELEVENLABS_API_KEY": "test_key"}, clear=True):
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
    mock_translation.style = "conversational"

    mock_translation_service = MagicMock()
    mock_translation_service.translate.return_value = mock_translation

    # Mock the audio service
    mock_audio_service = MagicMock()
    mock_audio_service.generate_audio_file.return_value = "/tmp/audio.mp3"

    # Mock the Anki client
    mock_anki_client = MagicMock()
    mock_anki_client.add_note.return_value = 12345

    # Mock the note type and field names
    mock_anki_client.get_field_names.return_value = [
        "Chinese",
        "Pronunciation",
        "Translation",
        "Sound",
    ]

    # Mock the config
    mock_config = MagicMock()
    mock_config.note_type = "Chinese Basic"

    with patch("add2anki.cli.TranslationService", return_value=mock_translation_service):
        with patch("add2anki.cli.create_audio_service", return_value=mock_audio_service):
            with patch("add2anki.cli.load_config", return_value=mock_config):
                with patch("add2anki.cli.save_config"):
                    # Test 1: Call the function with default tags (None)
                    process_sentence(
                        "Hello",
                        "Test Deck",
                        mock_anki_client,
                        audio_provider="google-translate",
                        style="conversational",
                    )

                    # Verify the calls
                    mock_translation_service.translate.assert_called_with("Hello", style="conversational")
                    mock_audio_service.generate_audio_file.assert_called_with("u4f60u597d")

                    # Default tag should be ["add2anki"]
                    mock_anki_client.add_note.assert_called_with(
                        deck_name="Test Deck",
                        note_type="Chinese Basic",
                        fields={"Chinese": "u4f60u597d", "Pronunciation": "nu01d0 hu01ceo", "Translation": "Hello"},
                        audio={
                            "path": "/tmp/audio.mp3",
                            "filename": mock_anki_client.add_note.call_args[1]["audio"]["filename"],
                            "fields": ["Sound"],
                        },
                        tags=["add2anki"],
                    )

                    # Reset mocks for next test
                    mock_anki_client.reset_mock()
                    mock_translation_service.reset_mock()
                    mock_audio_service.reset_mock()

                    # Test 2: Call the function with custom tags
                    process_sentence(
                        "Hello",
                        "Test Deck",
                        mock_anki_client,
                        audio_provider="google-translate",
                        style="conversational",
                        tags="custom,tags",
                    )

                    # Custom tags should be ["custom", "tags"]
                    mock_anki_client.add_note.assert_called_with(
                        deck_name="Test Deck",
                        note_type="Chinese Basic",
                        fields={"Chinese": "u4f60u597d", "Pronunciation": "nu01d0 hu01ceo", "Translation": "Hello"},
                        audio={
                            "path": "/tmp/audio.mp3",
                            "filename": mock_anki_client.add_note.call_args[1]["audio"]["filename"],
                            "fields": ["Sound"],
                        },
                        tags=["custom", "tags"],
                    )

                    # Reset mocks for next test
                    mock_anki_client.reset_mock()

                    # Test 3: Call the function with empty tags
                    process_sentence(
                        "Hello",
                        "Test Deck",
                        mock_anki_client,
                        audio_provider="google-translate",
                        style="conversational",
                        tags="",
                    )

                    # Empty tags should result in empty list
                    mock_anki_client.add_note.assert_called_with(
                        deck_name="Test Deck",
                        note_type="Chinese Basic",
                        fields={"Chinese": "u4f60u597d", "Pronunciation": "nu01d0 hu01ceo", "Translation": "Hello"},
                        audio={
                            "path": "/tmp/audio.mp3",
                            "filename": mock_anki_client.add_note.call_args[1]["audio"]["filename"],
                            "fields": ["Sound"],
                        },
                        tags=[],
                    )


def test_main_no_sentences_no_file() -> None:
    """Test main function with no sentences and no file (interactive mode)."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with patch("add2anki.cli.check_environment", return_value=(True, "All good")):
        with patch("add2anki.cli.AnkiClient") as mock_anki_client_class:
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            # Mock get_deck_names to return a list of decks
            mock_anki_client.get_deck_names.return_value = ["Default"]
            mock_anki_client_class.return_value = mock_anki_client

            # Mock config
            mock_config = MagicMock()
            mock_config.deck_name = None
            mock_config.note_type = "Basic"

            with patch("add2anki.cli.load_config", return_value=mock_config):
                # Mock save_config to avoid file operations
                with patch("add2anki.cli.save_config"):
                    # Mock Prompt.ask to simulate user input and then exit
                    with patch("rich.prompt.Prompt.ask", side_effect=["exit"]):
                        result = runner.invoke(main, [])
                        assert result.exit_code == 0


def test_main_with_sentences() -> None:
    """Test main function with sentences provided as arguments."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with patch("add2anki.cli.check_environment", return_value=(True, "All good")):
        with patch("add2anki.cli.AnkiClient") as mock_anki_client_class:
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            mock_anki_client_class.return_value = mock_anki_client

            # Mock load_config to return a config with deck_name set to "Smalltalk"
            mock_config = MagicMock()
            mock_config.deck_name = "Smalltalk"
            with patch("add2anki.cli.load_config", return_value=mock_config):
                # Mock process_sentence
                with patch("add2anki.cli.process_sentence") as mock_process_sentence:
                    result = runner.invoke(main, ["Hello", "world"])
                    assert result.exit_code == 0

                    # Looking at the CLI implementation, if all arguments have no spaces,
                    # they are joined together into a single sentence, and 'conversational' is the default style
                    mock_process_sentence.assert_called_once_with(
                        "Hello world",
                        "Smalltalk",
                        mock_anki_client,
                        "google-translate",
                        "conversational",
                        None,
                        False,
                        False,
                        False,
                        None,  # tags parameter
                    )


def test_main_with_file() -> None:
    """Test main function with a file input."""
    runner = CliRunner()

    # Create a temporary file with sentences
    with runner.isolated_filesystem():
        with open("sentences.txt", "w") as f:
            f.write("Hello\nWorld\n")

        # Mock environment and Anki checks to pass
        with patch("add2anki.cli.check_environment", return_value=(True, "All good")):
            with patch("add2anki.cli.AnkiClient") as mock_anki_client_class:
                mock_anki_client = MagicMock()
                mock_anki_client.check_connection.return_value = (True, "Connected")
                mock_anki_client_class.return_value = mock_anki_client

                # Mock load_config to return a config with deck_name set to "Smalltalk"
                mock_config = MagicMock()
                mock_config.deck_name = "Smalltalk"
                with patch("add2anki.cli.load_config", return_value=mock_config):
                    # Mock process_sentence
                    with patch("add2anki.cli.process_sentence") as mock_process_sentence:
                        result = runner.invoke(main, ["--file", "sentences.txt"])
                        assert result.exit_code == 0

                        # Check that process_sentence was called for each line in the file
                        assert mock_process_sentence.call_count == 2
                        mock_process_sentence.assert_any_call(
                            "Hello",
                            "Smalltalk",
                            mock_anki_client,
                            "google-translate",
                            "conversational",
                            None,
                            False,
                            False,
                            False,
                            None,  # tags parameter
                        )
                        mock_process_sentence.assert_any_call(
                            "World",
                            "Smalltalk",
                            mock_anki_client,
                            "google-translate",
                            "conversational",
                            None,
                            False,
                            False,
                            False,
                            None,  # tags parameter
                        )


def test_is_chinese_learning_table() -> None:
    """Test the is_chinese_learning_table function."""
    # Test with Chinese-related headers
    assert is_chinese_learning_table(["Chinese", "English", "Notes"]) is True
    assert is_chinese_learning_table(["Mandarin", "Translation"]) is True
    assert is_chinese_learning_table(["Word", "Hanzi", "Meaning"]) is True
    assert is_chinese_learning_table(["ID", "chinese_word", "english_meaning"]) is True

    # Test with non-Chinese-related headers
    assert is_chinese_learning_table(["French", "English", "Notes"]) is False
    assert is_chinese_learning_table(["Word", "Translation", "Notes"]) is False
    assert is_chinese_learning_table(["ID", "Term", "Definition"]) is False


def test_main_with_csv_file() -> None:
    """Test main function with a CSV file input."""
    runner = CliRunner()

    # Create a temporary CSV file
    with runner.isolated_filesystem():
        with open("vocab.csv", "w") as f:
            f.write("Chinese,Pinyin,English,Notes\n")
            f.write("你好,ni hao,Hello,greeting\n")
            f.write("谢谢,xie xie,Thank you,polite\n")

        # Mock environment and Anki checks to pass
        with patch("add2anki.cli.check_environment", return_value=(True, "All good")):
            with patch("add2anki.cli.AnkiClient") as mock_anki_client_class:
                mock_anki_client = MagicMock()
                mock_anki_client.check_connection.return_value = (True, "Connected")
                mock_anki_client_class.return_value = mock_anki_client

                # Mock load_config to return a config with deck_name set to "Chinese"
                mock_config = MagicMock()
                mock_config.deck_name = "Chinese"
                with patch("add2anki.cli.load_config", return_value=mock_config):
                    # Mock process_structured_file
                    with patch("add2anki.cli.process_structured_file") as mock_process_structured_file:
                        result = runner.invoke(main, ["--file", "vocab.csv"])
                        assert result.exit_code == 0

                        # Check that process_structured_file was called with the CSV file
                        mock_process_structured_file.assert_called_once()
                        call_args = mock_process_structured_file.call_args[0]
                        assert call_args[0] == "vocab.csv"  # file path
                        assert call_args[1] == "Chinese"  # deck name


def test_main_with_tags() -> None:
    """Test main function with tags option."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with patch("add2anki.cli.check_environment", return_value=(True, "All good")):
        with patch("add2anki.cli.AnkiClient") as mock_anki_client_class:
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            mock_anki_client_class.return_value = mock_anki_client

            # Mock load_config to return a config with deck_name set to "Smalltalk"
            mock_config = MagicMock()
            mock_config.deck_name = "Smalltalk"
            with patch("add2anki.cli.load_config", return_value=mock_config):
                # Mock process_sentence
                with patch("add2anki.cli.process_sentence") as mock_process_sentence:
                    # Test with custom tags
                    result = runner.invoke(main, ["--tags", "test,tag", "Hello"])
                    assert result.exit_code == 0

                    mock_process_sentence.assert_called_with(
                        "Hello",
                        "Smalltalk",
                        mock_anki_client,
                        "google-translate",
                        "conversational",
                        None,
                        False,
                        False,
                        False,
                        "test,tag",  # tags parameter
                    )

                    # Reset mock
                    mock_process_sentence.reset_mock()

                    # Test with empty tags
                    result = runner.invoke(main, ["--tags", "", "Hello"])
                    assert result.exit_code == 0

                    mock_process_sentence.assert_called_with(
                        "Hello",
                        "Smalltalk",
                        mock_anki_client,
                        "google-translate",
                        "conversational",
                        None,
                        False,
                        False,
                        False,
                        "",  # empty tags parameter
                    )

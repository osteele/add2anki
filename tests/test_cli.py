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

    with (
        patch("add2anki.cli.TranslationService", return_value=mock_translation_service),
        patch("add2anki.cli.create_audio_service", return_value=mock_audio_service),
        patch("add2anki.cli.load_config", return_value=mock_config),
        patch("add2anki.cli.save_config"),
        patch(
            "add2anki.cli.find_suitable_note_types",
            return_value=[
                (
                    "Chinese Basic",
                    {
                        "hanzi_field": "Chinese",
                        "pinyin_field": "Pronunciation",
                        "english_field": "Translation",
                    },
                )
            ],
        ),
        patch("contextual_langdetect.contextual_detect") as mock_detect,
    ):
        # Mock language detection to return English
        mock_detect.return_value = ["en"]
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
            fields={
                "Chinese": "u4f60u597d",
                "Pronunciation": "nu01d0 hu01ceo",
                "Translation": "Hello",
            },
            audio={
                "path": "/tmp/audio.mp3",
                "filename": "audio.mp3",
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
            fields={
                "Chinese": "u4f60u597d",
                "Pronunciation": "nu01d0 hu01ceo",
                "Translation": "Hello",
            },
            audio={
                "path": "/tmp/audio.mp3",
                "filename": "audio.mp3",
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
            fields={
                "Chinese": "u4f60u597d",
                "Pronunciation": "nu01d0 hu01ceo",
                "Translation": "Hello",
            },
            audio={
                "path": "/tmp/audio.mp3",
                "filename": "audio.mp3",
                "fields": ["Sound"],
            },
            tags=[],
        )


def test_note_type_selection() -> None:
    """Test note type selection behavior."""
    # Mock the translation service
    mock_translation = MagicMock()
    mock_translation.hanzi = "你好"
    mock_translation.pinyin = "nǐ hǎo"
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
    mock_anki_client.get_field_names.return_value = [
        "Chinese",
        "Pronunciation",
        "Translation",
        "Sound",
    ]

    # Test 1: Using specific note type
    with (
        patch("add2anki.cli.TranslationService", return_value=mock_translation_service),
        patch("add2anki.cli.create_audio_service", return_value=mock_audio_service),
        patch("contextual_langdetect.contextual_detect", return_value=["en"]),
        patch("add2anki.cli.find_suitable_note_types", return_value=[("Chinese Basic", {}), ("Chinese Vocab", {})]),
        patch("add2anki.cli.load_config", return_value=MagicMock(note_type="Previous Note Type")),
        patch("add2anki.cli.save_config"),
    ):
        process_sentence(
            "Hello",
            "Test Deck",
            mock_anki_client,
            audio_provider="google-translate",
            style="conversational",
            note_type="Custom Note Type",
        )

        # Verify the note type was used as specified
        mock_anki_client.get_field_names.assert_called_with("Custom Note Type")

    # Reset mocks
    mock_anki_client.reset_mock()

    # Test 2: Using 'default' note type
    mock_config = MagicMock()
    mock_config.note_type = "Saved Note Type"

    with (
        patch("add2anki.cli.TranslationService", return_value=mock_translation_service),
        patch("add2anki.cli.create_audio_service", return_value=mock_audio_service),
        patch("contextual_langdetect.contextual_detect", return_value=["en"]),
        patch("add2anki.cli.find_suitable_note_types", return_value=[("Chinese Basic", {}), ("Chinese Vocab", {})]),
        patch("add2anki.cli.load_config", return_value=mock_config),
        patch("add2anki.cli.save_config"),
    ):
        process_sentence(
            "Hello",
            "Test Deck",
            mock_anki_client,
            audio_provider="google-translate",
            style="conversational",
            note_type="default",
        )

        # Verify the saved default note type was used
        mock_anki_client.get_field_names.assert_called_with("Saved Note Type")

    # Reset mocks
    mock_anki_client.reset_mock()

    # Test 3: Single available note type (auto-select)
    with (
        patch("add2anki.cli.TranslationService", return_value=mock_translation_service),
        patch("add2anki.cli.create_audio_service", return_value=mock_audio_service),
        patch("contextual_langdetect.contextual_detect", return_value=["en"]),
        patch("add2anki.cli.find_suitable_note_types", return_value=[("Chinese Basic", {})]),
        patch("add2anki.cli.load_config", return_value=MagicMock(note_type=None)),
        patch("add2anki.cli.save_config"),
    ):
        process_sentence(
            "Hello",
            "Test Deck",
            mock_anki_client,
            audio_provider="google-translate",
            style="conversational",
            note_type=None,
        )

        # Verify the only available note type was used
        mock_anki_client.get_field_names.assert_called_with("Chinese Basic")


def test_main_no_sentences_no_file() -> None:
    """Test main function with no sentences and no file (interactive mode)."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with (
        patch("add2anki.cli.check_environment", return_value=(True, "All good")),
        patch("add2anki.cli.AnkiClient") as mock_anki_client_class,
    ):
        mock_anki_client = MagicMock()
        mock_anki_client.check_connection.return_value = (True, "Connected")
        # Mock get_deck_names to return a list of decks
        mock_anki_client.get_deck_names.return_value = ["Default"]
        mock_anki_client_class.return_value = mock_anki_client

        # Mock config
        mock_config = MagicMock()
        mock_config.deck_name = None
        mock_config.note_type = "Basic"

        with (
            patch("add2anki.cli.load_config", return_value=mock_config),
            patch("add2anki.cli.save_config"),
            patch("rich.prompt.Prompt.ask", side_effect=["exit"]),
        ):
            result = runner.invoke(main, [])
            assert result.exit_code == 0


def test_main_with_sentences() -> None:
    """Test main function with sentences provided as arguments."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with (
        patch("add2anki.cli.check_environment", return_value=(True, "All good")),
        patch("add2anki.cli.AnkiClient") as mock_anki_client_class,
    ):
        mock_anki_client = MagicMock()
        mock_anki_client.check_connection.return_value = (True, "Connected")
        mock_anki_client_class.return_value = mock_anki_client

        # Test 1: Using --deck option with a specific deck name
        mock_config = MagicMock()
        mock_config.deck_name = "Previous Deck"
        with (
            patch("add2anki.cli.load_config", return_value=mock_config),
            patch("add2anki.cli.find_suitable_note_types", return_value=[("Chinese Basic", {})]),
            patch("add2anki.cli.process_sentence") as mock_process_sentence,
            patch("contextual_langdetect.contextual_detect") as mock_detect,
        ):
            # Mock language detection to return English
            mock_detect.return_value = ["en"]
            result = runner.invoke(main, ["Hello", "world", "--deck", "Smalltalk", "--no-launch-anki"])
            assert result.exit_code == 0

            # Verify process_sentence is called with the specified deck
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
                None,  # source_lang parameter
                None,  # target_lang parameter
            )
            mock_process_sentence.reset_mock()

        # Test 2: Using --deck default to use the saved default deck
        mock_config = MagicMock()
        mock_config.deck_name = "Previous Deck"
        with (
            patch("add2anki.cli.load_config", return_value=mock_config),
            patch("add2anki.cli.find_suitable_note_types", return_value=[("Chinese Basic", {})]),
            patch("add2anki.cli.process_sentence") as mock_process_sentence,
            patch("contextual_langdetect.contextual_detect") as mock_detect,
        ):
            # Mock language detection to return English
            mock_detect.return_value = ["en"]
            result = runner.invoke(main, ["Hello", "world", "--deck", "default", "--no-launch-anki"])
            assert result.exit_code == 0

            # Verify process_sentence is called with the saved default deck
            mock_process_sentence.assert_called_once_with(
                "Hello world",
                "Previous Deck",
                mock_anki_client,
                "google-translate",
                "conversational",
                None,
                False,
                False,
                False,
                None,  # tags parameter
                None,  # source_lang parameter
                None,  # target_lang parameter
            )


def test_main_with_file() -> None:
    """Test main function with a file input."""
    runner = CliRunner()

    # Create a temporary CSV file with sentences
    with runner.isolated_filesystem():
        with open("sentences.csv", "w") as f:
            f.write("text,Chinese,Pronunciation,Translation\n")
            f.write("Hello,你好,ni hao,Hello\n")
            f.write("World,世界,shi jie,World\n")

        # Mock environment and Anki checks to pass
        with (
            patch("add2anki.cli.check_environment", return_value=(True, "All good")),
            patch("add2anki.cli.AnkiClient") as mock_anki_client_class,
        ):
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            mock_anki_client.get_deck_names.return_value = ["Smalltalk", "Default"]
            mock_anki_client.get_note_types.return_value = ["Chinese Basic"]
            mock_anki_client.get_field_names.return_value = ["Chinese", "Pronunciation", "Translation", "Sound"]
            mock_anki_client.get_model_sort_field.return_value = "Chinese"  # Mock required field
            mock_anki_client.get_first_field.return_value = "Chinese"  # Mock first field as fallback

            # Setup return value for add_note and make sure audio is properly handled
            def mock_add_note(
                deck_name: str,
                note_type: str,
                fields: dict[str, str],
                audio: dict[str, str | list[str]] | None = None,
                tags: list[str] | None = None,
            ) -> int:
                # Replace MagicMock objects with simple dictionaries to avoid serialization issues
                if audio is not None and isinstance(audio, MagicMock):
                    audio = {"path": "/tmp/audio.mp3", "filename": "audio.mp3", "fields": ["Sound"]}
                return 12345

            mock_anki_client.add_note.side_effect = mock_add_note
            mock_anki_client_class.return_value = mock_anki_client

            # Mock config that will be loaded
            mock_config = MagicMock()
            mock_config.deck_name = "Smalltalk"

            with (
                patch("add2anki.cli.load_config", return_value=mock_config),
                # Mock the IntPrompt.ask to return the first option (Smalltalk)
                patch("rich.prompt.IntPrompt.ask", return_value="1"),
                # Mock save_config directly to prevent serialization issues
                patch("add2anki.cli.save_config"),
            ):
                # Run the CLI command
                result = runner.invoke(main, ["--file", "sentences.csv", "--no-launch-anki"])

                # Check that the command executed successfully
                assert result.exit_code == 0

                # Verify AnkiClient.add_note was called (implies process_structured_file ran)
                # Expecting 2 calls, one for each row in the CSV
                assert mock_anki_client.add_note.call_count == 2


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
        with (
            patch("add2anki.cli.check_environment", return_value=(True, "All good")),
            patch("add2anki.cli.AnkiClient") as mock_anki_client_class,
        ):
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            mock_anki_client_class.return_value = mock_anki_client

            # Mock load_config to return a config with deck_name set to "Chinese"
            mock_config = MagicMock()
            mock_config.deck_name = "Smalltalk"
            with (
                patch("add2anki.cli.load_config", return_value=mock_config),
                patch("rich.prompt.IntPrompt.ask", return_value="1"),
                patch("add2anki.cli.process_structured_file", return_value=None) as mock_process_structured_file,
            ):
                # Use --deck option to bypass the interactive prompt
                result = runner.invoke(main, ["--file", "vocab.csv", "--deck", "Smalltalk", "--no-launch-anki"])

                # Verify the command executed successfully
                assert result.exit_code == 0

                # Verify process_structured_file was called with the right arguments
                mock_process_structured_file.assert_called_once()
                call_args = mock_process_structured_file.call_args[0]
                assert call_args[0] == "vocab.csv"  # file path
                assert call_args[1] == "Smalltalk"  # deck name


def test_main_with_tags() -> None:
    """Test main function with tags option."""
    runner = CliRunner()

    # Mock environment and Anki checks to pass
    with (
        patch("add2anki.cli.check_environment", return_value=(True, "All good")),
        patch("add2anki.cli.AnkiClient") as mock_anki_client_class,
    ):
        mock_anki_client = MagicMock()
        mock_anki_client.check_connection.return_value = (True, "Connected")
        mock_anki_client.get_deck_names.return_value = ["Smalltalk", "Default"]
        mock_anki_client.get_note_types.return_value = ["Chinese Basic"]
        mock_anki_client.get_field_names.return_value = ["Chinese", "Pronunciation", "Translation", "Sound"]

        # Mock translation service to return expected values
        with patch("add2anki.cli.TranslationService") as mock_translation_service_class:
            mock_translation = MagicMock()
            mock_translation.hanzi = "你好"
            mock_translation.pinyin = "ni hao"
            mock_translation.english = "Hello"

            mock_translation_service = MagicMock()
            mock_translation_service.translate.return_value = mock_translation
            mock_translation_service_class.return_value = mock_translation_service

            # Mock audio service
            with patch("add2anki.cli.create_audio_service") as mock_audio_service_class:
                mock_audio_service = MagicMock()
                mock_audio_service.generate_audio_file.return_value = "/tmp/audio.mp3"
                mock_audio_service_class.return_value = mock_audio_service

                # Setup return value for add_note
                mock_anki_client.add_note.return_value = 12345
                mock_anki_client_class.return_value = mock_anki_client

                # Mock config that will be loaded
                mock_config = MagicMock()
                mock_config.deck_name = "Smalltalk"
                mock_config.note_type = "Chinese Basic"
                with (
                    patch("add2anki.cli.load_config", return_value=mock_config),
                    patch("contextual_langdetect.contextual_detect") as mock_detect,
                    patch("rich.prompt.IntPrompt.ask", return_value=1),
                    patch("add2anki.cli.process_sentence", return_value=None) as mock_process_sentence,
                ):
                    # Mock language detection to return English
                    mock_detect.return_value = ["en"]

                    # Test 1: Default tags (None) - use --deck to bypass interactive prompt
                    result = runner.invoke(main, ["Hello", "--deck", "Smalltalk", "--no-launch-anki"])
                    assert result.exit_code == 0

                    # Verify process_sentence is called with default tags (None)
                    mock_process_sentence.assert_called_once_with(
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
                        None,  # source_lang parameter
                        None,  # target_lang parameter
                    )
                    mock_process_sentence.reset_mock()

                    # Test 2: Custom tags - use --deck to bypass interactive prompt
                    result = runner.invoke(
                        main, ["Hello", "--deck", "Smalltalk", "--tags", "custom,tags", "--no-launch-anki"]
                    )
                    assert result.exit_code == 0

                    # Verify process_sentence is called with custom tags
                    mock_process_sentence.assert_called_once_with(
                        "Hello",
                        "Smalltalk",
                        mock_anki_client,
                        "google-translate",
                        "conversational",
                        None,
                        False,
                        False,
                        False,
                        "custom,tags",  # tags parameter
                        None,  # source_lang parameter
                        None,  # target_lang parameter
                    )
                    mock_process_sentence.reset_mock()

                    # Test 3: Empty tags - use --deck to bypass interactive prompt
                    result = runner.invoke(main, ["Hello", "--deck", "Smalltalk", "--tags", "", "--no-launch-anki"])
                    assert result.exit_code == 0

                    # Verify process_sentence is called with empty tags
                    mock_process_sentence.assert_called_once_with(
                        "Hello",
                        "Smalltalk",
                        mock_anki_client,
                        "google-translate",
                        "conversational",
                        None,
                        False,
                        False,
                        False,
                        "",  # tags parameter
                        None,  # source_lang parameter
                        None,  # target_lang parameter
                    )

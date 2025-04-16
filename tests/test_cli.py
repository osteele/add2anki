"""Tests for the CLI module."""

import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from add2anki.cli import (
    add_translation_to_anki,
    check_environment,
    classify_positional_args,
    is_chinese_learning_table,
    main,
    map_fields_to_anki,
    process_sentence,
    process_text_file,
)
from add2anki.exceptions import Add2ankiError


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
            mock_translation_service,
            mock_audio_service,
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
                "Sound": "[sound:audio.mp3]",
            },
            audio=None,
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
            mock_translation_service,
            mock_audio_service,
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
                "Sound": "[sound:audio.mp3]",
            },
            audio=None,
            tags=["custom", "tags"],
        )

        # Reset mocks for next test
        mock_anki_client.reset_mock()

        # Test 3: Call the function with empty tags
        process_sentence(
            "Hello",
            "Test Deck",
            mock_anki_client,
            mock_translation_service,
            mock_audio_service,
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
                "Sound": "[sound:audio.mp3]",
            },
            audio=None,
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
            mock_translation_service,
            mock_audio_service,
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
            mock_translation_service,
            mock_audio_service,
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
            mock_translation_service,
            mock_audio_service,
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
            mock_process_sentence.assert_called_with(
                "Hello world",
                "Smalltalk",
                mock_anki_client,
                mock_process_sentence.call_args[0][3],  # translation_service
                mock_process_sentence.call_args[0][4],  # audio_service
                "conversational",
                "Chinese Basic",
                False,  # dry_run
                False,  # verbose
                False,  # debug
                None,  # tags
                None,  # source_lang
                "zh",  # target_lang
                None,  # state
                False,  # launch_anki
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
                mock_process_sentence.assert_called_with(
                    "Hello world",
                    "Previous Deck",
                    mock_anki_client,
                    mock_process_sentence.call_args[0][3],  # translation_service
                    mock_process_sentence.call_args[0][4],  # audio_service
                    "conversational",
                    "Chinese Basic",
                    False,  # dry_run
                    False,  # verbose
                    False,  # debug
                    None,  # tags
                    None,  # source_lang
                    "zh",  # target_lang
                    None,  # state
                    False,  # launch_anki
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
            patch("add2anki.cli.process_file", return_value=None) as mock_process_file,
            # Patch classify_positional_args to recognize the file
            patch("add2anki.cli.classify_positional_args", return_value={"mode": "paths", "values": ["sentences.csv"]}),
        ):
            mock_anki_client = MagicMock()
            mock_anki_client.check_connection.return_value = (True, "Connected")
            mock_anki_client_class.return_value = mock_anki_client

            # Mock config that will be loaded
            mock_config = MagicMock()
            mock_config.deck_name = "Smalltalk"

            with (
                patch("add2anki.cli.load_config", return_value=mock_config),
                patch("rich.prompt.IntPrompt.ask", return_value="1"),
                patch("add2anki.cli.save_config"),
            ):
                # Run the CLI command
                result = runner.invoke(main, ["--file", "sentences.csv", "--no-launch-anki"])

                # Check that the command executed successfully
                assert result.exit_code == 0

                # Verify process_file was called with the right arguments
                mock_process_file.assert_called_once()


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
            patch("add2anki.cli.process_file", return_value=None) as mock_process_file,
            # Patch classify_positional_args to recognize the file
            patch("add2anki.cli.classify_positional_args", return_value={"mode": "paths", "values": ["vocab.csv"]}),
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
            ):
                # Use --deck option to bypass the interactive prompt
                result = runner.invoke(main, ["--file", "vocab.csv", "--deck", "Smalltalk", "--no-launch-anki"])

                # Verify the command executed successfully
                assert result.exit_code == 0

                # Verify process_file was called with the right arguments
                mock_process_file.assert_called_once()


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


def test_map_fields_to_anki_basic_mapping() -> None:
    """Test basic mapping with standard field types."""
    field_names = ["Hanzi", "Pinyin", "English", "Sound"]
    sentence = "Hello"
    hanzi = "你好"
    pinyin = "nǐ hǎo"
    detected = "en"
    target_lang = "zh"
    audio_path = "/tmp/audio.mp3"

    fields, audio_field_set = map_fields_to_anki(
        field_names, sentence, hanzi, pinyin, detected, target_lang, audio_path
    )

    # Verify correct field mapping
    assert fields["Hanzi"] == hanzi
    assert fields["Pinyin"] == pinyin
    assert fields["English"] == sentence
    assert fields["Sound"] == "[sound:audio.mp3]"
    assert audio_field_set is True


def test_map_fields_to_anki_mixed_case() -> None:
    """Test mapping with mixed case field names and variations."""
    sentence = "Hello"
    hanzi = "你好"
    pinyin = "nǐ hǎo"
    detected = "en"
    target_lang = "zh"
    audio_path = "/tmp/audio.mp3"
    field_names = ["Chinese", "PRONUNCIATION", "TransLation", "Audio_Field"]

    fields, audio_field_set = map_fields_to_anki(
        field_names, sentence, hanzi, pinyin, detected, target_lang, audio_path
    )

    # Verify correct field mapping with varied casing
    assert fields["Chinese"] == hanzi
    assert fields["PRONUNCIATION"] == pinyin
    assert fields["TransLation"] == sentence
    assert fields["Audio_Field"] == "[sound:audio.mp3]"
    assert audio_field_set is True


def test_map_fields_to_anki_no_audio() -> None:
    """Test mapping when no audio path is provided."""
    sentence = "Hello"
    hanzi = "你好"
    pinyin = "nǐ hǎo"
    detected = "en"
    target_lang = "zh"
    field_names = ["Chinese", "PRONUNCIATION", "TransLation", "Audio_Field"]

    fields, audio_field_set = map_fields_to_anki(field_names, sentence, hanzi, pinyin, detected, target_lang, None)

    # Verify no audio field is set
    assert "Audio_Field" not in fields
    assert audio_field_set is False


def test_map_fields_to_anki_multiple_audio_fields() -> None:
    """Test that only the first audio field is set when multiple are present."""
    sentence = "Hello"
    hanzi = "你好"
    pinyin = "nǐ hǎo"
    detected = "en"
    target_lang = "zh"
    audio_path = "/tmp/audio.mp3"
    field_names = ["Chinese", "Pinyin", "English", "Sound1", "Sound2"]

    fields, audio_field_set = map_fields_to_anki(
        field_names, sentence, hanzi, pinyin, detected, target_lang, audio_path
    )

    # Verify only first audio field is set
    assert fields["Sound1"] == "[sound:audio.mp3]"
    assert "Sound2" not in fields
    assert audio_field_set is True


def test_classify_positional_args() -> None:
    """Test the classify_positional_args function."""
    # Empty arguments - interactive mode
    result = classify_positional_args(())
    assert result["mode"] == "interactive"
    assert result["values"] == []

    # File paths (with patch to simulate file existence)
    with patch("os.path.exists", return_value=True):
        # Single file path
        result = classify_positional_args(("file.txt",))
        assert result["mode"] == "paths"
        assert result["values"] == ["file.txt"]

        # Multiple file paths
        result = classify_positional_args(("file1.txt", "file2.csv"))
        assert result["mode"] == "paths"
        assert result["values"] == ["file1.txt", "file2.csv"]

    # File-like arguments that don't exist
    with patch("os.path.exists", return_value=False):
        # Single file-like path
        result = classify_positional_args(("file.txt",))
        assert result["mode"] == "paths"
        assert result["values"] == ["file.txt"]

        # Multiple file-like paths
        result = classify_positional_args(("file1.txt", "file2.csv"))
        assert result["mode"] == "paths"
        assert result["values"] == ["file1.txt", "file2.csv"]

    # Text arguments
    # Single sentence
    result = classify_positional_args(("Hello world",))
    assert result["mode"] == "sentences"
    assert result["values"] == ["Hello world"]

    # Multiple words that should be joined into a sentence
    result = classify_positional_args(("Hello", "world"))
    assert result["mode"] == "sentences"
    assert result["values"] == ["Hello world"]

    # Multiple sentences
    result = classify_positional_args(("Hello world", "How are you?"))
    assert result["mode"] == "sentences"
    assert result["values"] == ["Hello world", "How are you?"]

    # Mixed arguments should raise ValueError
    with patch("os.path.exists", side_effect=lambda path_str: path_str == "file.txt"), pytest.raises(ValueError):
        classify_positional_args(("file.txt", "Hello world"))


def test_add_translation_to_anki_normal() -> None:
    """Test add_translation_to_anki with normal use case (with audio)."""
    # Setup test data
    sentence = "Hello"
    hanzi = "你好"
    pinyin = "nǐ hǎo"
    deck_name = "Test Deck"
    note_type = "Chinese Basic"
    field_names = ["Chinese", "Pinyin", "English", "Sound"]
    anki_client = MagicMock()
    anki_client.add_note.return_value = 12345
    audio_service = MagicMock()
    audio_service.generate_audio_file.return_value = "/tmp/audio.mp3"
    target_lang = "zh"
    detected_lang = "en"

    with patch("add2anki.cli.map_fields_to_anki") as mock_map_fields:
        # Mock the field mapping
        mock_map_fields.return_value = (
            {
                "Chinese": hanzi,
                "Pinyin": pinyin,
                "English": sentence,
                "Sound": "[sound:audio.mp3]",
            },
            True,  # audio_field_set
        )

        # Test with default parameters
        note_id = add_translation_to_anki(
            sentence=sentence,
            hanzi=hanzi,
            pinyin=pinyin,
            deck_name=deck_name,
            note_type=note_type,
            field_names=field_names,
            anki_client=anki_client,
            audio_service=audio_service,
            target_lang=target_lang,
            detected_lang=detected_lang,
        )

        # Verify the function worked correctly
        assert note_id == 12345
        mock_map_fields.assert_called_once()
        anki_client.add_note.assert_called_once()


def test_add_translation_to_anki_dry_run() -> None:
    """Test add_translation_to_anki in dry run mode."""
    # Setup test data
    sentence = "Hello"
    hanzi = "你好"
    pinyin = "nǐ hǎo"
    deck_name = "Test Deck"
    note_type = "Chinese Basic"
    field_names = ["Chinese", "Pinyin", "English", "Sound"]
    anki_client = MagicMock()
    anki_client.add_note.return_value = 12345
    audio_service = MagicMock()
    audio_service.generate_audio_file.return_value = "/tmp/audio.mp3"
    target_lang = "zh"
    detected_lang = "en"

    with patch("add2anki.cli.map_fields_to_anki") as mock_map_fields, patch("add2anki.cli.console"):
        # Mock the field mapping
        mock_map_fields.return_value = (
            {
                "Chinese": hanzi,
                "Pinyin": pinyin,
                "English": sentence,
                "Sound": "[sound:audio.mp3]",
            },
            True,  # audio_field_set
        )

        # Test with dry_run=True
        note_id = add_translation_to_anki(
            sentence=sentence,
            hanzi=hanzi,
            pinyin=pinyin,
            deck_name=deck_name,
            note_type=note_type,
            field_names=field_names,
            anki_client=anki_client,
            audio_service=audio_service,
            target_lang=target_lang,
            detected_lang=detected_lang,
            dry_run=True,
        )

        # Verify no actual Anki note was created
        assert note_id is None
        anki_client.add_note.assert_not_called()


def test_add_translation_to_anki_error_handling() -> None:
    """Test add_translation_to_anki handles errors properly."""
    # Setup test data
    sentence = "Hello"
    hanzi = "你好"
    pinyin = "nǐ hǎo"
    deck_name = "Test Deck"
    note_type = "Chinese Basic"
    field_names = ["Chinese", "Pinyin", "English", "Sound"]
    anki_client = MagicMock()
    anki_client.add_note.side_effect = Add2ankiError("Test error")
    audio_service = MagicMock()
    audio_service.generate_audio_file.return_value = "/tmp/audio.mp3"
    target_lang = "zh"
    detected_lang = "en"

    with patch("add2anki.cli.map_fields_to_anki") as mock_map_fields, patch("add2anki.cli.console"):
        # Mock the field mapping
        mock_map_fields.return_value = (
            {
                "Chinese": hanzi,
                "Pinyin": pinyin,
                "English": sentence,
                "Sound": "[sound:audio.mp3]",
            },
            True,  # audio_field_set
        )

        # Test error case
        note_id = add_translation_to_anki(
            sentence=sentence,
            hanzi=hanzi,
            pinyin=pinyin,
            deck_name=deck_name,
            note_type=note_type,
            field_names=field_names,
            anki_client=anki_client,
            audio_service=audio_service,
            target_lang=target_lang,
            detected_lang=detected_lang,
        )

        # Verify error was handled and no note ID was returned
        assert note_id is None


def test_process_text_file_with_content() -> None:
    """Test processing a text file with valid sentences."""
    # Setup test data
    path = "sentences.txt"
    deck = "Test Deck"
    anki_client = MagicMock()
    translation_service = MagicMock()
    audio_service = MagicMock()
    style = "conversational"

    with (
        patch("builtins.open", new_callable=MagicMock),
        patch("add2anki.cli.process_batch") as mock_process_batch,
        patch("add2anki.cli.console"),
    ):
        # Mock file content
        file_content = """Hello world
        # This is a comment and should be ignored
        How are you?

        # Empty lines should be skipped
        Nice to meet you!"""

        # Setup mock file
        mock_file = MagicMock()
        mock_file.__enter__.return_value = file_content.splitlines()
        mock_open = MagicMock(return_value=mock_file)

        with patch("builtins.open", mock_open):
            # Call the function
            process_text_file(
                path=path,
                deck=deck,
                anki_client=anki_client,
                translation_service=translation_service,
                audio_service=audio_service,
                style=style,
                note_type="Chinese Basic",
                dry_run=False,
                verbose=False,
                debug=False,
                tags="test,tag",
                source_lang="en",
                target_lang="zh",
                launch_anki=True,
            )

            # Verify process_batch was called with the correct arguments
            mock_process_batch.assert_called_once()
            call_args = mock_process_batch.call_args[0]

            # Check sentences list - should have comments and empty lines filtered out
            assert "Hello world" in call_args[0]
            assert "How are you?" in call_args[0]
            assert "Nice to meet you!" in call_args[0]
            assert len(call_args[0]) == 3  # 3 valid sentences

            # Check other arguments were passed correctly
            assert call_args[1] == deck
            assert call_args[2] == anki_client
            assert call_args[3] == translation_service
            assert call_args[4] == audio_service
            assert call_args[5] == style


def test_process_text_file_empty() -> None:
    """Test processing an empty text file with only comments."""
    # Setup test data
    path = "empty.txt"
    deck = "Test Deck"
    anki_client = MagicMock()
    translation_service = MagicMock()
    audio_service = MagicMock()
    style = "conversational"

    with (
        patch("builtins.open", new_callable=MagicMock),
        patch("add2anki.cli.process_batch") as mock_process_batch,
        patch("add2anki.cli.console"),
    ):
        # Mock empty file
        file_content = """# Just comments
        # And more comments

        """

        # Setup mock file
        mock_file = MagicMock()
        mock_file.__enter__.return_value = file_content.splitlines()
        mock_open = MagicMock(return_value=mock_file)

        with patch("builtins.open", mock_open):
            # Call the function
            process_text_file(
                path=path,
                deck=deck,
                anki_client=anki_client,
                translation_service=translation_service,
                audio_service=audio_service,
                style=style,
                note_type="Chinese Basic",
                dry_run=False,
                verbose=False,
                debug=False,
                tags=None,
                source_lang=None,
                target_lang=None,
                launch_anki=True,
            )

            # Verify process_batch was not called for empty file
            mock_process_batch.assert_not_called()


def test_process_text_file_error() -> None:
    """Test processing a text file with a file opening error."""
    # Setup test data
    path = "nonexistent.txt"
    deck = "Test Deck"
    anki_client = MagicMock()
    translation_service = MagicMock()
    audio_service = MagicMock()
    style = "conversational"

    with (
        patch("builtins.open", side_effect=OSError("File not found")),
        patch("add2anki.cli.process_batch") as mock_process_batch,
        patch("add2anki.cli.console"),
    ):
        # Call the function
        process_text_file(
            path=path,
            deck=deck,
            anki_client=anki_client,
            translation_service=translation_service,
            audio_service=audio_service,
            style=style,
            note_type="Chinese Basic",
            dry_run=False,
            verbose=False,
            debug=False,
            tags=None,
            source_lang=None,
            target_lang=None,
            launch_anki=True,
        )

        # Verify process_batch was not called due to error
        mock_process_batch.assert_not_called()


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
                    mock_process_sentence.assert_called_with(
                        "Hello",
                        "Smalltalk",
                        mock_anki_client,
                        mock_process_sentence.call_args[0][3],  # translation_service
                        mock_process_sentence.call_args[0][4],  # audio_service
                        "conversational",
                        "Chinese Basic",
                        False,  # dry_run
                        False,  # verbose
                        False,  # debug
                        None,  # tags
                        None,  # source_lang
                        "zh",  # target_lang
                        None,  # state
                        False,  # launch_anki
                    )

                    mock_process_sentence.reset_mock()

                    # Test 2: Custom tags - use --deck to bypass interactive prompt
                    result = runner.invoke(
                        main, ["Hello", "--deck", "Smalltalk", "--tags", "custom,tags", "--no-launch-anki"]
                    )
                    assert result.exit_code == 0

                    # Verify process_sentence is called with custom tags
                    mock_process_sentence.assert_called_with(
                        "Hello",
                        "Smalltalk",
                        mock_anki_client,
                        mock_process_sentence.call_args[0][3],  # translation_service
                        mock_process_sentence.call_args[0][4],  # audio_service
                        "conversational",
                        "Chinese Basic",
                        False,  # dry_run
                        False,  # verbose
                        False,  # debug
                        "custom,tags",  # tags
                        None,  # source_lang
                        "zh",  # target_lang
                        None,  # state
                        False,  # launch_anki
                    )

                    mock_process_sentence.reset_mock()

                    # Test 3: Empty tags - use --deck to bypass interactive prompt
                    result = runner.invoke(main, ["Hello", "--deck", "Smalltalk", "--tags", "", "--no-launch-anki"])
                    assert result.exit_code == 0

                    # Verify process_sentence is called with empty tags
                    mock_process_sentence.assert_called_with(
                        "Hello",
                        "Smalltalk",
                        mock_anki_client,
                        mock_process_sentence.call_args[0][3],  # translation_service
                        mock_process_sentence.call_args[0][4],  # audio_service
                        "conversational",
                        "Chinese Basic",
                        False,  # dry_run
                        False,  # verbose
                        False,  # debug
                        "",  # tags
                        None,  # source_lang
                        "zh",  # target_lang
                        None,  # state
                        False,  # launch_anki
                    )

                    mock_process_sentence.reset_mock()

"""Command-line interface for add2anki."""

import csv
import logging
import os
import pathlib
from collections.abc import Sequence
from typing import Any, Protocol, TypedDict, cast

import click
from contextual_langdetect import contextual_detect
from rich.console import Console
from rich.prompt import IntPrompt
from rich.table import Table

from add2anki.anki_client import AnkiClient
from add2anki.audio import create_audio_service

# Import directly from config.py to avoid circular imports
from add2anki.config import (
    FIELD_SYNONYMS,
    FieldMapping,
    find_matching_field,
    find_suitable_note_types,
    load_config,
    save_config,
)
from add2anki.exceptions import Add2ankiError, LanguageDetectionError
from add2anki.language_detection import Language, LanguageState
from add2anki.language_detection import process_batch as process_batch_detect
from add2anki.language_detection import process_sentence as process_sentence_detect
from add2anki.srt import filter_srt_entries, is_mandarin, parse_srt_file
from add2anki.translation import StyleType, TranslationService

console = Console()


class AudioConfig(TypedDict):
    """Type definition for audio configuration dictionary."""

    path: str
    filename: str
    fields: list[str]


class AnkiClientProtocol(Protocol):
    """Protocol for AnkiClient to avoid circular imports."""

    def get_note_types(self) -> list[str]: ...
    def get_field_names(self, note_type: str) -> list[str]: ...
    def get_card_templates(self, note_type: str) -> list[str]: ...
    def get_model_sort_field(self, note_type: str) -> str | None: ...
    def get_first_field(self, note_type: str) -> str | None: ...
    def get_deck_names(self) -> list[str]: ...
    def create_deck(self, deck_name: str) -> int: ...
    def add_note(
        self,
        deck_name: str,
        note_type: str,
        fields: dict[str, str],
        audio: dict[str, str | list[str]] | None = None,
        tags: list[str] | None = None,
    ) -> int: ...
    def check_anki_status(self) -> tuple[bool, str]: ...
    def launch_anki(self, timeout: int = 30) -> tuple[bool, str]: ...


def is_chinese_learning_table(headers: Sequence[str]) -> bool:
    """Determine if the CSV/TSV table is for Chinese language learning.

    Args:
        headers: Sequence of column headers from the CSV/TSV file

    Returns:
        True if the table appears to be for Chinese learning
    """
    chinese_indicators = ["chinese", "mandarin", "hanzi"]
    headers_lower = [h.lower() for h in headers]

    return any(indicator in header for header in headers_lower for indicator in chinese_indicators)


def map_csv_headers_to_anki_fields(headers: Sequence[str], field_list: Sequence[str]) -> dict[str, str]:
    """Map CSV/TSV headers to Anki note fields.

    Args:
        headers: Sequence of column headers from the CSV/TSV file
        field_list: Sequence of field names from the Anki note type

    Returns:
        Dictionary mapping Anki field names to CSV/TSV column names
    """
    field_mapping: dict[str, str] = {}

    # Create a case-insensitive mapping of Anki fields
    anki_fields_lower = {field.lower(): field for field in field_list}

    # Map each header to a field if they match exactly (case-insensitive)
    for header in headers:
        header_lower = header.lower()
        if header_lower in anki_fields_lower:
            field_mapping[anki_fields_lower[header_lower]] = header

    # For fields that didn't get an exact match, try using synonyms
    for concept, synonyms in FIELD_SYNONYMS.items():
        # Skip if we already have a mapping for this concept
        if concept == "hanzi" and any(find_matching_field(field, "hanzi") for field in field_mapping):
            continue
        if concept == "pinyin" and any(find_matching_field(field, "pinyin") for field in field_mapping):
            continue
        if concept == "english" and any(find_matching_field(field, "english") for field in field_mapping):
            continue

        # Try to find a match using synonyms
        for header in headers:
            header_lower = header.lower()
            if any(synonym in header_lower for synonym in synonyms):
                # Find Anki field that matches this concept
                for field in field_list:
                    if field not in field_mapping and find_matching_field(field, concept):
                        field_mapping[field] = header
                        break

    # Check for audio/sound field
    for field in field_list:
        if "sound" in field.lower() and field not in field_mapping:
            for header in headers:
                if "sound" in header.lower() or "audio" in header.lower():
                    field_mapping[field] = header
                    break

    return field_mapping


def verify_audio_files(file_path: str, rows: list[dict[str, str]], audio_columns: list[str]) -> list[str]:
    """Verify that audio files referenced in the CSV/TSV exist.

    Args:
        file_path: Path to the CSV/TSV file
        rows: List of dictionaries representing rows from the CSV/TSV
        audio_columns: List of column names that contain audio file paths

    Returns:
        List of missing audio files
    """
    missing_files: list[str] = []
    base_dir = pathlib.Path(file_path).parent
    media_dir = base_dir / "media"

    for row_num, row in enumerate(rows, 1):
        for column in audio_columns:
            if row.get(column):
                audio_value = row[column]

                # Handle Anki-style sound field value
                if audio_value.startswith("[sound:") and audio_value.endswith("]"):
                    filename = audio_value[7:-1]  # Remove [sound: and ]
                    # Try base directory first, then media subdirectory
                    audio_path = base_dir / filename
                    if not audio_path.exists():
                        audio_path = media_dir / filename
                        if not audio_path.exists():
                            missing_files.append(
                                f"Row {row_num}, '{column}': {filename} (not found in {base_dir} or {media_dir})"
                            )
                else:
                    # Regular file path
                    audio_path = base_dir / audio_value
                    if not audio_path.exists():
                        missing_files.append(f"Row {row_num}, '{column}': {audio_value}")

    return missing_files


def find_audio_columns(headers: Sequence[str]) -> list[str]:
    """Find columns that might contain audio file paths.

    Args:
        headers: Sequence of column headers from the CSV/TSV file

    Returns:
        List of column names that likely contain audio file paths
    """
    audio_indicators = ["audio", "sound", "mp3", "wav", "ogg"]
    return [header for header in headers if any(indicator in header.lower() for indicator in audio_indicators)]


def check_environment(audio_provider: str) -> tuple[bool, str]:
    """Check if all required environment variables are set.

    Args:
        audio_provider: The audio service provider to use.

    Returns:
        A tuple of (status, message)
    """
    missing_vars: list[str] = []
    if not os.environ.get("OPENAI_API_KEY"):
        missing_vars.append("OPENAI_API_KEY")

    # Check for provider-specific environment variables
    if audio_provider.lower() == "elevenlabs" and not os.environ.get("ELEVENLABS_API_KEY"):
        missing_vars.append("ELEVENLABS_API_KEY")
    # Google Translate doesn't require any credentials

    if missing_vars:
        return False, f"Missing environment variables: {', '.join(missing_vars)}"
    return True, "All required environment variables are set"


def get_required_field(anki_client: AnkiClientProtocol, note_type: str) -> str | None:
    """Get the required field for a note type.

    Args:
        anki_client: AnkiClient instance
        note_type: The name of the note type

    Returns:
        The name of the required field, or None if not available
    """
    # First try to get the sort field, which is often the required field
    required_field = anki_client.get_model_sort_field(note_type)

    # If that fails, fall back to the first field
    if required_field is None:
        required_field = anki_client.get_first_field(note_type)

    return required_field


def filter_compatible_note_types(anki_client: AnkiClientProtocol, headers: Sequence[str]) -> list[str]:
    """Filter note types to only include those that have compatible required fields.

    Args:
        anki_client: AnkiClient instance
        headers: CSV/TSV headers

    Returns:
        List of compatible note type names
    """
    all_note_types = anki_client.get_note_types()
    headers_lower = [h.lower() for h in headers]

    compatible_note_types: list[str] = []

    for nt in all_note_types:
        # Check if there's some overlap between headers and fields
        field_names = anki_client.get_field_names(nt)
        field_names_lower = [f.lower() for f in field_names]

        if any(h in field_names_lower for h in headers_lower):
            # Get the required field
            required_field = get_required_field(anki_client, nt)

            # If required field exists, check if it can be mapped from CSV headers
            if required_field:
                # Create temporary field mapping
                field_mapping = map_csv_headers_to_anki_fields(headers, field_names)

                # Only include this note type if the required field can be mapped
                if required_field in field_mapping:
                    compatible_note_types.append(nt)
            else:
                # If we can't determine the required field, include it anyway
                compatible_note_types.append(nt)

    return compatible_note_types


def check_note_type_compatibility(
    anki_client: AnkiClientProtocol, note_type: str, headers: Sequence[str]
) -> tuple[bool, str | None]:
    """Check if a note type is compatible with the given headers.

    Args:
        anki_client: AnkiClient instance
        note_type: The note type to check
        headers: CSV/TSV headers

    Returns:
        A tuple of (is_compatible, error_message)
    """
    field_names = anki_client.get_field_names(note_type)
    required_field = get_required_field(anki_client, note_type)

    if required_field is None:
        # If we can't determine the required field, assume it's compatible
        return True, None

    # Create field mapping
    field_mapping = map_csv_headers_to_anki_fields(headers, field_names)

    # Check if required field is mapped
    if required_field not in field_mapping:
        return False, f"Required field '{required_field}' has no matching column in the input data"

    return True, None


def create_audio_config(
    audio_path: str, field_names: list[str], specific_fields: list[str] | None = None
) -> AudioConfig:
    """Create a standardized audio configuration dictionary.

    Args:
        audio_path: Path to the audio file
        field_names: List of all field names in the note type
        specific_fields: Specific fields to attach audio to.

    If specific_fields is None, will find fields with 'sound' or 'audio' in their name.

    Returns:
        AudioConfig with standardized structure
    """
    if specific_fields:
        fields = specific_fields
    else:
        fields = [field for field in field_names if "sound" in field.lower() or "audio" in field.lower()]

    return {
        "path": audio_path,
        "filename": os.path.basename(audio_path),
        "fields": fields,
    }


def display_note_types(
    note_types: list[str] | list[tuple[str, FieldMapping]], anki_client: AnkiClientProtocol, is_chinese: bool = False
) -> None:
    """Display available note types in a consistent tabular format.

    Args:
        note_types: Either a list of note type names or a list of tuples containing (note_type_name, field_mapping)
        anki_client: AnkiClient instance
        is_chinese: Whether this is for Chinese learning (affects field highlighting)
    """
    table = Table(show_header=True, header_style="bold magenta", title="Available Note Types")
    table.add_column("#", style="dim", width=3)
    table.add_column("Note Type", style="bold blue")
    table.add_column("Fields", style="green")
    table.add_column("Audio Field", style="yellow")
    table.add_column("Card Types", style="cyan")

    for i, note_type_entry in enumerate(note_types, 1):
        # Handle both string and tuple inputs
        if isinstance(note_type_entry, str):
            nt = note_type_entry
            mapping: FieldMapping = {}  # type: ignore
        else:
            nt, mapping = note_type_entry

        # Get card templates
        card_templates = anki_client.get_card_templates(nt)
        cards_str = ", ".join(card_templates)

        # Get all fields
        field_names = anki_client.get_field_names(nt)

        # Format fields based on type
        formatted_fields: list[str] = []
        for field in field_names:
            if is_chinese:
                hanzi_field: str = mapping.get("hanzi_field", "")
                pinyin_field: str = mapping.get("pinyin_field", "")
                english_field: str = mapping.get("english_field", "")

                if field == hanzi_field or "hanzi" in field.lower():
                    formatted_fields.append(f"[bold blue]{field}[/bold blue]")
                elif field == pinyin_field or "pinyin" in field.lower():
                    formatted_fields.append(f"[green]{field}[/green]")
                elif field == english_field or "english" in field.lower():
                    formatted_fields.append(f"[yellow]{field}[/yellow]")
                else:
                    formatted_fields.append(field)
            else:
                formatted_fields.append(field)

        fields_str = " • ".join(formatted_fields)

        # Find audio field from mapping or by name
        sound_field: str | None = mapping.get("sound_field")
        audio_field: str = (
            sound_field
            if sound_field
            else next((f for f in field_names if "sound" in f.lower() or "audio" in f.lower()), "[dim]N/A[/dim]")
        )

        table.add_row(
            str(i),
            nt,
            fields_str,
            audio_field,
            cards_str,
        )

    console.print(table)

    if is_chinese:
        console.print("\nField colors: [bold blue]Hanzi[/bold blue] • [green]Pinyin[/green] • [yellow]English[/yellow]")
    console.print("Fields are separated by • bullets for better readability")


def process_structured_file(
    file_path: str,
    deck_name: str,
    anki_client: AnkiClientProtocol,
    audio_provider: str,
    style: StyleType,
    note_type: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    debug: bool = False,
    tags: str | None = None,
) -> None:
    """Process a CSV or TSV file and add the rows to Anki.

    Args:
        file_path: Path to the CSV/TSV file
        deck_name: The name of the Anki deck to add the cards to
        anki_client: The AnkiClient instance
        audio_provider: The audio service provider to use
        style: The style of the translation
        note_type: Optional note type to use
        dry_run: If True, don't actually add to Anki
        verbose: If True, show more detailed output
        debug: If True, log debug information
        tags: Optional comma-separated list of tags to add to the note
    """
    # Determine file type and delimiter from extension
    file_ext = pathlib.Path(file_path).suffix.lower()
    if file_ext == ".csv":
        delimiter = ","
        file_type = "CSV"
    elif file_ext == ".tsv":
        delimiter = "\t"
        file_type = "TSV"
    else:
        raise Add2ankiError(f"Unsupported file extension: {file_ext}. Expected .csv or .tsv")

    # Read the file
    try:
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                raise Add2ankiError(f"No headers found in {file_type} file")

            headers = reader.fieldnames
            rows = list(reader)

            if not rows:
                raise Add2ankiError(f"No data rows found in {file_type} file")
    except Exception as e:
        raise Add2ankiError(f"Error reading {file_type} file: {e}") from e

    console.print(f"[bold green]Read {len(rows)} rows from {file_type} file[/bold green]")

    # Check if the table is for Chinese language learning
    is_chinese = is_chinese_learning_table(headers)

    # Verify audio files if applicable
    audio_columns = find_audio_columns(headers)
    if audio_columns:
        console.print(f"[bold blue]Found potential audio columns:[/bold blue] {', '.join(audio_columns)}")
        missing_files = verify_audio_files(file_path, rows, audio_columns)
        if missing_files:
            for missing in missing_files:
                console.print(f"[bold red]Missing audio file:[/bold red] {missing}")
            raise Add2ankiError(f"Found {len(missing_files)} missing audio files. Please fix before continuing.")

    # Load or create configuration
    config = load_config()

    # We handle note type differently based on whether it's Chinese learning
    if is_chinese:
        console.print("[bold blue]Detected Chinese language learning table[/bold blue]")

        # For Chinese learning, use the note type from command line, config, or prompt
        selected_note_type = note_type or config.note_type

        if not selected_note_type:
            # Find suitable note types for Chinese learning
            suitable_note_types = find_suitable_note_types(anki_client)

            if not suitable_note_types:
                console.print("[bold red]Error:[/bold red] No suitable note types found in Anki.")
                console.print(
                    "Please create a note type with fields for Hanzi/Chinese, Pinyin/Pronunciation, "
                    "and English/Translation."
                )
                return

            if len(suitable_note_types) == 1:
                # If there's only one suitable note type, use it
                selected_note_type, _ = suitable_note_types[0]
                console.print(f"[bold green]Using note type:[/bold green] {selected_note_type}")

                # Save only the note type in the configuration
                config.note_type = selected_note_type
                if not dry_run:
                    save_config(config)
            else:
                display_note_types(suitable_note_types, anki_client, is_chinese=True)
                selection = IntPrompt.ask(
                    "[bold blue]Select a note type[/bold blue]",
                    choices=[str(i) for i in range(1, len(suitable_note_types) + 1)],
                    default=1,
                )
                note_type_tuple = suitable_note_types[selection - 1]
                selected_note_type = note_type_tuple[0]  # Extract note type name from tuple

            # Save only the note type in the configuration
            config.note_type = selected_note_type
            if not dry_run:
                save_config(config)
    else:
        console.print("[bold blue]Non-Chinese language learning table detected[/bold blue]")

        # For non-Chinese learning, only use note type from command line or prompt
        # (don't use or save to config)
        selected_note_type: str | None = note_type

        if not selected_note_type:
            # Filter note types that are compatible with our CSV headers
            compatible_note_types = filter_compatible_note_types(anki_client, headers)

            if not compatible_note_types:
                console.print("[bold red]Error:[/bold red] No compatible note types found in Anki.")
                console.print("No note type has compatible fields that match your CSV headers.")
                console.print(f"Your CSV has these columns: {', '.join(headers)}")
                return

            if len(compatible_note_types) == 1:
                # If there's only one compatible note type, use it
                selected_note_type = compatible_note_types[0]
                console.print(f"[bold green]Using note type:[/bold green] {selected_note_type}")
            else:
                display_note_types(compatible_note_types, anki_client, is_chinese=False)
                selection = IntPrompt.ask(
                    "[bold blue]Select a note type[/bold blue]",
                    choices=[str(i) for i in range(1, len(compatible_note_types) + 1)],
                    default=1,
                )
                note_type_tuple = compatible_note_types[selection - 1]
                selected_note_type = note_type_tuple[0]

    # At this point we have a selected note type
    field_names = anki_client.get_field_names(selected_note_type)

    # Check if this note type is compatible with our CSV headers
    is_compatible, error_message = check_note_type_compatibility(anki_client, selected_note_type, headers)
    if not is_compatible:
        console.print(f"[bold red]Error:[/bold red] {error_message}")
        console.print(f"Your CSV has these columns: {', '.join(headers)}")
        console.print(f"Note type '{selected_note_type}' requires a field that cannot be mapped from your data.")
        console.print("Options:")
        console.print("  1. Add the missing column to your CSV")
        console.print("  2. Choose a different note type")
        console.print("  3. Rename one of your CSV columns to match the required field name")
        return

    # Map CSV/TSV headers to Anki fields
    field_mapping = map_csv_headers_to_anki_fields(headers, field_names)

    if not field_mapping:
        console.print("[bold red]Error:[/bold red] Could not map any CSV/TSV headers to Anki fields.")
        return

    # Show the field mapping
    console.print("[bold blue]Field mapping:[/bold blue]")
    field_table = Table(show_header=True, header_style="bold magenta")
    field_table.add_column("Anki Field")
    field_table.add_column("CSV/TSV Column")

    for anki_field, csv_column in field_mapping.items():
        field_table.add_row(anki_field, csv_column)

    console.print(field_table)

    # Check for any unmapped Anki fields
    unmapped_fields = [f for f in field_names if f not in field_mapping]
    if unmapped_fields:
        console.print(f"[bold yellow]Warning:[/bold yellow] Unmapped Anki fields: {', '.join(unmapped_fields)}")

    # Prepare tags
    note_tags = []
    if tags is not None:
        if tags:  # If tags is not empty string
            note_tags = [tag.strip() for tag in tags.split(",")]
    else:
        note_tags = ["add2anki"]

    # Display tags information
    if note_tags:
        console.print(f"[bold blue]Adding tags:[/bold blue] {', '.join(note_tags)}")
    else:
        console.print("[bold blue]No tags will be added[/bold blue]")

    # Process each row in the CSV/TSV
    success_count = 0
    error_count = 0

    for row_num, row in enumerate(rows, 1):
        try:
            console.print(f"\n[bold blue]Processing row {row_num} of {len(rows)}[/bold blue]")

            # Prepare fields for the note from mapped columns
            fields: dict[str, str] = {}
            for anki_field, csv_column in field_mapping.items():
                if csv_column in row:
                    fields[anki_field] = row[csv_column]

            # For Chinese learning, determine if we need to translate or generate audio
            if is_chinese:
                # Get information about which fields are for which purpose
                hanzi_field = None
                pinyin_field = None
                english_field = None
                sound_field = None

                for field in field_names:
                    if not hanzi_field and find_matching_field(field, "hanzi"):
                        hanzi_field = field
                    elif not pinyin_field and find_matching_field(field, "pinyin"):
                        pinyin_field = field
                    elif not english_field and find_matching_field(field, "english"):
                        english_field = field
                    elif not sound_field and "sound" in field.lower():
                        sound_field = field

                # Check if we need to translate
                needs_translation = True
                needs_audio = True

                # Skip translation if:
                # 1. There's no English field in the note type
                # 2. English field is already provided in the CSV row
                if not english_field or (fields.get(english_field)):
                    needs_translation = False

                # Skip audio generation if:
                # 1. There's no Sound field in the note type
                # 2. Sound field is provided in the CSV row as a file path
                # 3. There's a column with audio/sound in the name and this row has a value for it
                if (
                    not sound_field
                    or (fields.get(sound_field))
                    or (audio_columns and any(col in row and row[col] for col in audio_columns))
                ):
                    needs_audio = False

                # If we have the Hanzi but need to generate pinyin, english, or audio
                if hanzi_field and fields.get(hanzi_field):
                    hanzi_text = fields[hanzi_field]

                    # Translate if needed
                    if needs_translation:
                        # Need to implement reverse translation with TranslationService
                        console.print(f"[bold blue]Getting pronunciation and translation for:[/bold blue] {hanzi_text}")

                        # TODO: Add proper reverse translation method
                        # For now, let's just set the fields we know
                        if english_field and english_field not in fields:
                            fields[english_field] = "TRANSLATION NEEDED"  # Placeholder

                    # Generate audio if needed
                    if needs_audio and sound_field:
                        console.print(f"[bold blue]Generating audio for:[/bold blue] {hanzi_text}")
                        audio_service = create_audio_service(provider=audio_provider)
                        audio_path = audio_service.generate_audio_file(hanzi_text)

                        # Prepare audio field
                        audio_config = create_audio_config(audio_path, field_names, [sound_field])
                    else:
                        audio_config = None
                else:
                    # If we don't have Hanzi, we can't generate audio or pinyin
                    audio_config = None
                    if not hanzi_field or not fields.get(hanzi_field):
                        console.print("[bold red]Warning:[/bold red] No Chinese text found for this row")
            else:
                # For non-Chinese cards, just use the mapped fields directly
                # Check for audio fields to import
                audio_config = None
                for col in audio_columns:
                    if row.get(col):
                        audio_value = row[col]

                        # Handle Anki-style sound field value
                        if audio_value.startswith("[sound:") and audio_value.endswith("]"):
                            filename = audio_value[7:-1]  # Remove [sound: and ]
                            # Try base directory first, then media subdirectory
                            base_dir = pathlib.Path(file_path).parent
                            audio_path = base_dir / filename
                            if not audio_path.exists():
                                audio_path = base_dir / "media" / filename
                        else:
                            # Regular file path
                            audio_path = pathlib.Path(file_path).parent / audio_value

                        if audio_path.exists():
                            # Find an Anki field that might be for audio
                            sound_field = next(
                                (f for f in field_names if "sound" in f.lower() or "audio" in f.lower()), None
                            )
                            if sound_field:
                                # If it's an Anki-style sound field, preserve the [sound:...] format
                                if audio_value.startswith("[sound:") and audio_value.endswith("]"):
                                    fields[sound_field] = audio_value
                                    audio_config = None  # Don't need audio config since we're using the field directly
                                else:
                                    audio_config = create_audio_config(str(audio_path), field_names, [sound_field])
                                break

            # Show preview in dry run mode
            if dry_run:
                console.print(f"[bold yellow]DRY RUN:[/bold yellow] Would add note to deck '{deck_name}'")
                console.print(f"[bold yellow]Note type:[/bold yellow] {selected_note_type}")
                console.print(f"[bold yellow]Fields:[/bold yellow] {fields}")
                if audio_config:
                    console.print(f"[bold yellow]Audio:[/bold yellow] {audio_config['filename']}")
                if note_tags:
                    console.print(f"[bold yellow]Tags:[/bold yellow] {', '.join(note_tags)}")
                else:
                    console.print("[bold yellow]Tags:[/bold yellow] none")
                continue

            # Add the note to Anki
            try:
                # Prepare audio configuration
                audio_config = None
                # Use sound_field or audio_column information that has been gathered earlier in the function
                # Don't try to directly access audio_path without knowing its availability

                note_id = anki_client.add_note(
                    deck_name=deck_name,
                    note_type=selected_note_type,
                    fields=fields,
                    audio=cast(dict[str, str | list[str]], audio_config),
                    tags=tags.split(",") if tags else ["add2anki"],
                )
                console.print(f"[bold green]✓ Added note with ID:[/bold green] {note_id}")
                success_count += 1
            except Exception as e:
                console.print(f"[bold red]Error adding note:[/bold red] {e}")
                error_count += 1

        except Add2ankiError as e:
            console.print(f"[bold red]Error processing row {row_num}:[/bold red] {e}")
            error_count += 1

    # Update the last used deck in config
    if is_chinese:
        config.deck_name = deck_name
        if not dry_run:
            save_config(config)

    # Show summary
    if dry_run:
        console.print(f"\n[bold yellow]DRY RUN SUMMARY: Would have processed {len(rows)} rows[/bold yellow]")
    else:
        console.print(f"\n[bold green]Successfully added {success_count} notes[/bold green]")
        if error_count > 0:
            console.print(f"[bold red]Failed to add {error_count} notes[/bold red]")


def process_sentence(
    sentence: str,
    deck_name: str,
    anki_client: AnkiClientProtocol,
    audio_provider: str,
    style: StyleType,
    note_type: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    debug: bool = False,
    tags: str | None = None,
    source_lang: str | None = None,
    target_lang: str | None = None,
    state: Any | None = None,
    launch_anki: bool = True,
) -> None:
    """Process a single sentence and add it to Anki.

    Args:
        sentence: The sentence to process.
        deck_name: Name of the Anki deck to add the card to.
        anki_client: AnkiClient instance.
        audio_provider: Audio service provider to use.
        style: Style of the translation.
        note_type: Note type to use. If None, will try to find a suitable one.
        dry_run: If True, don't add the card to Anki.
        verbose: If True, show more detailed output.
        debug: If True, enable debug logging.
        tags: Comma-separated list of tags to add to the note.
        source_lang: Optional source language code. If None, will detect automatically.
        target_lang: Optional target language code. If None, will be determined automatically.
        state: Optional language state for REPL mode context.
        launch_anki: If True, attempt to launch Anki if not running. Default: True.
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Create services
    translation_service = TranslationService()
    audio_service = create_audio_service(audio_provider)

    # Launch Anki if needed
    if launch_anki:
        anki_client.launch_anki()

    # Determine target language - don't hardcode to Chinese
    target_lang = get_target_language(source_lang, target_lang)
    if verbose:
        console.print(f"[blue]Target language: {target_lang}[/blue]")

    # Get note type
    selected_note_type: str
    if note_type:
        selected_note_type = note_type
    else:
        note_types = find_suitable_note_types(anki_client)
        if not note_types:
            raise Add2ankiError("No suitable note types found")
        if len(note_types) == 1:
            note_type_tuple = note_types[0]
            selected_note_type = note_type_tuple[0]  # Extract note type name from tuple
            console.print(f"[bold green]Using note type:[/bold green] {selected_note_type}")
        else:
            display_note_types(note_types, anki_client, is_chinese=True)
            selection = IntPrompt.ask(
                "[bold blue]Select a note type[/bold blue]",
                choices=[str(i) for i in range(1, len(note_types) + 1)],
                default=1,
            )
            note_type_tuple = note_types[selection - 1]
            selected_note_type = note_type_tuple[0]  # Extract note type name from tuple

    # Get field names
    field_names = anki_client.get_field_names(selected_note_type)

    # Create language state for REPL mode if not provided
    if state is None:
        state = LanguageState()

    def on_translation(sentence: str, hanzi: str, pinyin: str) -> None:
        """Callback for translation results."""
        # Determine the source language (the language of 'sentence')
        detected = None
        try:
            languages = contextual_detect([sentence])
            if languages and languages[0]:
                detected = Language(languages[0])
                if verbose:
                    console.print(f"\n[blue]Detected language: {detected}[/blue]")
        except Exception:
            if verbose:
                console.print("\n[yellow]Could not detect language of the original text[/yellow]")

        if verbose:
            console.print(f"Original: {sentence}")
            console.print(f"Translation: {hanzi}")
            console.print(f"Pinyin: {pinyin}")

        # Generate audio for the target language text
        audio_path = None
        if audio_provider != "none":
            try:
                audio_path = audio_service.generate_audio_file(hanzi)
                if verbose:
                    console.print(f"[blue]Generated audio file: {audio_path}[/blue]")
            except Exception as e:
                console.print(f"[bold red]Error generating audio:[/bold red] {e}")

        # Create note fields - more intelligently map fields based on detected languages
        fields: dict[str, str] = {}

        # Map fields based on detected languages
        for field in field_names:
            # Field for the text in target language (typically Chinese/hanzi)
            if (
                find_matching_field(field, "hanzi")
                or find_matching_field(field, target_lang)
                or find_matching_field(field, "Chinese")
            ):
                fields[field] = hanzi
            # Field for pronunciation (typically pinyin)
            elif (
                find_matching_field(field, "pinyin")
                or find_matching_field(field, "pronunciation")
                or find_matching_field(field, "Pronunciation")
            ):
                fields[field] = pinyin
            # Field for text in source language (typically English)
            elif (
                find_matching_field(field, "english")
                or find_matching_field(field, "translation")
                or (detected and find_matching_field(field, detected))
                or find_matching_field(field, "Translation")
            ):
                fields[field] = sentence

        # Add note to Anki
        try:
            # Prepare audio configuration
            audio_config = None
            if audio_path:
                audio_config = create_audio_config(audio_path, field_names)

            # Prepare tags
            note_tags = []
            if tags is not None:  # If tags parameter was provided
                if tags.strip():  # Non-empty string
                    note_tags = [tag.strip() for tag in tags.split(",")]
                # Otherwise leave as empty list for empty string
            else:  # If tags parameter was not provided (None)
                note_tags = ["add2anki"]

            note_id = anki_client.add_note(
                deck_name=deck_name,
                note_type=selected_note_type,
                fields=fields,
                audio=cast(dict[str, str | list[str]], audio_config),
                tags=note_tags,
            )
            console.print(f"[bold green]✓ Added note with ID:[/bold green] {note_id}")
        except Exception as e:
            console.print(f"[bold red]Error adding note:[/bold red] {e}")
            if verbose:
                console.print(f"[dim]Fields: {fields}[/dim]")
            raise

    try:
        # Use source_lang if provided
        source_lang_obj = Language(source_lang) if source_lang else None
        if verbose and source_lang:
            console.print(f"[blue]Source language: {source_lang}[/blue]")

        process_sentence_detect(
            sentence,
            Language(target_lang),
            translation_service,
            state,
            source_lang=source_lang_obj,
            on_translation=on_translation,
        )
    except LanguageDetectionError as e:
        if verbose:
            console.print(f"\n[red]Error: {e}[/red]")
        raise


def get_target_language(source_lang: str | None = None, target_lang: str | None = None) -> str:
    """Determine target language based on source language.

    Args:
        source_lang: Optional source language code.
        target_lang: Optional target language code. If provided, overrides the automatic selection.

    Returns:
        The target language code.
    """
    # If target language is explicitly provided, use it
    if target_lang:
        return target_lang

    # Default target language is Chinese if no source language specified
    if not source_lang:
        return "zh"

    # Default opposite language mappings
    language_pairs = {
        "en": "zh",  # English -> Chinese
        "zh": "en",  # Chinese -> English
        "ja": "en",  # Japanese -> English
        "es": "en",  # Spanish -> English
        "fr": "en",  # French -> English
        "de": "en",  # German -> English
    }

    return language_pairs.get(source_lang, "zh")


def process_batch(
    sentences: Sequence[str],
    deck_name: str,
    anki_client: AnkiClientProtocol,
    audio_provider: str,
    style: StyleType,
    note_type: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    debug: bool = False,
    tags: str | None = None,
    source_lang: str | None = None,
    target_lang: str | None = None,
    launch_anki: bool = True,
) -> None:
    """Process a batch of sentences and add them to Anki.

    Args:
        sentences: The sentences to process.
        deck_name: Name of the Anki deck to add the cards to.
        anki_client: AnkiClient instance.
        audio_provider: Audio service provider to use.
        style: Style of the translation.
        note_type: Note type to use. If None, will try to find a suitable one.
        dry_run: If True, don't add the cards to Anki.
        verbose: If True, show more detailed output.
        debug: If True, enable debug logging.
        tags: Comma-separated list of tags to add to the notes.
        source_lang: Optional source language code. If None, will detect automatically.
        target_lang: Optional target language code. If None, will be determined automatically.
        launch_anki: If True, attempt to launch Anki if not running. Default: True.
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Create services
    translation_service = TranslationService()
    audio_service = create_audio_service(audio_provider)

    # Launch Anki if needed
    if launch_anki:
        anki_client.launch_anki()

    # Determine target language - don't hardcode to Chinese
    target_lang = get_target_language(source_lang, target_lang)
    if verbose:
        console.print(f"[blue]Target language: {target_lang}[/blue]")

    # Get note type
    if not note_type:
        note_types = find_suitable_note_types(anki_client)
        if not note_types:
            raise Add2ankiError("No suitable note types found")
        if len(note_types) == 1:
            note_type_tuple = note_types[0]
            note_type = note_type_tuple[0]  # Extract note type name from tuple
        else:
            display_note_types(note_types, anki_client, is_chinese=True)
            selection = IntPrompt.ask(
                "[bold blue]Select a note type[/bold blue]",
                choices=[str(i) for i in range(1, len(note_types) + 1)],
                default=1,
            )
            note_type_tuple = note_types[selection - 1]
            note_type = note_type_tuple[0]  # Extract note type name from tuple

    # Get field names
    field_names = anki_client.get_field_names(note_type)

    # Track statistics for reporting
    success_count = 0
    error_count = 0
    skipped_count = 0

    def on_translation(sentence: str, hanzi: str, pinyin: str) -> None:
        """Callback for translation results."""
        nonlocal success_count

        # Determine the source language (the language of 'sentence')
        detected = None
        # Use contextual detection
        detected_langs = contextual_detect([sentence])
        detected = detected_langs[0] if detected_langs and detected_langs[0] else None
        if verbose and detected:
            console.print(f"\n[blue]Detected language: {detected}[/blue]")
        elif verbose:
            console.print("\n[yellow]Could not detect language of the original text[/yellow]")

        if verbose:
            console.print(f"Original: {sentence}")
            console.print(f"Translation: {hanzi}")
            console.print(f"Pinyin: {pinyin}")

        # Generate audio
        audio_path = audio_service.generate_audio_file(hanzi)
        audio_url = f"[sound:{os.path.basename(audio_path)}]"

        # Create note fields - more intelligently map fields based on detected languages
        fields: dict[str, str] = {}

        # Map fields based on detected languages
        for field in field_names:
            # Field for the text in target language (typically Chinese/hanzi)
            if find_matching_field(field, "hanzi") or find_matching_field(field, target_lang):
                fields[field] = hanzi
            # Field for pronunciation (typically pinyin)
            elif find_matching_field(field, "pinyin") or find_matching_field(field, "pronunciation"):
                fields[field] = pinyin
            # Field for text in source language (typically English)
            elif find_matching_field(field, "english") or (detected and find_matching_field(field, detected)):
                fields[field] = sentence
            # Sound/audio field
            elif "sound" in field.lower() or "audio" in field.lower():
                fields[field] = audio_url

        # Add note to Anki
        if not dry_run:
            try:
                note_id = anki_client.add_note(
                    deck_name=deck_name,
                    note_type=note_type,
                    fields=fields,
                    audio={
                        "path": str(audio_path),
                        "filename": os.path.basename(audio_path),
                        "fields": [
                            field for field in field_names if "sound" in field.lower() or "audio" in field.lower()
                        ],
                    },
                    tags=tags.split(",") if tags else ["add2anki"],
                )
                console.print(f"[bold green]✓ Added note with ID:[/bold green] {note_id}")
                success_count += 1
            except Exception as e:
                nonlocal error_count
                console.print(f"[bold red]Error adding note:[/bold red] {e}")
                if verbose:
                    console.print(f"[dim]Fields: {fields}[/dim]")
                error_count += 1

    try:
        # Pre-analyze sentences for debugging/reporting
        if verbose:
            console.print("\n[bold blue]Analyzing input sentences...[/bold blue]")
            language_stats: dict[str, int] = {}
            ambiguous_count = 0

            # Use batch detection for better context
            detected_langs = contextual_detect(sentences)

            for idx, (sentence, lang) in enumerate(zip(sentences, detected_langs, strict=False), 1):
                if not lang:
                    console.print(f"[yellow]Sentence {idx}: Could not detect language[/yellow]")
                    continue

                # Update language statistics
                if lang in language_stats:
                    language_stats[lang] += 1
                else:
                    language_stats[lang] = 1

                # Count potentially ambiguous detections based on length
                if len(sentence) < 6:
                    ambiguous_count += 1
                    console.print(
                        f"[yellow]Sentence {idx}: Potentially ambiguous detection - "
                        f"short text detected as {lang}[/yellow]"
                    )

            # Report statistics
            console.print("\n[bold blue]Language statistics:[/bold blue]")
            for lang, count in language_stats.items():
                console.print(f"- {lang}: {count} sentences ({count / len(sentences) * 100:.1f}%)")

            if ambiguous_count:
                console.print(
                    f"[yellow]Warning: {ambiguous_count} sentences "
                    f"({ambiguous_count / len(sentences) * 100:.1f}%) have ambiguous language detection.[/yellow]"
                )

        # Process the batch
        console.print(f"\n[bold blue]Processing {len(sentences)} sentences...[/bold blue]")
        process_batch_detect(
            sentences,
            Language(target_lang),
            translation_service,
            source_lang=Language(source_lang) if source_lang else None,
            on_translation=on_translation,
        )

        # Report results
        if not dry_run:
            console.print(
                f"\n[bold green]Successfully processed {success_count} out of {len(sentences)} sentences[/bold green]"
            )
            if error_count > 0:
                console.print(f"[bold red]{error_count} sentences failed to be added[/bold red]")
            if skipped_count > 0:
                console.print(
                    f"[bold yellow]{skipped_count} sentences were skipped due to ambiguous detection[/bold yellow]"
                )

    except LanguageDetectionError as e:
        if verbose:
            console.print(f"\n[red]Error: {e}[/red]")
        raise


def process_srt_file(
    file_path: str,
    deck_name: str,
    anki_client: AnkiClientProtocol,
    audio_provider: str,
    style: StyleType,
    note_type: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    debug: bool = False,
    tags: str | None = None,
) -> None:
    """Process an SRT subtitle file and add the entries to Anki.

    Args:
        file_path: Path to the SRT file
        deck_name: The name of the Anki deck to add the cards to
        anki_client: The AnkiClient instance
        audio_provider: The audio service provider to use
        style: The style of the translation
        note_type: Optional note type to use
        dry_run: If True, don't actually add to Anki
        verbose: If True, show more detailed output
        debug: If True, log debug information
        tags: Optional comma-separated list of tags to add to the note
    """
    # Parse the SRT file
    console.print(f"[bold blue]Parsing SRT file:[/bold blue] {file_path}")

    try:
        # Parse and filter entries
        entries = list(filter_srt_entries(parse_srt_file(file_path)))

        if not entries:
            raise Add2ankiError("No valid subtitles found in the SRT file")

        console.print(f"[bold green]Found {len(entries)} valid subtitles[/bold green]")

        # Check if the entries contain Mandarin
        sample_entries = entries[: min(5, len(entries))]
        mandarin_count = sum(1 for entry in sample_entries if is_mandarin(entry.text))

        if mandarin_count / len(sample_entries) < 0.5:
            raise Add2ankiError("The SRT file does not appear to contain Mandarin Chinese subtitles")

        # Create translation service for translating Mandarin to English
        translation_service = TranslationService()

        # Get audio service
        audio_service = create_audio_service(provider=audio_provider)

        # Load or create configuration
        config = load_config()

        # Initialize selected_note_type
        selected_note_type: str
        if note_type:
            selected_note_type = note_type
        else:
            # If note_type is not provided, use the one from config or find suitable ones
            if config.note_type:
                selected_note_type = config.note_type
            else:
                suitable_note_types = find_suitable_note_types(anki_client)

                if not suitable_note_types:
                    console.print("[bold red]Error:[/bold red] No suitable note types found in Anki.")
                    console.print(
                        "Please create a note type with fields for Hanzi/Chinese, Pinyin/Pronunciation, "
                        "and English/Translation."
                    )
                    raise Add2ankiError("No suitable note types found")

                if len(suitable_note_types) == 1:
                    # If there's only one suitable note type, use it
                    selected_note_type = suitable_note_types[0][0]
                    console.print(f"[bold green]Using note type:[/bold green] {selected_note_type}")

                    # Save only the note type in the configuration
                    config.note_type = selected_note_type
                    if not dry_run:
                        save_config(config)
                else:
                    display_note_types(suitable_note_types, anki_client, is_chinese=True)
                    selection = IntPrompt.ask(
                        "[bold blue]Select a note type[/bold blue]",
                        choices=[str(i) for i in range(1, len(suitable_note_types) + 1)],
                        default=1,
                    )
                    note_type_tuple = suitable_note_types[selection - 1]
                    selected_note_type = note_type_tuple[0]  # Extract note type name from tuple

                    # Save only the note type in the configuration
                    config.note_type = selected_note_type
                    if not dry_run:
                        save_config(config)

        # Get field mappings for the selected note type
        field_names = anki_client.get_field_names(selected_note_type)

        # Update the last used deck in config
        config.deck_name = deck_name
        if not dry_run:
            save_config(config)

        # Process tags
        note_tags = []
        if tags is not None:
            if tags:  # If tags is not empty string
                note_tags = [tag.strip() for tag in tags.split(",")]
        else:
            note_tags = ["add2anki", "srt"]

        # Display tags information
        if note_tags:
            console.print(f"[bold blue]Adding tags:[/bold blue] {', '.join(note_tags)}")
        else:
            console.print("[bold blue]No tags will be added[/bold blue]")

        # Process each subtitle entry
        success_count = 0
        error_count = 0
        skip_count = 0

        for i, entry in enumerate(entries, 1):
            try:
                console.print(f"\n[bold blue]Processing subtitle {i} of {len(entries)}[/bold blue]")

                if verbose:
                    console.print(f"[blue]Time: {entry.start_time} → {entry.end_time}[/blue]")

                console.print(f"[bold]Original (Mandarin):[/bold] {entry.text}")

                # Create reverse translation (Mandarin to English)
                try:
                    # Re-purpose translation service by swapping input/output
                    # We'll send Mandarin text and instruct to translate to English
                    response = translation_service.client.chat.completions.create(
                        model=translation_service.model,
                        response_format={"type": "json_object"},
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful assistant that translates Mandarin Chinese to English. "
                                "Provide the translation with the original Chinese (hanzi), pinyin romanization, "
                                "and the English translation. "
                                "Respond with a JSON object with fields 'hanzi', 'pinyin', and 'english'.",
                            },
                            {
                                "role": "user",
                                "content": f"Translate the following Mandarin Chinese text to English: {entry.text}",
                            },
                        ],
                    )

                    # Parse the response content as JSON
                    import json

                    content = response.choices[0].message.content
                    if not content:
                        raise Add2ankiError("Empty response from OpenAI API")

                    data = json.loads(content)

                    # Extract fields
                    hanzi = data.get("hanzi", entry.text)
                    pinyin = data.get("pinyin", "")
                    english = data.get("english", "")

                    # Generate audio for the Mandarin text
                    console.print(f"[bold blue]Generating audio for:[/bold blue] {hanzi}")
                    audio_path = audio_service.generate_audio_file(hanzi)

                    # Prepare fields for the note
                    fields: dict[str, str] = {}
                    hanzi_field = field_names[0] if field_names else "Hanzi"
                    fields[hanzi_field] = hanzi

                    pinyin_field = field_names[1] if len(field_names) > 1 else "Pinyin"
                    fields[pinyin_field] = pinyin

                    english_field = field_names[2] if len(field_names) > 2 else "English"
                    fields[english_field] = english

                    # Get field names for the selected note type
                    field_names = [hanzi_field, pinyin_field, english_field]

                    # Prepare audio field
                    sound_field = field_names[2] if len(field_names) > 2 else "Sound"
                    audio_config = create_audio_config(
                        audio_path, field_names, [sound_field] if sound_field in field_names else ["Sound"]
                    )

                    # Show preview in dry run mode
                    if dry_run:
                        console.print(f"[bold yellow]DRY RUN:[/bold yellow] Would add note to deck '{deck_name}'")
                        note_type_str = selected_note_type or "Chinese English -> Hanzi"
                        console.print(f"[bold yellow]Note type:[/bold yellow] {note_type_str}")
                        console.print(f"[bold yellow]Fields:[/bold yellow] {fields}")
                        console.print(f"[bold yellow]Audio:[/bold yellow] {audio_config['filename']}")
                        if note_tags:
                            console.print(f"[bold yellow]Tags:[/bold yellow] {', '.join(note_tags)}")
                        else:
                            console.print("[bold yellow]Tags:[/bold yellow] none")
                        success_count += 1
                        continue

                    # Add the note to Anki
                    note_id = anki_client.add_note(
                        deck_name=deck_name,
                        note_type=selected_note_type or "Chinese English -> Hanzi",
                        fields=fields,
                        audio={
                            "path": str(audio_path),
                            "filename": os.path.basename(audio_path),
                            "fields": [
                                field for field in field_names if "sound" in field.lower() or "audio" in field.lower()
                            ],
                        },
                        tags=note_tags,
                    )

                    console.print(f"[bold green]✓ Added note with ID:[/bold green] {note_id}")
                    success_count += 1

                except Add2ankiError as e:
                    console.print(f"[bold red]Error processing subtitle {i}:[/bold red] {e}")
                    error_count += 1

            except Exception as e:
                console.print(f"[bold red]Error processing subtitle {i}:[/bold red] {e}")
                error_count += 1

        # Show summary
        if dry_run:
            console.print(
                f"\n[bold yellow]DRY RUN SUMMARY: Would have processed {len(entries)} subtitles[/bold yellow]"
            )
            console.print(f"[bold yellow]Would have added {success_count} notes[/bold yellow]")
            if skip_count > 0:
                console.print(f"[bold yellow]Would have skipped {skip_count} subtitles[/bold yellow]")
            if error_count > 0:
                console.print(f"[bold yellow]Would have encountered {error_count} errors[/bold yellow]")
        else:
            console.print(f"\n[bold green]Successfully added {success_count} notes[/bold green]")
            if skip_count > 0:
                console.print(f"[bold blue]Skipped {skip_count} subtitles[/bold blue]")
            if error_count > 0:
                console.print(f"[bold red]Failed to add {error_count} notes[/bold red]")

    except Add2ankiError as e:
        console.print(f"[bold red]Error processing SRT file:[/bold red] {e}")
        raise


@click.command()
@click.argument("sentences", nargs=-1)
@click.option(
    "--deck",
    "-d",
    default=None,
    help="Name of the Anki deck to add cards to. If not specified, will use saved deck or prompt for selection.",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help="File containing data to add (text file, .csv/.tsv with headers, or .srt subtitle file)",
)
@click.option(
    "--host",
    default="localhost",
    help="Host where AnkiConnect is running. Default: localhost",
)
@click.option(
    "--port",
    default=8765,
    help="Port where AnkiConnect is running. Default: 8765",
)
@click.option(
    "--audio-provider",
    "-a",
    type=click.Choice(["google-translate", "elevenlabs"], case_sensitive=False),
    default="google-translate",
    help="Audio generation service to use. Default: google-translate",
)
@click.option(
    "--style",
    "-s",
    type=click.Choice(["written", "formal", "conversational"], case_sensitive=False),
    default="conversational",
    help="Style of the translation. Default: conversational",
)
@click.option(
    "--note-type",
    "-n",
    help="Note type to use. If not specified, will try to find a suitable one.",
)
@click.option(
    "--tags",
    "-t",
    help="Comma-separated list of tags to add to the note. Default: 'add2anki'. Use empty string for no tags.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Process sentences but don't add them to Anki",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show more detailed output",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging for troubleshooting",
)
@click.option(
    "--launch-anki/--no-launch-anki",
    default=True,
    help="Launch Anki if it's not running. Default: True",
)
@click.option(
    "--source-lang",
    "-l",
    type=click.Choice(["en", "zh", "ja", "es", "fr", "de"], case_sensitive=False),
    help="Source language code. If not specified, will detect automatically.",
)
@click.option(
    "--target-lang",
    "-t",
    type=click.Choice(["en", "zh", "ja", "fr", "de"], case_sensitive=False),
    help="Target language code. If not specified, will be determined based on source language.",
)
def main(
    sentences: tuple[str, ...],
    deck: str | None,
    file: str | None,
    host: str,
    port: int,
    audio_provider: str,
    style: str,
    note_type: str | None,
    tags: str | None,
    dry_run: bool,
    verbose: bool,
    debug: bool,
    launch_anki: bool,
    source_lang: str | None,
    target_lang: str | None,
) -> None:
    """Add language learning cards to Anki.

    SENTENCES are the sentences to add. If not provided, will read from FILE.
    If a SENTENCE appears to be a file path and exists, it will be processed as a file.
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Check environment
    status, message = check_environment(audio_provider)
    if not status:
        console.print(f"[red]Error: {message}[/red]")
        return

    # Create Anki client
    anki_client = AnkiClient(host=host, port=port)
    if launch_anki:
        anki_client.launch_anki()

    # Get deck name
    if not deck:
        config = load_config()
        if not config.deck_name:
            decks = anki_client.get_deck_names()
            if not decks:
                console.print("[red]Error: No decks found in Anki[/red]")
                return
            if len(decks) == 1:
                deck = decks[0]
            else:
                console.print("\nAvailable decks:")
                for i, d in enumerate(decks, 1):
                    console.print(f"{i}. {d}")
                deck = decks[IntPrompt.ask("Select deck", choices=[str(i) for i in range(1, len(decks) + 1)]) - 1]
            config.deck_name = deck
            save_config(config)
        else:
            deck = config.deck_name

    # Cast style to StyleType
    style_type = cast(StyleType, style)

    # Check if a single sentence argument is actually a file path
    if len(sentences) == 1 and os.path.exists(sentences[0]) and not file:
        file = sentences[0]
        sentences = ()

    # Process sentences
    if sentences:
        try:
            # Show source and target languages in verbose mode
            if verbose:
                if source_lang:
                    console.print(f"[blue]Source language: {source_lang}[/blue]")
                if target_lang:
                    console.print(f"[blue]Target language: {target_lang}[/blue]")

            if len(sentences) == 1:
                process_sentence(
                    sentences[0],
                    deck,
                    anki_client,
                    audio_provider,
                    style_type,
                    note_type,
                    dry_run,
                    verbose,
                    debug,
                    tags,
                    source_lang,
                    target_lang,
                )
            else:
                # Join multiple arguments into a single sentence if they're meant to be processed together
                combined_sentence = " ".join(sentences)
                process_sentence(
                    combined_sentence,
                    deck,
                    anki_client,
                    audio_provider,
                    style_type,
                    note_type,
                    dry_run,
                    verbose,
                    debug,
                    tags,
                    source_lang,
                    target_lang,
                )
        except LanguageDetectionError as e:
            console.print(f"[bold red]Language detection error:[/bold red] {e}")
            console.print("[yellow]Language detection is ambiguous[/yellow]")

            # Provide recovery suggestions
            if not source_lang:
                console.print("\n[bold yellow]Suggestions:[/bold yellow]")
                console.print("1. Specify the source language with --source-lang")
                console.print("2. For ambiguous text, try providing a longer sample")
                console.print("3. For batch processing, ensure the file contains some unambiguous sentences")

                # If in interactive mode, offer to retry with source language
                if not file:
                    retry = click.confirm("Would you like to try again with an explicit source language?")
                    if retry:
                        detected_lang = e.args[0].split("'")[1] if "'" in e.args[0] else None
                        if detected_lang:
                            console.print(f"[bold blue]Detected language: {detected_lang}[/bold blue]")

                        langs = ["en", "zh", "ja", "es", "fr", "de"]  # Common languages
                        if detected_lang and detected_lang in langs:
                            langs.remove(detected_lang)

                        source_lang = click.prompt(
                            "Enter source language code", type=click.Choice(langs), default=langs[0]
                        )

                        # Retry with explicit source language
                        if len(sentences) == 1:
                            process_sentence(
                                sentences[0],
                                deck,
                                anki_client,
                                audio_provider,
                                style_type,
                                note_type,
                                dry_run,
                                verbose,
                                debug,
                                tags,
                                source_lang,
                                target_lang,
                            )
                        else:
                            combined_sentence = " ".join(sentences)
                            process_sentence(
                                combined_sentence,
                                deck,
                                anki_client,
                                audio_provider,
                                style_type,
                                note_type,
                                dry_run,
                                verbose,
                                debug,
                                tags,
                                source_lang,
                                target_lang,
                            )
            return
    elif file:
        # Check file extension
        if file.endswith(".srt"):
            process_srt_file(
                file,
                deck,
                anki_client,
                audio_provider,
                style_type,
                note_type,
                dry_run,
                verbose,
                debug,
                tags,
            )
        elif file.endswith(".csv") or file.endswith(".tsv"):
            process_structured_file(
                file,
                deck,
                anki_client,
                audio_provider,
                style_type,
                note_type,
                dry_run,
                verbose,
                debug,
                tags,
            )
        else:
            # Handle text files with one sentence per line
            try:
                with open(file, encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]

                # Skip header if present
                if lines and lines[0].lower() == "text":
                    lines = lines[1:]

                if not lines:
                    console.print("[yellow]Warning: No sentences found in the file[/yellow]")
                    return

                for line in lines:
                    process_sentence(
                        line,
                        deck,
                        anki_client,
                        audio_provider,
                        style_type,
                        note_type,
                        dry_run,
                        verbose,
                        debug,
                        tags,
                        source_lang,
                    )
            except Exception as e:
                raise Add2ankiError(
                    f"Unsupported file extension: {os.path.splitext(file)[1]}. Expected .csv or .tsv"
                ) from e
    else:
        console.print("[red]Error: No sentences or file provided[/red]")
        return


if __name__ == "__main__":
    # Click will parse arguments from sys.argv
    main()

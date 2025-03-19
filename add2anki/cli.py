"""Command-line interface for add2anki."""

import csv
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from add2anki.anki_client import AnkiClient
from add2anki.audio import AudioGenerationService, create_audio_service

# Import directly from config.py to avoid circular imports
from add2anki.config import (
    FIELD_SYNONYMS,
    find_matching_field,
    find_suitable_note_types,
    load_config,
    save_config,
)
from add2anki.exceptions import add2ankiError
from add2anki.translation import StyleType, TranslationService

console = Console()


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


def map_csv_headers_to_anki_fields(headers: Sequence[str], field_list: Sequence[str]) -> Dict[str, str]:
    """Map CSV/TSV headers to Anki note fields.

    Args:
        headers: Sequence of column headers from the CSV/TSV file
        field_list: Sequence of field names from the Anki note type

    Returns:
        Dictionary mapping Anki field names to CSV/TSV column names
    """
    field_mapping: Dict[str, str] = {}

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


def verify_audio_files(file_path: str, rows: List[Dict[str, str]], audio_columns: List[str]) -> List[str]:
    """Verify that audio files referenced in the CSV/TSV exist.

    Args:
        file_path: Path to the CSV/TSV file
        rows: List of dictionaries representing rows from the CSV/TSV
        audio_columns: List of column names that contain audio file paths

    Returns:
        List of missing audio files
    """
    missing_files: List[str] = []
    base_dir = pathlib.Path(file_path).parent

    for row_num, row in enumerate(rows, 1):
        for column in audio_columns:
            if column in row and row[column]:
                audio_path = base_dir / row[column]
                if not audio_path.exists():
                    missing_files.append(f"Row {row_num}, '{column}': {row[column]}")

    return missing_files


def find_audio_columns(headers: Sequence[str]) -> List[str]:
    """Find columns that might contain audio file paths.

    Args:
        headers: Sequence of column headers from the CSV/TSV file

    Returns:
        List of column names that likely contain audio file paths
    """
    audio_indicators = ["audio", "sound", "mp3", "wav", "ogg"]
    return [header for header in headers if any(indicator in header.lower() for indicator in audio_indicators)]


def check_environment(audio_provider: str) -> Tuple[bool, str]:
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


def process_structured_file(
    file_path: str,
    deck_name: str,
    anki_client: AnkiClient,
    audio_provider: str,
    style: StyleType,
    note_type: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False,
    debug: bool = False,
    tags: Optional[str] = None,
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
        raise add2ankiError(f"Unsupported file extension: {file_ext}. Expected .csv or .tsv")

    # Read the file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                raise add2ankiError(f"No headers found in {file_type} file")

            headers = reader.fieldnames
            rows = list(reader)

            if not rows:
                raise add2ankiError(f"No data rows found in {file_type} file")
    except Exception as e:
        raise add2ankiError(f"Error reading {file_type} file: {e}")

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
            raise add2ankiError(f"Found {len(missing_files)} missing audio files. Please fix before continuing.")

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
                # If there are multiple suitable note types, ask the user to select one
                console.print("[bold blue]Multiple suitable note types found:[/bold blue]")

                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="dim")
                table.add_column("Note Type")
                table.add_column("Translation")
                table.add_column("Sound Field")
                table.add_column("Cards")

                for i, (note_type_name, mapping) in enumerate(suitable_note_types, 1):
                    # Get card templates for this note type
                    card_templates = anki_client.get_card_templates(note_type_name)
                    cards_str = ", ".join(card_templates)

                    table.add_row(
                        str(i),
                        note_type_name,
                        mapping["english_field"],
                        mapping.get("sound_field", "N/A"),
                        cards_str,
                    )

                console.print(table)

                # Ask the user to select a note type
                selection = IntPrompt.ask(
                    "[bold blue]Select a note type[/bold blue]",
                    choices=[str(i) for i in range(1, len(suitable_note_types) + 1)],
                    default=1,
                )

                # Get the selected note type
                selected_note_type, _ = suitable_note_types[selection - 1]

                # Save only the note type in the configuration
                config.note_type = selected_note_type
                if not dry_run:
                    save_config(config)
    else:
        console.print("[bold blue]Non-Chinese language learning table detected[/bold blue]")

        # For non-Chinese learning, only use note type from command line or prompt
        # (don't use or save to config)
        selected_note_type: Optional[str] = note_type

        if not selected_note_type:
            # Get all note types
            all_note_types = anki_client.get_note_types()

            # Find note types that have fields matching our CSV headers
            compatible_note_types: List[str] = []
            for nt in all_note_types:
                field_names = anki_client.get_field_names(nt)
                field_names_lower = [f.lower() for f in field_names]
                headers_lower = [h.lower() for h in headers]

                # Check if there's some overlap between headers and fields
                if any(h in field_names_lower for h in headers_lower):
                    compatible_note_types.append(nt)

            if not compatible_note_types:
                console.print("[bold red]Error:[/bold red] No compatible note types found in Anki.")
                console.print("No note type has fields that match any of the CSV headers.")
                return

            if len(compatible_note_types) == 1:
                # If there's only one compatible note type, use it
                selected_note_type = compatible_note_types[0]
                console.print(f"[bold green]Using note type:[/bold green] {selected_note_type}")
            else:
                # If there are multiple compatible note types, ask the user to select one
                console.print("[bold blue]Multiple compatible note types found:[/bold blue]")

                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="dim")
                table.add_column("Note Type")
                table.add_column("Fields")

                for i, nt_name in enumerate(compatible_note_types, 1):
                    field_names = anki_client.get_field_names(nt_name)
                    fields_str = ", ".join(field_names)

                    table.add_row(
                        str(i),
                        nt_name,
                        fields_str,
                    )

                console.print(table)

                # Ask the user to select a note type
                selection = IntPrompt.ask(
                    "[bold blue]Select a note type[/bold blue]",
                    choices=[str(i) for i in range(1, len(compatible_note_types) + 1)],
                    default=1,
                )

                # Get the selected note type
                selected_note_type = compatible_note_types[selection - 1]

    # At this point we have a selected note type
    field_names = anki_client.get_field_names(selected_note_type)

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
                if not english_field or (english_field in fields and fields[english_field]):
                    needs_translation = False

                # Skip audio generation if:
                # 1. There's no Sound field in the note type
                # 2. Sound field is provided in the CSV row as a file path
                # 3. There's a column with audio/sound in the name and this row has a value for it
                if not sound_field or (sound_field in fields and fields[sound_field]):
                    needs_audio = False
                elif audio_columns and any(col in row and row[col] for col in audio_columns):
                    needs_audio = False

                # If we have the Hanzi but need to generate pinyin, english, or audio
                if hanzi_field in fields and fields[hanzi_field]:
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
                        audio_config = {
                            "path": audio_path,
                            "filename": f"{hash(hanzi_text)}.mp3",
                            "fields": [sound_field],
                        }
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
                    if col in row and row[col]:
                        # Found an audio file to import
                        audio_path = pathlib.Path(file_path).parent / row[col]
                        if audio_path.exists():
                            # Find an Anki field that might be for audio
                            sound_field = next(
                                (f for f in field_names if "sound" in f.lower() or "audio" in f.lower()), None
                            )
                            if sound_field:
                                audio_config = {
                                    "path": str(audio_path),
                                    "filename": os.path.basename(row[col]),
                                    "fields": [sound_field],
                                }
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
                note_id = anki_client.add_note(
                    deck_name=deck_name,
                    note_type=selected_note_type,
                    fields=fields,
                    audio=audio_config,
                    tags=note_tags,
                )
                console.print(f"[bold green]✓ Added note with ID:[/bold green] {note_id}")
                success_count += 1
            except Exception as e:
                console.print(f"[bold red]Error adding note:[/bold red] {e}")
                error_count += 1

        except add2ankiError as e:
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
    anki_client: AnkiClient,
    audio_provider: str,
    style: StyleType,
    note_type: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False,
    debug: bool = False,
    tags: Optional[str] = None,
) -> None:
    """Process a single sentence and add it to Anki.

    Args:
        sentence: The sentence to process
        deck_name: The name of the Anki deck to add the card to
        anki_client: The AnkiClient instance
        audio_provider: The audio service provider to use
        style: The style of the translation (written, formal, or conversational)
        note_type: Optional note type to use
        dry_run: If True, don't actually add to Anki
        verbose: If True, show more detailed output
        debug: If True, log debug information
        tags: Optional comma-separated list of tags to add to the note
    """
    # Translate the sentence
    console.print(f"\n[bold blue]Translating:[/bold blue] {sentence}")
    if verbose:
        console.print(f"[bold blue]Using style:[/bold blue] {style}")
    translation_service = TranslationService()
    translation = translation_service.translate(sentence, style=style)

    # Generate audio
    console.print(f"[bold blue]Generating audio for:[/bold blue] {translation.hanzi}")
    audio_service: AudioGenerationService = create_audio_service(provider=audio_provider)
    audio_path = audio_service.generate_audio_file(translation.hanzi)

    # Load or create configuration
    config = load_config()

    # If note_type is provided, use it; otherwise use the one from config
    selected_note_type: Optional[str] = note_type or config.note_type

    # If we still don't have a note type, find suitable ones
    if not selected_note_type:
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
            # If there are multiple suitable note types, ask the user to select one
            console.print("[bold blue]Multiple suitable note types found:[/bold blue]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim")
            table.add_column("Note Type")
            table.add_column("Translation")
            table.add_column("Sound Field")
            table.add_column("Cards")

            for i, (note_type_name, mapping) in enumerate(suitable_note_types, 1):
                # Get card templates for this note type
                card_templates = anki_client.get_card_templates(note_type_name)
                cards_str = ", ".join(card_templates)

                table.add_row(
                    str(i),
                    note_type_name,
                    mapping["english_field"],
                    mapping.get("sound_field", "N/A"),
                    cards_str,
                )

            console.print(table)

            # Ask the user to select a note type
            selection = IntPrompt.ask(
                "[bold blue]Select a note type[/bold blue]",
                choices=[str(i) for i in range(1, len(suitable_note_types) + 1)],
                default=1,
            )

            # Get the selected note type
            selected_note_type, _ = suitable_note_types[selection - 1]

            # Save only the note type in the configuration
            config.note_type = selected_note_type
            if not dry_run:
                save_config(config)

    # Get field mappings for the selected note type
    field_mapping = {}
    if selected_note_type:
        field_names = anki_client.get_field_names(selected_note_type)

        # Find matching fields
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

        field_mapping = {
            "hanzi_field": hanzi_field,
            "pinyin_field": pinyin_field,
            "english_field": english_field,
            "sound_field": sound_field,
        }

    # Prepare fields for the note
    fields: dict[str, str] = {}
    hanzi_field = field_mapping.get("hanzi_field")
    if hanzi_field is not None:
        fields[hanzi_field] = translation.hanzi
    else:
        fields["Hanzi"] = translation.hanzi

    pinyin_field = field_mapping.get("pinyin_field")
    if pinyin_field is not None:
        fields[pinyin_field] = translation.pinyin
    else:
        fields["Pinyin"] = translation.pinyin

    english_field = field_mapping.get("english_field")
    if english_field is not None:
        fields[english_field] = translation.english
    else:
        fields["English"] = translation.english

    if dry_run:
        console.print(f"[bold yellow]DRY RUN:[/bold yellow] Would add note to deck '{deck_name}'")
        console.print(f"[bold yellow]Note type:[/bold yellow] {selected_note_type or 'Chinese English -> Hanzi'}")
        console.print(f"[bold yellow]Fields:[/bold yellow] {fields}")
        # Display tags information in dry run
        if tags is None:
            console.print("[bold yellow]Tags:[/bold yellow] add2anki")
        elif tags == "":
            console.print("[bold yellow]Tags:[/bold yellow] none")
        else:
            console.print(f"[bold yellow]Tags:[/bold yellow] {tags}")
        return

    # Update the last used deck in config
    config.deck_name = deck_name
    if not dry_run:
        save_config(config)

    console.print(f"[bold blue]Adding to Anki deck:[/bold blue] {deck_name}")

    # Prepare audio field
    sound_field = field_mapping.get("sound_field")
    audio_config: dict[str, Any] = {
        "path": audio_path,
        "filename": f"{hash(translation.hanzi)}.mp3",
        "fields": [sound_field] if sound_field is not None else ["Sound"],
    }

    # Process tags
    note_tags = []
    if tags is not None:
        if tags:  # If tags is not empty string
            note_tags = [tag.strip() for tag in tags.split(",")]
    else:
        note_tags = ["add2anki"]

    # Display tags information
    if verbose:
        if note_tags:
            console.print(f"[bold blue]Adding tags:[/bold blue] {', '.join(note_tags)}")
        else:
            console.print("[bold blue]No tags will be added[/bold blue]")

    note_id = anki_client.add_note(
        deck_name=deck_name,
        note_type=selected_note_type or "Chinese English -> Hanzi",
        fields=fields,
        audio=audio_config,
        tags=note_tags,
    )

    console.print(f"[bold green]✓ Added note with ID:[/bold green] {note_id}")


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
    help="File containing data to add (text file with one sentence per line, or .csv/.tsv with headers)",
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
def main(
    sentences: Tuple[str, ...],
    deck: Optional[str],
    file: Optional[str],
    host: str,
    port: int,
    audio_provider: str,
    style: str,
    note_type: Optional[str],
    tags: Optional[str],
    dry_run: bool,
    verbose: bool,
    debug: bool,
) -> None:
    """Add language learning cards to Anki.

    If SENTENCES are provided, they will be processed and added to Anki.
    If no SENTENCES are provided and --file is not specified, the program will enter interactive mode.

    Examples:
        add2anki "Hello, how are you?"
        add2anki --deck "Chinese" "Hello, how are you?"

        # Process a text file (one sentence per line)
        add2anki --file sentences.txt

        # Process a CSV or TSV file (with headers)
        add2anki --file vocabulary.csv
        add2anki --file vocabulary.tsv --deck "Chinese" --tags "csv,imported"

        add2anki --style formal "Hello, how are you?"
        add2anki --note-type "Basic" "Hello, how are you?"
        add2anki --tags "chinese,beginner" "Hello, how are you?"
        add2anki --tags "" "Hello, how are you?"  # No tags
        add2anki --audio-provider elevenlabs "Hello, how are you?"
        add2anki --audio-provider google-cloud "Hello, how are you?"
        add2anki --dry-run "Hello, how are you?"
        add2anki --verbose "Hello, how are you?"
        add2anki --debug "Hello, how are you?"
        add2anki  # Interactive mode
    """
    # Configure logging if debug is enabled
    if debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console.print("[bold blue]Debug logging enabled[/bold blue]")

    # Validate and cast style to StyleType
    style_type = cast(StyleType, style)

    # Check environment variables
    env_status, env_msg = check_environment(audio_provider)
    if not env_status:
        console.print(f"[bold red]Error:[/bold red] {env_msg}")
        raise click.Abort(env_msg)

    # Check Anki connection
    anki_client = AnkiClient(host=host, port=port)
    anki_status, anki_msg = anki_client.check_connection()
    if not anki_status:
        console.print(f"[bold red]Error:[/bold red] {anki_msg}")
        raise click.Abort(anki_msg)

    console.print(f"[bold green]✓ {anki_msg}[/bold green]")
    if verbose:
        console.print(f"[bold green]✓ {env_msg}[/bold green]")
        console.print(f"[bold green]✓ Using audio provider:[/bold green] {audio_provider}")
        console.print(f"[bold green]✓ Using translation style:[/bold green] {style}")
        if tags is not None:
            if tags:
                console.print(f"[bold green]✓ Using tags:[/bold green] {tags}")
            else:
                console.print("[bold green]✓ No tags will be added[/bold green]")
        else:
            console.print("[bold green]✓ Using default tag:[/bold green] add2anki")

    if dry_run:
        console.print("[bold yellow]Running in dry-run mode (no changes will be made to Anki)[/bold yellow]")

    # Load configuration
    config = load_config()

    # Use deck from command line, or from config, or select from available decks
    deck_name = deck or config.deck_name

    # If no deck is specified, show available decks and let user choose
    if not deck_name:
        available_decks = anki_client.get_deck_names()

        if not available_decks:
            console.print("[bold red]Error:[/bold red] No decks found in Anki. Please create a deck first.")
            raise click.Abort()

        if len(available_decks) == 1:
            # If there's only one deck, use it
            deck_name = available_decks[0]
            console.print(f"[bold green]Using deck:[/bold green] {deck_name}")

            # Save the deck name in the configuration
            config.deck_name = deck_name
            if not dry_run:
                save_config(config)
        else:
            # If there are multiple decks, ask the user to select one
            console.print("[bold blue]Available decks:[/bold blue]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim")
            table.add_column("Deck Name")

            for i, name in enumerate(available_decks, 1):
                table.add_row(str(i), name)

            console.print(table)

            # Ask the user to select a deck
            selection = IntPrompt.ask(
                "[bold blue]Select a deck[/bold blue]",
                choices=[str(i) for i in range(1, len(available_decks) + 1)],
                default=1,
            )

            # Get the selected deck
            deck_name = available_decks[selection - 1]

            # Save the deck name in the configuration
            config.deck_name = deck_name
            if not dry_run:
                save_config(config)

    # Ensure deck_name is not None at this point
    assert deck_name is not None, "Deck name should be set by now"

    # Process sentences from file if provided
    if file is not None:
        file_path = pathlib.Path(file)
        file_ext = file_path.suffix.lower()

        # Check if it's a CSV or TSV file
        if file_ext in [".csv", ".tsv"]:
            try:
                process_structured_file(
                    file,
                    deck_name,
                    anki_client,
                    audio_provider,
                    style_type,
                    note_type,
                    dry_run,
                    verbose,
                    debug,
                    tags,
                )
            except add2ankiError as e:
                console.print(f"[bold red]Error processing file:[/bold red] {e}")
        else:
            # Traditional text file processing (one sentence per line)
            with open(file, "r", encoding="utf-8") as f:
                file_sentences = [line.strip() for line in f if line.strip()]
                for sentence in file_sentences:
                    try:
                        process_sentence(
                            sentence,
                            deck_name,
                            anki_client,
                            audio_provider,
                            style_type,
                            note_type,
                            dry_run,
                            verbose,
                            debug,
                            tags,
                        )
                    except add2ankiError as e:
                        console.print(f"[bold red]Error processing '{sentence}':[/bold red] {e}")
        return

    # Process sentences from command line arguments
    if sentences:
        # If there's only one sentence with no spaces, it might be a concatenated string
        # This is to handle the case where the shell splits the arguments
        if len(sentences) > 1 and all(" " not in s for s in sentences):
            joined_sentence = " ".join(sentences)
            try:
                process_sentence(
                    joined_sentence,
                    deck_name,
                    anki_client,
                    audio_provider,
                    style_type,
                    note_type,
                    dry_run,
                    verbose,
                    debug,
                    tags,
                )
            except add2ankiError as e:
                console.print(f"[bold red]Error processing '{joined_sentence}':[/bold red] {e}")
        else:
            for sentence in sentences:
                try:
                    process_sentence(
                        sentence,
                        deck_name,
                        anki_client,
                        audio_provider,
                        style_type,
                        note_type,
                        dry_run,
                        verbose,
                        debug,
                        tags,
                    )
                except add2ankiError as e:
                    console.print(f"[bold red]Error processing '{sentence}':[/bold red] {e}")
        return

    # Interactive mode
    console.print(
        Panel(
            "[bold]Welcome to add2anki![/bold]\n\n"
            "Enter English sentences to add to your Anki deck.\n"
            "Press Ctrl+C or type 'exit' to quit.",
            title="Interactive Mode",
            border_style="blue",
        )
    )

    if dry_run:
        console.print("[bold yellow]Running in dry-run mode (no changes will be made to Anki)[/bold yellow]")

    while True:
        try:
            sentence = Prompt.ask("\n[bold blue]Enter an English sentence[/bold blue]")
            if sentence.lower() in ("exit", "quit"):
                break
            if sentence.strip():
                try:
                    process_sentence(
                        sentence,
                        deck_name,
                        anki_client,
                        audio_provider,
                        style_type,
                        note_type,
                        dry_run,
                        verbose,
                        debug,
                        tags,
                    )
                except add2ankiError as e:
                    console.print(f"[bold red]Error:[/bold red] {e}")
        except KeyboardInterrupt:
            console.print("\n[bold blue]Exiting...[/bold blue]")
            break


if __name__ == "__main__":
    # Click will parse arguments from sys.argv
    main()

"""Command-line interface for add2anki."""

import logging
import os
from typing import Any, Optional, Tuple, cast

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from add2anki.anki_client import AnkiClient
from add2anki.audio import AudioGenerationService, create_audio_service

# Import directly from config.py to avoid circular imports
from add2anki.config import (
    find_matching_field,
    find_suitable_note_types,
    load_config,
    save_config,
)
from add2anki.exceptions import add2ankiError
from add2anki.translation import StyleType, TranslationService

console = Console()


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
    elif audio_provider.lower() == "google-cloud" and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        missing_vars.append("GOOGLE_APPLICATION_CREDENTIALS")
    # Google Translate doesn't require any credentials

    if missing_vars:
        return False, f"Missing environment variables: {', '.join(missing_vars)}"
    return True, "All required environment variables are set"


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
        field_list = anki_client.get_field_names(selected_note_type)

        # Find matching fields
        hanzi_field = None
        pinyin_field = None
        english_field = None
        sound_field = None

        for field in field_list:
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
    help="File containing sentences to add, one per line",
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
    type=click.Choice(["google-translate", "google-cloud", "elevenlabs"], case_sensitive=False),
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
        add2anki --file sentences.txt
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

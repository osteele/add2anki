"""Command-line interface for langki."""

import logging
import os
from typing import Optional, Tuple, cast

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from langki.anki_client import AnkiClient
from langki.audio import AudioGenerationService, create_audio_service
from langki.exceptions import LangkiError
from langki.translation import StyleType, TranslationService

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
    dry_run: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Process a single sentence and add it to Anki.

    Args:
        sentence: The sentence to process
        deck_name: The name of the Anki deck to add the card to
        anki_client: The AnkiClient instance
        audio_provider: The audio service provider to use
        style: The style of the translation (written, formal, or conversational)
        dry_run: If True, don't actually add to Anki
        verbose: If True, show more detailed output
        debug: If True, log debug information
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

    # Add to Anki
    note_type = "Chinese English -> Hanzi"

    # Prepare fields for the note
    fields = {
        "Hanzi": translation.hanzi,
        "Pinyin": translation.pinyin,
        "English": translation.english,
    }

    if dry_run:
        console.print(f"[bold yellow]DRY RUN:[/bold yellow] Would add note to deck '{deck_name}'")
        return

    console.print(f"[bold blue]Adding to Anki deck:[/bold blue] {deck_name}")
    note_id = anki_client.add_note(
        deck_name=deck_name,
        note_type=note_type,
        fields=fields,
        audio={
            "path": audio_path,
            "filename": f"{hash(translation.hanzi)}.mp3",
            "fields": ["Sound"],
        },
    )

    console.print(f"[bold green]✓ Added note with ID:[/bold green] {note_id}")


@click.command()
@click.argument("sentences", nargs=-1)
@click.option(
    "--deck",
    "-d",
    default="Smalltalk",
    help="Name of the Anki deck to add cards to. Default: Smalltalk",
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
    deck: str,
    file: Optional[str],
    host: str,
    port: int,
    audio_provider: str,
    style: str,
    dry_run: bool,
    verbose: bool,
    debug: bool,
) -> None:
    """Add language learning cards to Anki.

    If SENTENCES are provided, they will be processed and added to Anki.
    If no SENTENCES are provided and --file is not specified, the program will enter interactive mode.

    Examples:
        langki "Hello, how are you?"
        langki --deck "Chinese" "Hello, how are you?"
        langki --file sentences.txt
        langki --style formal "Hello, how are you?"
        langki --audio-provider elevenlabs "Hello, how are you?"
        langki --audio-provider google-cloud "Hello, how are you?"
        langki --dry-run "Hello, how are you?"
        langki --verbose "Hello, how are you?"
        langki --debug "Hello, how are you?"
        langki  # Interactive mode
    """
    # Configure logging if debug is enabled
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

    if dry_run:
        console.print("[bold yellow]Running in dry-run mode (no changes will be made to Anki)[/bold yellow]")

    # Process sentences from file if provided
    if file is not None:
        with open(file, "r", encoding="utf-8") as f:
            file_sentences = [line.strip() for line in f if line.strip()]
            for sentence in file_sentences:
                try:
                    process_sentence(sentence, deck, anki_client, audio_provider, style_type, dry_run, verbose, debug)
                except LangkiError as e:
                    console.print(f"[bold red]Error processing '{sentence}':[/bold red] {e}")
        return

    # Process sentences from command line arguments
    if sentences:
        # If there's only one sentence with no spaces, it might be a concatenated string
        # This is to handle the case where the shell splits the arguments
        if len(sentences) > 1 and all(" " not in s for s in sentences):
            joined_sentence = " ".join(sentences)
            try:
                process_sentence(joined_sentence, deck, anki_client, audio_provider, style_type, dry_run, verbose, debug)
            except LangkiError as e:
                console.print(f"[bold red]Error processing '{joined_sentence}':[/bold red] {e}")
        else:
            for sentence in sentences:
                try:
                    process_sentence(sentence, deck, anki_client, audio_provider, style_type, dry_run, verbose, debug)
                except LangkiError as e:
                    console.print(f"[bold red]Error processing '{sentence}':[/bold red] {e}")
        return

    # Interactive mode
    console.print(
        Panel(
            "[bold]Welcome to langki![/bold]\n\n"
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
                    process_sentence(sentence, deck, anki_client, audio_provider, style_type, dry_run, verbose, debug)
                except LangkiError as e:
                    console.print(f"[bold red]Error:[/bold red] {e}")
        except KeyboardInterrupt:
            console.print("\n[bold blue]Exiting...[/bold blue]")
            break


if __name__ == "__main__":
    # Click will parse arguments from sys.argv
    main()

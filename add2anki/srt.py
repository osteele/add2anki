"""SRT file parsing for add2anki."""

import pathlib
import re
from collections.abc import Iterator
from typing import NamedTuple

from add2anki.exceptions import Add2ankiError


class SrtEntry(NamedTuple):
    """Represents a subtitle entry from an SRT file."""

    # This is intentionally named to match what's in the SRT file, ignoring the tuple.index warning
    index: int  # type: ignore
    start_time: str
    end_time: str
    text: str


class SrtParsingError(Add2ankiError):
    """Exception raised when there is an error parsing an SRT file."""

    pass


def is_mandarin(text: str) -> bool:
    """Check if a text string contains Mandarin characters.

    Args:
        text: The text to check

    Returns:
        True if the text contains Mandarin characters, False otherwise
    """
    # Check for Chinese characters in the CJK Unified Ideographs block
    # This is a simplified check that will also match other CJK characters
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def strip_speaker_name(text: str) -> str:
    """Strip speaker names from the beginning of utterances.

    For example, "Oliver: 哦,对" becomes "哦,对".

    Args:
        text: The text to process

    Returns:
        The text with speaker name removed if present
    """
    # Match a name followed by a colon at the beginning of the text
    # The name should be a sequence of non-colon characters
    match = re.match(r"^([^:]+):\s*(.+)$", text)
    if match:
        # Return the part after the colon, trimmed
        return match.group(2).strip()
    return text


def parse_srt_file(file_path: str | pathlib.Path) -> Iterator[SrtEntry]:
    """Parse an SRT file and yield subtitle entries.

    Args:
        file_path: Path to the SRT file

    Yields:
        SrtEntry objects representing each subtitle in the file

    Raises:
        SrtParsingError: If there is an error parsing the file
        FileNotFoundError: If the file does not exist
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with another common encoding
        with open(file_path, encoding="latin-1") as f:
            content = f.read()

    # Split content into subtitle blocks (separated by double newlines)
    subtitle_blocks = re.split(r"\n\s*\n", content.strip())

    for block in subtitle_blocks:
        if not block.strip():
            continue

        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue  # Skip invalid blocks

        # First line is the index
        try:
            index = int(lines[0])
        except ValueError:
            continue  # Skip if index is not a number

        # Second line is the timestamp
        timestamp_match = re.match(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1])
        if not timestamp_match:
            continue  # Skip if timestamp format is invalid

        start_time, end_time = timestamp_match.groups()

        # Remaining lines are the subtitle text
        text = " ".join(lines[2:]).strip()

        yield SrtEntry(index, start_time, end_time, text)


def filter_srt_entries(entries: Iterator[SrtEntry]) -> Iterator[SrtEntry]:
    """Filter SRT entries to remove single-word subtitles and duplicates.

    Args:
        entries: Iterator of SrtEntry objects

    Yields:
        Filtered SrtEntry objects with duplicates removed
    """
    seen_texts: set[str] = set()

    for entry in entries:
        # Strip speaker names if present
        cleaned_text = strip_speaker_name(entry.text)

        # Create a new entry with the cleaned text
        cleaned_entry = SrtEntry(entry.index, entry.start_time, entry.end_time, cleaned_text)

        # Check if the subtitle is a single word
        # We split by both spaces and Chinese characters
        words = re.findall(r"[\u4e00-\u9fff]|[^\s\u4e00-\u9fff]+", cleaned_text)

        # Skip entries with only one word
        if len(words) <= 1:
            continue

        # Skip duplicate entries
        normalized_text = cleaned_text.strip()
        if normalized_text in seen_texts:
            continue

        seen_texts.add(normalized_text)
        yield cleaned_entry

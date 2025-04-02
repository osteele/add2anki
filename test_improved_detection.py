#!/usr/bin/env python
"""Test script for contextual language detection.

This script demonstrates the context-aware language detection approach
implemented with contextual-langdetect in add2anki. It can be used to analyze
text files and see how the language detection works with different content.
"""

import argparse
import sys
from typing import Dict

from contextual_langdetect import contextual_detect
from rich.console import Console
from rich.table import Table

console = Console()


def process_file_with_context(file_path: str) -> None:
    """Process text file using context-aware language detection.

    Args:
        file_path: Path to the text file to analyze
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        console.print(f"[bold red]Error reading file:[/bold red] {e}")
        sys.exit(1)

    if not lines:
        console.print("[bold yellow]No text found in the file.[/bold yellow]")
        sys.exit(1)

    console.print(f"[bold blue]Analyzing {len(lines)} lines from {file_path}[/bold blue]")

    # Detect languages with context awareness
    detected_languages = contextual_detect(lines)

    # Create table for line-by-line analysis
    line_table = Table(show_header=True)
    line_table.add_column("#", style="dim", justify="right")
    line_table.add_column("Text", style="bold")
    line_table.add_column("Language", style="blue")
    line_table.add_column("Status", style="yellow")

    # Process results for display
    language_counts: Dict[str, int] = {}

    for i, (line, language) in enumerate(zip(lines, detected_languages), 1):
        if not language:
            # Skip if no language was detected
            console.print(f"[bold red]No language detected for line {i}:[/bold red] {line}")
            continue

        # Count languages
        language_counts[language] = language_counts.get(language, 0) + 1

        # Determine ambiguity based on text length
        is_ambiguous = len(line) < 6
        status = "[yellow]POTENTIALLY AMBIGUOUS[/yellow]" if is_ambiguous else "OK"

        # Add to the table
        line_table.add_row(str(i), line[:40] + ("..." if len(line) > 40 else ""), str(language), status)

    # Print the table of detections
    console.print("\n[bold green]=== LINE-BY-LINE ANALYSIS ===[/bold green]")
    console.print(line_table)

    # Print language distribution
    console.print("\n[bold green]=== DOCUMENT ANALYSIS ===[/bold green]")
    console.print("[bold]Language distribution:[/bold]")

    total_lines = len(lines)
    for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / total_lines * 100
        bar = "█" * int(percentage / 5)  # Scale bar to reasonable length
        console.print(f"{lang}: {bar} {count} lines ({percentage:.1f}%)")

    # Print summary statistics
    console.print("\n[bold green]=== RESULTS SUMMARY ===[/bold green]")
    console.print(f"Total lines: {len(lines)}")

    # Count languages with significant presence (>10% of sentences)
    primary_languages = []
    threshold = max(1, len(lines) * 0.1)
    primary_languages = [lang for lang, count in language_counts.items() if count >= threshold]

    console.print(f"Primary languages (>10% of text): {', '.join(primary_languages)}")

    # Count potentially ambiguous cases
    ambiguous_count = sum(1 for line in lines if len(line) < 6)
    console.print(
        f"Potentially ambiguous detections (short text): {ambiguous_count} ({ambiguous_count / len(lines) * 100:.1f}%)"
    )


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Test contextual language detection")
    parser.add_argument("file", help="Text file to analyze")
    args = parser.parse_args()

    process_file_with_context(args.file)


if __name__ == "__main__":
    main()

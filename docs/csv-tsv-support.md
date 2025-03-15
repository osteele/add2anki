# CSV/TSV Import Feature Design

## Overview

This feature extends add2anki to support importing cards from CSV and TSV files, in addition to the existing plain text file support.

## File Format Detection

- File format is detected based on file extension:
  - `.csv` for comma-separated values
  - `.tsv` for tab-separated values
  - `.txt` for traditional single-sentence-per-line format

## Header Parsing

- First row is treated as column headers
- Headers are matched case-insensitively to Anki note fields
- Special case detection for Chinese language learning cards:
  - Presence of "Chinese", "Mandarin", or "Hanzi" field indicates Chinese learning deck

## Audio File Handling

- If the CSV/TSV contains an "Audio" or "Sound" field (case-insensitive):
  - Values are treated as paths to audio files, relative to the input file's directory
  - Files are verified to exist before processing begins
  - Audio generation is skipped for these entries

## Workflow

### For Chinese Language Learning Decks:

1. Detect if input is for Chinese learning by checking for Chinese/Mandarin/Hanzi field
2. Use existing note type selection logic (command line, config, or user prompt)
3. Skip translation when:
   - English field is already provided in the CSV/TSV
   - Model doesn't have an English field
4. Skip Pinyin generation when:
   - Pinyin field is already provided in the CSV/TSV
   - Model doesn't have a Pinyin field
5. Skip audio generation when:
   - Audio/Sound field is already provided in the CSV/TSV
   - Model doesn't have an Audio field

### For Non-Chinese Language Learning Decks:

1. Skip reading note type from config file
2. Show list of compatible note types (those with fields matching CSV/TSV headers)
3. Allow user to select note type and deck (or use command-line options)
4. Add cards with specified tags (default to "add2anki" if none provided)
5. Do not save note type selection to config

## Command Line Interface

Extends existing `--file` option to handle CSV/TSV files:
```
add2anki --file vocab.csv [--deck "My Deck"] [--note-type "Basic"] [--tags "csv,import"]
```

Existing options like `--deck`, `--note-type`, and `--tags` work the same way as with text files.
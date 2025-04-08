# Command Line Reference

## Basic Usage

```bash
add2anki "Hello, how are you?"
```

Words without spaces will be joined into a sentence:

```bash
add2anki Hello how are you
```

## Options

| Option | Description | Default |
|--------|-------------|--------|
| `--deck` | Name of the Anki deck to add cards to | Interactive selection |
| `--note-type` | Name of the Anki note type to use | Interactive selection |
| `--tags` | Comma-separated list of tags to add to the cards | "add2anki" |
| `--style` | Translation style: `conversational`, `formal`, or `written` | "conversational" |
| `--audio-provider` | Audio provider: `google` or `elevenlabs` | "google" |
| `--file` | Process input from a file (text, CSV/TSV, or SRT) | None |
| `--source-lang` | Source language code (e.g., "en" for English) | Auto-detected |
| `--target-lang` | Target language code (e.g., "zh" for Chinese) | "zh" |
| `--anki-host` | Hostname of the AnkiConnect server | "localhost" |
| `--anki-port` | Port of the AnkiConnect server | 8765 |
| `--launch-anki` | Whether to launch Anki if it's not running | true |

## Examples

### Translation Styles

```bash
# Default conversational style
add2anki "Hello, how are you?"

# Formal style (more polite expressions)
add2anki --style formal "Hello, how are you?"

# Written style (literary style for written texts)
add2anki --style written "Hello, how are you?"
```

### Deck and Note Type Selection

```bash
# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Use the previously saved default deck
add2anki --deck default "Hello, how are you?"

# Use the previously saved default note type
add2anki --note-type default "Hello, how are you?"
```

When no deck or note type is specified on the command line, add2anki will prompt you to select one from the available options. The previously used deck or note type will be pre-selected as the default option. Your selection will be saved for future use.

If there is only one available deck or suitable note type, it will be automatically selected without prompting.

### Tags

```bash
# Add custom tags
add2anki --tags "chinese,beginner" "Hello, how are you?"

# No tags
add2anki --tags "" "Hello, how are you?"
```

### Audio Providers

```bash
# Use Google Translate TTS (default, no authentication required)
add2anki --audio-provider google "Hello, how are you?"

# Use ElevenLabs (requires API key)
add2anki --audio-provider elevenlabs "Hello, how are you?"
```

### File Input

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# Or specify the CSV/TSV file directly as an argument
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt
```

### Interactive Mode

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

### Combining Options

```bash
# Combine multiple options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"

# Combine options with file input
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
```

## File Formats

### CSV/TSV Format

CSV and TSV files must include a header row. The column headers are matched to Anki fields (case-insensitive).

For Chinese language learning, if the CSV/TSV includes columns for:
- Chinese/Mandarin/Hanzi
- Pinyin/Pronunciation
- English/Translation/Meaning
- Audio/Sound

These will be mapped to the corresponding fields in your Anki note type. Missing fields will be generated automatically.

Example CSV for Chinese vocabulary:
```csv
Chinese,Pinyin,English,Notes
你好,nǐ hǎo,Hello,Common greeting
谢谢,xiè xiè,Thank you,Polite expression
再见,zài jiàn,Goodbye,Common farewell
```

### SRT Subtitle Format

SRT files are standard subtitle files with sequential entries containing:
1. Entry number
2. Timestamp range (start --> end)
3. Subtitle text (can span multiple lines)

add2anki will:
- Parse the SRT file and extract each subtitle entry
- Skip entries containing single words only
- Remove duplicate subtitles to avoid creating duplicate cards
- Verify the text is Mandarin Chinese
- Translate to English using OpenAI
- Generate pinyin romanization for the Mandarin text
- Generate audio for the Mandarin text
- Create Anki cards with Mandarin text, pinyin, English translation, and audio

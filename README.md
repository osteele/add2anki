# add2anki — add language study cards to Anki
A CLI tool to add language learning cards to Anki, with automatic translation and audio generation.

Currently supports English to Mandarin Chinese translation with audio generation using three providers:
- Google Translate TTS (default, no authentication required)
- ElevenLabs (requires API key)

## Features

- Translate English text to Mandarin Chinese using OpenAI's GPT models
- Support for different translation styles:
  - `conversational` (default): Natural, everyday language
  - `formal`: More polite expressions appropriate for business or formal situations
  - `written`: Literary style suitable for written texts
- Generate high-quality audio for Chinese text using one of three providers:
  - Google Translate TTS (default, no authentication required)
  - ElevenLabs (requires API key)
- Add cards to Anki with translation and audio
- Add custom tags to notes or use the default "add2anki" tag
- Automatic detection of suitable note types and field mappings
- Support for custom note types with field name synonyms (Hanzi/Chinese, Pinyin/Pronunciation, English/Translation)
- Configuration saved between sessions
- Support for batch processing from text, CSV/TSV, or SRT subtitle files
- Parse SRT files to create cards from Mandarin subtitles
- Interactive mode for adding cards one by one

## Prerequisites

- Python 3.11 or higher
- [Anki](https://apps.ankiweb.net/) with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed
- OpenAI API key
- For audio generation (optional, as Google Translate is used by default):
  - ElevenLabs API key (for ElevenLabs)

## Installation

1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
2. Run `uv tool install git_https://github.com/osteele/add2anki@release`

## Environment Variables

Set the following environment variables:

```bash
# Required for translation
export OPENAI_API_KEY=your_openai_api_key

# Required only if using ElevenLabs
export ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

## Usage

### Command-line

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

### File Input

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

#### CSV/TSV Format

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

For audio files, you can specify either:
1. A path relative to the CSV/TSV file:
  ```csv
  Chinese,Pinyin,English,Audio
  你好,nǐ hǎo,Hello,audio/nihao.mp3
  谢谢,xiè xiè,Thank you,audio/xiexie.mp3
  ```

2. Or an Anki-style sound field value:

  ```csv
  Chinese,Pinyin,English,Audio
  你好,nǐ hǎo,Hello,[sound:audio2anki_f0adc643_7ec88127.mp3]
  谢谢,xiè xiè,Thank you,[sound:audio2anki_xiexie_123456.mp3]
  ```

When using Anki-style sound field values:
- The format is `[sound:filename.mp3]`
- The file will be looked for in:
  1. The directory containing the CSV file
  2. The `media` subdirectory relative to the CSV file

#### SRT Subtitle Format

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

Example SRT entry:

```text
1
00:00:15,000 --> 00:00:18,000
你好，我很高兴认识你

2
00:00:20,100 --> 00:00:22,900
我的名字是王小明
```

### Interactive Mode

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

## Note Type and Deck Selection

add2anki will automatically detect suitable note types in your Anki collection. A suitable note type must have fields that match:

- Hanzi/Chinese/Characters for the Chinese characters
- Pinyin/Pronunciation/Reading for the pronunciation
- English/Translation/Meaning for the English translation

If multiple suitable note types are found, you'll be prompted to select one.

Similarly, if no deck is specified via the `--deck` option and no previously selected deck is found in the configuration, add2anki will display a list of available decks and prompt you to select one.

Your selections for both note type and deck will be saved for future use.

You can also specify a note type or deck directly with the `--note-type` and `--deck` options.

## Configuration

add2anki saves your preferences (deck name, note type, field mappings) in a configuration file:

- On Windows: `%APPDATA%\add2anki\config.json`
- On macOS/Linux: `~/.config/add2anki/config.json`

## Development

1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
2. [Install `just`](https://just.systems/man/en/pre-built-binaries.html)

3.
```bash
# Clone the repository
git clone https://github.com/osteele/add2anki.git
cd add2anki

# Install dependencies
just setup

# Install pre-commit hooks
uv run --dev pre-commit install

# Run tests
just test

# Format code and run type checking
just fmt
just tc

# Run all checks
just check
```

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run code formatting before each commit.
The hooks will automatically run `just fmt` to format your code with ruff.

To install the pre-commit hooks:

```bash
uv run --dev pre-commit install
```

After installation, the hooks will run automatically on each commit.

## Acknowledgements

This project relies on several excellent libraries:

- [click](https://github.com/pallets/click) for building the command-line interface
- [rich](https://github.com/Textualize/rich) for beautiful text formatting
- [pydantic](https://github.com/samuelcolvin/pydantic) for robust data validation
- [requests](https://github.com/psf/requests) for making HTTP requests

Services:
- [openai](https://github.com/openai/openai-python) for transcription and translation
- [elevenlabs](https://github.com/elevenlabs/elevenlabs-python) for audio generation

## License

MIT

## Author

Oliver Steele (@osteele)

### Options

- `--deck-name`: Name of the Anki deck to add cards to. Defaults to "add2anki".
- `--note-type`: Name of the Anki note type to use. Defaults to "add2anki".
- `--tags`: Comma-separated list of tags to add to the cards. Defaults to "add2anki".
- `--source`: Source of the text to translate. Can be a file path or "-" for stdin.
- `--target-lang`: Target language code (e.g., "zh" for Chinese). Required.
- `--source-lang`: Source language code (e.g., "en" for English). Optional.
- `--anki-host`: Hostname of the AnkiConnect server. Defaults to "localhost".
- `--anki-port`: Port of the AnkiConnect server. Defaults to 8765.
- `--launch-anki`: Whether to launch Anki if it's not running. Defaults to true.

### Examples

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"
add2anki --tags "" "Hello, how are you?"  # No tags (default is "add2anki")

# Use a different audio provider
add2anki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
add2anki --deck "Business Chinese" --style formal --audio-provider elevenlabs --tags "business,formal" "Hello, how are you?"
```

```bash
# Process sentences from a text file (one per line)
add2anki --file sentences.txt

# Process vocabulary from a CSV file (with headers)
add2anki --file vocabulary.csv
# You can also specify the CSV/TSV file directly as an argument without the --file option
add2anki vocabulary.csv

# Process vocabulary from a TSV file (with headers)
add2anki --file vocabulary.tsv
add2anki vocabulary.tsv

# Process Mandarin subtitles from an SRT file
add2anki --file subtitles.srt
add2anki subtitles.srt

# Combine with other options
add2anki --file sentences.txt --deck "Chinese" --style written --audio-provider elevenlabs --tags "from-file,written"
add2anki vocabulary.csv --deck "Chinese" --tags "csv,imported"
add2anki subtitles.srt --deck "Mandarin" --tags "movie,subtitles"
```

```bash
# Start interactive mode
add2anki

# Start interactive mode with specific options
add2anki --deck "Chinese" --style formal --audio-provider elevenlabs --tags "interactive,formal"
```

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Words without spaces will be joined into a sentence
add2anki Hello how are you

# Specify a different Anki deck
add2anki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
add2anki --style formal "Hello, how are you?"
add2anki --style written "Hello, how are you?"

# Specify a note type
add2anki --note-type "Basic" "Hello, how are you?"

# Add tags to the note
add2anki --tags "chinese,beginner" "Hello, how are you?"

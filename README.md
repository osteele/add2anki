# Langki — add language study cards to Anki
A CLI tool to add language learning cards to Anki, with automatic translation and audio generation.

Currently supports English to Mandarin Chinese translation with audio generation using three providers:
- Google Translate TTS (default, no authentication required)
- Google Cloud Text-to-Speech (requires API key)
- ElevenLabs (requires API key)

## Features

- Translate English text to Mandarin Chinese using OpenAI's GPT models
- Support for different translation styles:
  - `conversational` (default): Natural, everyday language
  - `formal`: More polite expressions appropriate for business or formal situations
  - `written`: Literary style suitable for written texts
- Generate high-quality audio for Chinese text using one of three providers:
  - Google Translate TTS (default, no authentication required)
  - Google Cloud Text-to-Speech (requires API key)
  - ElevenLabs (requires API key)
- Add cards to Anki with translation and audio
- Automatic detection of suitable note types and field mappings
- Support for custom note types with field name synonyms (Hanzi/Chinese, Pinyin/Pronunciation, English/Translation)
- Configuration saved between sessions
- Support for batch processing from a file
- Interactive mode for adding cards one by one

## Prerequisites

- Python 3.12 or higher
- [Anki](https://apps.ankiweb.net/) with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed
- OpenAI API key
- For audio generation (optional, as Google Translate is used by default):
  - Google Cloud credentials (for Google Cloud TTS)
  - ElevenLabs API key (for ElevenLabs)

## Installation

1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
2. Run `uv tool install https://github.com/osteele/langki.git`

## Environment Variables

Set the following environment variables:

```bash
# Required for translation
export OPENAI_API_KEY=your_openai_api_key

# Required only if using Google Cloud Text-to-Speech
export GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json

# Required only if using ElevenLabs
export ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

## Usage

### Command-line

```bash
# Basic usage (uses Google Translate TTS by default)
langki "Hello, how are you?"

# Words without spaces will be joined into a sentence
langki Hello how are you

# Specify a different Anki deck
langki --deck "Chinese" "Hello, how are you?"

# Specify a different translation style
langki --style formal "Hello, how are you?"
langki --style written "Hello, how are you?"

# Specify a note type
langki --note-type "Basic" "Hello, how are you?"

# Use a different audio provider
langki --audio-provider google-cloud "Hello, how are you?"
langki --audio-provider elevenlabs "Hello, how are you?"

# Combine options
langki --deck "Business Chinese" --style formal --audio-provider elevenlabs "Hello, how are you?"
```

### File Input

```bash
# Process sentences from a file (one per line)
langki --file sentences.txt

# Combine with other options
langki --file sentences.txt --deck "Chinese" --style written --audio-provider google-cloud
```

### Interactive Mode

```bash
# Start interactive mode
langki

# Start interactive mode with specific options
langki --deck "Chinese" --style formal --audio-provider elevenlabs
```

## Note Type Selection

Langki will automatically detect suitable note types in your Anki collection. A suitable note type must have fields that match:

- Hanzi/Chinese/Characters for the Chinese characters
- Pinyin/Pronunciation/Reading for the pronunciation
- English/Translation/Meaning for the English translation

If multiple suitable note types are found, you'll be prompted to select one. Your selection will be saved for future use.

You can also specify a note type directly with the `--note-type` option.

## Configuration

Langki saves your preferences (last used deck, note type, field mappings) in a configuration file:

- On Windows: `%APPDATA%\langki\config.json`
- On macOS/Linux: `~/.config/langki/config.json`

## Development

1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
2. [Install `just`](https://just.systems/man/en/pre-built-binaries.html)

3.
```bash
# Clone the repository
git clone https://github.com/osteele/langki.git
cd langki

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
- [google-cloud-texttospeech](https://github.com/googleapis/python-texttospeech) for Google Cloud TTS

## License

MIT

## Author

Oliver Steele (@osteele)

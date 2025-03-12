# Langki — add language study cards to Anki

A CLI tool to add language learning cards to Anki using OpenAI for translations and audio generation with one of three providers:
- Google Translate TTS (default, no authentication required)
- Google Cloud Text-to-Speech (requires credentials)
- ElevenLabs (requires API key)

## Features

- Translate English sentences to Mandarin Chinese (with Hanzi and Pinyin)
- Generate audio for the translated sentences using one of three providers:
  - Google Translate TTS (free, no authentication)
  - Google Cloud Text-to-Speech (requires credentials)
  - ElevenLabs (requires API key)
- Add cards to Anki decks
- Multiple input modes: command-line arguments, file input, or interactive mode

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

## Usage

Before using Langki, make sure to:

1. Start Anki
2. Have the AnkiConnect plugin installed and enabled
3. Set your API keys as environment variables:

```bash
export OPENAI_API_KEY=your_openai_api_key

# For Google Cloud Text-to-Speech (optional)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json

# For ElevenLabs (optional)
export ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

### Command-line mode

```bash
# Add a single sentence (using Google Translate TTS by default)
langki "Hello, how are you?"

# Use Google Cloud Text-to-Speech
langki --audio-provider google-cloud "Hello, how are you?"

# Use ElevenLabs
langki --audio-provider elevenlabs "Hello, how are you?"

# Add multiple sentences
langki "Hello, how are you?" "I like to travel."

# Words without spaces will be joined into a sentence
langki Hello how are you

# Specify a different deck
langki --deck "Chinese Vocabulary" "Hello, how are you?"
```

### File input mode

Create a text file with one sentence per line:

```
Hello, how are you?
I like to travel.
I am studying Chinese.
```

Then run:

```bash
langki --file sentences.txt

# Or with other audio providers
langki --file sentences.txt --audio-provider google-cloud
langki --file sentences.txt --audio-provider elevenlabs
```

### Interactive mode

If no sentences or file are provided, Langki will enter interactive mode:

```bash
langki

# Or with other audio providers
langki --audio-provider google-cloud
langki --audio-provider elevenlabs
```

You'll be prompted to enter sentences one by one. Type `exit` or press Ctrl+C to quit.

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

# Run tests
just test

# Format code and run type checking
just fmt
just tc

# Run all checks
just check
```
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

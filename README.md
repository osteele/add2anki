# add2anki — add language study cards to Anki

[![PyPI version](https://img.shields.io/pypi/v/add2anki.svg)](https://pypi.org/project/add2anki/)
[![Python Version](https://img.shields.io/pypi/pyversions/add2anki.svg)](https://pypi.org/project/add2anki/)
[![License](https://img.shields.io/github/license/osteele/add2anki.svg)](https://github.com/osteele/add2anki/blob/main/LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/osteele/add2anki/actions/workflows/ci.yml/badge.svg)](https://github.com/osteele/add2anki/actions/workflows/ci.yml)

A CLI tool to add language learning cards to Anki, with automatic translation and audio generation.

Currently supports English to Mandarin Chinese translation with audio generation using two providers:
- Google Translate TTS (default, no authentication required)
- ElevenLabs (requires API key)

For related language learning resources, visit [Oliver Steele's Language
Learning Resources](https://osteele.com/topics/language-learning/).

## Features

- 🔄 Translate English text to Mandarin Chinese using OpenAI's GPT models
- 🗣️ Support for different translation styles:
  - `conversational` (default): Natural, everyday language
  - `formal`: More polite expressions appropriate for business or formal situations
  - `written`: Literary style suitable for written texts
- 🔊 Generate high-quality audio for Chinese text using one of two providers:
  - Google Translate TTS (default, no authentication required)
  - ElevenLabs (requires API key)
- 🃏 Add cards to Anki with translation and audio
- 🏷️ Add custom tags to notes or use the default "add2anki" tag
- 🧠 Context-aware language detection that automatically identifies languages
- 🔍 Automatic detection of suitable note types and field mappings
- 🔧 Support for custom note types with field name synonyms (Hanzi/Chinese, Pinyin/Pronunciation, English/Translation)
- 💾 Configuration saved between sessions
- 📚 Support for batch processing from text, CSV/TSV, or SRT subtitle files
- 🎬 Parse SRT files to create cards from Mandarin subtitles
- 🤔 Interactive mode for adding cards one by one

## Prerequisites

- Python 3.11 or higher
- [Anki](https://apps.ankiweb.net/) with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed
- OpenAI API key
- For audio generation (optional, as Google Translate is used by default):
  - ElevenLabs API key (for ElevenLabs)

## Installation

You can install add2anki using either `uv`, or `pipx`, or `pip`:

### Using uv

1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it already.

2. Install `add2anki`:
  ```bash
  uv tool install add2anki
  ```

### Using pipx

1. [Install `pipx`](https://pipx.pypa.io/stable/installation/) if you don't have it already.

2. Install add2anki
  ```bash
  pipx install add2anki
  ```

### Using pip (not recommended)

This method doesn't require a third-party tool, but it is not recommended as it will install add2anki in the current Python environment, which may cause conflicts with other packages.

```bash
pip install add2anki
```

## Environment Variables

Set the following environment variables:

```bash
# Required for translation
export OPENAI_API_KEY=your_openai_api_key

# Required only if using ElevenLabs
export ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

## Quick Start

```bash
# Basic usage (uses Google Translate TTS by default)
add2anki "Hello, how are you?"

# Start interactive mode
add2anki
```

## Documentation

- [Command Line Reference](docs/command-line.md) - Detailed usage and options
- [Development Guide](DEVELOPMENT.md) - Information for contributors

## Note Type and Deck Selection

add2anki will automatically detect suitable note types in your Anki collection. A suitable note type must have fields that match:

- Hanzi/Chinese/Characters for the Chinese characters
- Pinyin/Pronunciation/Reading for the pronunciation
- English/Translation/Meaning for the English translation

If multiple suitable note types are found, you'll be prompted to select one.

Similarly, if no deck is specified via the `--deck` option and no previously selected deck is found in the configuration, add2anki will display a list of available decks and prompt you to select one.

Your selections for both note type and deck will be saved for future use.

## Configuration

add2anki saves your preferences (deck name, note type, field mappings) in a configuration file:

- On Windows: `%APPDATA%\add2anki\config.json`
- On macOS/Linux: `~/.config/add2anki/config.json`

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

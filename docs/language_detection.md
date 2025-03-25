# Language Detection

add2anki uses [fast-langdetect](https://pypi.org/project/fast-langdetect/) to
automatically detect the language of input text. This enables the tool to handle
both source->target and target->source translation flows with any supported language pair.

## Overview

When processing input text (from command line, REPL, or files), add2anki:

1. Detects the language of each sentence
2. Decides whether the sentence is in the source or target language:
   - If the sentence is in the specified source language, it is treated as source text
   - If the sentence is in the specified target language, it is treated as target text
3. If the sentence is in the target language:
   - Uses it as the target text
   - Translates it to the source language for use as the source text
4. Otherwise:
   - Uses the sentence as the source text
   - Translates it to the target language

## Language Detection Process

### Single Sentence Mode

When processing a single sentence (command line or REPL):

1. If `--source-lang` and/or `--target-lang` are specified:
   - Uses these as the explicit language directions
   - Only detects whether the sentence is in source or target language
   - Uses the specified languages for translation direction

2. Otherwise:
   - Detects the language using fast-langdetect
   - Uses the detected language to determine translation direction
   - If detection is ambiguous, uses context from previous sentences (in REPL mode)
   - If detection fails or remains ambiguous, prompts the user for clarification
   - In REPL mode, stores the detected language for subsequent sentences

### Batch Mode

When processing files (text, CSV, TSV, or SRT):

1. First Pass:
   - Detects language for each sentence
   - Identifies unambiguous cases where language detection has high confidence

2. Second Pass:
   - For ambiguous cases (where language detection has low confidence):
     - Uses the predominant language from unambiguous sentences as context
     - Makes an informed decision based on the surrounding context
     - If no unambiguous sentences exist:
       - In REPL mode: asks the user for clarification
       - In batch mode: skips with a warning

## Handling Ambiguity

add2anki uses several strategies to handle ambiguous language detection:

1. **Context-based disambiguation**:
   - In REPL mode: Uses previously detected languages as context
   - In batch mode: Uses unambiguous sentences (from both before and after) as context

2. **User intervention**:
   - In interactive mode: Prompts the user when ambiguity cannot be resolved
   - Allows explicit language specification via command-line options

3. **Skip with warning**:
   - In batch mode: When ambiguity cannot be resolved and no user is present to intervene,
     the sentence is skipped with a warning message

## Language Detection Flow

```
                           ┌───────────────────┐
                           │  Input Sentence   │
                           └─────────┬─────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ Language Detection│
                           └─────────┬─────────┘
                                     │
                                     ▼
                    ┌───────────────────────────────┐
                    │ Is language detection certain?│
                    └─┬─────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
┌──────────────────┐    ┌──────────────────────┐
│     Certain      │    │      Ambiguous       │
└────────┬─────────┘    └──────────┬───────────┘
         │                         │
         │                         ▼
         │             ┌───────────────────────┐
         │             │ Try context-based     │
         │             │ disambiguation        │
         │             └───────────┬───────────┘
         │                         │
         │                         ▼
         │             ┌───────────────────────┐
         │             │ Resolved with context?│
         │             └┬─────────────────────┬┘
         │              │                     │
         │              │ Yes                 │ No
         │              ▼                     ▼
         │     ┌────────────────┐    ┌────────────────┐
         │     │ Use resolved   │    │ Interactive    │◄─── Yes ┌─────────────┐
         │     │ language       │    │ mode?          ├─────────►Ask user     │
         │     └───────┬────────┘    └──────┬─────────┘         └──────┬──────┘
         │             │                    │ No                       │
         │             │                    ▼                          │
         │             │            ┌────────────────┐                 │
         │             │            │ Skip with      │                 │
         │             │            │ warning        │                 │
         │             │            └────────────────┘                 │
         ▼             ▼                                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Process sentence:                              │
│                  - Determine source/target direction                    │
│                  - Translate as needed                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Examples

### Source to Target Translation

```bash
# English to Spanish
add2anki "Hello, how are you?"

# English to Japanese with explicit target
add2anki --target-lang ja "Hello, how are you?"
```

### Target to Source Translation

```bash
# Spanish to English
add2anki "¿Hola, cómo estás?"

# Japanese to English
add2anki "こんにちは、お元気ですか？"
```

### Batch Processing

```bash
# Process a file with mixed languages
add2anki --file mixed.txt
# mixed.txt contents:
# Hello, how are you?
# ¿Hola, cómo estás?
# こんにちは、お元気ですか？
```

### Explicit Source/Target Languages

```bash
# Force Spanish as source language
add2anki --source-lang es "¿Hola, cómo estás?"

# Force Japanese as target language
add2anki --target-lang ja "Hello, how are you?"

# Explicit source and target languages
add2anki --source-lang en --target-lang fr "Hello, how are you?"
```

## Limitations

- Relies on fast-langdetect for language detection
- Language detection accuracy depends on text length and uniqueness
- May require user input for ambiguous cases in interactive mode
- Skips ambiguous sentences in batch mode if no clear pattern exists
- Very short sentences (1-3 words) may have lower detection accuracy

# Language Detection

add2anki uses [contextual-langdetect](https://github.com/osteele/contextual-langdetect) for intelligent, context-aware language detection. This enables the tool to handle both source->target and target->source translation flows with any supported language pair.

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

## Context-Aware Language Detection

add2anki uses contextual-langdetect for improved language detection reliability, especially for short or ambiguous sentences:

### The Problem with Per-Sentence Detection

Traditional language detection analyzes each sentence in isolation, which has limitations:
- Short phrases may have insufficient linguistic features for reliable detection
- Some phrases look similar across related languages (e.g., Chinese, Japanese)
- No benefit from the context of surrounding text

### Contextual Approach

add2anki addresses these limitations using the contextual-langdetect package:

1. **Document-Level Context Awareness:**
   - Instead of detecting each sentence independently, the entire document is analyzed together
   - The context of surrounding sentences is used to improve detection accuracy
   - Patterns in the document help resolve ambiguous cases

2. **Handling Short or Ambiguous Sentences:**
   - Very short sentences (less than 6 characters) are more prone to misidentification
   - For these cases, the detection system considers:
     - The primary languages used in the document
     - Previous language detections in REPL mode
     - Expected languages when specified

This contextual awareness mimics how humans use surrounding text to understand language in context.

## Language Detection Process

### Single Sentence Mode

When processing a single sentence (command line or REPL):

1. If `--source-lang` and/or `--target-lang` are specified:
   - Uses these as the explicit language directions
   - Only detects whether the sentence is in source or target language
   - Uses the specified languages for translation direction

2. Otherwise:
   - Detects the language using contextual detection
   - Uses the detected language to determine translation direction
   - If detection is ambiguous, uses context from previous sentences (in REPL mode)
   - If detection fails or remains ambiguous, prompts the user for clarification
   - In REPL mode, builds a language context model for subsequent sentences

### Batch Mode

When processing files (text, CSV, TSV, or SRT):

1. The contextual-langdetect package processes all sentences together:
   - Analyzes document-level language patterns
   - Considers context when detecting each sentence
   - Improves accuracy for ambiguous sentences

2. After detection:
   - Sentences already in the target language are skipped
   - Other sentences are translated to the target language
   - If detection fails for a sentence, it is skipped with a warning

## Handling Ambiguity

add2anki uses several strategies to handle ambiguous language detection:

1. **Context-based disambiguation**:
   - In REPL mode: Uses previously detected languages as context
   - In batch mode: Uses full document context via contextual-langdetect
   - For very short sentences, applies additional scrutiny

2. **User intervention**:
   - In interactive mode: Prompts the user when ambiguity cannot be resolved
   - Allows explicit language specification via command-line options

3. **Expected language hints**:
   - When processing with known language context, provides hints to the detector
   - Especially useful when working with bilingual content

## Examples

### Basic Usage

```bash
# This will identify the language automatically
add2anki tests/data/test-zh.txt
```

### Mixed Language Content

```bash
# Can automatically handle alternating languages
add2anki --file tests/data/test-mixed.txt
# (Contains both Chinese and English sentences)
```

### Ambiguous Text Handling

Short phrases that might be ambiguous:

```bash
# Context-aware detection helps resolve ambiguity
add2anki "天气很冷。"  # Short Chinese phrase
```

### Explicit Language Specification

When you want to override automatic detection:

```bash
# Force source language to be Chinese
add2anki --source-lang zh --target-lang en tests/data/test-zh.txt
```

## Benefits of Contextual Detection

- **Improved accuracy** for short phrases and sentences
- **Better handling** of mixed-language documents
- **Reduced need** for explicit language specification
- **More consistent results** across various content types
- **Graceful degradation** for challenging cases

## Limitations

- Language detection is still probabilistic and may not be perfect
- Very short sentences (1-2 words) remain challenging
- Closely related languages can sometimes be difficult to distinguish
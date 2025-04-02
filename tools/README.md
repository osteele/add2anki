# Development Tools

This directory contains tools for developing and testing add2anki.

## Language Detection Tools

- `test_lang_detection.py` - A script to test the context-aware language detection on any text file

### Usage

```bash
# Test on a file with Chinese content
python tools/test_lang_detection.py tests/data/test-zh.txt

# Test on a mixed-language file
python tools/test_lang_detection.py tests/data/test-mixed.txt
```

### Features

The script provides:

- Line-by-line language detection analysis
- Document-level language statistics
- Visualization of corrections made by the context-aware system
- Compact summary table of all lines and their language status
- Distribution of confidence levels and languages

This is useful for:
1. Debugging language detection issues
2. Understanding how the context-aware system works
3. Testing new content before adding it to Anki
4. Evaluating detection performance on different types of content
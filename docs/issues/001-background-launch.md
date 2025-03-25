# Background Launch Support

This document describes the status and requirements for launching Anki in the background on different platforms.

## Current Status

- ✅ macOS: Implemented
- ❌ Windows: Not yet implemented
- ❌ Linux: Not yet implemented

## Implementation Notes

### Windows (Not Implemented)

A possible implementation could use:
```bash
start /b anki.exe
```
where:
- `start` launches a new process
- `/b` runs the process in the background without creating a new window

### Linux (Not Implemented)

A possible implementation could use:
```python
subprocess.Popen(
    ["anki"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,  # Creates a new session
)
```

Note: The effectiveness of background launch on Linux may vary depending on the desktop environment and window manager.

## Testing Requirements

For each platform:
1. Verify Anki launches successfully
2. Verify the Anki window does not steal focus
3. Verify AnkiConnect becomes available
4. Test behavior when Anki is already running

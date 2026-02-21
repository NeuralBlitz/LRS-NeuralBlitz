# Voice Interface System - Quick Start Guide

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set OpenAI API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

## Quick Test

### Test Text Input (No Microphone Required)

```python
from voice_interface import VoiceInterface, VoiceConfig

# Create interface
interface = VoiceInterface()

# Process text
result = interface.process_text("Hello, how are you?")
print(f"Response: {result['response']}")
```

### Test Voice Input (Requires Microphone)

```python
from voice_interface import VoiceInterface, VoiceConfig

# Create interface
interface = VoiceInterface()

# Record and process
print("Recording... Speak now!")
result = interface.listen_and_process(duration=5)
print(f"You said: {result['transcribed_text']}")
print(f"Response: {result['response']}")
```

## Interactive Mode

```bash
python voice_interface.py
```

Available commands:
- `listen` - Record and process voice input
- `quit` - Exit
- `say <text>` - Speak text
- Or type any text to process it

## Running Examples

```bash
python examples.py
```

This will run 7 comprehensive examples demonstrating:
1. Basic usage
2. Custom handlers
3. Voice recording
4. Conversation history
5. Async processing
6. File operations
7. Integration patterns

## Custom Command Handlers

```python
from voice_interface import (
    VoiceInterface, 
    VoiceCommand, 
    VoiceCommandType
)

interface = VoiceInterface()

# Define custom handler
def handle_weather(command: VoiceCommand) -> str:
    return "It's sunny today!"

# Register handler
interface.register_handler(
    VoiceCommandType.QUESTION, 
    handle_weather
)

# Test
result = interface.process_text("What's the weather?")
print(result['response'])  # "It's sunny today!"
```

## Configuration

```python
from voice_interface import VoiceConfig

config = VoiceConfig(
    recording_duration=10,      # Longer recordings
    tts_engine="openai",        # Higher quality TTS
    language="es",              # Spanish
    tts_rate=120                # Slower speech
)

interface = VoiceInterface(config)
```

## Troubleshooting

### Issue: No microphone detected
**Solution:** Check audio permissions and device settings

### Issue: OpenAI API errors
**Solution:** Verify API key is set: `echo $OPENAI_API_KEY`

### Issue: TTS not working
**Solution:** Install espeak for pyttsx3:
```bash
# Ubuntu/Debian
sudo apt-get install espeak

# macOS
brew install espeak

# Windows
# Download from espeak.sourceforge.net
```

### Issue: Import errors
**Solution:** Install all dependencies:
```bash
pip install openai sounddevice soundfile pyttsx3 numpy
```

## Next Steps

1. Review `examples.py` for comprehensive usage patterns
2. Read `REPORT.md` for technical details
3. Customize handlers for your application
4. Add wake word detection
5. Integrate with your existing codebase

## API Key Security

⚠️ **Never commit your API key!**

Use environment variables or a `.env` file (add to `.gitignore`):

```bash
# .gitignore
.env
*.key
*.pem
```

```python
# Safe usage
import os
from voice_interface import VoiceConfig

config = VoiceConfig(
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
```

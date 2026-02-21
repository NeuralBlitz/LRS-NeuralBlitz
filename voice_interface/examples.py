"""
Example usage of the Voice Interface System
==========================================
Demonstrates various use cases and integration patterns.
"""

import os
import asyncio
from voice_interface import VoiceInterface, VoiceConfig, VoiceCommand, VoiceCommandType


def example_basic_usage():
    """Example 1: Basic voice interface usage."""
    print("=" * 50)
    print("Example 1: Basic Voice Interface")
    print("=" * 50)

    # Initialize configuration
    config = VoiceConfig(recording_duration=5, tts_engine="pyttsx3", language="en")

    # Create interface
    interface = VoiceInterface(config)

    # Process text input (for testing without microphone)
    result = interface.process_text("Hello, how are you?")

    print(f"\nCommand: {result['command']['raw_text']}")
    print(f"Type: {result['command']['command_type']}")
    print(f"Intent: {result['command']['intent']}")
    print(f"Response: {result['response']}")
    print(f"Confidence: {result['command']['confidence']:.2f}")


def example_custom_handlers():
    """Example 2: Custom command handlers."""
    print("\n" + "=" * 50)
    print("Example 2: Custom Command Handlers")
    print("=" * 50)

    config = VoiceConfig()
    interface = VoiceInterface(config)

    # Define custom handlers
    def handle_weather(command: VoiceCommand) -> str:
        location = command.entities.get("location", "your area")
        return f"Checking weather for {location}... It's sunny today!"

    def handle_time(command: VoiceCommand) -> str:
        from datetime import datetime

        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."

    # Register handlers
    interface.register_handler(VoiceCommandType.QUESTION, handle_weather)
    interface.register_handler(VoiceCommandType.SYSTEM, handle_time)

    # Test with different commands
    test_commands = ["What's the weather like?", "What time is it?", "Open the browser"]

    for cmd_text in test_commands:
        result = interface.process_text(cmd_text)
        print(f"\nInput: {cmd_text}")
        print(f"Response: {result['response']}")


def example_voice_recording():
    """Example 3: Voice recording and transcription."""
    print("\n" + "=" * 50)
    print("Example 3: Voice Recording & Transcription")
    print("=" * 50)

    config = VoiceConfig(recording_duration=3)
    interface = VoiceInterface(config)

    print("\nRecording audio... (speak now)")

    try:
        # Record and process
        result = interface.listen_and_process(duration=3)

        if result["success"]:
            print(f"\nTranscribed: {result['transcribed_text']}")
            print(f"Command Type: {result['command']['command_type']}")
            print(f"Response: {result['response']}")
        else:
            print(f"Error: {result['error']}")

    except Exception as e:
        print(f"Recording failed: {e}")
        print("Note: This requires a working microphone")


def example_conversation_history():
    """Example 4: Conversation history and statistics."""
    print("\n" + "=" * 50)
    print("Example 4: Conversation History")
    print("=" * 50)

    config = VoiceConfig()
    interface = VoiceInterface(config)

    # Simulate conversation
    commands = [
        "Hello",
        "What's the weather?",
        "Open settings",
        "How do I use this?",
        "Goodbye",
    ]

    print("\nSimulating conversation:")
    for cmd in commands:
        result = interface.process_text(cmd)
        print(f"  User: {cmd}")
        print(f"  Assistant: {result['response']}")

    # Get statistics
    stats = interface.get_stats()
    print(f"\nConversation Statistics:")
    print(f"  Total Commands: {stats['total_commands']}")
    print(f"  Command Types: {stats['command_types']}")
    print(f"  Avg Confidence: {stats['avg_confidence']:.2f}")


def example_async_processing():
    """Example 5: Async processing for advanced use cases."""
    print("\n" + "=" * 50)
    print("Example 5: Async Processing")
    print("=" * 50)

    async def process_multiple():
        config = VoiceConfig()
        interface = VoiceInterface(config)

        commands = ["Hello there", "What's the time?", "Navigate to home"]

        # Process commands concurrently
        tasks = []
        for cmd in commands:
            # Note: process_text is sync, but we wrap for async pattern
            tasks.append(asyncio.to_thread(interface.process_text, cmd))

        results = await asyncio.gather(*tasks)

        for cmd, result in zip(commands, results):
            print(f"\n  {cmd} -> {result['response']}")

    try:
        asyncio.run(process_multiple())
    except Exception as e:
        print(f"Async processing demo: {e}")


def example_file_operations():
    """Example 6: Audio file operations."""
    print("\n" + "=" * 50)
    print("Example 6: Audio File Operations")
    print("=" * 50)

    from voice_interface import SpeechToText, TextToSpeech, VoiceConfig
    import tempfile
    import numpy as np

    config = VoiceConfig()

    # Create dummy audio data for demonstration
    print("\nCreating sample audio...")
    sample_rate = 16000
    duration = 2
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone

    # Initialize components
    stt = SpeechToText(config)
    tts = TextToSpeech(config)

    # Save audio to file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        stt.save_audio(audio, tmp.name)
        print(f"Saved audio to: {tmp.name}")

        # Note: This would fail in practice since it's just a tone,
        # but demonstrates the API
        print("Note: Real speech would be transcribed here")

    # Save TTS to file
    output_path = tempfile.mktemp(suffix=".wav")
    tts.save_to_file("Hello from voice interface", output_path)
    print(f"Saved TTS to: {output_path}")


def example_integration_pattern():
    """Example 7: Integration pattern with existing application."""
    print("\n" + "=" * 50)
    print("Example 7: Integration Pattern")
    print("=" * 50)

    class Application:
        """Example application integrating voice interface."""

        def __init__(self):
            self.config = VoiceConfig()
            self.voice = VoiceInterface(self.config)
            self.setup_voice_handlers()

        def setup_voice_handlers(self):
            """Configure voice command handlers."""

            def handle_open(command: VoiceCommand) -> str:
                app = command.entities.get("object", "application")
                return f"Opening {app}..."

            def handle_search(command: VoiceCommand) -> str:
                query = command.raw_text.replace("search for", "").strip()
                return f"Searching for: {query}"

            def handle_help(command: VoiceCommand) -> str:
                return """Available commands:
                - Open [application]
                - Search for [query]
                - What's the time?
                - Help"""

            self.voice.register_handler(VoiceCommandType.ACTION, handle_open)
            self.voice.register_handler(VoiceCommandType.QUESTION, handle_search)
            self.voice.register_handler(VoiceCommandType.SYSTEM, handle_help)

        def run(self):
            """Run the application."""
            print("\nApplication started with voice control")
            print("Test commands:")

            test_inputs = ["Open browser", "Search for python tutorials", "Help"]

            for input_text in test_inputs:
                result = self.voice.process_text(input_text)
                print(f"\n  > {input_text}")
                print(f"  {result['response']}")

    # Run application
    app = Application()
    app.run()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("VOICE INTERFACE SYSTEM - USAGE EXAMPLES")
    print("=" * 70)

    # Run examples
    example_basic_usage()
    example_custom_handlers()
    example_conversation_history()
    example_async_processing()
    example_file_operations()
    example_integration_pattern()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("\nFor interactive mode, run:")
    print("  python voice_interface.py")
    print("\nFor testing with voice, use:")
    print('  python -c "from voice_interface import VoiceInterface, VoiceConfig; ')
    print('    vi = VoiceInterface(VoiceConfig()); vi.listen_and_process()"')
    print("=" * 70)


if __name__ == "__main__":
    main()

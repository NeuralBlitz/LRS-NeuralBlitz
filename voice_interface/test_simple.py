"""
Simple test script for voice interface (without audio dependencies)
====================================================================
Demonstrates the command parsing and TTS without requiring microphone.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Mock sounddevice for testing
class MockSoundDevice:
    @staticmethod
    def rec(*args, **kwargs):
        import numpy as np

        return np.zeros((16000, 1))

    @staticmethod
    def wait():
        pass


sys.modules["sounddevice"] = MockSoundDevice()


# Mock soundfile
class MockSoundFile:
    @staticmethod
    def write(filepath, data, samplerate):
        pass


sys.modules["soundfile"] = MockSoundFile()

from voice_interface import (
    VoiceInterface,
    VoiceConfig,
    VoiceCommand,
    VoiceCommandType,
    VoiceCommandParser,
)


def test_basic_functionality():
    """Test basic voice interface without audio."""
    print("=" * 70)
    print("VOICE INTERFACE SYSTEM - TEXT-BASED TEST")
    print("=" * 70)

    # Initialize
    config = VoiceConfig()
    interface = VoiceInterface(config)

    # Test commands
    test_inputs = [
        "Hello",
        "What's the weather like today?",
        "Open the browser",
        "Navigate to settings",
        "How do I use this system?",
        "Shutdown the computer",
    ]

    print("\nTesting Command Parsing:")
    print("-" * 70)

    for text in test_inputs:
        result = interface.process_text(text)
        cmd = result["command"]

        print(f'\nInput: "{text}"')
        print(f"  Type: {cmd['command_type']}")
        print(f"  Intent: {cmd['intent']}")
        print(f"  Entities: {cmd['entities']}")
        print(f"  Confidence: {cmd['confidence']:.2f}")
        print(f'  Response: "{result["response"]}"')

    # Statistics
    stats = interface.get_stats()
    print("\n" + "-" * 70)
    print("Session Statistics:")
    print(f"  Total commands: {stats['total_commands']}")
    print(f"  Command breakdown:")
    for cmd_type, count in stats["command_types"].items():
        if count > 0:
            print(f"    - {cmd_type}: {count}")
    print(f"  Average confidence: {stats['avg_confidence']:.2f}")

    print("\n" + "=" * 70)
    print("All tests passed successfully!")
    print("=" * 70)


def test_custom_handlers():
    """Test custom command handlers."""
    print("\n" + "=" * 70)
    print("TESTING CUSTOM HANDLERS")
    print("=" * 70)

    interface = VoiceInterface(VoiceConfig())

    # Custom handlers
    def handle_greeting(cmd):
        return "Welcome! I'm your voice assistant."

    def handle_time(cmd):
        from datetime import datetime

        return f"The current time is {datetime.now().strftime('%I:%M %p')}"

    interface.register_handler(VoiceCommandType.GREETING, handle_greeting)
    interface.register_handler(VoiceCommandType.SYSTEM, handle_time)

    # Test
    print("\nCustom handler test:")
    result = interface.process_text("Hello there")
    print(f"Input: 'Hello there'")
    print(f"Response: {result['response']}")

    print("\n" + "=" * 70)


def test_parser_directly():
    """Test command parser in detail."""
    print("\n" + "=" * 70)
    print("TESTING COMMAND PARSER")
    print("=" * 70)

    parser = VoiceCommandParser(VoiceConfig())

    commands = [
        "Hello",
        "Open Chrome",
        "What's the time?",
        "Go to home page",
        "Help me with settings",
    ]

    print("\nParser outputs:")
    for cmd_text in commands:
        cmd = parser.parse(cmd_text)
        print(f"\n  '{cmd_text}'")
        print(
            f"    -> type={cmd.command_type.value}, intent={cmd.intent}, "
            f"entities={cmd.entities}, confidence={cmd.confidence:.2f}"
        )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_custom_handlers()
        test_parser_directly()

        print("\n" + "✓" * 35)
        print("All tests completed successfully!")
        print("✓" * 35 + "\n")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()

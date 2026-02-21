"""
Voice Interface System using OpenAI Whisper
============================================
A comprehensive voice interface with speech-to-text, command parsing, and text-to-speech.
"""

import os
import json
import time
import tempfile
import wave
import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

# Audio processing
import numpy as np
import sounddevice as sd
import soundfile as sf

# OpenAI integration
import openai
from openai import OpenAI

# Text-to-speech
import pyttsx3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceCommandType(Enum):
    """Types of voice commands supported."""

    GREETING = "greeting"
    QUESTION = "question"
    ACTION = "action"
    NAVIGATION = "navigation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class VoiceCommand:
    """Parsed voice command structure."""

    raw_text: str
    command_type: VoiceCommandType
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "raw_text": self.raw_text,
            "command_type": self.command_type.value,
            "intent": self.intent,
            "entities": self.entities,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class VoiceConfig:
    """Configuration for voice interface."""

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "float32"
    recording_duration: int = 5  # seconds

    # Whisper settings
    whisper_model: str = "whisper-1"
    language: str = "en"

    # TTS settings
    tts_engine: str = "pyttsx3"  # or "openai"
    tts_voice: str = "default"
    tts_rate: int = 150

    # OpenAI settings
    openai_api_key: Optional[str] = None

    # Command parsing
    min_confidence: float = 0.6

    def __post_init__(self):
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")


class SpeechToText:
    """Speech-to-Text using OpenAI Whisper."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.recording = False
        self.audio_data = []

    def record_audio(self, duration: Optional[int] = None) -> np.ndarray:
        """Record audio from microphone."""
        duration = duration or self.config.recording_duration

        logger.info(f"Recording for {duration} seconds...")

        # Record audio
        audio = sd.rec(
            int(duration * self.config.sample_rate),
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
        )
        sd.wait()

        logger.info("Recording complete")
        return audio

    def save_audio(self, audio: np.ndarray, filepath: str) -> str:
        """Save audio to file."""
        sf.write(filepath, audio, self.config.sample_rate)
        return filepath

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio using OpenAI Whisper."""
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.config.whisper_model,
                    file=audio_file,
                    language=self.config.language,
                )
            return response.text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def transcribe_buffer(self, audio: np.ndarray) -> str:
        """Transcribe audio buffer directly."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            self.save_audio(audio, tmp.name)
            result = self.transcribe(tmp.name)
            os.unlink(tmp.name)
        return result

    async def transcribe_stream(self, audio_stream) -> str:
        """Transcribe streaming audio (async)."""
        chunks = []
        async for chunk in audio_stream:
            chunks.append(chunk)

        audio = np.concatenate(chunks)
        return self.transcribe_buffer(audio)


class VoiceCommandParser:
    """Parse voice commands into structured intents."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)

        # Command patterns
        self.command_patterns = {
            VoiceCommandType.GREETING: [
                "hello",
                "hi",
                "hey",
                "good morning",
                "good afternoon",
                "good evening",
            ],
            VoiceCommandType.ACTION: [
                "open",
                "close",
                "start",
                "stop",
                "play",
                "pause",
                "create",
                "delete",
            ],
            VoiceCommandType.NAVIGATION: [
                "go to",
                "navigate",
                "show me",
                "take me",
                "find",
            ],
            VoiceCommandType.SYSTEM: [
                "shutdown",
                "restart",
                "settings",
                "configure",
                "help",
            ],
            VoiceCommandType.QUESTION: [
                "what",
                "how",
                "why",
                "when",
                "where",
                "who",
                "is",
                "are",
                "can",
                "do",
            ],
        }

    def parse(self, text: str) -> VoiceCommand:
        """Parse transcribed text into structured command."""
        text_lower = text.lower().strip()

        # Determine command type
        command_type = self._detect_command_type(text_lower)

        # Extract intent and entities
        intent, entities = self._extract_intent(text_lower)

        # Calculate confidence
        confidence = self._calculate_confidence(text, command_type, intent)

        return VoiceCommand(
            raw_text=text,
            command_type=command_type,
            intent=intent,
            entities=entities,
            confidence=confidence,
        )

    def parse_with_llm(self, text: str) -> VoiceCommand:
        """Parse command using OpenAI LLM for complex understanding."""
        try:
            prompt = f"""
            Parse this voice command into structured format:
            Command: "{text}"
            
            Return JSON with:
            - command_type: (greeting, question, action, navigation, system, unknown)
            - intent: brief description of what user wants
            - entities: key entities mentioned (objects, locations, actions)
            
            JSON response:"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You parse voice commands into structured data.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=200,
            )

            result = json.loads(response.choices[0].message.content)

            return VoiceCommand(
                raw_text=text,
                command_type=VoiceCommandType(result.get("command_type", "unknown")),
                intent=result.get("intent", "unknown"),
                entities=result.get("entities", {}),
                confidence=0.85,
            )

        except Exception as e:
            logger.error(f"LLM parsing error: {e}")
            return self.parse(text)  # Fallback to rule-based

    def _detect_command_type(self, text: str) -> VoiceCommandType:
        """Detect command type from keywords."""
        for cmd_type, keywords in self.command_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    return cmd_type
        return VoiceCommandType.UNKNOWN

    def _extract_intent(self, text: str) -> tuple:
        """Extract intent and entities from text."""
        # Simple rule-based extraction
        words = text.split()

        # Extract action verbs
        action_verbs = [
            "open",
            "close",
            "start",
            "stop",
            "play",
            "create",
            "find",
            "show",
        ]
        intent = "unknown"
        entities = {}

        for i, word in enumerate(words):
            if word in action_verbs:
                intent = word
                # Look for object after action
                if i + 1 < len(words):
                    entities["object"] = words[i + 1]
                break

        # Extract locations
        location_keywords = ["to", "in", "at"]
        for i, word in enumerate(words):
            if word in location_keywords and i + 1 < len(words):
                entities["location"] = words[i + 1]

        return intent, entities

    def _calculate_confidence(
        self, text: str, cmd_type: VoiceCommandType, intent: str
    ) -> float:
        """Calculate confidence score for parsing."""
        confidence = 0.5

        # Boost confidence based on command type detection
        if cmd_type != VoiceCommandType.UNKNOWN:
            confidence += 0.2

        # Boost based on intent extraction
        if intent != "unknown":
            confidence += 0.2

        # Boost based on text length (longer = more context)
        if len(text.split()) > 3:
            confidence += 0.1

        return min(confidence, 1.0)


class TextToSpeech:
    """Text-to-Speech synthesis."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.engine = None
        self.client = OpenAI(api_key=config.openai_api_key)

        if config.tts_engine == "pyttsx3":
            self._init_pyttsx3()

    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", self.config.tts_rate)

            # List available voices
            voices = self.engine.getProperty("voices")
            if voices and len(voices) > 0:
                self.engine.setProperty("voice", voices[0].id)
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            self.engine = None

    def speak(self, text: str, block: bool = True) -> None:
        """Speak text using configured TTS engine."""
        if self.config.tts_engine == "pyttsx3" and self.engine:
            self._speak_pyttsx3(text, block)
        elif self.config.tts_engine == "openai":
            self._speak_openai(text)
        else:
            logger.info(f"TTS: {text}")

    def _speak_pyttsx3(self, text: str, block: bool = True):
        """Speak using pyttsx3."""
        if self.engine:
            self.engine.say(text)
            if block:
                self.engine.runAndWait()

    def _speak_openai(self, text: str):
        """Speak using OpenAI TTS."""
        try:
            response = self.client.audio.speech.create(
                model="tts-1", voice="alloy", input=text
            )

            # Save and play
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                response.stream_to_file(tmp.name)
                os.system(f"mpg321 {tmp.name}")  # or use pydub
                os.unlink(tmp.name)
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")

    def save_to_file(self, text: str, filepath: str) -> str:
        """Save speech to audio file."""
        if self.config.tts_engine == "pyttsx3" and self.engine:
            self.engine.save_to_file(text, filepath)
            self.engine.runAndWait()
            return filepath
        elif self.config.tts_engine == "openai":
            try:
                response = self.client.audio.speech.create(
                    model="tts-1", voice="alloy", input=text
                )
                response.stream_to_file(filepath)
                return filepath
            except Exception as e:
                logger.error(f"OpenAI TTS save error: {e}")
        return ""


class VoiceInterface:
    """Main voice interface combining STT, command parsing, and TTS."""

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()

        # Initialize components
        self.stt = SpeechToText(self.config)
        self.parser = VoiceCommandParser(self.config)
        self.tts = TextToSpeech(self.config)

        # Command handlers
        self.handlers: Dict[VoiceCommandType, Callable] = {}
        self.default_handler: Optional[Callable] = None

        # State
        self.is_listening = False
        self.conversation_history: List[VoiceCommand] = []

    def register_handler(self, command_type: VoiceCommandType, handler: Callable):
        """Register a handler for specific command type."""
        self.handlers[command_type] = handler

    def register_default_handler(self, handler: Callable):
        """Register default handler for unknown commands."""
        self.default_handler = handler

    def listen_and_process(self, duration: Optional[int] = None) -> Dict:
        """Record audio, transcribe, parse, and respond."""
        # Record
        audio = self.stt.record_audio(duration)

        # Transcribe
        text = self.stt.transcribe_buffer(audio)
        logger.info(f"Transcribed: {text}")

        if not text:
            return {"success": False, "error": "No speech detected"}

        # Parse command
        command = self.parser.parse_with_llm(text)
        self.conversation_history.append(command)

        # Generate response
        response = self._generate_response(command)

        # Speak response
        self.tts.speak(response)

        return {
            "success": True,
            "command": command.to_dict(),
            "response": response,
            "transcribed_text": text,
        }

    def process_text(self, text: str) -> Dict:
        """Process text input directly (for testing)."""
        command = self.parser.parse_with_llm(text)
        self.conversation_history.append(command)

        response = self._generate_response(command)
        self.tts.speak(response)

        return {"success": True, "command": command.to_dict(), "response": response}

    def _generate_response(self, command: VoiceCommand) -> str:
        """Generate response based on command."""
        # Check if handler exists
        if command.command_type in self.handlers:
            try:
                return self.handlers[command.command_type](command)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        # Default responses
        responses = {
            VoiceCommandType.GREETING: f"Hello! How can I help you today?",
            VoiceCommandType.QUESTION: f"I'm looking into: {command.raw_text}",
            VoiceCommandType.ACTION: f"I'll {command.intent} that for you.",
            VoiceCommandType.NAVIGATION: f"Navigating to {command.entities.get('location', 'destination')}.",
            VoiceCommandType.SYSTEM: "System command acknowledged.",
            VoiceCommandType.UNKNOWN: f"I heard: {command.raw_text}. Can you rephrase that?",
        }

        return responses.get(
            command.command_type, "I'm not sure how to help with that."
        )

    def interactive_session(self):
        """Start interactive voice session."""
        print("🎤 Voice Interface Active")
        print("Commands: 'listen' to record, 'quit' to exit")

        self.tts.speak("Voice interface ready")

        while True:
            try:
                user_input = input("\n> ").strip().lower()

                if user_input == "quit":
                    self.tts.speak("Goodbye")
                    break
                elif user_input == "listen":
                    result = self.listen_and_process()
                    print(json.dumps(result, indent=2))
                elif user_input.startswith("say "):
                    text = user_input[4:]
                    self.tts.speak(text)
                else:
                    result = self.process_text(user_input)
                    print(json.dumps(result, indent=2))

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Session error: {e}")

    def get_stats(self) -> Dict:
        """Get interface statistics."""
        return {
            "total_commands": len(self.conversation_history),
            "command_types": {
                cmd_type.value: sum(
                    1 for c in self.conversation_history if c.command_type == cmd_type
                )
                for cmd_type in VoiceCommandType
            },
            "avg_confidence": sum(c.confidence for c in self.conversation_history)
            / max(len(self.conversation_history), 1),
        }


# Example command handlers
def handle_greeting(command: VoiceCommand) -> str:
    """Handle greeting commands."""
    greetings = [
        "Hello! How can I assist you?",
        "Hi there! What can I do for you?",
        "Hey! Ready to help.",
    ]
    import random

    return random.choice(greetings)


def handle_action(command: VoiceCommand) -> str:
    """Handle action commands."""
    action = command.intent
    obj = command.entities.get("object", "that")
    return f"I'll {action} the {obj} right away."


def handle_question(command: VoiceCommand) -> str:
    """Handle question commands."""
    return f"You asked: {command.raw_text}. Let me find that information for you."


# Example usage
if __name__ == "__main__":
    # Initialize
    config = VoiceConfig(recording_duration=5, tts_engine="pyttsx3")

    # Create interface
    interface = VoiceInterface(config)

    # Register custom handlers
    interface.register_handler(VoiceCommandType.GREETING, handle_greeting)
    interface.register_handler(VoiceCommandType.ACTION, handle_action)
    interface.register_handler(VoiceCommandType.QUESTION, handle_question)

    # Start interactive session
    interface.interactive_session()

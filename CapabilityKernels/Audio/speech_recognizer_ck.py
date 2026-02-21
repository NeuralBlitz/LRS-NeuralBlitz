#!/usr/bin/env python3
"""
Audio/SpeechRecognizer Capability Kernel v1.0.0
NeuralBlitz Σ-SOI Audio Processing Module

Speech-to-text transcription using OpenAI Whisper with ethical content filtering,
PII detection/redaction, and NeuralBlitz governance integration.

Author: NeuralBlitz Architect
Version: 1.0.0
License: NeuralBlitz Charter ϕ₁–ϕ₁₅
"""

import base64
import hashlib
import json
import logging
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CKRequest:
    """Standard CK request envelope following NeuralBlitz CK contract"""

    kernel: str
    version: str
    intent: str
    request_id: str
    payload: Dict[str, Any]
    provenance: Dict[str, str]
    bounds: Dict[str, Any]
    governance: Dict[str, bool]
    telemetry: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CKRequest":
        return cls(
            kernel=data["kernel"],
            version=data["version"],
            intent=data["intent"],
            request_id=data.get("request_id", str(uuid.uuid4())),
            payload=data["payload"],
            provenance=data["provenance"],
            bounds=data["bounds"],
            governance=data["governance"],
            telemetry=data["telemetry"],
        )


@dataclass
class ContentFlags:
    """Content analysis flags for ethical review"""

    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    sensitive_content: bool = False
    redacted_segments: List[int] = field(default_factory=list)


@dataclass
class TranscriptionSegment:
    """A single transcription segment with timing and confidence"""

    id: int
    start: float
    end: float
    text: str
    words: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class SpeechRecognizerOutput:
    """CK output following NeuralBlitz contract schema"""

    transcription: str
    segments: List[TranscriptionSegment]
    language: str
    duration: float
    confidence_score: float
    content_flags: ContentFlags
    nbhs512_seal: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcription": self.transcription,
            "segments": [
                {
                    "id": seg.id,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "words": seg.words,
                    "confidence": seg.confidence,
                }
                for seg in self.segments
            ],
            "language": self.language,
            "duration": self.duration,
            "confidence_score": self.confidence_score,
            "content_flags": {
                "pii_detected": self.content_flags.pii_detected,
                "pii_types": self.content_flags.pii_types,
                "sensitive_content": self.content_flags.sensitive_content,
                "redacted_segments": self.content_flags.redacted_segments,
            },
            "nbhs512_seal": self.nbhs512_seal,
        }


class WhisperEngine:
    """
    Mock Whisper engine for demonstration.
    In production, this wraps OpenAI Whisper or faster-whisper.
    """

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.available_models = ["tiny", "base", "small", "medium", "large"]
        logger.info(f"Initialized WhisperEngine with model size: {model_size}")

    def transcribe(
        self,
        audio_path: str,
        language: str = "auto",
        task: str = "transcribe",
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file
            language: Language code (auto for detection)
            task: transcribe or translate
            temperature: Sampling temperature

        Returns:
            Dictionary with transcription results
        """
        # Mock transcription for demonstration
        # In production: result = model.transcribe(audio_path, ...)

        duration = 15.5  # Mock duration

        # Simulate segments
        segments = [
            {
                "id": 0,
                "start": 0.0,
                "end": 5.2,
                "text": "Hello, this is a demonstration of the NeuralBlitz speech recognition system.",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.98},
                    {"word": "this", "start": 0.6, "end": 0.9, "probability": 0.95},
                    {"word": "is", "start": 0.9, "end": 1.0, "probability": 0.99},
                    {"word": "a", "start": 1.1, "end": 1.2, "probability": 0.97},
                    {
                        "word": "demonstration",
                        "start": 1.3,
                        "end": 2.1,
                        "probability": 0.92,
                    },
                    {"word": "of", "start": 2.2, "end": 2.4, "probability": 0.96},
                    {"word": "the", "start": 2.5, "end": 2.7, "probability": 0.98},
                    {
                        "word": "NeuralBlitz",
                        "start": 2.8,
                        "end": 3.4,
                        "probability": 0.88,
                    },
                    {"word": "speech", "start": 3.5, "end": 3.9, "probability": 0.94},
                    {
                        "word": "recognition",
                        "start": 4.0,
                        "end": 4.6,
                        "probability": 0.91,
                    },
                    {"word": "system", "start": 4.7, "end": 5.2, "probability": 0.97},
                ],
            },
            {
                "id": 1,
                "start": 5.3,
                "end": 10.8,
                "text": "My phone number is 555-0123 and email is test@example.com for contact.",
                "words": [
                    {"word": "My", "start": 5.3, "end": 5.5, "probability": 0.97},
                    {"word": "phone", "start": 5.6, "end": 5.9, "probability": 0.95},
                    {"word": "number", "start": 6.0, "end": 6.4, "probability": 0.93},
                    {"word": "is", "start": 6.5, "end": 6.7, "probability": 0.98},
                    {"word": "555-0123", "start": 6.8, "end": 7.5, "probability": 0.89},
                    {"word": "and", "start": 7.6, "end": 7.8, "probability": 0.96},
                    {"word": "email", "start": 7.9, "end": 8.2, "probability": 0.94},
                    {"word": "is", "start": 8.3, "end": 8.5, "probability": 0.99},
                    {
                        "word": "test@example.com",
                        "start": 8.6,
                        "end": 9.4,
                        "probability": 0.87,
                    },
                    {"word": "for", "start": 9.5, "end": 9.7, "probability": 0.95},
                    {"word": "contact", "start": 9.8, "end": 10.8, "probability": 0.92},
                ],
            },
            {
                "id": 2,
                "start": 10.9,
                "end": 15.5,
                "text": "The system demonstrates high accuracy and ethical content filtering capabilities.",
                "words": [
                    {"word": "The", "start": 10.9, "end": 11.1, "probability": 0.96},
                    {"word": "system", "start": 11.2, "end": 11.7, "probability": 0.94},
                    {
                        "word": "demonstrates",
                        "start": 11.8,
                        "end": 12.5,
                        "probability": 0.90,
                    },
                    {"word": "high", "start": 12.6, "end": 12.9, "probability": 0.93},
                    {
                        "word": "accuracy",
                        "start": 13.0,
                        "end": 13.6,
                        "probability": 0.91,
                    },
                    {"word": "and", "start": 13.7, "end": 13.9, "probability": 0.97},
                    {
                        "word": "ethical",
                        "start": 14.0,
                        "end": 14.5,
                        "probability": 0.88,
                    },
                    {
                        "word": "content",
                        "start": 14.6,
                        "end": 15.0,
                        "probability": 0.92,
                    },
                    {
                        "word": "filtering",
                        "start": 15.1,
                        "end": 15.5,
                        "probability": 0.89,
                    },
                ],
            },
        ]

        return {
            "text": " ".join([seg["text"] for seg in segments]),
            "segments": segments,
            "language": "en",
            "duration": duration,
        }


class PIIDetector:
    """
    PII (Personally Identifiable Information) detector for ethical content filtering.
    Implements regex-based and heuristic PII detection.
    """

    PII_PATTERNS = {
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
        "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    }

    def detect(self, text: str) -> Tuple[bool, List[str], str]:
        """
        Detect PII in text.

        Returns:
            Tuple of (pii_detected, pii_types, redacted_text)
        """
        pii_detected = False
        pii_types = []
        redacted_text = text

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                pii_detected = True
                if pii_type not in pii_types:
                    pii_types.append(pii_type)
                # Redact with placeholder
                redacted_text = pattern.sub(
                    f"[{pii_type.upper()}_REDACTED]", redacted_text
                )

        return pii_detected, pii_types, redacted_text


class SpeechRecognizerCK:
    """
    Audio/SpeechRecognizer Capability Kernel

    Converts speech to text with ethical content filtering,
    PII redaction, and NeuralBlitz governance compliance.
    """

    KERNEL_NAME = "Audio/SpeechRecognizer"
    VERSION = "1.0.0"
    INTENT = "Convert audio speech to text with ethical content awareness and privacy protection"

    def __init__(self):
        self.whisper_engine: Optional[WhisperEngine] = None
        self.pii_detector = PIIDetector()
        logger.info(f"Initialized {self.KERNEL_NAME} v{self.VERSION}")

    def _validate_request(self, request: CKRequest) -> bool:
        """Validate CK request against contract"""
        if request.kernel != self.KERNEL_NAME:
            raise ValueError(f"Invalid kernel: {request.kernel}")
        if request.governance.get("cect", False) and not self._check_cect_compliance():
            raise RuntimeError("CECT compliance check failed")
        return True

    def _check_cect_compliance(self) -> bool:
        """Check Charter-Ethical Constraint Tensor compliance"""
        # Mock CECT check - in production, queries Conscientia++
        return True

    def _compute_nbhs512_seal(self, data: Dict[str, Any]) -> str:
        """
        Compute NBHS-512 seal for output provenance.
        Simplified version for demonstration.
        """
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
        # First SHA-256 hash
        hash1 = hashlib.sha256(canonical.encode()).digest()
        # Second round for 512-bit (simplified)
        hash2 = hashlib.sha256(hash1).digest()
        # Combine for 512 bits
        combined = hash1 + hash2
        return combined.hex()

    def _redact_segments(
        self, segments: List[Dict[str, Any]], pii_detector: PIIDetector
    ) -> Tuple[List[Dict[str, Any]], ContentFlags]:
        """Redact PII from transcription segments"""
        redacted_segments = []
        content_flags = ContentFlags()
        redacted_ids = []

        for seg in segments:
            seg_text = seg["text"]
            pii_found, pii_types, redacted_text = pii_detector.detect(seg_text)

            if pii_found:
                content_flags.pii_detected = True
                content_flags.pii_types.extend(
                    [t for t in pii_types if t not in content_flags.pii_types]
                )
                redacted_ids.append(seg["id"])

            # Redact words if they contain PII
            redacted_words = []
            for word in seg.get("words", []):
                word_pii, _, word_redacted = pii_detector.detect(word["word"])
                if word_pii:
                    redacted_words.append(
                        {**word, "word": word_redacted, "redacted": True}
                    )
                else:
                    redacted_words.append(word)

            redacted_segments.append(
                {**seg, "text": redacted_text, "words": redacted_words}
            )

        content_flags.redacted_segments = redacted_ids
        return redacted_segments, content_flags

    def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute speech recognition with full governance.

        Args:
            request_data: CK request following contract schema

        Returns:
            CK output with transcription, content flags, and NBHS-512 seal
        """
        request = CKRequest.from_dict(request_data)

        # Validate request
        self._validate_request(request)

        # Extract parameters
        payload = request.payload
        audio_data = payload.get("audio_data")
        audio_cid = payload.get("audio_cid")
        language = payload.get("language", "auto")
        model_size = payload.get("model_size", "base")
        task = payload.get("task", "transcribe")
        temperature = payload.get("temperature", 0.0)
        pii_redaction = payload.get("pii_redaction", True)

        logger.info(f"Processing speech recognition request {request.request_id}")
        logger.info(f"Language: {language}, Model: {model_size}, Task: {task}")

        # Initialize engine if needed
        if self.whisper_engine is None or self.whisper_engine.model_size != model_size:
            self.whisper_engine = WhisperEngine(model_size)

        # Process audio (mock path handling)
        audio_path = self._get_audio_path(audio_data, audio_cid)

        # Transcribe
        result = self.whisper_engine.transcribe(
            audio_path=audio_path, language=language, task=task, temperature=temperature
        )

        # Apply PII redaction if enabled
        if pii_redaction:
            segments, content_flags = self._redact_segments(
                result["segments"], self.pii_detector
            )
        else:
            segments = result["segments"]
            content_flags = ContentFlags()

        # Calculate confidence score
        all_confidences = []
        for seg in segments:
            for word in seg.get("words", []):
                all_confidences.append(word.get("probability", 0.0))
        confidence_score = np.mean(all_confidences) if all_confidences else 0.0

        # Build output
        output = SpeechRecognizerOutput(
            transcription=" ".join([seg["text"] for seg in segments]),
            segments=[
                TranscriptionSegment(
                    id=seg["id"],
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"],
                    words=seg.get("words", []),
                    confidence=np.mean(
                        [w.get("probability", 0.0) for w in seg.get("words", [])]
                    )
                    if seg.get("words")
                    else 0.0,
                )
                for seg in segments
            ],
            language=result["language"],
            duration=result["duration"],
            confidence_score=float(confidence_score),
            content_flags=content_flags,
            nbhs512_seal="",  # Will be computed after building dict
        )

        # Compute seal
        output_dict = output.to_dict()
        output.nbhs512_seal = self._compute_nbhs512_seal(output_dict)
        output_dict["nbhs512_seal"] = output.nbhs512_seal

        logger.info(f"Speech recognition complete. Confidence: {confidence_score:.2%}")
        logger.info(
            f"PII detected: {content_flags.pii_detected}, Types: {content_flags.pii_types}"
        )

        return output_dict

    def _get_audio_path(
        self, audio_data: Optional[str], audio_cid: Optional[str]
    ) -> str:
        """Resolve audio source to file path"""
        if audio_data:
            # Decode base64 and save to temp file
            audio_bytes = base64.b64decode(audio_data)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                return f.name
        elif audio_cid:
            # In production: resolve CID from Scriptorium
            return f"/tmp/{audio_cid}.wav"
        else:
            raise ValueError("Either audio_data or audio_cid must be provided")


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("Audio/SpeechRecognizer CK v1.0.0 - Demonstration")
    print("=" * 80)

    # Initialize CK
    ck = SpeechRecognizerCK()

    # Example request following NeuralBlitz contract
    example_request = {
        "kernel": "Audio/SpeechRecognizer",
        "version": "1.0.0",
        "intent": "Convert audio speech to text with ethical content awareness and privacy protection",
        "request_id": "req-speech-001",
        "payload": {
            "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",  # Minimal WAV header
            "language": "en",
            "model_size": "base",
            "task": "transcribe",
            "temperature": 0.0,
            "pii_redaction": True,
            "content_filter_level": "moderate",
        },
        "provenance": {
            "caller_principal_id": "Principal/Operator#123",
            "caller_dag_ref": "a1b2c3d4e5f6" * 8,
        },
        "bounds": {
            "entropy_max": 0.15,
            "time_ms_max": 300000,
            "scope": "AudioProcessing.Speech",
        },
        "governance": {
            "rcf": True,
            "cect": True,
            "veritas_watch": True,
            "judex_quorum": False,
        },
        "telemetry": {
            "explain_vector": True,
            "dag_attach": True,
            "trace_id": "trace-speech-001",
        },
    }

    print("\nExample CK Request:")
    print(json.dumps(example_request, indent=2))

    print("\nExecuting Speech Recognition...")
    result = ck.execute(example_request)

    print("\n" + "=" * 80)
    print("CK Output:")
    print("=" * 80)
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  - Transcription: {result['transcription'][:80]}...")
    print(f"  - Language: {result['language']}")
    print(f"  - Duration: {result['duration']:.1f}s")
    print(f"  - Confidence: {result['confidence_score']:.2%}")
    print(f"  - PII Detected: {result['content_flags']['pii_detected']}")
    print(f"  - PII Types: {result['content_flags']['pii_types']}")
    print(f"  - NBHS-512 Seal: {result['nbhs512_seal'][:16]}...")
    print("=" * 80)

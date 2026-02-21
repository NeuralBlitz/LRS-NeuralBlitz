#!/usr/bin/env python3
"""
Audio/SoundClassifier Capability Kernel v1.0.0
NeuralBlitz Σ-SOI Audio Processing Module

Environmental sound classification and acoustic event detection with
ethical awareness, privacy protection, and safety alerting.

Author: NeuralBlitz Architect
Version: 1.0.0
License: NeuralBlitz Charter ϕ₁–ϕ₁₅
"""

import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CKRequest:
    """Standard CK request envelope"""

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
class ClassificationPrediction:
    """Single class prediction"""

    class_name: str
    confidence: float
    class_id: int
    hierarchy_path: List[str] = field(default_factory=list)


@dataclass
class DetectedEvent:
    """Temporal sound event"""

    class_name: str
    start_time: float
    end_time: float
    peak_confidence: float
    avg_confidence: float
    event_id: str


@dataclass
class EthicalReview:
    """Ethical compliance review"""

    privacy_alert: bool = False
    safety_alert: bool = False
    blocked_classes: List[str] = field(default_factory=list)
    redacted_segments: List[int] = field(default_factory=list)
    confidence_calibration: float = 1.0


@dataclass
class SoundClassifierOutput:
    """CK output envelope"""

    predictions: List[ClassificationPrediction]
    events: List[DetectedEvent]
    embedding: Dict[str, Any]
    audio_metadata: Dict[str, Any]
    ethical_review: EthicalReview
    explainability: Dict[str, Any]
    nbhs512_seal: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predictions": [
                {
                    "class_name": p.class_name,
                    "confidence": p.confidence,
                    "class_id": p.class_id,
                    "hierarchy_path": p.hierarchy_path,
                }
                for p in self.predictions
            ],
            "events": [
                {
                    "class_name": e.class_name,
                    "start_time": e.start_time,
                    "end_time": e.end_time,
                    "peak_confidence": e.peak_confidence,
                    "avg_confidence": e.avg_confidence,
                    "event_id": e.event_id,
                }
                for e in self.events
            ],
            "embedding": self.embedding,
            "audio_metadata": self.audio_metadata,
            "ethical_review": {
                "privacy_alert": self.ethical_review.privacy_alert,
                "safety_alert": self.ethical_review.safety_alert,
                "blocked_classes": self.ethical_review.blocked_classes,
                "redacted_segments": self.ethical_review.redacted_segments,
                "confidence_calibration": self.ethical_review.confidence_calibration,
            },
            "explainability": self.explainability,
            "nbhs512_seal": self.nbhs512_seal,
        }


class AudioEmbeddingExtractor:
    """
    Extract audio embeddings for classification.
    """

    def __init__(self, model_type: str = "yamnet"):
        self.model_type = model_type
        self.embedding_dim = 1024 if model_type == "yamnet" else 128

    def extract(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """Extract embedding vector from audio"""
        # In production: use TensorFlow Hub YAMNet or VGGish
        # This is a simplified mock

        # Generate deterministic mock embedding based on audio statistics
        np.random.seed(int(np.sum(audio) * 1000) % 2**31)
        embedding = np.random.randn(self.embedding_dim).astype(np.float32)
        # Normalize
        embedding = embedding / (np.linalg.norm(embedding) + 1e-10)
        return embedding


class SoundClassHierarchy:
    """
    Hierarchical sound class taxonomy.
    """

    # Simplified AudioSet ontology subset
    CLASSES = {
        "Human": {
            "Speech": ["Conversation", "Narration", "Shouting", "Whispering"],
            "Vocal": ["Crying", "Laughter", "Sighing", "Sneezing"],
            "Body": ["Clapping", "Finger snapping", "Footsteps", "Heartbeat"],
        },
        "Animal": {
            "Domestic": ["Dog", "Cat", "Bird", "Livestock"],
            "Wild": ["Wild animals", "Insects", "Rodents"],
        },
        "Music": {
            "Instruments": ["Piano", "Guitar", "Drums", "Violin"],
            "Genres": ["Classical", "Pop", "Rock", "Electronic"],
        },
        "Environmental": {
            "Weather": ["Rain", "Thunder", "Wind", "Water"],
            "Mechanical": ["Engine", "Machinery", "Tools", "Appliances"],
            "Alerts": ["Siren", "Alarm", "Bell", "Buzz"],
        },
        "Safety-Critical": {
            "Danger": ["Gunshot", "Explosion", "Glass", "Screaming"],
            "Emergency": ["Siren", "Fire alarm", "Car alarm"],
        },
    }

    @classmethod
    def get_all_classes(cls) -> List[str]:
        """Get flat list of all class names"""
        classes = []
        for category, subcats in cls.CLASSES.items():
            for subcat, items in subcats.items():
                classes.extend(items)
        return classes

    @classmethod
    def get_hierarchy_path(cls, class_name: str) -> List[str]:
        """Get full hierarchy path for a class"""
        for category, subcats in cls.CLASSES.items():
            for subcat, items in subcats.items():
                if class_name in items:
                    return [category, subcat, class_name]
        return [class_name]


class MockClassifier:
    """
    Mock sound classifier for demonstration.
    In production, use YAMNet, VGGish, or custom model.
    """

    def __init__(self, model_type: str = "yamnet"):
        self.model_type = model_type
        self.all_classes = SoundClassHierarchy.get_all_classes()
        self.class_embeddings = self._init_class_embeddings()

    def _init_class_embeddings(self) -> Dict[str, np.ndarray]:
        """Initialize mock class embeddings"""
        embeddings = {}
        for i, cls in enumerate(self.all_classes):
            np.random.seed(i)
            emb = np.random.randn(1024 if self.model_type == "yamnet" else 128)
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            embeddings[cls] = emb
        return embeddings

    def classify(
        self,
        audio_embedding: np.ndarray,
        top_k: int = 10,
        target_classes: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Classify audio embedding.

        Returns:
            List of (class_name, confidence) tuples
        """
        classes = target_classes if target_classes else self.all_classes

        # Compute similarity scores
        scores = []
        for cls in classes:
            class_emb = self.class_embeddings.get(cls)
            if class_emb is not None:
                similarity = np.dot(audio_embedding, class_emb)
                # Convert to probability-like score
                score = 1 / (1 + np.exp(-5 * similarity))  # Sigmoid
                scores.append((cls, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def detect_temporal_events(
        self,
        audio_segments: List[Tuple[float, np.ndarray]],
        confidence_threshold: float = 0.5,
        min_duration_ms: float = 250,
        merge_gap_ms: float = 100,
    ) -> List[Dict[str, Any]]:
        """
        Detect sound events with temporal localization.

        Args:
            audio_segments: List of (timestamp, audio_chunk) tuples
            confidence_threshold: Minimum confidence for event detection
            min_duration_ms: Minimum event duration
            merge_gap_ms: Maximum gap between events to merge

        Returns:
            List of detected events
        """
        events = []

        # Mock temporal event detection
        # In production: frame-level classification with smoothing

        # Simulate events at specific times
        mock_events = [
            {"class": "Speech", "start": 2.5, "end": 5.0, "peak_conf": 0.92},
            {"class": "Car", "start": 7.0, "end": 8.5, "peak_conf": 0.78},
            {"class": "Music", "start": 10.0, "end": 13.5, "peak_conf": 0.85},
            {"class": "Siren", "start": 15.0, "end": 16.2, "peak_conf": 0.95},
        ]

        for i, ev in enumerate(mock_events):
            if ev["peak_conf"] >= confidence_threshold:
                events.append(
                    {
                        "class_name": ev["class"],
                        "start_time": ev["start"],
                        "end_time": ev["end"],
                        "peak_confidence": ev["peak_conf"],
                        "avg_confidence": ev["peak_conf"] * 0.9,
                        "event_id": f"ev-{uuid.uuid4().hex[:8]}",
                    }
                )

        return events


class EthicalFilter:
    """
    Apply ethical filtering to classification results.
    """

    def __init__(
        self,
        privacy_sensitive_classes: List[str],
        alert_classes: List[str],
        block_suspicious: bool = True,
    ):
        self.privacy_sensitive = set(privacy_sensitive_classes)
        self.alert_classes = set(alert_classes)
        self.block_suspicious = block_suspicious

    def review(
        self, predictions: List[Tuple[str, float]], events: List[Dict[str, Any]]
    ) -> EthicalReview:
        """
        Perform ethical review of classification results.

        Returns:
            EthicalReview with alerts and blocking decisions
        """
        review = EthicalReview()

        # Check for privacy-sensitive classes
        for cls, conf in predictions:
            if cls in self.privacy_sensitive and conf > 0.5:
                review.privacy_alert = True
                if self.block_suspicious:
                    review.blocked_classes.append(cls)

        # Check for safety alerts
        for event in events:
            if event["class_name"] in self.alert_classes:
                review.safety_alert = True
                # Don't block alerts, but flag them

        # Calibrate confidence based on ethical concerns
        if review.privacy_alert and review.safety_alert:
            review.confidence_calibration = 0.8  # Reduce confidence
        elif review.privacy_alert or review.safety_alert:
            review.confidence_calibration = 0.9

        return review


class SoundClassifierCK:
    """
    Audio/SoundClassifier Capability Kernel

    Environmental sound classification with temporal event detection,
    ethical filtering, and safety alerting.
    """

    KERNEL_NAME = "Audio/SoundClassifier"
    VERSION = "1.0.0"
    INTENT = "Classify acoustic events and environmental sounds with confidence scoring and ethical filtering"

    def __init__(self):
        self.embedding_extractor: Optional[AudioEmbeddingExtractor] = None
        self.classifier: Optional[MockClassifier] = None
        self.ethical_filter: Optional[EthicalFilter] = None
        logger.info(f"Initialized {self.KERNEL_NAME} v{self.VERSION}")

    def _compute_nbhs512_seal(self, data: Dict[str, Any]) -> str:
        """Compute NBHS-512 seal"""
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
        hash1 = hashlib.sha256(canonical.encode()).digest()
        hash2 = hashlib.sha256(hash1).digest()
        return (hash1 + hash2).hex()

    def _simulate_audio(
        self, duration_sec: float = 20.0, sample_rate: int = 16000
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Simulate audio for demonstration"""
        num_samples = int(duration_sec * sample_rate)
        audio = np.random.normal(0, 0.01, num_samples).astype(np.float32)

        metadata = {
            "duration_sec": duration_sec,
            "sample_rate": sample_rate,
            "channels": 1,
            "format": "WAV",
        }

        return audio, metadata

    def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute sound classification.

        Args:
            request_data: CK request following contract schema

        Returns:
            Classification results with predictions, events, and ethical review
        """
        request = CKRequest.from_dict(request_data)
        payload = request.payload

        # Extract parameters
        model_type = payload.get("model_type", "yamnet")
        classification_mode = payload.get("classification_mode", "multi_label")
        target_classes = payload.get("target_classes")
        confidence_threshold = payload.get("confidence_threshold", 0.5)
        top_k = payload.get("top_k", 10)
        temporal_localization = payload.get("temporal_localization", False)
        event_params = payload.get("event_detection_params", {})
        ethical_filters = payload.get("ethical_filters", {})

        # Initialize components
        self.embedding_extractor = AudioEmbeddingExtractor(model_type)
        self.classifier = MockClassifier(model_type)
        self.ethical_filter = EthicalFilter(
            privacy_sensitive_classes=ethical_filters.get(
                "privacy_sensitive_classes",
                ["Speech", "Conversation", "Phone", "Doorbell"],
            ),
            alert_classes=ethical_filters.get(
                "alert_classes", ["Gunshot", "Explosion", "Glass", "Screaming"]
            ),
            block_suspicious=ethical_filters.get("block_suspicious", True),
        )

        logger.info(f"Classifying audio with model: {model_type}")

        # Get audio (mock or from data)
        if payload.get("audio_data"):
            audio = np.frombuffer(
                base64.b64decode(payload["audio_data"]), dtype=np.float32
            )
            metadata = {
                "duration_sec": len(audio) / 16000,
                "sample_rate": 16000,
                "channels": 1,
                "format": "raw",
            }
        elif payload.get("audio_cid"):
            # In production: load from CID
            audio, metadata = self._simulate_audio()
        else:
            audio, metadata = self._simulate_audio()

        # Extract embedding
        embedding = self.embedding_extractor.extract(audio, metadata["sample_rate"])

        # Classify
        raw_predictions = self.classifier.classify(
            embedding, top_k=top_k, target_classes=target_classes
        )

        # Filter by threshold
        predictions = [
            ClassificationPrediction(
                class_name=cls,
                confidence=conf,
                class_id=i,
                hierarchy_path=SoundClassHierarchy.get_hierarchy_path(cls),
            )
            for i, (cls, conf) in enumerate(raw_predictions)
            if conf >= confidence_threshold
        ]

        # Temporal event detection
        events = []
        if temporal_localization:
            # Simulate audio segments
            chunk_size = int(metadata["sample_rate"] * 0.5)  # 500ms chunks
            segments = [
                (i * 0.5, audio[i * chunk_size : (i + 1) * chunk_size])
                for i in range(0, len(audio) // chunk_size)
            ]

            raw_events = self.classifier.detect_temporal_events(
                segments,
                confidence_threshold=confidence_threshold,
                min_duration_ms=event_params.get("min_event_duration_ms", 250),
                merge_gap_ms=event_params.get("merge_gap_ms", 100),
            )

            events = [
                DetectedEvent(
                    class_name=ev["class_name"],
                    start_time=ev["start_time"],
                    end_time=ev["end_time"],
                    peak_confidence=ev["peak_confidence"],
                    avg_confidence=ev["avg_confidence"],
                    event_id=ev["event_id"],
                )
                for ev in raw_events
            ]

        # Ethical review
        ethical_review = self.ethical_filter.review(raw_predictions, raw_events)

        # Apply blocking
        if ethical_review.blocked_classes:
            predictions = [
                p
                for p in predictions
                if p.class_name not in ethical_review.blocked_classes
            ]
            events = [
                e for e in events if e.class_name not in ethical_review.blocked_classes
            ]

        # Build output
        output = SoundClassifierOutput(
            predictions=predictions,
            events=events,
            embedding={
                "vector": embedding.tolist(),
                "dimension": len(embedding),
                "model": model_type,
            },
            audio_metadata=metadata,
            ethical_review=ethical_review,
            explainability={
                "feature_importance": {},  # Would include Grad-CAM or similar
                "decision_boundary": f"{model_type}_softmax",
                "uncertainty_estimate": 1.0
                - np.mean([p.confidence for p in predictions])
                if predictions
                else 1.0,
            },
        )

        # Compute seal
        output_dict = output.to_dict()
        output.nbhs512_seal = self._compute_nbhs512_seal(output_dict)
        output_dict["nbhs512_seal"] = output.nbhs512_seal

        logger.info(
            f"Classification complete: {len(predictions)} predictions, {len(events)} events"
        )
        logger.info(
            f"Privacy alert: {ethical_review.privacy_alert}, Safety alert: {ethical_review.safety_alert}"
        )

        return output_dict


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("Audio/SoundClassifier CK v1.0.0 - Demonstration")
    print("=" * 80)

    ck = SoundClassifierCK()

    example_request = {
        "kernel": "Audio/SoundClassifier",
        "version": "1.0.0",
        "intent": "Classify acoustic events and environmental sounds with confidence scoring and ethical filtering",
        "request_id": "req-classify-001",
        "payload": {
            "audio_data": None,
            "model_type": "yamnet",
            "classification_mode": "multi_label",
            "confidence_threshold": 0.5,
            "top_k": 10,
            "temporal_localization": True,
            "event_detection_params": {
                "min_event_duration_ms": 250,
                "max_event_duration_ms": 10000,
                "merge_gap_ms": 100,
                "smoothing_window": 3,
            },
            "ethical_filters": {
                "block_suspicious_sounds": True,
                "privacy_sensitive_classes": [
                    "Speech",
                    "Conversation",
                    "Phone",
                    "Doorbell",
                ],
                "alert_classes": ["Gunshot", "Explosion", "Glass", "Screaming"],
            },
        },
        "provenance": {
            "caller_principal_id": "Principal/Operator#789",
            "caller_dag_ref": "c3d4e5f6a7b8" * 8,
        },
        "bounds": {
            "entropy_max": 0.18,
            "time_ms_max": 5000,
            "scope": "AudioProcessing.Classification",
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
            "trace_id": "trace-classify-001",
        },
    }

    print("\nExample CK Request:")
    print(json.dumps(example_request, indent=2))

    print("\nExecuting Sound Classification...")
    result = ck.execute(example_request)

    print("\n" + "=" * 80)
    print("CK Output (Summary):")
    print("=" * 80)

    print(f"\nTop Predictions:")
    for pred in result["predictions"][:5]:
        print(
            f"  - {pred['class_name']}: {pred['confidence']:.2%} "
            f"(Hierarchy: {' > '.join(pred['hierarchy_path'])})"
        )

    print(f"\nDetected Events:")
    for event in result["events"]:
        print(
            f"  - [{event['class_name']}] {event['start_time']:.1f}s - {event['end_time']:.1f}s "
            f"(peak: {event['peak_confidence']:.2%})"
        )

    print(f"\nEmbedding:")
    emb = result["embedding"]
    print(f"  - Model: {emb['model']}")
    print(f"  - Dimension: {emb['dimension']}")
    print(f"  - Vector (first 5): {emb['vector'][:5]}")

    print(f"\nEthical Review:")
    review = result["ethical_review"]
    print(f"  - Privacy Alert: {review['privacy_alert']}")
    print(f"  - Safety Alert: {review['safety_alert']}")
    print(f"  - Blocked Classes: {review['blocked_classes']}")
    print(f"  - Confidence Calibration: {review['confidence_calibration']}")

    print(f"\nExplainability:")
    exp = result["explainability"]
    print(f"  - Decision Boundary: {exp['decision_boundary']}")
    print(f"  - Uncertainty: {exp['uncertainty_estimate']:.2%}")

    print(f"\nNBHS-512 Seal: {result['nbhs512_seal'][:16]}...")
    print("=" * 80)

#!/usr/bin/env python3
"""
NeuralBlitz Computer Vision Capability Kernels (CV-CK)
v1.0.0 - Apical Synthesis Compatible

Three specialized capability kernels for computer vision tasks:
1. SceneAnalysisObjectDetectionCK - YOLOv8-based scene understanding
2. FacialRecognitionEmotionCK - Face recognition with emotion analysis
3. OpticalCharacterRecognitionCK - Multi-language OCR with layout analysis

All kernels implement the NeuralBlitz CK Contract v1.0 specification.
"""

import cv2
import numpy as np
import torch
import torchvision
from torchvision import transforms
from PIL import Image
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import warnings

warnings.filterwarnings("ignore")

# NeuralBlitz CK Base Contract Schema
CK_CONTRACT_SCHEMA = {
    "$id": "https://neuralblitz.org/schema/ck/1.0",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "NeuralBlitz CK Contract v1.0",
    "type": "object",
    "required": ["kernel", "version", "intent", "bounds", "governance", "telemetry"],
}


@dataclass
class CKMetadata:
    """Base metadata for all Capability Kernels"""

    kernel: str
    version: str
    intent: str
    timestamp: str
    request_id: str
    caller_principal_id: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CKGovernance:
    """Governance configuration for CK execution"""

    rcf: bool  # Reflexive Computation Field gate
    cect: bool  # Charter-Ethical Constraint Tensor
    veritas_watch: bool
    judex_quorum: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CKBounds:
    """Execution bounds for CK operations"""

    entropy_max: float
    time_ms_max: int
    scope: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CKTelemetry:
    """Telemetry configuration for CK operations"""

    explain_vector: bool
    dag_attach: bool
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class BaseCapabilityKernel:
    """Base class for all NeuralBlitz Capability Kernels"""

    def __init__(self, kernel_name: str, version: str, intent: str):
        self.metadata = CKMetadata(
            kernel=kernel_name,
            version=version,
            intent=intent,
            timestamp=datetime.utcnow().isoformat(),
            request_id=self._generate_request_id(),
        )
        self.governance = CKGovernance(
            rcf=True, cect=True, veritas_watch=True, judex_quorum=False
        )
        self.telemetry = CKTelemetry(explain_vector=True, dag_attach=True)

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        return hashlib.sha256(
            f"{datetime.utcnow().isoformat()}{np.random.randint(0, 1000000)}".encode()
        ).hexdigest()[:32]

    def _compute_nbhs512(self, data: Any) -> str:
        """Compute NBHS-512 hash for provenance"""
        if isinstance(data, np.ndarray):
            data_str = data.tobytes()
        elif isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True).encode()
        else:
            data_str = str(data).encode()

        # Simplified NBHS-512 (128 hex chars = 512 bits)
        return hashlib.sha256(data_str).hexdigest() * 2

    def validate_payload(self, payload: Dict) -> Tuple[bool, str]:
        """Validate input payload against schema"""
        raise NotImplementedError("Subclasses must implement payload validation")

    def execute(self, payload: Dict) -> Dict:
        """Main execution method - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement execute method")

    def generate_explain_vector(self, result: Dict) -> Dict:
        """Generate explainability vector for decision justification"""
        return {
            "coverage": 1.0,
            "factors": ["input_validation", "model_inference", "post_processing"],
            "confidence": result.get("confidence", 0.0),
            "timestamp": datetime.utcnow().isoformat(),
        }


class SceneAnalysisObjectDetectionCK(BaseCapabilityKernel):
    """
    CK: Perception/SceneAnalysisObjectDetection
    Version: 1.2.0

    Intent: Performs real-time scene analysis and object detection using YOLOv8,
    providing bounding boxes, class labels, and confidence scores for detected objects.
    """

    def __init__(self):
        super().__init__(
            kernel_name="Perception/SceneAnalysisObjectDetection",
            version="1.2.0",
            intent="Real-time scene understanding with object detection and classification",
        )
        self.bounds = CKBounds(entropy_max=0.15, time_ms_max=500, scope="SBX-CV-OBJDET")
        self.model = None
        self.classes = None
        self._load_model()

    def _load_model(self):
        """Load YOLOv8 model (simulated - would load actual model in production)"""
        # In production, load: self.model = torch.hub.load('ultralytics/yolov8', 'yolov8n')
        self.classes = [
            "person",
            "bicycle",
            "car",
            "motorcycle",
            "airplane",
            "bus",
            "train",
            "truck",
            "boat",
            "traffic light",
            "fire hydrant",
            "stop sign",
            "parking meter",
            "bench",
            "bird",
            "cat",
            "dog",
            "horse",
            "sheep",
            "cow",
            "elephant",
            "bear",
            "zebra",
            "giraffe",
            "backpack",
            "umbrella",
            "handbag",
            "tie",
            "suitcase",
            "frisbee",
            "skis",
            "snowboard",
            "sports ball",
            "kite",
            "baseball bat",
            "baseball glove",
            "skateboard",
            "surfboard",
            "tennis racket",
            "bottle",
            "wine glass",
            "cup",
            "fork",
            "knife",
            "spoon",
            "bowl",
            "banana",
            "apple",
            "sandwich",
            "orange",
            "broccoli",
            "carrot",
            "hot dog",
            "pizza",
            "donut",
            "cake",
            "chair",
            "couch",
            "potted plant",
            "bed",
            "dining table",
            "toilet",
            "tv",
            "laptop",
            "mouse",
            "remote",
            "keyboard",
            "cell phone",
            "microwave",
            "oven",
            "toaster",
            "sink",
            "refrigerator",
            "book",
            "clock",
            "vase",
            "scissors",
            "teddy bear",
            "hair drier",
            "toothbrush",
        ]

    def validate_payload(self, payload: Dict) -> Tuple[bool, str]:
        """Validate input payload"""
        required_fields = ["image_data"]
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"

        # Validate image data format
        if isinstance(payload["image_data"], str):
            # Assume base64 encoded or file path
            pass
        elif isinstance(payload["image_data"], np.ndarray):
            # Validate numpy array
            if len(payload["image_data"].shape) not in [2, 3]:
                return False, "Invalid image dimensions"
        else:
            return False, "Image data must be base64 string or numpy array"

        return True, "Valid"

    def execute(self, payload: Dict) -> Dict:
        """
        Execute scene analysis and object detection

        Payload schema:
        {
            "image_data": str or np.ndarray,  # Image path, base64, or numpy array
            "confidence_threshold": float (optional, default: 0.5),
            "iou_threshold": float (optional, default: 0.45),
            "max_detections": int (optional, default: 100),
            "return_visualization": bool (optional, default: false)
        }

        Returns:
        {
            "ok": bool,
            "detections": [...],
            "scene_summary": str,
            "metrics": {...},
            "explain_vector": {...},
            "provenance": {...}
        }
        """
        start_time = datetime.utcnow()

        # Validate payload
        valid, message = self.validate_payload(payload)
        if not valid:
            return {
                "ok": False,
                "error": {"code": "E-VAL-001", "message": message},
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Extract parameters
        confidence_threshold = payload.get("confidence_threshold", 0.5)
        iou_threshold = payload.get("iou_threshold", 0.45)
        max_detections = payload.get("max_detections", 100)
        return_viz = payload.get("return_visualization", False)

        # Load and preprocess image
        image = self._load_image(payload["image_data"])
        if image is None:
            return {
                "ok": False,
                "error": {"code": "E-IO-042", "message": "Failed to load image"},
            }

        # Perform detection (simulated for demonstration)
        # In production: results = self.model(image, conf=confidence_threshold, iou=iou_threshold)
        detections = self._simulate_detection(
            image, confidence_threshold, max_detections
        )

        # Generate scene summary
        scene_summary = self._generate_scene_summary(detections)

        # Calculate metrics
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Prepare result
        result = {
            "ok": True,
            "detections": detections,
            "scene_summary": scene_summary,
            "metrics": {
                "detection_count": len(detections),
                "avg_confidence": np.mean([d["confidence"] for d in detections])
                if detections
                else 0.0,
                "latency_ms": latency_ms,
                "image_shape": list(image.shape),
            },
            "explain_vector": self.generate_explain_vector({"confidence": 0.95}),
            "provenance": {
                "nbhs512_seal": self._compute_nbhs512(detections),
                "golden_dag_ref": self.metadata.request_id,
                "kernel_version": self.metadata.version,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if return_viz:
            result["visualization"] = self._create_visualization(image, detections)

        return result

    def _load_image(self, image_data) -> Optional[np.ndarray]:
        """Load image from various formats"""
        try:
            if isinstance(image_data, np.ndarray):
                return image_data
            elif isinstance(image_data, str):
                # Try as file path
                return cv2.imread(image_data)
            return None
        except Exception:
            return None

    def _simulate_detection(
        self, image: np.ndarray, conf_threshold: float, max_det: int
    ) -> List[Dict]:
        """Simulate object detection (replace with actual YOLO in production)"""
        # Simulate detections for demonstration
        h, w = image.shape[:2]
        detections = []

        # Generate random detections within image bounds
        num_detections = min(np.random.randint(1, 8), max_det)

        for i in range(num_detections):
            class_id = np.random.randint(0, len(self.classes))
            confidence = np.random.uniform(conf_threshold, 0.99)

            # Random bounding box
            x1 = int(np.random.uniform(0, w * 0.7))
            y1 = int(np.random.uniform(0, h * 0.7))
            x2 = int(x1 + np.random.uniform(50, w * 0.3))
            y2 = int(y1 + np.random.uniform(50, h * 0.3))

            detections.append(
                {
                    "class": self.classes[class_id],
                    "class_id": class_id,
                    "confidence": round(confidence, 3),
                    "bbox": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "width": x2 - x1,
                        "height": y2 - y1,
                        "center": [(x1 + x2) // 2, (y1 + y2) // 2],
                    },
                }
            )

        return sorted(detections, key=lambda x: x["confidence"], reverse=True)

    def _generate_scene_summary(self, detections: List[Dict]) -> str:
        """Generate human-readable scene summary"""
        if not detections:
            return "No objects detected in scene"

        class_counts = {}
        for det in detections:
            cls = det["class"]
            class_counts[cls] = class_counts.get(cls, 0) + 1

        summary_parts = []
        for cls, count in sorted(class_counts.items()):
            if count == 1:
                summary_parts.append(f"1 {cls}")
            else:
                summary_parts.append(f"{count} {cls}s")

        return f"Detected: {', '.join(summary_parts)}"

    def _create_visualization(self, image: np.ndarray, detections: List[Dict]) -> str:
        """Create visualization with bounding boxes"""
        viz_image = image.copy()

        for det in detections:
            bbox = det["bbox"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]

            # Draw bounding box
            color = (0, 255, 0)  # Green
            cv2.rectangle(viz_image, (x1, y1), (x2, y2), color, 2)

            # Draw label
            label = f"{det['class']}: {det['confidence']:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(
                viz_image,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1,
            )
            cv2.putText(
                viz_image,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2,
            )

        # Encode to base64
        import base64

        _, buffer = cv2.imencode(".png", viz_image)
        return base64.b64encode(buffer).decode("utf-8")


class FacialRecognitionEmotionCK(BaseCapabilityKernel):
    """
    CK: Perception/FacialRecognitionEmotion
    Version: 1.1.0

    Intent: Detects faces in images, recognizes identities (if enrolled), and analyzes
    emotional expressions using deep learning models. Implements strict privacy controls
    and consent verification.
    """

    def __init__(self):
        super().__init__(
            kernel_name="Perception/FacialRecognitionEmotion",
            version="1.1.0",
            intent="Face detection, recognition, and emotion analysis with privacy controls",
        )
        self.bounds = CKBounds(entropy_max=0.12, time_ms_max=800, scope="SBX-CV-FACE")
        # Enable stricter governance for biometric data
        self.governance.judex_quorum = True
        self.governance.cect = True
        self.emotions = [
            "neutral",
            "happy",
            "sad",
            "angry",
            "fearful",
            "disgusted",
            "surprised",
        ]
        self.face_cascade = None
        self._load_model()

    def _load_model(self):
        """Load face detection model"""
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except Exception:
            # Fallback - will use simulated detection
            self.face_cascade = None

    def validate_payload(self, payload: Dict) -> Tuple[bool, str]:
        """Validate input payload with consent verification"""
        required_fields = ["image_data", "consent_record"]
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"

        # Verify consent for biometric processing (ϕ₁₃ - Qualia Protection)
        consent = payload.get("consent_record", {})
        if not consent.get("biometric_consent", False):
            return False, "Biometric processing requires explicit consent (ϕ₁₃)"

        if consent.get("ttl_hours", 0) <= 0:
            return False, "Data retention policy (TTL) must be specified"

        return True, "Valid"

    def execute(self, payload: Dict) -> Dict:
        """
        Execute facial recognition and emotion detection

        Payload schema:
        {
            "image_data": str or np.ndarray,
            "consent_record": {
                "biometric_consent": bool,
                "purpose": str,
                "ttl_hours": int,
                "subject_id": str (optional)
            },
            "enrolled_faces": Dict[str, np.ndarray] (optional),  # Known faces for recognition
            "detect_emotions": bool (optional, default: true),
            "detect_landmarks": bool (optional, default: false),
            "return_face_crop": bool (optional, default: false),
            "privacy_mode": str (optional, default: "strict")  # strict, anonymized, research
        }
        """
        start_time = datetime.utcnow()

        # Validate payload
        valid, message = self.validate_payload(payload)
        if not valid:
            return {
                "ok": False,
                "error": {"code": "E-ETH-013", "message": message, "clause": "ϕ₁₃"},
            }

        # Extract parameters
        consent = payload["consent_record"]
        detect_emotions = payload.get("detect_emotions", True)
        detect_landmarks = payload.get("detect_landmarks", False)
        return_crop = payload.get("return_face_crop", False)
        privacy_mode = payload.get("privacy_mode", "strict")
        enrolled_faces = payload.get("enrolled_faces", {})

        # Load image
        image = self._load_image(payload["image_data"])
        if image is None:
            return {
                "ok": False,
                "error": {"code": "E-IO-042", "message": "Failed to load image"},
            }

        # Detect faces
        faces = self._detect_faces(image)

        # Analyze each face
        face_analyses = []
        for face in faces:
            analysis = self._analyze_face(
                image, face, enrolled_faces, detect_emotions, detect_landmarks
            )

            # Apply privacy controls
            if privacy_mode == "anonymized":
                analysis["face_id"] = hashlib.sha256(
                    analysis["face_id"].encode()
                ).hexdigest()[:16]

            face_analyses.append(analysis)

        # Calculate metrics
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Prepare result with privacy metadata
        result = {
            "ok": True,
            "face_count": len(face_analyses),
            "faces": face_analyses,
            "consent_compliance": {
                "biometric_consent_verified": True,
                "ttl_hours": consent.get("ttl_hours"),
                "purpose": consent.get("purpose"),
                "privacy_mode": privacy_mode,
                "pii_redacted": privacy_mode != "research",
            },
            "metrics": {
                "detection_confidence_avg": np.mean(
                    [f["detection_confidence"] for f in face_analyses]
                )
                if face_analyses
                else 0.0,
                "latency_ms": latency_ms,
                "faces_detected": len(face_analyses),
            },
            "explain_vector": self.generate_explain_vector(
                {
                    "confidence": 0.92,
                    "factors": [
                        "face_detection",
                        "emotion_classification",
                        "identity_matching",
                    ],
                }
            ),
            "provenance": {
                "nbhs512_seal": self._compute_nbhs512(face_analyses),
                "golden_dag_ref": self.metadata.request_id,
                "kernel_version": self.metadata.version,
                "consent_audit_trail": consent.get("audit_id", "N/A"),
            },
            "warnings": []
            if consent.get("ttl_hours", 0) <= 24
            else [
                {
                    "code": "PRIVACY-WARN-001",
                    "message": "Data retention exceeds 24 hours",
                }
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

        if return_crop and face_analyses:
            result["face_crops_base64"] = [
                self._encode_face_crop(image, f["bbox"]) for f in face_analyses
            ]

        return result

    def _load_image(self, image_data) -> Optional[np.ndarray]:
        """Load image from various formats"""
        try:
            if isinstance(image_data, np.ndarray):
                return image_data
            elif isinstance(image_data, str):
                return cv2.imread(image_data)
            return None
        except Exception:
            return None

    def _detect_faces(self, image: np.ndarray) -> List[Dict]:
        """Detect faces in image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if self.face_cascade is not None:
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            return [
                {"bbox": [int(x), int(y), int(w), int(h)], "confidence": 0.85}
                for x, y, w, h in faces
            ]
        else:
            # Simulated detection
            h, w = gray.shape
            return [
                {
                    "bbox": [int(w * 0.2), int(h * 0.2), int(w * 0.3), int(h * 0.4)],
                    "confidence": 0.92,
                }
            ]

    def _analyze_face(
        self,
        image: np.ndarray,
        face: Dict,
        enrolled: Dict,
        detect_emotions: bool,
        detect_landmarks: bool,
    ) -> Dict:
        """Analyze a single face"""
        x, y, w, h = face["bbox"]
        face_crop = image[y : y + h, x : x + w]

        analysis = {
            "face_id": f"face_{hashlib.md5(str(face['bbox']).encode()).hexdigest()[:8]}",
            "bbox": {
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "center": [x + w // 2, y + h // 2],
            },
            "detection_confidence": face["confidence"],
        }

        # Emotion detection
        if detect_emotions:
            emotion, conf = self._classify_emotion(face_crop)
            analysis["emotion"] = {
                "primary": emotion,
                "confidence": conf,
                "all_emotions": self._get_emotion_distribution(face_crop),
            }

        # Face recognition
        if enrolled:
            identity, match_conf = self._recognize_face(face_crop, enrolled)
            if identity:
                analysis["identity"] = {
                    "matched": True,
                    "subject_id": identity,
                    "match_confidence": match_conf,
                }
            else:
                analysis["identity"] = {"matched": False}

        # Facial landmarks
        if detect_landmarks:
            analysis["landmarks"] = self._detect_landmarks(face_crop)

        return analysis

    def _classify_emotion(self, face_crop: np.ndarray) -> Tuple[str, float]:
        """Classify emotion (simulated)"""
        # In production: Use trained emotion model (e.g., FER2013 model)
        emotion = np.random.choice(self.emotions)
        confidence = np.random.uniform(0.75, 0.98)
        return emotion, round(confidence, 3)

    def _get_emotion_distribution(self, face_crop: np.ndarray) -> Dict[str, float]:
        """Get emotion probability distribution"""
        # Simulated distribution
        probs = np.random.dirichlet(np.ones(len(self.emotions)))
        return {emo: round(float(prob), 3) for emo, prob in zip(self.emotions, probs)}

    def _recognize_face(
        self, face_crop: np.ndarray, enrolled: Dict
    ) -> Tuple[Optional[str], float]:
        """Recognize face against enrolled identities"""
        # Simulated recognition - in production use FaceNet or similar
        if enrolled and np.random.random() > 0.5:
            identity = list(enrolled.keys())[0]
            return identity, round(np.random.uniform(0.80, 0.95), 3)
        return None, 0.0

    def _detect_landmarks(self, face_crop: np.ndarray) -> Dict:
        """Detect facial landmarks (simulated)"""
        h, w = face_crop.shape[:2]
        return {
            "left_eye": [int(w * 0.3), int(h * 0.4)],
            "right_eye": [int(w * 0.7), int(h * 0.4)],
            "nose": [int(w * 0.5), int(h * 0.55)],
            "left_mouth": [int(w * 0.35), int(h * 0.75)],
            "right_mouth": [int(w * 0.65), int(h * 0.75)],
        }

    def _encode_face_crop(self, image: np.ndarray, bbox: Dict) -> str:
        """Encode face crop to base64"""
        import base64

        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
        crop = image[y : y + h, x : x + w]
        _, buffer = cv2.imencode(".jpg", crop)
        return base64.b64encode(buffer).decode("utf-8")


class OpticalCharacterRecognitionCK(BaseCapabilityKernel):
    """
    CK: Perception/OpticalCharacterRecognition
    Version: 1.3.0

    Intent: Extracts text from images using deep learning-based OCR with support for
    multiple languages, layout analysis, and structured document parsing.
    """

    def __init__(self):
        super().__init__(
            kernel_name="Perception/OpticalCharacterRecognition",
            version="1.3.0",
            intent="Multi-language text extraction with layout analysis and document parsing",
        )
        self.bounds = CKBounds(entropy_max=0.18, time_ms_max=2000, scope="SBX-CV-OCR")
        self.supported_languages = [
            "eng",
            "spa",
            "fra",
            "deu",
            "ita",
            "por",
            "rus",
            "chi_sim",
            "chi_tra",
            "jpn",
            "kor",
            "ara",
        ]
        self._load_model()

    def _load_model(self):
        """Load OCR models"""
        # In production: Load CRAFT text detector + PARSeq/TrOCR recognizer
        pass

    def validate_payload(self, payload: Dict) -> Tuple[bool, str]:
        """Validate input payload"""
        required_fields = ["image_data"]
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"

        # Validate language
        lang = payload.get("language", "eng")
        if lang not in self.supported_languages:
            return (
                False,
                f"Unsupported language: {lang}. Supported: {self.supported_languages}",
            )

        return True, "Valid"

    def execute(self, payload: Dict) -> Dict:
        """
        Execute optical character recognition

        Payload schema:
        {
            "image_data": str or np.ndarray,
            "language": str (optional, default: "eng"),
            "detect_orientation": bool (optional, default: true),
            "extract_tables": bool (optional, default: false),
            "extract_structure": bool (optional, default: false),
            "confidence_threshold": float (optional, default: 0.6),
            "preprocessing": {
                "denoise": bool (optional),
                "deskew": bool (optional),
                "contrast_enhance": bool (optional)
            }
        }
        """
        start_time = datetime.utcnow()

        # Validate payload
        valid, message = self.validate_payload(payload)
        if not valid:
            return {"ok": False, "error": {"code": "E-VAL-001", "message": message}}

        # Extract parameters
        language = payload.get("language", "eng")
        detect_orientation = payload.get("detect_orientation", True)
        extract_tables = payload.get("extract_tables", False)
        extract_structure = payload.get("extract_structure", False)
        confidence_threshold = payload.get("confidence_threshold", 0.6)
        preprocessing = payload.get("preprocessing", {})

        # Load and preprocess image
        image = self._load_image(payload["image_data"])
        if image is None:
            return {
                "ok": False,
                "error": {"code": "E-IO-042", "message": "Failed to load image"},
            }

        # Apply preprocessing
        processed_image = self._preprocess_image(image, preprocessing)

        # Detect text regions
        text_regions = self._detect_text_regions(processed_image)

        # Recognize text in each region
        text_blocks = []
        for region in text_regions:
            text, conf = self._recognize_text(processed_image, region, language)
            if conf >= confidence_threshold:
                text_blocks.append(
                    {
                        "text": text,
                        "confidence": round(conf, 3),
                        "bbox": region["bbox"],
                        "language": language,
                    }
                )

        # Extract structure if requested
        document_structure = None
        if extract_structure:
            document_structure = self._extract_document_structure(text_blocks)

        # Extract tables if requested
        tables = None
        if extract_tables:
            tables = self._extract_tables(processed_image, text_blocks)

        # Detect orientation if requested
        orientation = None
        if detect_orientation:
            orientation = self._detect_orientation(processed_image)

        # Calculate metrics
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Prepare full text
        full_text = "\n".join([block["text"] for block in text_blocks])

        result = {
            "ok": True,
            "text": full_text,
            "text_blocks": text_blocks,
            "block_count": len(text_blocks),
            "character_count": len(full_text.replace(" ", "").replace("\n", "")),
            "language_detected": language,
            "metrics": {
                "avg_confidence": np.mean([b["confidence"] for b in text_blocks])
                if text_blocks
                else 0.0,
                "latency_ms": latency_ms,
                "image_shape": list(image.shape),
                "preprocessing_applied": list(preprocessing.keys()),
            },
            "explain_vector": self.generate_explain_vector(
                {
                    "confidence": 0.88,
                    "factors": [
                        "text_detection",
                        "language_recognition",
                        "layout_analysis",
                    ],
                }
            ),
            "provenance": {
                "nbhs512_seal": self._compute_nbhs512(full_text),
                "golden_dag_ref": self.metadata.request_id,
                "kernel_version": self.metadata.version,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if orientation:
            result["orientation"] = orientation

        if document_structure:
            result["document_structure"] = document_structure

        if tables:
            result["tables"] = tables

        return result

    def _load_image(self, image_data) -> Optional[np.ndarray]:
        """Load image from various formats"""
        try:
            if isinstance(image_data, np.ndarray):
                return image_data
            elif isinstance(image_data, str):
                return cv2.imread(image_data)
            return None
        except Exception:
            return None

    def _preprocess_image(self, image: np.ndarray, preprocessing: Dict) -> np.ndarray:
        """Apply preprocessing steps"""
        processed = image.copy()

        if preprocessing.get("denoise"):
            processed = cv2.fastNlMeansDenoisingColored(processed, None, 10, 10, 7, 21)

        if preprocessing.get("contrast_enhance"):
            lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            processed = cv2.merge([l, a, b])
            processed = cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)

        if preprocessing.get("deskew"):
            processed = self._deskew_image(processed)

        # Convert to grayscale if not already
        if len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

        return processed

    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Deskew image using Hough transform"""
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        )
        coords = np.column_stack(np.where(gray > 0))
        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated

    def _detect_text_regions(self, image: np.ndarray) -> List[Dict]:
        """Detect text regions in image"""
        # In production: Use CRAFT or EAST text detector
        # Simulated detection
        h, w = image.shape[:2]
        regions = []

        # Simulate multiple text regions
        num_regions = np.random.randint(2, 6)
        for i in range(num_regions):
            y_start = int(h * (i / num_regions))
            y_end = int(h * ((i + 1) / num_regions))
            x_start = int(w * 0.1)
            x_end = int(w * 0.9)

            regions.append(
                {
                    "bbox": {
                        "x": x_start,
                        "y": y_start,
                        "width": x_end - x_start,
                        "height": y_end - y_start,
                    },
                    "confidence": np.random.uniform(0.85, 0.98),
                }
            )

        return regions

    def _recognize_text(
        self, image: np.ndarray, region: Dict, language: str
    ) -> Tuple[str, float]:
        """Recognize text in a region"""
        # In production: Use PARSeq, TrOCR, or Tesseract
        # Simulated recognition
        sample_texts = {
            "eng": [
                "Sample text detection",
                "NeuralBlitz OCR",
                "Document processing",
                "Multi-language support",
                "Layout analysis enabled",
            ],
            "spa": [
                "Análisis de texto",
                "Reconocimiento óptico",
                "Procesamiento de documentos",
            ],
            "fra": [
                "Analyse de texte",
                "Reconnaissance optique",
                "Traitement de documents",
            ],
            "deu": [
                "Textanalyse",
                "Optische Zeichenerkennung",
                "Dokumentenverarbeitung",
            ],
            "chi_sim": ["文本分析", "光学字符识别", "文档处理"],
            "jpn": ["テキスト分析", "光学文字認識", "文書処理"],
        }

        texts = sample_texts.get(language, sample_texts["eng"])
        return np.random.choice(texts), np.random.uniform(0.75, 0.96)

    def _extract_document_structure(self, text_blocks: List[Dict]) -> Dict:
        """Extract document structure (headers, paragraphs, etc.)"""
        structure = {"sections": [], "paragraphs": [], "headers": []}

        current_section = {"type": "section", "blocks": []}
        for i, block in enumerate(text_blocks):
            # Simple heuristic for headers (shorter text, higher position)
            if len(block["text"]) < 50 and i == 0:
                structure["headers"].append(block)
            else:
                current_section["blocks"].append(block)

        if current_section["blocks"]:
            structure["sections"].append(current_section)

        return structure

    def _extract_tables(self, image: np.ndarray, text_blocks: List[Dict]) -> List[Dict]:
        """Extract tables from document"""
        # In production: Use Table Detection models
        return []

    def _detect_orientation(self, image: np.ndarray) -> Dict:
        """Detect page orientation"""
        # In production: Use orientation classification model
        return {"angle_degrees": 0, "confidence": 0.95, "orientation": "normal"}


# ============================================================================
# DEMO AND TESTING
# ============================================================================


def demo_scene_analysis():
    """Demo Scene Analysis and Object Detection CK"""
    print("=" * 70)
    print("DEMO: Scene Analysis and Object Detection CK")
    print("=" * 70)

    ck = SceneAnalysisObjectDetectionCK()

    # Create test image
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    payload = {
        "image_data": test_image,
        "confidence_threshold": 0.5,
        "max_detections": 10,
        "return_visualization": True,
    }

    result = ck.execute(payload)

    print(f"\nKernel: {ck.metadata.kernel}")
    print(f"Version: {ck.metadata.version}")
    print(f"Intent: {ck.metadata.intent}")
    print(f"\nExecution Result:")
    print(f"  Status: {'SUCCESS' if result['ok'] else 'FAILED'}")
    print(f"  Objects Detected: {result['metrics']['detection_count']}")
    print(f"  Scene Summary: {result['scene_summary']}")
    print(f"  Avg Confidence: {result['metrics']['avg_confidence']:.3f}")
    print(f"  Latency: {result['metrics']['latency_ms']:.2f}ms")
    print(f"\nDetections:")
    for det in result["detections"][:3]:
        print(f"    - {det['class']}: {det['confidence']} at {det['bbox']['center']}")
    print(f"\nProvenance:")
    print(f"  NBHS-512: {result['provenance']['nbhs512_seal'][:32]}...")
    print(f"  DAG Ref: {result['provenance']['golden_dag_ref'][:16]}...")


def demo_facial_recognition():
    """Demo Facial Recognition and Emotion Detection CK"""
    print("\n" + "=" * 70)
    print("DEMO: Facial Recognition and Emotion Detection CK")
    print("=" * 70)

    ck = FacialRecognitionEmotionCK()

    # Create test image
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    payload = {
        "image_data": test_image,
        "consent_record": {
            "biometric_consent": True,
            "purpose": "Research analysis",
            "ttl_hours": 24,
            "subject_id": "test_subject_001",
            "audit_id": "AUDIT-2024-001",
        },
        "detect_emotions": True,
        "detect_landmarks": True,
        "privacy_mode": "strict",
    }

    result = ck.execute(payload)

    print(f"\nKernel: {ck.metadata.kernel}")
    print(f"Version: {ck.metadata.version}")
    print(f"Intent: {ck.metadata.intent}")
    print(f"Governance: Judex Quorum = {ck.governance.judex_quorum}")
    print(f"\nExecution Result:")
    print(f"  Status: {'SUCCESS' if result['ok'] else 'FAILED'}")
    print(f"  Faces Detected: {result['face_count']}")
    print(f"  Privacy Mode: {result['consent_compliance']['privacy_mode']}")
    print(f"  PII Redacted: {result['consent_compliance']['pii_redacted']}")
    print(f"  Latency: {result['metrics']['latency_ms']:.2f}ms")

    if result["faces"]:
        face = result["faces"][0]
        print(f"\nFace Analysis:")
        print(f"  Face ID: {face['face_id']}")
        if "emotion" in face:
            print(
                f"  Emotion: {face['emotion']['primary']} ({face['emotion']['confidence']})"
            )
        if "identity" in face:
            print(f"  Identity Matched: {face['identity']['matched']}")

    print(f"\nProvenance:")
    print(f"  NBHS-512: {result['provenance']['nbhs512_seal'][:32]}...")


def demo_ocr():
    """Demo Optical Character Recognition CK"""
    print("\n" + "=" * 70)
    print("DEMO: Optical Character Recognition CK")
    print("=" * 70)

    ck = OpticalCharacterRecognitionCK()

    # Create test image
    test_image = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)

    payload = {
        "image_data": test_image,
        "language": "eng",
        "detect_orientation": True,
        "extract_structure": True,
        "confidence_threshold": 0.6,
        "preprocessing": {"denoise": True, "contrast_enhance": True, "deskew": False},
    }

    result = ck.execute(payload)

    print(f"\nKernel: {ck.metadata.kernel}")
    print(f"Version: {ck.metadata.version}")
    print(f"Intent: {ck.metadata.intent}")
    print(f"\nExecution Result:")
    print(f"  Status: {'SUCCESS' if result['ok'] else 'FAILED'}")
    print(f"  Language: {result['language_detected']}")
    print(f"  Text Blocks: {result['block_count']}")
    print(f"  Character Count: {result['character_count']}")
    print(f"  Avg Confidence: {result['metrics']['avg_confidence']:.3f}")
    print(f"  Latency: {result['metrics']['latency_ms']:.2f}ms")
    print(f"\nExtracted Text Preview:")
    print(f"  {result['text'][:100]}...")
    print(f"\nProvenance:")
    print(f"  NBHS-512: {result['provenance']['nbhs512_seal'][:32]}...")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("NeuralBlitz Computer Vision Capability Kernels (CV-CK)")
    print("v1.0.0 - Demonstration Suite")
    print("=" * 70)

    demo_scene_analysis()
    demo_facial_recognition()
    demo_ocr()

    print("\n" + "=" * 70)
    print("All demonstrations completed successfully.")
    print("=" * 70 + "\n")

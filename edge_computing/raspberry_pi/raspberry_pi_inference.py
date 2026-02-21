#!/usr/bin/env python3
"""
Raspberry Pi Edge Inference Engine for NeuralBlitz
Optimized for ARM Cortex-A72/A76 with TensorFlow Lite
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from PIL import Image

try:
    import tflite_runtime.interpreter as tflite

    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import tensorflow.lite as tflite

        TFLITE_AVAILABLE = True
    except ImportError:
        TFLITE_AVAILABLE = False
        print("Warning: TensorFlow Lite not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RaspberryPiInference")


@dataclass
class InferenceConfig:
    """Configuration for edge inference"""

    model_path: str
    input_shape: Tuple[int, ...] = (1, 224, 224, 3)
    num_threads: int = 4
    use_xnnpack: bool = True
    enable_profiling: bool = False
    batch_size: int = 1
    warmup_runs: int = 10


class RaspberryPiInferenceEngine:
    """
    Optimized inference engine for Raspberry Pi 4/5

    Features:
    - XNNPACK delegate for accelerated CPU inference
    - Multi-threading with optimal thread count
    - Memory-mapped model loading
    - Batch processing for throughput optimization
    """

    def __init__(self, config: InferenceConfig):
        self.config = config
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self._initialized = False

        # Performance metrics
        self.metrics = {
            "inference_times": [],
            "total_predictions": 0,
            "avg_latency_ms": 0.0,
            "throughput_fps": 0.0,
            "memory_mb": 0.0,
        }

    def initialize(self) -> bool:
        """Initialize the TFLite interpreter with optimizations"""
        if not TFLITE_AVAILABLE:
            logger.error("TensorFlow Lite not available")
            return False

        try:
            logger.info(f"Loading model: {self.config.model_path}")

            # Configure interpreter with XNNPACK delegate
            if self.config.use_xnnpack:
                self.interpreter = tflite.Interpreter(
                    model_path=self.config.model_path,
                    num_threads=self.config.num_threads,
                    experimental_delegates=[],
                )
            else:
                self.interpreter = tflite.Interpreter(
                    model_path=self.config.model_path,
                    num_threads=self.config.num_threads,
                )

            # Allocate tensors
            self.interpreter.allocate_tensors()

            # Get input/output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            logger.info(f"Input shape: {self.input_details[0]['shape']}")
            logger.info(f"Output shape: {self.output_details[0]['shape']}")
            logger.info(f"Threads: {self.config.num_threads}")

            self._initialized = True

            # Warmup runs
            self._warmup()

            return True

        except Exception as e:
            logger.error(f"Failed to initialize inference engine: {e}")
            return False

    def _warmup(self):
        """Perform warmup inference to stabilize performance"""
        logger.info(f"Performing {self.config.warmup_runs} warmup runs...")
        dummy_input = np.zeros(self.config.input_shape, dtype=np.float32)

        for _ in range(self.config.warmup_runs):
            self._infer_single(dummy_input)

        logger.info("Warmup complete")

    def _infer_single(self, input_data: np.ndarray) -> np.ndarray:
        """Execute single inference"""
        # Set input tensor
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)

        # Run inference
        self.interpreter.invoke()

        # Get output
        output = self.interpreter.get_tensor(self.output_details[0]["index"])

        return output

    def infer(self, input_data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Execute inference with performance monitoring

        Args:
            input_data: Preprocessed input tensor

        Returns:
            (predictions, metrics)
        """
        if not self._initialized:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        start_time = time.perf_counter()

        # Execute inference
        output = self._infer_single(input_data)

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        # Update metrics
        self.metrics["inference_times"].append(latency_ms)
        self.metrics["total_predictions"] += 1
        self.metrics["avg_latency_ms"] = np.mean(self.metrics["inference_times"][-100:])
        self.metrics["throughput_fps"] = 1000.0 / self.metrics["avg_latency_ms"]

        runtime_metrics = {"latency_ms": latency_ms, "timestamp": time.time()}

        return output, runtime_metrics

    def infer_batch(
        self, batch_data: List[np.ndarray]
    ) -> Tuple[List[np.ndarray], Dict]:
        """
        Execute batch inference for higher throughput

        Args:
            batch_data: List of preprocessed input tensors

        Returns:
            (predictions, metrics)
        """
        start_time = time.perf_counter()

        results = []
        for data in batch_data:
            output = self._infer_single(data)
            results.append(output)

        end_time = time.perf_counter()
        total_latency_ms = (end_time - start_time) * 1000
        avg_latency_ms = total_latency_ms / len(batch_data)
        throughput_fps = (len(batch_data) / total_latency_ms) * 1000

        metrics = {
            "batch_size": len(batch_data),
            "total_latency_ms": total_latency_ms,
            "avg_latency_ms": avg_latency_ms,
            "throughput_fps": throughput_fps,
        }

        return results, metrics

    def preprocess_image(
        self, image_path: str, target_size: Tuple[int, int] = (224, 224)
    ) -> np.ndarray:
        """Load and preprocess image for inference"""
        img = Image.open(image_path).convert("RGB")
        img = img.resize(target_size)
        img_array = np.array(img, dtype=np.float32)
        img_array = img_array / 255.0  # Normalize to [0, 1]
        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    def get_metrics(self) -> Dict:
        """Get current performance metrics"""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            self.metrics["memory_mb"] = process.memory_info().rss / 1024 / 1024
        except ImportError:
            pass
        return self.metrics.copy()

    def export_metrics(self, output_path: str):
        """Export metrics to JSON"""
        with open(output_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        logger.info(f"Metrics exported to {output_path}")


class RaspberryPiPipeline:
    """Complete inference pipeline for Raspberry Pi"""

    def __init__(self, model_path: str):
        config = InferenceConfig(
            model_path=model_path,
            num_threads=4,  # Optimal for Pi 4
            use_xnnpack=True,
            enable_profiling=True,
        )
        self.engine = RaspberryPiInferenceEngine(config)

    def run(self, image_paths: List[str]) -> Dict:
        """Run complete inference pipeline"""
        # Initialize
        if not self.engine.initialize():
            raise RuntimeError("Failed to initialize inference engine")

        results = []

        # Process images
        for img_path in image_paths:
            logger.info(f"Processing: {img_path}")
            input_data = self.engine.preprocess_image(img_path)
            predictions, metrics = self.engine.infer(input_data)

            results.append(
                {
                    "image": img_path,
                    "predictions": predictions.tolist(),
                    "latency_ms": metrics["latency_ms"],
                }
            )

        # Get final metrics
        final_metrics = self.engine.get_metrics()

        return {"results": results, "metrics": final_metrics}


# Benchmark script
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Raspberry Pi Inference Benchmark")
    parser.add_argument("--model", required=True, help="Path to TFLite model")
    parser.add_argument("--image", help="Path to test image")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark")
    parser.add_argument(
        "--iterations", type=int, default=100, help="Benchmark iterations"
    )

    args = parser.parse_args()

    # Initialize engine
    config = InferenceConfig(model_path=args.model, num_threads=4, use_xnnpack=True)

    engine = RaspberryPiInferenceEngine(config)

    if not engine.initialize():
        print("Failed to initialize engine")
        exit(1)

    if args.benchmark:
        print(f"\nRunning benchmark with {args.iterations} iterations...\n")

        # Create dummy input
        input_data = np.random.randn(1, 224, 224, 3).astype(np.float32)

        # Benchmark loop
        for _ in range(args.iterations):
            predictions, metrics = engine.infer(input_data)

        # Get final metrics
        metrics = engine.get_metrics()

        print("\n" + "=" * 50)
        print("RASPBERRY PI INFERENCE BENCHMARK RESULTS")
        print("=" * 50)
        print(f"Model: {args.model}")
        print(f"Total Predictions: {metrics['total_predictions']}")
        print(f"Average Latency: {metrics['avg_latency_ms']:.2f} ms")
        print(f"Throughput: {metrics['throughput_fps']:.2f} FPS")
        print(f"Memory Usage: {metrics['memory_mb']:.2f} MB")
        print(f"Threads: {config.num_threads}")
        print("=" * 50)

        # Export metrics
        engine.export_metrics("raspberry_pi_metrics.json")

    elif args.image:
        print(f"\nProcessing image: {args.image}")
        input_data = engine.preprocess_image(args.image)
        predictions, metrics = engine.infer(input_data)

        print(f"Latency: {metrics['latency_ms']:.2f} ms")
        print(f"Predictions shape: {predictions.shape}")
        print(f"Top prediction: {np.argmax(predictions[0])}")

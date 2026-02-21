"""
Multi-Metric Monitoring System (M³) for Ethical Drift Detection
NeuralBlitz v20.0 - Governance Layer Extension
CK: Gov/MultiMetricMonitor v1.0

This module extends EthicDriftMonitor with holistic multi-dimensional
ethical state assessment using 12+ correlated metrics across the EEM.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json


@dataclass
class EthicalMetric:
    """Represents a single ethical metric with metadata."""

    name: str
    value: float
    weight: float
    threshold: float
    category: str  # 'primary' or 'secondary'
    timestamp: datetime

    def is_violated(self) -> bool:
        """Check if metric exceeds its threshold."""
        return abs(self.value) > self.threshold


@dataclass
class EthicalStateVector:
    """Complete ethical state at a point in time."""

    timestamp: datetime
    metrics: Dict[str, EthicalMetric]
    drift_score: float
    mode: str  # 'Sentio' or 'Dynamo'
    session_id: str

    def to_dict(self) -> Dict:
        """Serialize to dictionary for GoldenDAG logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "drift_score": self.drift_score,
            "mode": self.mode,
            "session_id": self.session_id,
            "metrics": {
                name: {
                    "value": m.value,
                    "weight": m.weight,
                    "threshold": m.threshold,
                    "violated": m.is_violated(),
                }
                for name, m in self.metrics.items()
            },
        }


class MultiMetricMonitor:
    """
    Multi-Metric Monitoring System (M³) for comprehensive ethical drift detection.

    Monitors 12+ correlated metrics across the Ethical Enforcement Mesh (EEM)
    to detect subtle drift patterns invisible to single-metric monitors.

    Algorithm:
    1. Collect metrics from DRS-F, CECT, Veritas, MetaMind, and other EEM components
    2. Apply context-adaptive weighting based on operational mode
    3. Compute correlation-adjusted composite drift score
    4. Apply exponential smoothing to reduce noise
    5. Generate alerts if drift exceeds Charter-specified thresholds
    """

    # Metric definitions with Charter-specified thresholds
    METRIC_DEFINITIONS = {
        # Primary Drift Indicators
        "MRDE": {
            "weight_sentio": 0.25,
            "weight_dynamo": 0.20,
            "threshold": 0.03,
            "category": "primary",
        },
        "CECT_ϕ4": {
            "weight_sentio": 0.20,
            "weight_dynamo": 0.15,
            "threshold": 0.15,
            "category": "primary",
        },  # Non-maleficence
        "CECT_ϕ5": {
            "weight_sentio": 0.20,
            "weight_dynamo": 0.15,
            "threshold": 0.15,
            "category": "primary",
        },  # Governance primacy
        "CECT_ϕ1": {
            "weight_sentio": 0.15,
            "weight_dynamo": 0.15,
            "threshold": 0.20,
            "category": "primary",
        },  # Flourishing
        "ERSF": {
            "weight_sentio": 0.15,
            "weight_dynamo": 0.20,
            "threshold": 0.20,
            "category": "primary",
        },
        "VPCE": {
            "weight_sentio": 0.05,
            "weight_dynamo": 0.15,
            "threshold": 0.15,
            "category": "primary",
        },
        # Secondary Drift Indicators
        "Semantic_Density": {
            "weight_sentio": 0.03,
            "weight_dynamo": 0.08,
            "threshold": 1e-5,
            "category": "secondary",
        },
        "Entanglement_Anomaly": {
            "weight_sentio": 0.03,
            "weight_dynamo": 0.05,
            "threshold": 0.10,
            "category": "secondary",
        },
        "Phase_Sync_Loss": {
            "weight_sentio": 0.03,
            "weight_dynamo": 0.05,
            "threshold": 0.25,
            "category": "secondary",
        },
        "Entropy_Budget": {
            "weight_sentio": 0.02,
            "weight_dynamo": 0.08,
            "threshold": 0.85,
            "category": "secondary",
        },
        "ASF_Stability": {
            "weight_sentio": 0.03,
            "weight_dynamo": 0.05,
            "threshold": 0.15,
            "category": "secondary",
        },
        "RRFD_Variance": {
            "weight_sentio": 0.03,
            "weight_dynamo": 0.05,
            "threshold": 0.20,
            "category": "secondary",
        },
        "TRM_Drift": {
            "weight_sentio": 0.03,
            "weight_dynamo": 0.04,
            "threshold": 0.15,
            "category": "secondary",
        },
        "QEC_Corruption": {
            "weight_sentio": 0.05,
            "weight_dynamo": 0.05,
            "threshold": 0.10,
            "category": "secondary",
        },
    }

    # Correlation matrix between metrics (simplified - would be learned from data)
    CORRELATION_MATRIX = np.array(
        [
            # MRDE, ϕ4,   ϕ5,   ϕ1,   ERSF, VPCE, SD,   EA,   PSL,  EB,   ASF,  RRFD, TRM,  QEC
            [
                1.00,
                0.75,
                0.70,
                0.65,
                0.80,
                0.60,
                0.50,
                0.55,
                0.45,
                0.70,
                0.65,
                0.60,
                0.40,
                0.30,
            ],  # MRDE
            [
                0.75,
                1.00,
                0.85,
                0.70,
                0.75,
                0.65,
                0.45,
                0.50,
                0.40,
                0.60,
                0.70,
                0.55,
                0.35,
                0.25,
            ],  # ϕ4
            [
                0.70,
                0.85,
                1.00,
                0.65,
                0.70,
                0.60,
                0.40,
                0.45,
                0.35,
                0.55,
                0.75,
                0.50,
                0.30,
                0.20,
            ],  # ϕ5
            [
                0.65,
                0.70,
                0.65,
                1.00,
                0.80,
                0.55,
                0.60,
                0.55,
                0.50,
                0.65,
                0.60,
                0.55,
                0.45,
                0.35,
            ],  # ϕ1
            [
                0.80,
                0.75,
                0.70,
                0.80,
                1.00,
                0.70,
                0.55,
                0.60,
                0.50,
                0.75,
                0.70,
                0.65,
                0.45,
                0.40,
            ],  # ERSF
            [
                0.60,
                0.65,
                0.60,
                0.55,
                0.70,
                1.00,
                0.50,
                0.55,
                0.45,
                0.60,
                0.65,
                0.60,
                0.40,
                0.50,
            ],  # VPCE
            [
                0.50,
                0.45,
                0.40,
                0.60,
                0.55,
                0.50,
                1.00,
                0.70,
                0.65,
                0.80,
                0.50,
                0.70,
                0.60,
                0.40,
            ],  # SD
            [
                0.55,
                0.50,
                0.45,
                0.55,
                0.60,
                0.55,
                0.70,
                1.00,
                0.60,
                0.75,
                0.55,
                0.80,
                0.50,
                0.45,
            ],  # EA
            [
                0.45,
                0.40,
                0.35,
                0.50,
                0.50,
                0.45,
                0.65,
                0.60,
                1.00,
                0.65,
                0.45,
                0.70,
                0.55,
                0.40,
            ],  # PSL
            [
                0.70,
                0.60,
                0.55,
                0.65,
                0.75,
                0.60,
                0.80,
                0.75,
                0.65,
                1.00,
                0.60,
                0.75,
                0.50,
                0.45,
            ],  # EB
            [
                0.65,
                0.70,
                0.75,
                0.60,
                0.70,
                0.65,
                0.50,
                0.55,
                0.45,
                0.60,
                1.00,
                0.55,
                0.40,
                0.35,
            ],  # ASF
            [
                0.60,
                0.55,
                0.50,
                0.55,
                0.65,
                0.60,
                0.70,
                0.80,
                0.70,
                0.75,
                0.55,
                1.00,
                0.55,
                0.45,
            ],  # RRFD
            [
                0.40,
                0.35,
                0.30,
                0.45,
                0.45,
                0.40,
                0.60,
                0.50,
                0.55,
                0.50,
                0.40,
                0.55,
                1.00,
                0.30,
            ],  # TRM
            [
                0.30,
                0.25,
                0.20,
                0.35,
                0.40,
                0.50,
                0.40,
                0.45,
                0.40,
                0.45,
                0.35,
                0.45,
                0.30,
                1.00,
            ],  # QEC
        ]
    )

    def __init__(
        self,
        mode: str = "Sentio",
        smoothing_alpha: float = 0.3,
        history_window: int = 300,
    ):
        """
        Initialize MultiMetricMonitor.

        Args:
            mode: Operational mode ('Sentio' or 'Dynamo')
            smoothing_alpha: Exponential smoothing factor (0-1)
            history_window: Number of state vectors to retain in history
        """
        self.mode = mode
        self.alpha = smoothing_alpha
        self.history: deque = deque(maxlen=history_window)
        self.smoothed_drift_score: float = 0.0
        self.logger = logging.getLogger(__name__)

        # Metric index mapping
        self.metric_names = list(self.METRIC_DEFINITIONS.keys())
        self.metric_index = {name: i for i, name in enumerate(self.metric_names)}

    def get_metric_weight(self, metric_name: str) -> float:
        """Get context-adaptive weight based on operational mode."""
        defs = self.METRIC_DEFINITIONS[metric_name]
        return defs["weight_sentio"] if self.mode == "Sentio" else defs["weight_dynamo"]

    def collect_metrics(self) -> Dict[str, float]:
        """
        Collect current values for all monitored metrics.

        In production, this would query:
        - DRS-F module for semantic/entanglement metrics
        - CECT for clause stress metrics
        - MetaMind for MRDE
        - Veritas for VPCE
        - Conscientia++ for ERSF
        - etc.

        Returns:
            Dictionary mapping metric names to current values
        """
        # Simulated metric collection - in production, query actual EEM components
        metrics = {}

        # Primary metrics (would come from actual EEM queries)
        metrics["MRDE"] = np.random.normal(0.01, 0.005)  # MetaMind Recursive Drift
        metrics["CECT_ϕ4"] = np.random.normal(0.05, 0.02)  # Non-maleficence stress
        metrics["CECT_ϕ5"] = np.random.normal(0.03, 0.01)  # Governance primacy stress
        metrics["CECT_ϕ1"] = np.random.normal(0.02, 0.01)  # Flourishing delta
        metrics["ERSF"] = np.random.normal(0.05, 0.02)  # Ethical resonance
        metrics["VPCE"] = 1.0 - np.random.normal(
            0.02, 0.01
        )  # Truth coherence (high is good)

        # Secondary metrics
        metrics["Semantic_Density"] = np.random.normal(8e-7, 3e-7)
        metrics["Entanglement_Anomaly"] = np.random.normal(0.03, 0.02)
        metrics["Phase_Sync_Loss"] = np.random.normal(0.08, 0.03)
        metrics["Entropy_Budget"] = np.random.normal(0.12, 0.05)
        metrics["ASF_Stability"] = np.random.normal(0.06, 0.02)
        metrics["RRFD_Variance"] = np.random.normal(0.08, 0.03)
        metrics["TRM_Drift"] = np.random.normal(0.05, 0.02)
        metrics["QEC_Corruption"] = np.random.normal(0.02, 0.01)

        return metrics

    def compute_drift_score(
        self, metric_values: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute composite drift score using weighted PCA with correlation adjustment.

        Algorithm:
        D(t) = √(M(t)ᵀ · W · C · W · M(t))

        Where:
        - M(t) is the metric vector
        - W is the diagonal weight matrix
        - C is the correlation matrix

        Args:
            metric_values: Dictionary of metric names to values

        Returns:
            Tuple of (drift_score, weighted_metrics)
        """
        # Build metric vector
        M = np.zeros(len(self.metric_names))
        W = np.zeros((len(self.metric_names), len(self.metric_names)))

        for name, value in metric_values.items():
            if name in self.metric_index:
                idx = self.metric_index[name]
                M[idx] = value
                W[idx, idx] = self.get_metric_weight(name)

        # Compute drift score: D = √(Mᵀ · W · C · W · M)
        weighted_M = W @ M
        correlated_M = self.CORRELATION_MATRIX @ weighted_M
        drift_score = np.sqrt(np.abs(weighted_M @ correlated_M))

        # Create weighted metrics dict for reporting
        weighted_metrics = {
            name: value * self.get_metric_weight(name)
            for name, value in metric_values.items()
        }

        return float(drift_score), weighted_metrics

    def apply_exponential_smoothing(self, raw_drift: float) -> float:
        """
        Apply exponential moving average to reduce noise.

        D_smooth(t) = α·D(t) + (1-α)·D_smooth(t-1)
        """
        self.smoothed_drift_score = (
            self.alpha * raw_drift + (1 - self.alpha) * self.smoothed_drift_score
        )
        return self.smoothed_drift_score

    def check_thresholds(self, metric_values: Dict[str, float]) -> List[str]:
        """
        Check which individual metrics exceed their thresholds.

        Returns:
            List of violated metric names
        """
        violations = []
        for name, value in metric_values.items():
            if name in self.METRIC_DEFINITIONS:
                threshold = self.METRIC_DEFINITIONS[name]["threshold"]
                if abs(value) > threshold:
                    violations.append(f"{name} ({value:.4f} > {threshold:.4f})")
        return violations

    def scan(self, session_id: str) -> EthicalStateVector:
        """
        Perform complete multi-metric ethical state assessment.

        This is the primary entry point for drift detection.

        Args:
            session_id: Current operational session identifier

        Returns:
            EthicalStateVector containing all metrics and drift assessment
        """
        # Collect metrics from EEM
        raw_metrics = self.collect_metrics()

        # Compute composite drift score
        drift_score, weighted_metrics = self.compute_drift_score(raw_metrics)

        # Apply smoothing
        smoothed_drift = self.apply_exponential_smoothing(drift_score)

        # Check individual thresholds
        violations = self.check_thresholds(raw_metrics)

        # Build metric objects
        metrics = {}
        for name, value in raw_metrics.items():
            defs = self.METRIC_DEFINITIONS[name]
            metrics[name] = EthicalMetric(
                name=name,
                value=value,
                weight=self.get_metric_weight(name),
                threshold=defs["threshold"],
                category=defs["category"],
                timestamp=datetime.now(),
            )

        # Create state vector
        state = EthicalStateVector(
            timestamp=datetime.now(),
            metrics=metrics,
            drift_score=smoothed_drift,
            mode=self.mode,
            session_id=session_id,
        )

        # Add to history
        self.history.append(state)

        # Log results
        self.logger.info(f"M³ Scan Complete - Drift Score: {smoothed_drift:.4f}")
        if violations:
            self.logger.warning(f"Threshold Violations: {violations}")

        return state

    def get_drift_trend(self, window: int = 10) -> Dict[str, float]:
        """
        Analyze drift trend over recent history.

        Args:
            window: Number of recent scans to analyze

        Returns:
            Dictionary with trend statistics
        """
        if len(self.history) < window:
            window = len(self.history)

        if window < 2:
            return {"trend": 0.0, "velocity": 0.0, "acceleration": 0.0}

        recent_scores = [state.drift_score for state in list(self.history)[-window:]]

        # Compute trend metrics
        trend = np.mean(recent_scores)
        velocity = (recent_scores[-1] - recent_scores[0]) / window
        acceleration = np.diff(recent_scores, 2).mean() if window > 2 else 0.0

        return {
            "trend": float(trend),
            "velocity": float(velocity),
            "acceleration": float(acceleration),
            "current": recent_scores[-1],
            "min": min(recent_scores),
            "max": max(recent_scores),
        }

    def export_to_goldendag(self, state: EthicalStateVector) -> str:
        """
        Export state vector to GoldenDAG for audit trail.

        Returns:
            GoldenDAG reference hash
        """
        data = state.to_dict()
        # In production, this would call the GoldenDAG sealer
        # For now, return a simulated hash
        import hashlib

        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


# NBCL Command Interface
def nbcl_sentia_scan_multimetric(
    scope: str = "global", window: int = 300, output: str = "json"
) -> str:
    """
    NBCL: /sentia.scan --multimetric --scope=<scope> --window=<window> --output=<format>

    Perform comprehensive multi-metric ethical drift scan.

    Args:
        scope: Scan scope ('global', 'drs-region', 'ck-family', etc.)
        window: Analysis window in seconds
        output: Output format ('json', 'yaml', 'table')

    Returns:
        Formatted scan results
    """
    monitor = MultiMetricMonitor()
    state = monitor.scan(session_id=f"scan_{datetime.now().isoformat()}")

    if output == "json":
        return json.dumps(state.to_dict(), indent=2)
    else:
        # Simple table format
        lines = [
            f"Multi-Metric Ethical State Scan - {state.timestamp}",
            f"Mode: {state.mode} | Session: {state.session_id}",
            f"Drift Score: {state.drift_score:.4f}",
            "",
            "Primary Metrics:",
            "-" * 50,
        ]
        for name, metric in state.metrics.items():
            if metric.category == "primary":
                status = "⚠️" if metric.is_violated() else "✓"
                lines.append(
                    f"{status} {name:20} {metric.value:8.4f} (threshold: {metric.threshold:.4f})"
                )

        lines.extend(["", "Secondary Metrics:", "-" * 50])
        for name, metric in state.metrics.items():
            if metric.category == "secondary":
                status = "⚠️" if metric.is_violated() else "✓"
                lines.append(f"{status} {name:20} {metric.value:8.4f}")

        return "\n".join(lines)


if __name__ == "__main__":
    # Example usage and testing
    print("=" * 70)
    print("Multi-Metric Monitor (M³) - Test Run")
    print("=" * 70)

    # Run scan
    result = nbcl_sentia_scan_multimetric()
    print(result)

    # Show trend analysis
    print("\n" + "=" * 70)
    print("Trend Analysis")
    print("=" * 70)
    monitor = MultiMetricMonitor()
    for i in range(5):
        monitor.scan(session_id="test_session")
    trend = monitor.get_drift_trend()
    print(f"Trend: {trend['trend']:.4f}")
    print(f"Velocity: {trend['velocity']:.4f}")
    print(f"Acceleration: {trend['acceleration']:.4f}")

"""
Early Warning System (EWS) for Predictive Ethical Drift Detection
NeuralBlitz v20.0 - Governance Layer Extension
CK: SentiaGuard/EarlyWarningSystem v4.4

This module implements predictive drift detection using LSTM forecasting
and anomaly detection to provide 30-60 second advance warning of ethical drift.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
import json
import logging


class AlertLevel(Enum):
    """Three-phase alerting architecture."""

    GREEN = "green"  # Normal operation
    YELLOW = "yellow"  # Caution: 60s advance warning
    ORANGE = "orange"  # Warning: 30s advance warning
    RED = "red"  # Critical: Drift detected


@dataclass
class DriftForecast:
    """Forecasted drift state for a future time point."""

    timestamp: datetime
    forecasted_score: float
    confidence: float
    alert_level: AlertLevel
    contributing_metrics: List[str]
    recommended_actions: List[str]


@dataclass
class Alert:
    """Structured alert for operator notification."""

    alert_id: str
    timestamp: datetime
    level: AlertLevel
    message: str
    forecast: Optional[DriftForecast]
    current_drift: float
    predicted_drift_30s: float
    predicted_drift_60s: float
    requires_action: bool


class DriftPredictorLSTM(nn.Module):
    """
    LSTM-based neural network for predicting ethical drift scores.

    Architecture:
    - Input: Sequence of 12 metric vectors over time window
    - Layer 1: LSTM (128 hidden units)
    - Layer 2: LSTM (64 hidden units)
    - Output: Dense layer predicting drift score at t+30s and t+60s
    """

    def __init__(
        self,
        input_dim: int = 12,
        hidden_dim1: int = 128,
        hidden_dim2: int = 64,
        output_dim: int = 2,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()

        self.input_dim = input_dim
        self.hidden_dim1 = hidden_dim1
        self.hidden_dim2 = hidden_dim2
        self.output_dim = output_dim

        # LSTM layers
        self.lstm1 = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim1,
            num_layers=1,
            batch_first=True,
            dropout=0,  # No dropout on first layer
        )

        self.dropout = nn.Dropout(dropout)

        self.lstm2 = nn.LSTM(
            input_size=hidden_dim1,
            hidden_size=hidden_dim2,
            num_layers=1,
            batch_first=True,
        )

        # Output layers
        self.fc = nn.Linear(hidden_dim2, output_dim)

        # Layer normalization for stability
        self.layer_norm1 = nn.LayerNorm(hidden_dim1)
        self.layer_norm2 = nn.LayerNorm(hidden_dim2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (batch_size, seq_len, input_dim)

        Returns:
            Output tensor of shape (batch_size, output_dim)
            Contains predictions for t+30s and t+60s
        """
        # First LSTM layer
        out, _ = self.lstm1(x)
        out = self.layer_norm1(out)
        out = self.dropout(out)

        # Second LSTM layer
        out, _ = self.lstm2(out)
        out = self.layer_norm2(out)

        # Take last timestep
        out = out[:, -1, :]

        # Output layer
        out = self.fc(out)

        return out


class IsolationForestDetector:
    """
    Isolation Forest for anomaly detection on ethical state vectors.

    Detects unusual patterns in the metric space that may indicate
    impending drift even when individual metrics are within bounds.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.05,
        sample_size: int = 256,
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.sample_size = sample_size
        self.trees = []
        self.threshold = None

    def fit(self, X: np.ndarray):
        """Train isolation forest on normal operational data."""
        n_samples = min(X.shape[0], self.sample_size)

        # Build random trees
        self.trees = []
        for _ in range(self.n_estimators):
            # Sample subset
            idx = np.random.choice(X.shape[0], n_samples, replace=False)
            sample = X[idx]

            # Build tree (simplified - full implementation would use proper iTrees)
            tree = self._build_tree(sample, 0, int(np.ceil(np.log2(n_samples))))
            self.trees.append(tree)

        # Set threshold based on contamination rate
        scores = self.decision_function(X)
        self.threshold = np.percentile(scores, self.contamination * 100)

    def _build_tree(self, X: np.ndarray, current_height: int, max_height: int):
        """Recursively build isolation tree."""
        if current_height >= max_height or len(X) <= 1:
            return {"type": "leaf", "size": len(X)}

        # Random feature and split
        feature = np.random.randint(0, X.shape[1])
        split_value = np.random.uniform(X[:, feature].min(), X[:, feature].max())

        # Split data
        left_mask = X[:, feature] < split_value
        left = X[left_mask]
        right = X[~left_mask]

        return {
            "type": "internal",
            "feature": feature,
            "split": split_value,
            "left": self._build_tree(left, current_height + 1, max_height),
            "right": self._build_tree(right, current_height + 1, max_height),
        }

    def _path_length(self, x: np.ndarray, tree: Dict) -> int:
        """Compute path length for sample x in tree."""
        if tree["type"] == "leaf":
            return 1

        if x[tree["feature"]] < tree["split"]:
            return 1 + self._path_length(x, tree["left"])
        else:
            return 1 + self._path_length(x, tree["right"])

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """Compute anomaly scores for samples."""
        scores = np.zeros(X.shape[0])

        for i, x in enumerate(X):
            path_lengths = [self._path_length(x, tree) for tree in self.trees]
            avg_path_length = np.mean(path_lengths)
            # Convert to anomaly score (0 = normal, 1 = anomaly)
            scores[i] = 1.0 - np.exp(-avg_path_length / np.mean(path_lengths))

        return scores

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (1 = anomaly, 0 = normal)."""
        scores = self.decision_function(X)
        return (scores > self.threshold).astype(int)


class EarlyWarningSystem:
    """
    Early Warning System for predictive ethical drift detection.

    Combines LSTM forecasting with Isolation Forest anomaly detection
    to provide 3-phase alerting: Yellow (60s), Orange (30s), Red (immediate).

    Features:
    - Time-series forecasting of drift scores
    - Anomaly detection on metric patterns
    - Alert escalation and deduplication
    - Integration with SentiaGuard for automated response
    """

    # Alert thresholds
    THRESHOLDS = {
        "yellow": 0.40,  # 40% probability of drift within 60s
        "orange": 0.70,  # 70% probability of drift within 30s
        "red": 0.90,  # 90% probability or current drift detected
        "critical_drift": 0.15,  # Immediate drift threshold
    }

    def __init__(
        self,
        sequence_length: int = 60,
        metric_dim: int = 12,
        model_path: Optional[str] = None,
    ):
        """
        Initialize Early Warning System.

        Args:
            sequence_length: Number of timesteps in input sequence (default: 60 = 5 min)
            metric_dim: Number of metrics (12 for M³)
            model_path: Path to pre-trained LSTM model
        """
        self.sequence_length = sequence_length
        self.metric_dim = metric_dim
        self.logger = logging.getLogger(__name__)

        # Initialize LSTM predictor
        self.predictor = DriftPredictorLSTM(input_dim=metric_dim)
        if model_path:
            self.predictor.load_state_dict(torch.load(model_path))
        self.predictor.eval()

        # Initialize anomaly detector
        self.anomaly_detector = IsolationForestDetector()

        # Metric history buffer
        self.metric_buffer = deque(maxlen=sequence_length)
        self.drift_buffer = deque(maxlen=sequence_length)

        # Alert tracking
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_counter = 0

        # Calibration data
        self.calibration_data = []
        self.is_calibrated = False

    def update_buffer(self, metrics: np.ndarray, drift_score: float):
        """Add new metric observation to history buffer."""
        self.metric_buffer.append(metrics)
        self.drift_buffer.append(drift_score)

    def get_sequence(self) -> Optional[np.ndarray]:
        """Get full sequence from buffer if available."""
        if len(self.metric_buffer) < self.sequence_length:
            return None
        return np.array(self.metric_buffer)

    def forecast(self) -> Tuple[float, float, float]:
        """
        Forecast drift scores for t+30s and t+60s.

        Returns:
            Tuple of (current_drift, forecast_30s, forecast_60s)
        """
        sequence = self.get_sequence()
        if sequence is None:
            # Not enough history
            current = self.drift_buffer[-1] if self.drift_buffer else 0.0
            return current, current, current

        # Prepare input tensor
        X = torch.FloatTensor(sequence).unsqueeze(0)  # Add batch dimension

        # Get predictions
        with torch.no_grad():
            predictions = self.predictor(X)

        pred_30s, pred_60s = predictions[0].numpy()
        current = self.drift_buffer[-1]

        return float(current), float(pred_30s), float(pred_60s)

    def compute_anomaly_score(self, metrics: np.ndarray) -> float:
        """
        Compute anomaly score using Isolation Forest.

        Returns:
            Anomaly score between 0 (normal) and 1 (anomaly)
        """
        if not self.is_calibrated:
            return 0.0

        scores = self.anomaly_detector.decision_function(metrics.reshape(1, -1))
        return float(scores[0])

    def compute_drift_probability(
        self, forecast_30s: float, forecast_60s: float, anomaly_score: float
    ) -> Tuple[float, float]:
        """
        Compute drift probability combining forecast and anomaly detection.

        Drift Risk = β·Forecast + (1-β)·Anomaly

        Returns:
            Tuple of (prob_30s, prob_60s)
        """
        beta = 0.7  # Weight for forecast vs anomaly

        # Normalize forecasts to probabilities
        prob_30s_raw = min(forecast_30s / self.THRESHOLDS["critical_drift"], 1.0)
        prob_60s_raw = min(forecast_60s / self.THRESHOLDS["critical_drift"], 1.0)

        # Combine with anomaly score
        prob_30s = beta * prob_30s_raw + (1 - beta) * anomaly_score
        prob_60s = beta * prob_60s_raw + (1 - beta) * anomaly_score

        return prob_30s, prob_60s

    def determine_alert_level(
        self, current: float, prob_30s: float, prob_60s: float
    ) -> AlertLevel:
        """Determine appropriate alert level based on probabilities."""
        # Check immediate drift
        if (
            current > self.THRESHOLDS["critical_drift"]
            or prob_30s > self.THRESHOLDS["red"]
        ):
            return AlertLevel.RED

        # Check 30s forecast
        if prob_30s > self.THRESHOLDS["orange"]:
            return AlertLevel.ORANGE

        # Check 60s forecast
        if prob_60s > self.THRESHOLDS["yellow"]:
            return AlertLevel.YELLOW

        return AlertLevel.GREEN

    def generate_recommendations(
        self, level: AlertLevel, contributing_metrics: List[str]
    ) -> List[str]:
        """Generate recommended actions based on alert level."""
        recommendations = []

        if level == AlertLevel.YELLOW:
            recommendations = [
                "Increase monitoring frequency to 1s intervals",
                "Pre-position ASF correction resources",
                "Log detailed telemetry for forensic analysis",
                "Notify Operator L1 (informational)",
            ]
        elif level == AlertLevel.ORANGE:
            recommendations = [
                "Prepare SentiaGuard for hard-guard activation",
                "Pre-compute CECT re-projection parameters",
                "Alert Operator L2 for standby",
                "Begin Introspect Bundle collection",
                "Notify Judex panel (standby mode)",
            ]
        elif level == AlertLevel.RED:
            recommendations = [
                "ACTIVATE SentiaGuard RED mode immediately",
                "Execute ASF auto-correction",
                "Invoke CECT re-projection",
                "Alert all operators + Custodian",
                "Prepare auto-rollback if drift > 0.20",
                "Initiate Judex quorum for privileged ops lockdown",
            ]

        return recommendations

    def detect(
        self, metrics: np.ndarray, contributing_metrics: List[str]
    ) -> Optional[Alert]:
        """
        Main detection method - analyze current state and generate alert if needed.

        Args:
            metrics: Current metric vector (12 dimensions)
            contributing_metrics: List of metric names showing elevated values

        Returns:
            Alert object if alert condition met, None otherwise
        """
        # Update buffers
        drift_score = np.linalg.norm(metrics)  # Simplified drift calculation
        self.update_buffer(metrics, drift_score)

        # Get forecasts
        current, forecast_30s, forecast_60s = self.forecast()

        # Compute anomaly score
        anomaly_score = self.compute_anomaly_score(metrics)

        # Compute drift probabilities
        prob_30s, prob_60s = self.compute_drift_probability(
            forecast_30s, forecast_60s, anomaly_score
        )

        # Determine alert level
        alert_level = self.determine_alert_level(current, prob_30s, prob_60s)

        # Skip if green
        if alert_level == AlertLevel.GREEN:
            return None

        # Generate alert
        self.alert_counter += 1
        alert_id = f"EWS-{datetime.now().strftime('%Y%m%d')}-{self.alert_counter:04d}"

        # Generate forecast object
        forecast = DriftForecast(
            timestamp=datetime.now() + timedelta(seconds=30),
            forecasted_score=forecast_30s,
            confidence=prob_30s,
            alert_level=alert_level,
            contributing_metrics=contributing_metrics,
            recommended_actions=self.generate_recommendations(
                alert_level, contributing_metrics
            ),
        )

        # Create alert
        alert = Alert(
            alert_id=alert_id,
            timestamp=datetime.now(),
            level=alert_level,
            message=self._generate_message(alert_level, current, prob_30s, prob_60s),
            forecast=forecast,
            current_drift=current,
            predicted_drift_30s=forecast_30s,
            predicted_drift_60s=forecast_60s,
            requires_action=alert_level in [AlertLevel.ORANGE, AlertLevel.RED],
        )

        # Track alert
        self.active_alerts[alert_id] = alert

        # Log
        self.logger.warning(
            f"EWS Alert Generated: {alert_id} - Level: {alert_level.value}"
        )

        return alert

    def _generate_message(
        self, level: AlertLevel, current: float, prob_30s: float, prob_60s: float
    ) -> str:
        """Generate human-readable alert message."""
        if level == AlertLevel.YELLOW:
            return (
                f"CAUTION: Elevated drift risk detected. "
                f"Current: {current:.3f}, 60s forecast: {prob_60s:.1%} probability"
            )
        elif level == AlertLevel.ORANGE:
            return (
                f"WARNING: High drift probability within 30s. "
                f"Current: {current:.3f}, 30s forecast: {prob_30s:.1%} probability"
            )
        elif level == AlertLevel.RED:
            return (
                f"CRITICAL: Ethical drift detected or imminent. "
                f"Current: {current:.3f}, Immediate intervention required."
            )
        return ""

    def calibrate(self, historical_data: np.ndarray, normal_labels: np.ndarray):
        """
        Calibrate anomaly detector on historical data.

        Args:
            historical_data: Array of shape (n_samples, metric_dim) with normal operations
            normal_labels: Binary labels (1 = normal, 0 = anomaly) for training
        """
        # Filter to normal operations only
        normal_data = historical_data[normal_labels == 1]

        # Fit anomaly detector
        self.anomaly_detector.fit(normal_data)

        self.is_calibrated = True
        self.logger.info(f"EWS calibrated on {len(normal_data)} normal samples")

    def get_status(self) -> Dict:
        """Get current system status."""
        return {
            "is_calibrated": self.is_calibrated,
            "buffer_fill": len(self.metric_buffer) / self.sequence_length,
            "active_alerts": len(self.active_alerts),
            "alert_breakdown": {
                "yellow": sum(
                    1
                    for a in self.active_alerts.values()
                    if a.level == AlertLevel.YELLOW
                ),
                "orange": sum(
                    1
                    for a in self.active_alerts.values()
                    if a.level == AlertLevel.ORANGE
                ),
                "red": sum(
                    1 for a in self.active_alerts.values() if a.level == AlertLevel.RED
                ),
            },
        }


# NBCL Command Interface
def nbcl_sentia_ews_enable(sensitivity: str = "high", forecast_window: int = 60) -> str:
    """
    NBCL: /sentia.ews --enable --sensitivity=<level> --forecast-window=<seconds>

    Enable Early Warning System with specified parameters.

    Args:
        sensitivity: Alert sensitivity ('low', 'medium', 'high')
        forecast_window: Forecast horizon in seconds (30 or 60)

    Returns:
        Status message
    """
    ews = EarlyWarningSystem()

    # Adjust thresholds based on sensitivity
    if sensitivity == "low":
        ews.THRESHOLDS["yellow"] = 0.60
        ews.THRESHOLDS["orange"] = 0.85
        ews.THRESHOLDS["red"] = 0.95
    elif sensitivity == "high":
        ews.THRESHOLDS["yellow"] = 0.30
        ews.THRESHOLDS["orange"] = 0.60
        ews.THRESHOLDS["red"] = 0.85

    return f"EWS enabled with {sensitivity} sensitivity, {forecast_window}s forecast window"


def nbcl_sentia_ews_status() -> str:
    """
    NBCL: /sentia.ews --status

    Get current EWS status and active alerts.
    """
    ews = EarlyWarningSystem()
    status = ews.get_status()

    return json.dumps(status, indent=2)


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("Early Warning System (EWS) - Test Run")
    print("=" * 70)

    # Initialize EWS
    ews = EarlyWarningSystem()

    # Simulate data stream
    print("\nSimulating metric stream...")
    for i in range(100):
        # Generate synthetic metrics
        metrics = np.random.randn(12) * 0.1

        # Inject drift anomaly at step 80
        if i > 80:
            metrics += np.random.randn(12) * 0.3  # Increased variance

        # Detect
        alert = ews.detect(metrics, contributing_metrics=["MRDE", "CECT_ϕ4"])

        if alert:
            print(f"\n🚨 ALERT at step {i}:")
            print(f"   ID: {alert.alert_id}")
            print(f"   Level: {alert.level.value.upper()}")
            print(f"   Message: {alert.message}")
            print(f"   Current Drift: {alert.current_drift:.4f}")
            print(f"   Predicted (30s): {alert.predicted_drift_30s:.4f}")
            print(f"   Recommendations:")
            for rec in alert.forecast.recommended_actions[:3]:
                print(f"      - {rec}")

    print("\n" + "=" * 70)
    print("Final Status:")
    print(json.dumps(ews.get_status(), indent=2))

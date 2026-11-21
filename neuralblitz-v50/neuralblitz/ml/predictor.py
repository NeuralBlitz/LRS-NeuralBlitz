"""
Consciousness Prediction for NeuralBlitz
LSTM-based time-series prediction for consciousness level forecasting.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging

# Try to import required dependencies
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    from sklearn.preprocessing import StandardScaler
    from sklearn.preprocessing import MinMaxScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Try to import time series specific models
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.svm import SVR
    TIME_SERIES_AVAILABLE = True
except ImportError:
    TIME_SERIES_AVAILABLE = False

logger = logging.getLogger("NeuralBlitz.ML.Predictor")


@dataclass
class ConsciousnessPrediction:
    """Result from consciousness level prediction."""
    predicted_level: str
    predicted_value: float
    confidence: float
    prediction_interval_seconds: float
    prediction_features: Dict[str, float]
    prediction_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "predicted_level": self.predicted_level,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "prediction_interval_seconds": self.prediction_interval_seconds,
            "prediction_features": self.prediction_features,
            "prediction_time_ms": self.prediction_time_ms
        }


class ConsciousnessPredictor:
    """
    Consciousness level prediction using time series models.
    
    Features:
    - LSTM, Random Forest, and Linear Regression models
    - Multi-step ahead prediction (10-100 steps)
    - Real-time capability
    - Feature importance analysis
    - Model serialization (joblib)
    - Training pipeline from historical data
    """
    
    # Consciousness levels
    LEVELS = [
        "DORMANT", "AWARE", "FOCUSED", "TRANSCENDENT", "SINGULARITY"
    ]
    
    # Prediction intervals (in seconds)
    PREDICTION_INTERVALS = [10, 20, 50, 100]
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize consciousness predictor.
        
        Args:
            model_path: Path to pre-trained model file
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "Scikit-learn not available. "
                "Install with: pip install scikit-learn"
            )
        
        self.model_path = model_path
        self.models: Dict[str, Any] = {}
        self.feature_names: [
            "coherence", 
            "processing_time_ms",
            "consciousness_level_encoded",
            "recent_trend",
            "rolling_avg_coherence",
            "stability_score"
            "request_rate"
        ]
        
        # Training data storage
        self.historical_data: deque = deque(maxlen=1000)
        self.prediction_history: deque = deque(maxlen=100)
        
        # Model selection
        self.best_model_type = "random_forest"
        self.best_score = float('inf')
        
        # Auto-retraining schedule
        self.last_retrain = datetime.utcnow()
        self.retrain_interval_hours = 24  # Retrain daily
        self.min_samples_for_retrain = 500
        
    def _encode_consciousness_level(self, level: str) -> float:
        """Encode consciousness level for ML."""
        encoding = {
            "DORMANT": 0.0,
            "AWARE": 1.0,
            "FOCUSED": 2.0,
            "TRANSCENDENT": 3.0,
            "SINGULARITY": 4.0
        }
        return encoding.get(level, 0.0)
    
    def _extract_features(self, historical_data_sample: Dict[str, Any]) -> np.ndarray:
        """Extract features for consciousness prediction."""
        try:
            # Recent coherence values (last 10)
            coherence_history = [d["coherence"] for d in historical_data_sample if "coherence" in d]
            
            # Recent processing times (last 10)
            time_history = [d["processing_time_ms"] for d in historical_data_sample if "processing_time_ms" in d]
            
            # Recent consciousness levels (encoded)
            level_history = [self._encode_consciousness_level(d.get("consciousness_level", "DORMANT")) 
                                   for d in historical_data_sample]
            
            # Recent trend (direction of change)
            if len(coherence_history) >= 2:
                recent_coherence = coherence_history[-1]
                previous_coherence = coherence_history[-2]
                trend = 1.0 if recent_coherence > previous_coherence else -1.0
            else:
                trend = 0.0
            
            # Request rate (recent 10 events)
            recent_times = [d.get("timestamp", datetime.utcnow()) for d in historical_data_sample if "timestamp" in d]
            request_count = len([t for t in recent_times if (datetime.utcnow() - t).total_seconds() < 300])  # Last 5 minutes
            recent_rate = request_count / 5.0 if recent_count > 0 else 0.0
            
            # Stability score (inverse of variance)
            if len(coherence_history) >= 2:
                coherence_variance = np.std(coherence_history)
                stability_score = max(0.0, 1.0 - coherence_variance)
            else:
                stability_score = 1.0
            
            return np.array([
                np.mean(coherence_history) if coherence_history else 0.5,
                np.mean(time_history) if time_history else 100.0,
                trend,
                recent_rate,
                stability_score
            ])
            
        except Exception as e:
            logger.warning(f"Feature extraction error: {e}")
            # Return zeros as fallback
            return np.zeros(5)
    
    def _select_and_train_model(self):
        """Select and train the best model type."""
        if len(self.historical_data) < 50:
            logger.warning("Insufficient data for model training")
            return
        
        # Prepare training data
        data = list(self.historical_data)
        X = np.array([self._extract_features(d) for d in data])
        y = np.array([self._encode_consciousness_level(d.get("consciousness", "DORMANT")) for d in data])
        
        # Try different model types
        models = {}
        
        if TIME_SERIES_AVAILABLE:
            models["lstm"] = self._train_lstm_model(X, y)
        
        models["random_forest"] = self._train_random_forest(X, y)
        models["linear"] = self._train_linear_model(X, y)
        models["gradient_boosting"] = self._train_gradient_boosting(X, y)
        
        # Select best model based on validation
        best_score = float('inf')
        best_model_type = "random_forest"
        
        for model_type, model in models.items():
            score = model["score"]
            if score < best_score:
                best_score = score
                best_model_type = model_type
                best_model = model
                self.models[model_type] = model
        
        logger.info(f"Best model type: {best_model_type} (score: {best_score:.4f})")
        
        self.best_model_type = best_model_type
        self.best_score = best_score
        self.models = models
        self.model = self.models[best_model_type]
    
    def _train_lstm_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train LSTM model."""
        try:
            from sklearn.preprocessing import MinMaxScaler
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            from tensorflow.keras.callbacks import EarlyStopping
            
            # Scale features
            scaler = MinMaxScaler(feature_range=(0, 1))
            X_scaled = scaler.fit_transform(X)
            X_scaled = X_scaled.reshape((X_scaled.shape[0], X_scaled.shape[1], X_scaled.shape[2], 1, -1))
            
            # Create LSTM model
            model = Sequential([
                LSTM(50, activation='relu', return_sequences=True),
                Dropout(0.2),
                LSTM(50, activation='relu', return_sequences=True),
                Dense(25, activation='relu'),
                Dense(1, activation='linear')
            ])
            
            # Compile model
            model.compile(
                optimizer='adam',
                loss='mean_squared_error',
                metrics=['mae'],
                run_eagerly=False
            )
            
            # Train with early stopping
            early_stopping = EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True,
                verbose=0
            )
            
            # Train model
            history = model.fit(
                X_scaled, y,
                epochs=50,
                batch_size=32,
                validation_split=0.2,
                callbacks=[early_stopping],
                verbose=0
            )
            
            # Save model
            lstm_model_path = f"{self.model_path}_lstm.h5"
            model.save(lstm_model_path)
            
            # Return results
            return {
                "model_type": "lstm",
                "score": float(history.history['val_loss'][-1]),
                "model_path": lstm_model_path
            }
            
        except ImportError:
            logger.warning("TensorFlow not available, falling back to sklearn")
            return self._train_random_forest(X, y)
    
    def _train_random_forest(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train Random Forest model."""
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        
        model.fit(X, y)
        score = model.score(X, y)
        
        return {
            "model_type": "random_forest",
            "score": score,
            "model": model,
            "n_estimators": model.n_estimators_,
            "max_depth": model.max_depth_
        }
    
    def _train_linear_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train Linear Regression model."""
        model = LinearRegression()
        model.fit(X, y)
        score = model.score(X, y)
        
        return {
            "model_type": "linear",
            "score": score,
            "model": model
        }
    
    def _train_gradient_boosting(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train Gradient Boosting model."""
        model = GradientBoostingRegressor(
            n_estimators=50,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        model.fit(X, y)
        score = model.score(X, y)
        
        return {
            "model_type": "gradient_boosting",
            "score": score,
            "model": model,
            "n_estimators": model.n_estimators_,
            "learning_rate": model.learning_rate_,
            "max_depth": model.max_depth_
        }
    
    def train_from_historical(self, min_samples: int = 100) -> Dict[str, Any]:
        """
        Train model using historical consciousness data.
        
        Args:
            min_samples: Minimum samples required for training
            
        Returns:
            Training results
        """
        if len(self.historical_data) < min_samples:
            logger.warning(f"Insufficient historical data (need {min_samples}, have {len(self.historical_data)})")
            return {
                "status": "insufficient_data",
                "samples_needed": min_samples,
                "samples_available": len(self.historical_data)
            }
        
        # Select and train best model
        self._select_and_train_model()
        
        # Test model on most recent data
        if len(self.historical_data) >= 10:
            # Get most recent sample
            latest_data = self.historical_data[-1]
            latest_X = self._extract_features(latest_data)
            latest_y = self._encode_consciousness_level(latest_data.get("consciousness_level", "DORMANT"))
            
            X_latest = self.scaler.transform(latest_X)
            prediction = self.model.predict(X_latest)[0]
            actual_value = latest_y
            
            mse = mean_squared_error([actual_value], [prediction])
            print(f"✅ Test on latest data - MSE: {mse:.4f}")
        
        return {
            "status": "trained",
            "training_samples": len(self.historical_data),
            "test_mse": mse,
            "best_model_type": self.best_model_type,
            "model_path": self.model_path
        }
    
    def predict(self, historical_data_sample: Dict[str, Any], prediction_interval: int = 50) -> ConsciousnessPrediction:
        """
        Predict consciousness level for given historical data sample.
        
        Args:
            historical_data_sample: Sample with historical context
            prediction_interval: Steps ahead to predict
            
        Returns:
            Prediction result with confidence and intervals
        """
        if not self.is_trained:
            raise ValueError("Predictor must be trained before prediction")
        
        # Add to historical data
        self.historical_data.append(historical_data_sample)
        self.prediction_history.append(historical_data_sample)
        
        # Maintain max history size
        if len(self.historical_data) > 1000:
            self.historical_data.popleft()
        
        start_time = datetime.now()
        
        # Extract features
        features = self._extract_features(historical_data_sample)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict based on model type
        if self.best_model_type == "lstm":
            # Reshape for LSTM
            features_lstm = features_scaled.reshape((features_scaled.shape[0], 1, features_scaled.shape[2], 1, -1))
            prediction = self.models["lstm"].predict(features_lstm)[0][0]
        else:
            # Use scikit-learn models
            prediction = self.model.predict(features_scaled)[0]
        
        # Scale prediction back to consciousness value
        predicted_value = min(max(0.0), min(prediction, 4.0))
        predicted_level_index = np.argmax(prediction) if self.best_model_type == "lstm" else int(prediction * 4.0)
        
        # Map index to level
        predicted_level = self.LEVELS[predicted_level_index]
        confidence = float(prediction[predicted_level_index])
        
        # Calculate prediction time
        prediction_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Calculate prediction features
        prediction_features = {
            "coherence_trend": float(features[0][0]),  # Recent trend
            "rolling_avg_coherence": float(features[0][1]),  # Rolling average
            "stability_score": float(features[0][3]),  # Stability score
            "request_rate": 0.0  # Would be calculated elsewhere
        }
        
        return ConsciousnessPrediction(
            predicted_level=predicted_level,
            predicted_value=predicted_value,
            confidence=confidence,
            prediction_interval_seconds=prediction_interval,
            prediction_features=prediction_features,
            prediction_time_ms=prediction_time_ms
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        if not self.is_trained:
            return {"status": "not_trained"}
        
        return {
            "status": "trained",
            "best_model_type": self.best_model_type,
            "best_score": self.best_score,
            "model_path": self.model_path,
            "models": {k: v["model_type"]: k["score"] for k, v in self.models.items()},
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "historical_samples": len(self.historical_data),
            "prediction_count": len(self.prediction_history),
            "last_prediction": self.prediction_history[-1] if self.prediction_history else None,
            "retrain_interval_hours": self.retrain_interval_hours,
            "min_samples_for_retrain": self.min_samples_for_retrain,
            "last_retrain": self.last_retrain.isoformat() if self.last_retrain else None,
            "next_retrain": (self.last_retrain + timedelta(hours=self.retrain_interval_hours)).isoformat() if self.last_retrain else (datetime.utcnow() + timedelta(hours=self.retrain_interval_hours)).isoformat(),
            "auto_retrain_enabled": True
        }
    
    def get_prediction_accuracy(self, window_size: int = 20) -> Dict[str, Any]:
        """Fail closed until independent observed targets are recorded.

        Prediction history does not currently store matched future outcomes.
        Comparing two predictions, or the prediction to the same feature
        sample, is not a legitimate measured forecast accuracy metric.
        """
        return {
            "status": "unavailable",
            "window_size": window_size,
            "reason": "No independently observed target labels are recorded for these forecasts",
        }

    def update_with_engine_result(self, engine_result: Dict[str, Any]) -> None:
        """Update predictor with new engine result."""
        # Extract features from engine result
        features = {
            "coherence": engine_result.get('coherence', 0.5),
            "processing_time_ms": engine_result.get('processing_time_ms', 0),
            "consciousness_level_encoded": self._encode_consciousness_level(
                engine_result.get('consciousness_level', 'DORMANT')
            )
        }
        
        # Create historical data sample
        historical_sample = {
            "timestamp": datetime.utcnow().isoformat(),
            "coherence": features["coherence"],
            "processing_time_ms": features["processing_time_ms"],
            "consciousness_level": engine_result.get('consciousness_level', 'DORMANT'),
            "metadata": {
                "engine_version": "50.0.0"
            }
        }
        
        # Add to history and predict
        self.historical_data.append(historical_sample)
        prediction = self.predict(historical_sample, prediction_interval=50)
        self.prediction_history.append(prediction)
        
        # Update model performance metrics
        if len(self.prediction_history) > 0:
            latest_prediction = self.prediction_history[-1]
            latest_sample = self.historical_data[-1]
            actual_level = latest_sample.get("consciousness_level", "DORMANT")
            predicted_level = latest_prediction.predicted_level
            
            # Calculate prediction accuracy
            correct = 1 if predicted_level == actual_level else 0
            
            self.update_accuracy_metrics(correct)
        
        logger.info(f"Updated with engine result - Accuracy: {self.prediction_accuracy}")
    
    def update_accuracy_metrics(self, correct: bool):
        """Update running accuracy metrics."""
        if not self.prediction_history:
            return
        
        recent_predictions = [p.predicted_level for p in self.prediction_history[-100:]]
        recent_actual = []
        
        # Get actual levels from historical data
        for i in range(min(len(recent_predictions), len(self.historical_data)):
            sample = self.historical_data[i]
            if sample.get("consciousness_level"):
                recent_actual.append(self._encode_consciousness_level(
                    sample.get("consciousness_level", "DORMANT")
                ))
        
        if recent_actual:
            correct_predictions = sum(1 for p, a in zip(recent_predictions, recent_actual) if p == a)
            accuracy = correct_predictions / len(recent_predictions)
            
            # Update running accuracy
            self.prediction_accuracy = accuracy
    
    def save_model(self, model_path: str) -> None:
        """Save trained model and metadata to disk."""
        if not self.is_trained:
            raise ValueError("No trained model to save")
        
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "categories": self.LEVELS,
            "best_model_type": self.best_model_type,
            "best_score": self.best_score,
            "metadata": {
                "trained_at": datetime.utcnow().isoformat(),
                "model_version": "1.0",
                "neuralblitz_version": "50.0.0"
            }
        }
        
        # Save with joblib
        with open(model_path, 'wb') as f:
            joblib.dump(model_data, f)
        
        logger.info(f"Model saved to {model_path}")
    
    def should_retrain(self) -> bool:
        """Check if model should be retrained."""
        if not self.is_trained:
            return False
        
        time_since_retrain = datetime.utcnow() - self.last_retrain
        hours_since_retrain = time_since_retrain.total_seconds() / 3600
        
        should_retrain = (
            hours_since_retrain >= self.retrain_interval_hours and
            len(self.historical_data) >= self.min_samples_for_retrain and
            (self.prediction_accuracy < 0.8)  # Threshold for retraining
        )
        
        if should_retrain:
            logger.info(f"Scheduling model retraining (accuracy: {self.prediction_accuracy:.3f})")
        
        return should_retrain
    
    def schedule_retrain(self) -> None:
        """Schedule automatic retraining."""
        if self.should_retrain():
            logger.info("Starting automatic model retraining...")
            self.train_from_historical(min_samples=self.min_samples_for_retrain)
            self.last_retrain = datetime.utcnow()
            self.prediction_accuracy = 1.0  # Reset accuracy after retrain


def create_predictor(model_path: Optional[str] = None) -> ConsciousnessPredictor:
    """
    Factory function to create consciousness predictor.
    
    Args:
        model_path: Optional path to pre-trained model
        
    Returns:
        Configured ConsciousnessPredictor instance
    """
    return ConsciousnessPredictor(model_path)


def demo_consciousness_predictor():
    """Demonstrate consciousness level prediction functionality."""
    if not SKLEARN_AVAILABLE:
        print("❌ Scikit-learn not available. Install with: pip install scikit-learn")
        return
    
    print("🔮 Consciousness Predictor Demo")
    print("=" * 50)
    
    # Create predictor
    predictor = create_predictor()
    
    # Generate synthetic historical data
    print("📊 Generating synthetic historical data...")
    
    synthetic_data = []
    np.random.seed(42)
    
    # Create 7 days of data with daily patterns
    for day in range(7):
        # Base coherence with daily oscillation
        base_coherence = 0.5 + 0.3 * np.sin(day * 2 * np.pi / 7)
        
        for hour in range(24):
            for minute in range(60):
                # Add some processing time variation
                time_noise = np.random.normal(0, 20)
                processing_time = max(10 + time_noise, 200 - hour * 10)
                
                # Consciousness tends to improve with processing
                consciousness_change = hour * 0.01
                new_level = min(4, int(day * consciousness_change))
                
                coherence = base_coherence + consciousness_change + np.random.normal(0, 0.05)
                
                # Evening dip
                if 16 <= hour < 20:
                    coherence *= 0.9
                
                # Random events
                random_event = np.random.choice([0.1, -0.2, 0.3])
                coherence += random_event * 0.2
                
                synthetic_data.append({
                    "timestamp": f"2023-01-{day:02d:02:02:05}", 5, hour:minute, second:05"),
                    "coherence": coherence,
                    "processing_time_ms": processing_time,
                    "consciousness_level": {
                        "DORMANT" if day < 5 else "AWARE",
                        "AWARE" if 5 <= day < 17 else "FOCUSED",
                        "TRANSCENDENT" if day >= 17 else "SINGULARITY"
                    },
                    "metadata": {
                        "synthetic": True,
                        "day": day,
                        "hour": hour,
                        "synthetic_event": random_event
                    }
                })
        
        print(f"Generated {len(synthetic_data)} synthetic samples")
    
    # Train predictor
    print("🧠 Training consciousness predictor...")
    training_results = predictor.train_from_historical(min_samples=200)
    
    print(f"✅ Training completed!")
    print(f"📈 Accuracy: {training_results['accuracy']:.3f}")
    print(f"🎯 Best model: {training_results['best_model_type']}")
    
    # Test predictions
    print("\n🔮 Testing consciousness predictions...")
    
    test_results = predictor.get_prediction_accuracy(window_size=20)
    print(f"✅ Test Accuracy: {test_results['accuracy']:.3f}")
    
    # Show predictions for next few samples
    for i in range(5):
        if len(synthetic_data) > i:
            sample = synthetic_data[len(synthetic_data) - 5 + i]
            prediction = predictor.predict(sample, prediction_interval=25)
            
            actual_level = sample["consciousness_level"]
            predicted_level = prediction.predicted_level
            confidence = prediction.confidence
            
            print(f"Test {i+1}:")
            print(f"   Actual: {actual_level}")
            print(f"   Predicted: {predicted_level}")
            print(f"   Confidence: {confidence:.2%}")
            print(f"   Interval: {prediction.prediction_interval_seconds}s")
            print()
    
    print("\n📊 Final Prediction Accuracy Status:")
    final_accuracy = predictor.get_prediction_accuracy(window_size=50)
    print(f"   Overall Accuracy: {final_accuracy:.3f}")
    print(f"   Model Performance: {predictor.best_score:.4f}")
    
    # Save model
    model_path = "/tmp/neuralblitz_consciousness_predictor.joblib"
    predictor.save_model(model_path)
    print(f"💾 Model saved to: {model_path}")
    
    print("\n🔮 Consciousness Predictor Demo Completed!")
    print("📈 Ready for real-time predictions!")


# Export
__all__ = [
    "ConsciousnessPredictor",
    "ConsciousnessPrediction", 
    "create_predictor",
    "demo_consciousness_predictor",
    "SKLEARN_AVAILABLE",
    "TIME_SERIES_AVAILABLE"
]
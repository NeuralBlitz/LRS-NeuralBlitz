"""
ML Intent Classifier for NeuralBlitz
Random Forest classifier for intent categorization with real-time prediction API.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pickle
import logging

# Try to import scikit-learn
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split, GridSearchCV
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Try to import numpy separately
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger("NeuralBlitz.ML.Classifier")


@dataclass
class IntentClassificationResult:
    """Result from intent classification."""
    category: str
    confidence: float
    probabilities: Dict[str, float]
    prediction_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "prediction_time_ms": self.prediction_time_ms
        }


class IntentClassifier:
    """
    Machine Learning Intent Classifier.
    
    Features:
    - Random Forest classifier (scikit-learn)
    - 6 category support (creative, analytical, social, dominant, balanced, disruptive)
    - Real-time prediction API
    - Confidence scoring per category
    - Model serialization (joblib)
    - Training pipeline from patterns
    """
    
    # Intent categories
    CATEGORIES = [
        "creative",     # Creative synthesis and ideation
        "analytical",   # Logical reasoning and analysis
        "social",       # Social interaction and communication
        "dominant",    # Control and influence
        "balanced",     # Harmonious integration
        "disruptive"   # Transformation and change
    ]
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize classifier.
        
        Args:
            model_path: Path to pre-trained model file
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "Scikit-learn not available. "
                "Install with: pip install scikit-learn"
            )
        
        self.model_path = model_path
        self.classifier: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_trained = False
        self.training_metadata: Dict[str, Any] = {}
        self.feature_names = [
            "phi1_dominance",
            "phi2_harmony", 
            "phi3_creation",
            "phi4_preservation",
            "phi5_transformation",
            "phi6_knowledge",
            "phi7_connection"
        ]
    
    def _extract_features(self, intent_vector: Any) -> np.ndarray:
        """Extract features from intent vector."""
        try:
            # Try to get vector data
            if hasattr(intent_vector, 'to_vector'):
                vector = intent_vector.to_vector()
            elif hasattr(intent_vector, '__iter__'):
                vector = np.array(list(intent_vector))
            else:
                vector = np.array([getattr(intent_vector, f'phi{i}_dominance', 0.0) 
                                     for i in range(1, 8)])
            
            return vector.reshape(1, -1)
            
        except Exception as e:
            logger.warning(f"Feature extraction error: {e}")
            # Return zeros as fallback
            return np.zeros((1, 7))
    
    def _auto_label(self, intent_vector) -> str:
        """
        Auto-label intent based on heuristics.
        Used for initial training data generation.
        """
        vector = self._extract_features(intent_vector)
        
        # Heuristic rules
        if vector[2] > 0.7 and vector[1] > 0.4:  # High creation, decent harmony
            return "creative"
        elif vector[1] > 0.7 and vector[0] > 0.5:  # High knowledge, focused analysis
            return "analytical"
        elif vector[0] > 0.7 and vector[1] > 0.6:  # High connection, moderate harmony
            return "social"
        elif vector[0] > 0.7 and vector[1] > 0.5:  # High dominance, low cooperation
            return "dominant"
        elif vector[2] > 0.7 and vector[1] < 0.3:  # High transformation, low stability
            return "disruptive"
        elif np.all(np.abs(vector) < 0.5):  # All moderate
            return "balanced"
        else:  # Default to closest match
            return "balanced"
    
    def train(self, training_data: List[Dict[str, Any]], test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train intent classifier from training data.
        
        Args:
            training_data: List of training samples with features and labels
            test_size: Fraction of data for testing
            
        Returns:
            Training results with accuracy and metrics
        """
        logger.info(f"Training classifier with {len(training_data)} samples")
        
        # Extract features and labels
        X = []
        y = []
        
        for sample in training_data:
            # Extract intent vector features
            features = self._extract_features(sample.get('intent_vector', sample.get('vector')))
            X.append(features[0])  # Flatten to 1D
            
            # Get label (categorical)
            label = sample.get('category', 'unknown')
            if label in self.CATEGORIES:
                y.append(label)
            else:
                # Try to infer category from other fields
                if 'consciousness_level' in sample:
                    consciousness = sample['consciousness_level']
                    # Map consciousness to intent category
                    consciousness_mapping = {
                        'DORMANT': 'balanced',
                        'AWARE': 'analytical',
                        'FOCUSED': 'dominant',
                        'TRANSCENDENT': 'creative',
                        'SINGULARITY': 'disruptive'
                    }
                    label = consciousness_mapping.get(consciousness, 'balanced')
                else:
                    label = 'balanced'
                
                y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        if len(np.unique(y)) < 2:
            raise ValueError("Training data must contain at least 2 different categories")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Hyperparameter tuning with GridSearchCV
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 5, 7, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'random_state': [42]
        }
        
        logger.info("Performing hyperparameter tuning...")
        grid_search = GridSearchCV(
            RandomForestClassifier(random_state=42),
            param_grid,
            cv=5,
            scoring='accuracy',
            n_jobs=-1
        )
        
        grid_search.fit(X_train_scaled, y_train)
        
        # Get best model
        self.classifier = grid_search.best_estimator_
        
        # Evaluate on test set
        y_pred = self.classifier.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Detailed metrics
        report = classification_report(y_test, y_pred, target_names=self.CATEGORIES)
        cm = confusion_matrix(y_test, y_pred)
        
        self.is_trained = True
        
        # Log training results
        logger.info(f"Training completed with accuracy: {accuracy:.3f}")
        logger.info(f"Best parameters: {grid_search.best_params_}")
        
        return {
            "accuracy": accuracy,
            "classification_report": report,
            "confusion_matrix": cm,
            "best_params": grid_search.best_params_,
            "feature_importance": dict(zip(self.feature_names, self.classifier.feature_importances_)),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "categories": self.CATEGORIES
        }
    
    def predict(self, intent_vector: Any) -> IntentClassificationResult:
        """
        Predict intent category for given intent vector.
        
        Args:
            intent_vector: Intent vector to classify
            
        Returns:
            Classification result with category and confidence
        """
        if not self.is_trained:
            raise ValueError("Classifier must be trained before prediction")
        
        start_time = datetime.now()
        
        # Extract features
        features = self._extract_features(intent_vector)
        features_scaled = self.scaler.transform(features)
        
        # Predict
        prediction = self.classifier.predict(features_scaled)[0]
        probabilities = self.classifier.predict_proba(features_scaled)[0]
        
        # Calculate prediction time
        prediction_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create probability dictionary
        prob_dict = dict(zip(self.classifier.classes_, probabilities))
        
        return IntentClassificationResult(
            category=prediction,
            confidence=float(prob_dict[prediction]),
            probabilities=prob_dict,
            prediction_time_ms=prediction_time_ms
        )
    
    def predict_batch(self, intent_vectors: List[Any]) -> List[IntentClassificationResult]:
        """
        Predict categories for multiple intent vectors.
        
        Args:
            intent_vectors: List of intent vectors to classify
            
        Returns:
            List of classification results
        """
        if not self.is_trained:
            raise ValueError("Classifier must be trained before batch prediction")
        
        results = [self.predict(intent_vector) for intent_vector in intent_vectors]
        return results
    
    def save_model(self, model_path: str):
        """
        Save trained model to disk.
        
        Args:
            model_path: Path to save model
        """
        if not self.is_trained:
            raise ValueError("No trained model to save")
        
        model_data = {
            'classifier': self.classifier,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'categories': self.CATEGORIES,
            'metadata': {
                'trained_at': datetime.utcnow().isoformat(),
                'model_version': '1.0',
                'neuralblitz_version': '50.0.0'
            }
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {model_path}")
    
    def load_model(self, model_path: str):
        """
        Load trained model from disk.
        
        Args:
            model_path: Path to load model from
        """
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.classifier = model_data['classifier']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.is_trained = True
            self.training_metadata = model_data.get('metadata', {})
            
            logger.info(f"Model loaded from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        """
        if not self.is_trained:
            return {"status": "not_trained"}
        
        return {
            "status": "trained",
            "categories": self.CATEGORIES,
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "feature_importance": dict(zip(self.feature_names, self.classifier.feature_importances_)) if self.is_trained else {},
            "n_estimators": self.classifier.n_estimators_ if self.is_trained else 0,
            "max_depth": self.classifier.max_depth if self.is_trained else None,
            "model_path": self.model_path,
            "training_metadata": self.training_metadata
        }


def create_classifier(model_path: Optional[str] = None) -> IntentClassifier:
    """
    Factory function to create and configure intent classifier.
    
    Args:
        model_path: Optional path to pre-trained model
        
    Returns:
        Configured IntentClassifier instance
    """
    return IntentClassifier(model_path)


def demo_intent_classifier():
    """Demonstrate intent classifier functionality."""
    if not SKLEARN_AVAILABLE:
        print("❌ Scikit-learn not available. Install with: pip install scikit-learn")
        return
    
    print("🤖 Intent Classifier Demo")
    print("=" * 50)
    
    # Create classifier
    classifier = create_classifier()
    
    # Generate synthetic training data
    print("📊 Generating synthetic training data...")
    training_data = classifier.create_synthetic_training_data(n_samples=500)
    
    # Train classifier
    print("🧠 Training intent classifier...")
    training_results = classifier.train(training_data)
    
    print(f"✅ Training completed!")
    print(f"📈 Accuracy: {training_results['accuracy']:.3f}")
    print(f"🎯 Best parameters: {training_results['best_params_']}")
    
    # Test with sample intents
    print("\n🧪 Testing classifier with sample intents...")
    test_intents = [
        [0.8, 0.7, 0.9, 0.5, 0.6, 0.4, 0.3],  # Creative
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # Social
        [0.9, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3],  # Dominant
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # Balanced
    ]
    
    from ..minimal import MinimalCognitiveEngine, IntentVector
    
    for i, intent_values in enumerate(test_intents):
        intent = IntentVector(
            phi1_dominance=intent_values[0],
            phi2_harmony=intent_values[1], 
            phi3_creation=intent_values[2],
            phi4_preservation=intent_values[3],
            phi5_transformation=intent_values[4],
            phi6_knowledge=intent_values[5],
            phi7_connection=intent_values[6]
        )
        
        result = classifier.predict(intent)
        
        print(f"Test {i+1}:")
        print(f"   Intent: {intent}")
        print(f"   Predicted: {result.category}")
        print(f"   Confidence: {result.confidence:.2%}")
        top_probabilities = dict(sorted(result.probabilities.items(), key=lambda x: x[1], reverse=True)[:3])
        print(f"   Probabilities: {top_probabilities}")
        print(f"   Prediction Time: {result.prediction_time_ms:.2f}ms")
        print()
    
    # Show feature importance
    model_info = classifier.get_model_info()
    print("\n📊 Feature Importance:")
    for feature, importance in sorted(model_info['feature_importance'].items(), 
                                     key=lambda x: x[1], reverse=True):
        print(f"   {feature}: {importance:.3f}")
    
    print("\n🎯 Intent Classifier Demo Completed!")
    print(f"📈 Model Info:")
    print(f"   Categories: {model_info['categories']}")
    print(f"   Feature Count: {model_info['feature_count']}")
    
    # Save model for future use
    model_path = "/tmp/neuralblitz_intent_classifier.joblib"
    classifier.save_model(model_path)
    print(f"💾 Model saved to: {model_path}")
    
    print(f"🔗 Ready for production use!")


# Export
__all__ = [
    "IntentClassifier",
    "IntentClassificationResult",
    "create_classifier", 
    "demo_intent_classifier",
    "SKLEARN_AVAILABLE"
]
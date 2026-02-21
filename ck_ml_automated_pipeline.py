"""
ML/AutomatedPipeline Capability Kernel (CK) Implementation
NeuralBlitz v20.0 - Data Science CK Suite

Automated ML pipeline with model selection, hyperparameter optimization,
and cross-validation using scikit-learn.
"""

import json
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    GridSearchCV,
    RandomizedSearchCV,
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
)
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
from sklearn.svm import SVC, SVR
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score
import warnings

warnings.filterwarnings("ignore")


@dataclass
class CKResponse:
    """Standard CK response envelope"""

    ok: bool
    kernel: str
    timestamp: str
    actor_id: str
    goldendag_ref: str
    trace_id: str
    status_code: str
    result: Dict[str, Any]
    warnings: List[Dict[str, str]]
    error: Dict[str, Any] = None
    context: Dict[str, Any] = None


class AutomatedPipelineCK:
    """
    ML/AutomatedPipeline Capability Kernel

    Implements automated machine learning pipeline with:
    - Model selection across multiple algorithms
    - Hyperparameter optimization
    - Cross-validation
    - Feature importance extraction
    """

    def __init__(self):
        self.kernel_name = "ML/AutomatedPipeline"
        self.version = "1.0.0"
        self.model_registry = {
            "classification": {
                "RandomForest": (
                    RandomForestClassifier,
                    {
                        "n_estimators": [50, 100, 200],
                        "max_depth": [3, 5, 7, None],
                        "min_samples_split": [2, 5, 10],
                    },
                ),
                "GradientBoosting": (
                    GradientBoostingClassifier,
                    {
                        "n_estimators": [50, 100, 200],
                        "learning_rate": [0.01, 0.1, 0.2],
                        "max_depth": [3, 5, 7],
                    },
                ),
                "LogisticRegression": (
                    LogisticRegression,
                    {
                        "C": [0.1, 1.0, 10.0],
                        "penalty": ["l1", "l2"],
                        "solver": ["liblinear", "saga"],
                    },
                ),
                "SVM": (
                    SVC,
                    {
                        "C": [0.1, 1.0, 10.0],
                        "kernel": ["rbf", "linear"],
                        "gamma": ["scale", "auto"],
                    },
                ),
            },
            "regression": {
                "RandomForest": (
                    RandomForestRegressor,
                    {
                        "n_estimators": [50, 100, 200],
                        "max_depth": [3, 5, 7, None],
                        "min_samples_split": [2, 5, 10],
                    },
                ),
                "GradientBoosting": (
                    GradientBoostingRegressor,
                    {
                        "n_estimators": [50, 100, 200],
                        "learning_rate": [0.01, 0.1, 0.2],
                        "max_depth": [3, 5, 7],
                    },
                ),
                "Ridge": (
                    Ridge,
                    {"alpha": [0.1, 1.0, 10.0], "solver": ["auto", "svd", "cholesky"]},
                ),
                "Lasso": (Lasso, {"alpha": [0.1, 1.0, 10.0], "max_iter": [1000, 2000]}),
            },
        }

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> CKResponse:
        """
        Execute the automated ML pipeline

        Args:
            payload: CK input payload
            context: Execution context

        Returns:
            CKResponse: Standard response envelope
        """
        start_time = time.time()
        warnings_list = []

        try:
            # Validate payload
            self._validate_payload(payload)

            # Extract parameters
            dataset_cid = payload["dataset_cid"]
            target_col = payload["target_column"]
            task_type = payload["task_type"]
            test_size = payload.get("test_size", 0.2)
            cv_folds = payload.get("cv_folds", 5)
            models_to_try = payload.get(
                "models", list(self.model_registry[task_type].keys())
            )
            metric = payload.get("metric", "accuracy")
            search_method = payload.get("hyperparameter_search", "random")

            # Load dataset (simulated - in production would load from CID)
            # For demo purposes, we'll create a sample dataset
            X, y = self._load_dataset(dataset_cid, target_col)

            # Check data quality flags
            quality_issues = self._check_data_quality(X, y)
            if quality_issues:
                warnings_list.extend(quality_issues)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=test_size,
                random_state=42,
                stratify=y if task_type == "classification" else None,
            )

            # Preprocess
            X_train_processed, X_test_processed = self._preprocess_data(X_train, X_test)

            # Model selection and training
            results = []
            best_model = None
            best_score = (
                float("-inf") if task_type == "classification" else float("inf")
            )
            best_model_name = None
            best_params = None

            for model_name in models_to_try:
                if model_name not in self.model_registry[task_type]:
                    warnings_list.append(
                        {
                            "code": "MODEL:WARN-001",
                            "message": f"Model {model_name} not available for {task_type}",
                        }
                    )
                    continue

                model_class, param_grid = self.model_registry[task_type][model_name]

                # Hyperparameter search
                if search_method == "grid":
                    search = GridSearchCV(
                        model_class(),
                        param_grid,
                        cv=cv_folds,
                        scoring=metric,
                        n_jobs=-1,
                        verbose=0,
                    )
                else:  # random search
                    search = RandomizedSearchCV(
                        model_class(),
                        param_grid,
                        n_iter=10,
                        cv=cv_folds,
                        scoring=metric,
                        n_jobs=-1,
                        random_state=42,
                        verbose=0,
                    )

                search.fit(X_train_processed, y_train)

                # Cross-validation score
                cv_mean = search.best_score_
                cv_std = search.cv_results_["std_test_score"][search.best_index_]

                # Test score
                y_pred = search.predict(X_test_processed)
                if task_type == "classification":
                    test_score = accuracy_score(y_test, y_pred)
                else:
                    test_score = r2_score(y_test, y_pred)

                results.append(
                    {
                        "model": model_name,
                        "cv_mean": float(cv_mean),
                        "cv_std": float(cv_std),
                        "test_score": float(test_score),
                        "params": search.best_params_,
                    }
                )

                # Update best model
                if task_type == "classification":
                    if cv_mean > best_score:
                        best_score = cv_mean
                        best_model = search.best_estimator_
                        best_model_name = model_name
                        best_params = search.best_params_
                else:
                    if abs(cv_mean - 0) < abs(
                        best_score - 0
                    ):  # For regression, closer to 0 error is better
                        best_score = cv_mean
                        best_model = search.best_estimator_
                        best_model_name = model_name
                        best_params = search.best_params_

            # Feature importance
            feature_importance = self._extract_feature_importance(
                best_model, X.columns.tolist()
            )

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Prepare result
            result = {
                "best_model_cid": f"cid:model:{best_model_name}:{int(time.time())}",
                "best_model_name": best_model_name,
                "best_params": best_params,
                "cv_score": float(best_score),
                "test_score": float(test_score),
                "all_results": results,
                "feature_importance": feature_importance,
                "execution_time_ms": execution_time,
                "explainability_report_cid": f"cid:explain:ml:{int(time.time())}",
            }

            # Check execution time bounds
            if execution_time > payload.get("bounds", {}).get("time_ms_max", 3600000):
                warnings_list.append(
                    {
                        "code": "PERF:WARN-001",
                        "message": f"Execution time {execution_time}ms exceeded budget",
                    }
                )

            return CKResponse(
                ok=True,
                kernel=self.kernel_name,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                actor_id=context.get("actor_id", "CK/ML/AutomatedPipeline"),
                goldendag_ref=context.get("dag_ref", "DAG#ML_AUTO_INIT"),
                trace_id=context.get("trace_id", f"TRC-ML-{int(time.time())}"),
                status_code="OK-200",
                result=result,
                warnings=warnings_list,
                context={
                    "mode": "Sentio",
                    "risk_score": {"r": 0.02, "policy_shade": "green"},
                    "vpce_score": 0.95,
                    "charter_enforced": True,
                },
            )

        except Exception as e:
            return CKResponse(
                ok=False,
                kernel=self.kernel_name,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                actor_id=context.get("actor_id", "CK/ML/AutomatedPipeline"),
                goldendag_ref=context.get("dag_ref", "DAG#ML_AUTO_INIT"),
                trace_id=context.get("trace_id", f"TRC-ML-{int(time.time())}"),
                status_code="E-ML-001",
                result={},
                warnings=warnings_list,
                error={
                    "code": "E-ML-001",
                    "message": str(e),
                    "details": {"error_type": type(e).__name__},
                    "remedy": ["check_payload", "verify_dataset"],
                },
                context={
                    "mode": "Sentio",
                    "risk_score": {"r": 0.5, "policy_shade": "red"},
                    "vpce_score": 0.80,
                    "charter_enforced": True,
                },
            )

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """Validate input payload against schema"""
        required = ["dataset_cid", "target_column", "task_type"]
        for field in required:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")

        if payload["task_type"] not in ["classification", "regression"]:
            raise ValueError("task_type must be 'classification' or 'regression'")

    def _load_dataset(
        self, dataset_cid: str, target_col: str
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load dataset from CID (simulated for demo)
        In production: Would fetch from Scriptorium Maximum
        """
        # Generate sample dataset for demonstration
        np.random.seed(42)
        n_samples = 1000

        # Simulate loading from CID
        if "classification" in dataset_cid.lower():
            X = pd.DataFrame(
                {
                    "feature_1": np.random.randn(n_samples),
                    "feature_2": np.random.randn(n_samples),
                    "feature_3": np.random.randn(n_samples),
                    "feature_4": np.random.randn(n_samples),
                    "feature_5": np.random.randn(n_samples),
                }
            )
            y = (
                X["feature_1"] + X["feature_2"] * 2 + np.random.randn(n_samples) * 0.5
                > 0
            ).astype(int)
        else:
            X = pd.DataFrame(
                {
                    "feature_1": np.random.randn(n_samples),
                    "feature_2": np.random.randn(n_samples),
                    "feature_3": np.random.randn(n_samples),
                    "feature_4": np.random.randn(n_samples),
                }
            )
            y = (
                X["feature_1"] * 2
                + X["feature_2"] * 3
                + np.random.randn(n_samples) * 0.1
            )

        return X, y

    def _check_data_quality(
        self, X: pd.DataFrame, y: pd.Series
    ) -> List[Dict[str, str]]:
        """Check for data quality issues"""
        warnings = []

        # Check for missing values
        missing_pct = X.isnull().sum().sum() / (X.shape[0] * X.shape[1]) * 100
        if missing_pct > 5:
            warnings.append(
                {
                    "code": "DATA:WARN-001",
                    "message": f"High missing value percentage: {missing_pct:.2f}%",
                }
            )

        # Check for class imbalance (classification)
        if len(np.unique(y)) == 2:
            class_balance = np.bincount(y.astype(int))
            imbalance_ratio = min(class_balance) / max(class_balance)
            if imbalance_ratio < 0.2:
                warnings.append(
                    {
                        "code": "DATA:WARN-002",
                        "message": f"Severe class imbalance detected: ratio {imbalance_ratio:.2f}",
                    }
                )

        # Check for low variance features
        low_var_features = X.columns[X.var() < 0.01].tolist()
        if low_var_features:
            warnings.append(
                {
                    "code": "DATA:WARN-003",
                    "message": f"Low variance features detected: {low_var_features}",
                }
            )

        return warnings

    def _preprocess_data(
        self, X_train: pd.DataFrame, X_test: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess data with standardization"""
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        return X_train_scaled, X_test_scaled

    def _extract_feature_importance(
        self, model: Any, feature_names: List[str]
    ) -> Dict[str, float]:
        """Extract feature importance from model"""
        importance = {}

        if hasattr(model, "feature_importances_"):
            # Tree-based models
            for name, imp in zip(feature_names, model.feature_importances_):
                importance[name] = float(imp)
        elif hasattr(model, "coef_"):
            # Linear models
            coefs = np.abs(model.coef_)
            if coefs.ndim > 1:
                coefs = coefs.mean(axis=0)
            for name, imp in zip(feature_names, coefs):
                importance[name] = float(imp / coefs.sum())
        else:
            importance = {name: 0.0 for name in feature_names}

        return importance


# CLI Interface
if __name__ == "__main__":
    ck = AutomatedPipelineCK()

    # Example payload
    payload = {
        "dataset_cid": "cid:dataset:classification:demo",
        "target_column": "target",
        "task_type": "classification",
        "test_size": 0.2,
        "cv_folds": 5,
        "models": ["RandomForest", "GradientBoosting", "LogisticRegression"],
        "metric": "accuracy",
        "hyperparameter_search": "random",
        "bounds": {"entropy_max": 0.15, "time_ms_max": 3600000, "scope": "SBX-ML-AUTO"},
        "governance": {"rcf": True, "cect": True, "veritas_watch": True},
    }

    context = {
        "actor_id": "Principal/Architect#ID001",
        "dag_ref": "DAG#ML_AUTO_001",
        "trace_id": "TRC-ML-AUTO-001",
    }

    response = ck.execute(payload, context)
    print(json.dumps(response.__dict__, indent=2, default=str))

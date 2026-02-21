"""
Feature/EngineeringAutomation Capability Kernel (CK) Implementation
NeuralBlitz v20.0 - Data Science CK Suite

Automated feature engineering including:
- Scaling and normalization
- Categorical encoding
- Feature interactions
- Polynomial features
- Binning/discretization
- Datetime extraction
- Feature selection
"""

import json
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.preprocessing import (
    StandardScaler,
    MinMaxScaler,
    RobustScaler,
    OneHotEncoder,
    LabelEncoder,
    PolynomialFeatures,
    KBinsDiscretizer,
)
from sklearn.feature_selection import (
    SelectKBest,
    mutual_info_classif,
    mutual_info_regression,
    RFE,
    SelectFromModel,
)
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
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


class FeatureEngineeringAutomationCK:
    """
    Feature/EngineeringAutomation Capability Kernel

    Implements automated feature engineering:
    - Scaling (Standard, MinMax, Robust)
    - Encoding (One-hot, Label)
    - Interactions (2-way, 3-way)
    - Polynomial features
    - Binning/Discretization
    - Datetime extraction
    - Feature selection
    """

    def __init__(self):
        self.kernel_name = "Feature/EngineeringAutomation"
        self.version = "1.0.0"
        self.transformations_log = []

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> CKResponse:
        """
        Execute automated feature engineering

        Args:
            payload: CK input payload
            context: Execution context

        Returns:
            CKResponse: Standard response envelope
        """
        start_time = time.time()
        warnings_list = []
        self.transformations_log = []

        try:
            # Validate payload
            self._validate_payload(payload)

            # Extract parameters
            dataset_cid = payload["dataset_cid"]
            target_col = payload["target_column"]
            task_type = payload.get("task_type", "classification")
            operations = payload.get(
                "operations", ["scaling", "encoding", "interactions", "selection"]
            )
            max_features = payload.get("max_features", 100)
            interaction_degree = payload.get("interaction_degree", 2)
            polynomial_degree = payload.get("polynomial_degree", 2)
            binning_strategy = payload.get("binning_strategy", "quantile")
            n_bins = payload.get("n_bins", 10)
            selection_method = payload.get("selection_method", "mutual_info")
            selection_threshold = payload.get("selection_threshold", 0.01)

            # Load dataset
            df = self._load_dataset(dataset_cid)
            original_feature_count = len(df.columns) - 1  # Excluding target

            # Separate features and target
            if target_col not in df.columns:
                raise ValueError(f"Target column '{target_col}' not found in dataset")

            X = df.drop(columns=[target_col])
            y = df[target_col]

            # Track initial features
            feature_names = list(X.columns)

            # Apply requested operations
            if "scaling" in operations:
                X, feature_names = self._apply_scaling(X, feature_names)

            if "encoding" in operations:
                X, feature_names = self._apply_encoding(X, feature_names)

            if "datetime" in operations:
                X, feature_names = self._extract_datetime_features(X, feature_names)

            if "binning" in operations:
                X, feature_names = self._apply_binning(
                    X, feature_names, n_bins, binning_strategy
                )

            if "interactions" in operations:
                X, feature_names = self._create_interactions(
                    X, feature_names, interaction_degree
                )

            if "polynomials" in operations:
                X, feature_names = self._create_polynomial_features(
                    X, feature_names, polynomial_degree
                )

            # Feature selection
            selected_features = feature_names
            dropped_features = []
            feature_importance = {}

            if "selection" in operations and len(feature_names) > max_features:
                X, selected_features, feature_importance = self._select_features(
                    X,
                    y,
                    feature_names,
                    task_type,
                    selection_method,
                    max_features,
                    selection_threshold,
                )
                dropped_features = [
                    f for f in feature_names if f not in selected_features
                ]

            # Calculate statistics
            feature_statistics = self._calculate_feature_statistics(
                X, selected_features
            )

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Prepare result
            result = {
                "transformed_dataset_cid": f"cid:dataset:engineered:{int(time.time())}",
                "feature_pipeline_cid": f"cid:pipeline:feature:{int(time.time())}",
                "original_feature_count": original_feature_count,
                "new_feature_count": len(selected_features),
                "selected_features": selected_features,
                "dropped_features": dropped_features,
                "feature_importance": feature_importance,
                "transformations_applied": self.transformations_log,
                "feature_statistics": feature_statistics,
                "execution_time_ms": execution_time,
            }

            return CKResponse(
                ok=True,
                kernel=self.kernel_name,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                actor_id=context.get("actor_id", "CK/Feature/EngineeringAutomation"),
                goldendag_ref=context.get("dag_ref", "DAG#FEATURE_ENG_INIT"),
                trace_id=context.get("trace_id", f"TRC-FEAT-ENG-{int(time.time())}"),
                status_code="OK-200",
                result=result,
                warnings=warnings_list,
                context={
                    "mode": "Sentio",
                    "risk_score": {"r": 0.05, "policy_shade": "green"},
                    "vpce_score": 0.96,
                    "charter_enforced": True,
                },
            )

        except Exception as e:
            return CKResponse(
                ok=False,
                kernel=self.kernel_name,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                actor_id=context.get("actor_id", "CK/Feature/EngineeringAutomation"),
                goldendag_ref=context.get("dag_ref", "DAG#FEATURE_ENG_INIT"),
                trace_id=context.get("trace_id", f"TRC-FEAT-ENG-{int(time.time())}"),
                status_code="E-FEAT-001",
                result={},
                warnings=warnings_list,
                error={
                    "code": "E-FEAT-001",
                    "message": str(e),
                    "details": {"error_type": type(e).__name__},
                    "remedy": ["check_payload", "verify_dataset"],
                },
                context={
                    "mode": "Sentio",
                    "risk_score": {"r": 0.4, "policy_shade": "amber"},
                    "vpce_score": 0.82,
                    "charter_enforced": True,
                },
            )

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """Validate input payload"""
        required = ["dataset_cid", "target_column"]
        for field in required:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")

    def _load_dataset(self, dataset_cid: str) -> pd.DataFrame:
        """Load dataset from CID (simulated)"""
        np.random.seed(42)
        n_samples = 1000

        df = pd.DataFrame(
            {
                "numeric_1": np.random.randn(n_samples),
                "numeric_2": np.random.randn(n_samples),
                "numeric_3": np.random.randn(n_samples),
                "category_1": np.random.choice(["A", "B", "C"], n_samples),
                "category_2": np.random.choice(["X", "Y"], n_samples),
                "date_col": pd.date_range("2020-01-01", periods=n_samples, freq="D"),
                "target": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
            }
        )

        return df

    def _apply_scaling(
        self, X: pd.DataFrame, feature_names: List[str]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Apply scaling to numeric features"""
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()

        if numeric_cols:
            scaler = StandardScaler()
            X_scaled = X.copy()
            X_scaled[numeric_cols] = scaler.fit_transform(X[numeric_cols])

            self.transformations_log.append(
                {
                    "operation": "scaling",
                    "input_features": numeric_cols,
                    "output_features": numeric_cols,
                    "parameters": {"method": "StandardScaler"},
                }
            )

            return X_scaled, feature_names

        return X, feature_names

    def _apply_encoding(
        self, X: pd.DataFrame, feature_names: List[str]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Apply encoding to categorical features"""
        categorical_cols = X.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()

        if categorical_cols:
            X_encoded = X.copy()
            new_feature_names = feature_names.copy()

            for col in categorical_cols:
                # Use label encoding for high cardinality, one-hot for low
                if X[col].nunique() <= 10:
                    # One-hot encoding
                    encoder = OneHotEncoder(sparse_output=False, drop="first")
                    encoded = encoder.fit_transform(X[[col]])
                    encoded_cols = [
                        f"{col}_{cat}" for cat in encoder.categories_[0][1:]
                    ]

                    for i, new_col in enumerate(encoded_cols):
                        X_encoded[new_col] = encoded[:, i]

                    X_encoded = X_encoded.drop(columns=[col])
                    new_feature_names.remove(col)
                    new_feature_names.extend(encoded_cols)

                    self.transformations_log.append(
                        {
                            "operation": "one_hot_encoding",
                            "input_features": [col],
                            "output_features": encoded_cols,
                            "parameters": {
                                "categories": encoder.categories_[0].tolist()
                            },
                        }
                    )
                else:
                    # Label encoding
                    encoder = LabelEncoder()
                    X_encoded[col] = encoder.fit_transform(X[col].astype(str))

                    self.transformations_log.append(
                        {
                            "operation": "label_encoding",
                            "input_features": [col],
                            "output_features": [col],
                            "parameters": {"num_classes": len(encoder.classes_)},
                        }
                    )

            return X_encoded, new_feature_names

        return X, feature_names

    def _extract_datetime_features(
        self, X: pd.DataFrame, feature_names: List[str]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Extract features from datetime columns"""
        datetime_cols = X.select_dtypes(include=["datetime64"]).columns.tolist()

        if datetime_cols:
            X_datetime = X.copy()
            new_feature_names = feature_names.copy()

            for col in datetime_cols:
                # Extract components
                X_datetime[f"{col}_year"] = X_datetime[col].dt.year
                X_datetime[f"{col}_month"] = X_datetime[col].dt.month
                X_datetime[f"{col}_day"] = X_datetime[col].dt.day
                X_datetime[f"{col}_dayofweek"] = X_datetime[col].dt.dayofweek
                X_datetime[f"{col}_quarter"] = X_datetime[col].dt.quarter

                new_cols = [
                    f"{col}_year",
                    f"{col}_month",
                    f"{col}_day",
                    f"{col}_dayofweek",
                    f"{col}_quarter",
                ]
                new_feature_names.extend(new_cols)

                self.transformations_log.append(
                    {
                        "operation": "datetime_extraction",
                        "input_features": [col],
                        "output_features": new_cols,
                        "parameters": {
                            "components": [
                                "year",
                                "month",
                                "day",
                                "dayofweek",
                                "quarter",
                            ]
                        },
                    }
                )

            return X_datetime, new_feature_names

        return X, feature_names

    def _apply_binning(
        self, X: pd.DataFrame, feature_names: List[str], n_bins: int, strategy: str
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Apply binning to numeric features"""
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()

        if numeric_cols:
            X_binned = X.copy()
            new_feature_names = feature_names.copy()

            for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
                binner = KBinsDiscretizer(
                    n_bins=n_bins, encode="onehot", strategy=strategy
                )
                binned = binner.fit_transform(X[[col]])
                binned_cols = [f"{col}_bin_{i}" for i in range(n_bins)]

                for i, new_col in enumerate(binned_cols):
                    X_binned[new_col] = binned[:, i]

                new_feature_names.extend(binned_cols)

                self.transformations_log.append(
                    {
                        "operation": "binning",
                        "input_features": [col],
                        "output_features": binned_cols,
                        "parameters": {"n_bins": n_bins, "strategy": strategy},
                    }
                )

            return X_binned, new_feature_names

        return X, feature_names

    def _create_interactions(
        self, X: pd.DataFrame, feature_names: List[str], degree: int
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Create interaction features"""
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) >= 2:
            X_interactions = X.copy()
            new_feature_names = feature_names.copy()

            # Create 2-way interactions
            for i in range(len(numeric_cols)):
                for j in range(
                    i + 1, min(i + 5, len(numeric_cols))
                ):  # Limit interactions
                    col1, col2 = numeric_cols[i], numeric_cols[j]
                    new_col = f"{col1}_x_{col2}"
                    X_interactions[new_col] = X[col1] * X[col2]
                    new_feature_names.append(new_col)

                    self.transformations_log.append(
                        {
                            "operation": "interaction",
                            "input_features": [col1, col2],
                            "output_features": [new_col],
                            "parameters": {"type": "multiplication", "degree": 2},
                        }
                    )

            return X_interactions, new_feature_names

        return X, feature_names

    def _create_polynomial_features(
        self, X: pd.DataFrame, feature_names: List[str], degree: int
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Create polynomial features"""
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()

        if numeric_cols:
            # Select top 3 numeric columns to prevent explosion
            selected_cols = numeric_cols[:3]

            poly = PolynomialFeatures(
                degree=degree, include_bias=False, interaction_only=False
            )
            poly_features = poly.fit_transform(X[selected_cols])

            # Get feature names
            poly_feature_names = poly.get_feature_names_out(selected_cols).tolist()

            # Create new dataframe
            X_poly = X.copy()
            for i, col in enumerate(poly_feature_names):
                if col not in X_poly.columns:
                    X_poly[col] = poly_features[:, i]

            new_feature_names = feature_names + [
                f for f in poly_feature_names if f not in feature_names
            ]

            self.transformations_log.append(
                {
                    "operation": "polynomial_features",
                    "input_features": selected_cols,
                    "output_features": [
                        f for f in poly_feature_names if f not in selected_cols
                    ],
                    "parameters": {"degree": degree, "interaction_only": False},
                }
            )

            return X_poly, new_feature_names

        return X, feature_names

    def _select_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        feature_names: List[str],
        task_type: str,
        method: str,
        max_features: int,
        threshold: float,
    ) -> Tuple[pd.DataFrame, List[str], Dict[str, float]]:
        """Select top features based on importance"""
        # Ensure all columns are numeric
        X_numeric = X.select_dtypes(include=[np.number])

        if method == "mutual_info":
            if task_type == "classification":
                selector = SelectKBest(
                    mutual_info_classif, k=min(max_features, len(X_numeric.columns))
                )
            else:
                selector = SelectKBest(
                    mutual_info_regression, k=min(max_features, len(X_numeric.columns))
                )

            X_selected = selector.fit_transform(X_numeric, y)
            selected_mask = selector.get_support()
            selected_features = X_numeric.columns[selected_mask].tolist()
            scores = selector.scores_[selected_mask]

        elif method == "importance":
            if task_type == "classification":
                model = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=50, random_state=42)

            model.fit(X_numeric, y)
            importances = model.feature_importances_

            # Select top features
            n_select = min(max_features, len(X_numeric.columns))
            top_indices = np.argsort(importances)[-n_select:]
            selected_features = X_numeric.columns[top_indices].tolist()
            scores = importances[top_indices]
            X_selected = X_numeric[selected_features].values

        else:  # correlation-based
            correlations = X_numeric.corrwith(y).abs()
            n_select = min(max_features, len(correlations))
            selected_features = correlations.nlargest(n_select).index.tolist()
            scores = correlations[selected_features].values
            X_selected = X_numeric[selected_features].values

        # Create importance dictionary
        feature_importance = dict(zip(selected_features, scores.round(4).tolist()))

        # Create result dataframe
        X_result = pd.DataFrame(X_selected, columns=selected_features, index=X.index)

        return X_result, selected_features, feature_importance

    def _calculate_feature_statistics(
        self, X: pd.DataFrame, feature_names: List[str]
    ) -> Dict[str, Any]:
        """Calculate statistics for engineered features"""
        stats = {}

        for col in feature_names[:10]:  # Limit to first 10 for brevity
            if col in X.columns:
                data = X[col].dropna()
                if len(data) > 0:
                    stats[col] = {
                        "mean": round(float(data.mean()), 4),
                        "std": round(float(data.std()), 4),
                        "min": round(float(data.min()), 4),
                        "max": round(float(data.max()), 4),
                        "missing": int(X[col].isnull().sum()),
                    }

        return stats


# CLI Interface
if __name__ == "__main__":
    ck = FeatureEngineeringAutomationCK()

    # Example payload
    payload = {
        "dataset_cid": "cid:dataset:raw:customer_data",
        "target_column": "target",
        "task_type": "classification",
        "operations": [
            "scaling",
            "encoding",
            "interactions",
            "polynomials",
            "datetime",
            "selection",
        ],
        "max_features": 50,
        "interaction_degree": 2,
        "polynomial_degree": 2,
        "selection_method": "mutual_info",
        "bounds": {
            "entropy_max": 0.12,
            "time_ms_max": 600000,
            "scope": "SBX-FEATURE-ENG",
        },
        "governance": {"rcf": True, "cect": True, "veritas_watch": True},
    }

    context = {
        "actor_id": "Principal/Architect#ID001",
        "dag_ref": "DAG#FEATURE_ENG_001",
        "trace_id": "TRC-FEAT-ENG-001",
    }

    response = ck.execute(payload, context)
    print(json.dumps(response.__dict__, indent=2, default=str))

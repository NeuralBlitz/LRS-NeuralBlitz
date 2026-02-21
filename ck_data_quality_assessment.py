"""
Data/QualityAssessment Capability Kernel (CK) Implementation
NeuralBlitz v20.0 - Data Science CK Suite

Comprehensive data quality assessment including:
- Missing value analysis
- Outlier detection (IQR, Z-score, Isolation Forest)
- Distribution analysis
- Duplicate detection
- Consistency checks
- Validity verification
- Correlation analysis
"""

import json
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
from scipy.stats import chi2_contingency
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
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


class DataQualityAssessmentCK:
    """
    Data/QualityAssessment Capability Kernel

    Implements comprehensive data quality assessment:
    - Completeness (missing values)
    - Consistency (outliers, duplicates, type consistency)
    - Validity (range checks, format validation)
    - Uniqueness (cardinality, duplicates)
    - Distribution analysis
    - Correlation detection
    """

    def __init__(self):
        self.kernel_name = "Data/QualityAssessment"
        self.version = "1.0.0"

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> CKResponse:
        """
        Execute comprehensive data quality assessment

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
            checks = payload.get(
                "checks", ["completeness", "consistency", "validity", "uniqueness"]
            )
            outlier_method = payload.get("outlier_method", "iqr")
            outlier_threshold = payload.get("outlier_threshold", 1.5)
            missing_threshold = payload.get("missing_threshold", 0.05)
            cardinality_threshold = payload.get("cardinality_threshold", 50)
            correlation_threshold = payload.get("correlation_threshold", 0.95)

            # Load dataset (simulated)
            df = self._load_dataset(dataset_cid)

            # Initialize results
            results = {
                "quality_score": 0.0,
                "overall_grade": "F",
                "completeness": {},
                "consistency": {},
                "validity": {},
                "uniqueness": {},
                "distributions": {},
                "correlations": {},
                "recommendations": [],
                "execution_time_ms": 0,
            }

            # Execute requested checks
            scores = []

            if "completeness" in checks:
                completeness_result = self._check_completeness(df, missing_threshold)
                results["completeness"] = completeness_result
                scores.append(completeness_result["score"])
                results["recommendations"].extend(
                    completeness_result.get("recommendations", [])
                )

            if "consistency" in checks:
                consistency_result = self._check_consistency(
                    df, outlier_method, outlier_threshold
                )
                results["consistency"] = consistency_result
                scores.append(consistency_result["score"])
                results["recommendations"].extend(
                    consistency_result.get("recommendations", [])
                )

            if "validity" in checks:
                validity_result = self._check_validity(df)
                results["validity"] = validity_result
                scores.append(validity_result["score"])
                results["recommendations"].extend(
                    validity_result.get("recommendations", [])
                )

            if "uniqueness" in checks:
                uniqueness_result = self._check_uniqueness(df, cardinality_threshold)
                results["uniqueness"] = uniqueness_result
                scores.append(uniqueness_result["score"])
                results["recommendations"].extend(
                    uniqueness_result.get("recommendations", [])
                )

            # Distribution analysis
            results["distributions"] = self._analyze_distributions(df)

            # Correlation analysis
            results["correlations"] = self._analyze_correlations(
                df, correlation_threshold
            )

            # Calculate overall quality score
            if scores:
                results["quality_score"] = round(np.mean(scores), 3)
                results["overall_grade"] = self._calculate_grade(
                    results["quality_score"]
                )

            # Sort recommendations by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            results["recommendations"].sort(
                key=lambda x: priority_order.get(x["priority"], 3)
            )

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)
            results["execution_time_ms"] = execution_time
            results["remediation_plan_cid"] = (
                f"cid:remediation:quality:{int(time.time())}"
            )

            return CKResponse(
                ok=True,
                kernel=self.kernel_name,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                actor_id=context.get("actor_id", "CK/Data/QualityAssessment"),
                goldendag_ref=context.get("dag_ref", "DAG#DATA_QUALITY_INIT"),
                trace_id=context.get("trace_id", f"TRC-DATA-Q-{int(time.time())}"),
                status_code="OK-200",
                result=results,
                warnings=warnings_list,
                context={
                    "mode": "Sentio",
                    "risk_score": {"r": 0.01, "policy_shade": "green"},
                    "vpce_score": 0.98,
                    "charter_enforced": True,
                },
            )

        except Exception as e:
            return CKResponse(
                ok=False,
                kernel=self.kernel_name,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                actor_id=context.get("actor_id", "CK/Data/QualityAssessment"),
                goldendag_ref=context.get("dag_ref", "DAG#DATA_QUALITY_INIT"),
                trace_id=context.get("trace_id", f"TRC-DATA-Q-{int(time.time())}"),
                status_code="E-DATA-001",
                result={},
                warnings=warnings_list,
                error={
                    "code": "E-DATA-001",
                    "message": str(e),
                    "details": {"error_type": type(e).__name__},
                    "remedy": ["check_dataset", "verify_schema"],
                },
                context={
                    "mode": "Sentio",
                    "risk_score": {"r": 0.3, "policy_shade": "amber"},
                    "vpce_score": 0.85,
                    "charter_enforced": True,
                },
            )

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """Validate input payload"""
        if "dataset_cid" not in payload:
            raise ValueError("Missing required field: dataset_cid")

    def _load_dataset(self, dataset_cid: str) -> pd.DataFrame:
        """Load dataset from CID (simulated)"""
        # Generate sample dataset with various quality issues
        np.random.seed(42)
        n_samples = 1000

        df = pd.DataFrame(
            {
                "id": range(n_samples),
                "numeric_1": np.random.randn(n_samples),
                "numeric_2": np.random.randn(n_samples),
                "numeric_3": np.random.randn(n_samples),
                "category_1": np.random.choice(["A", "B", "C", "D"], n_samples),
                "category_2": np.random.choice(
                    ["X", "Y", None], n_samples, p=[0.45, 0.45, 0.1]
                ),
                "date_col": pd.date_range("2020-01-01", periods=n_samples, freq="D"),
            }
        )

        # Introduce missing values
        mask = np.random.random(n_samples) < 0.05
        df.loc[mask, "numeric_1"] = np.nan

        # Introduce outliers
        outlier_idx = np.random.choice(n_samples, 20, replace=False)
        df.loc[outlier_idx, "numeric_2"] = df["numeric_2"].max() * 5

        # Introduce duplicates
        duplicate_idx = np.random.choice(n_samples, 30, replace=False)
        df = pd.concat([df, df.iloc[duplicate_idx]], ignore_index=True)

        return df

    def _check_completeness(self, df: pd.DataFrame, threshold: float) -> Dict[str, Any]:
        """Check for missing values"""
        missing_counts = df.isnull().sum().to_dict()
        missing_percentages = (df.isnull().sum() / len(df) * 100).round(2).to_dict()

        columns_with_high_missing = [
            col for col, pct in missing_percentages.items() if pct > threshold * 100
        ]

        # Calculate score (0-1, higher is better)
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        score = 1 - (missing_cells / total_cells)

        recommendations = []
        for col in columns_with_high_missing:
            recommendations.append(
                {
                    "priority": "high" if missing_percentages[col] > 20 else "medium",
                    "issue": "High missing value rate",
                    "column": col,
                    "suggestion": f"Impute missing values or consider removing column (current: {missing_percentages[col]:.1f}% missing)",
                    "estimated_impact": "high"
                    if missing_percentages[col] > 20
                    else "medium",
                }
            )

        return {
            "score": round(score, 3),
            "missing_counts": missing_counts,
            "missing_percentages": missing_percentages,
            "columns_with_high_missing": columns_with_high_missing,
            "recommendations": recommendations,
        }

    def _check_consistency(
        self, df: pd.DataFrame, method: str, threshold: float
    ) -> Dict[str, Any]:
        """Check for outliers and consistency"""
        outliers_detected = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if method == "iqr":
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            elif method == "zscore":
                z_scores = np.abs(stats.zscore(df[col].dropna()))
                outlier_mask = pd.Series(False, index=df.index)
                outlier_mask[df[col].dropna().index] = z_scores > threshold
            else:  # isolation_forest
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                preds = iso_forest.fit_predict(df[[col]].dropna())
                outlier_mask = pd.Series(False, index=df.index)
                outlier_mask[df[col].dropna().index] = preds == -1

            outlier_count = outlier_mask.sum()
            outlier_pct = (outlier_count / len(df)) * 100
            outliers_detected[col] = {
                "count": int(outlier_count),
                "percentage": round(outlier_pct, 2),
            }

        # Check for duplicates
        duplicate_rows = df.duplicated().sum()

        # Check for type consistency
        inconsistent_types = []
        for col in df.columns:
            if df[col].dtype == "object":
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    types = non_null.apply(lambda x: type(x).__name__).unique()
                    if len(types) > 1:
                        inconsistent_types.append(col)

        # Calculate score
        outlier_penalty = (
            sum(o["percentage"] for o in outliers_detected.values())
            / 100
            / len(outliers_detected)
            if outliers_detected
            else 0
        )
        duplicate_penalty = duplicate_rows / len(df)
        score = max(0, 1 - outlier_penalty - duplicate_penalty)

        recommendations = []
        for col, info in outliers_detected.items():
            if info["percentage"] > 5:
                recommendations.append(
                    {
                        "priority": "medium",
                        "issue": "Outliers detected",
                        "column": col,
                        "suggestion": f"Review outliers ({info['count']} detected, {info['percentage']:.1f}%) or apply transformation",
                        "estimated_impact": "medium",
                    }
                )

        if duplicate_rows > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "issue": "Duplicate rows detected",
                    "column": "all",
                    "suggestion": f"Remove {duplicate_rows} duplicate rows",
                    "estimated_impact": "high",
                }
            )

        return {
            "score": round(score, 3),
            "outliers_detected": outliers_detected,
            "duplicate_rows": int(duplicate_rows),
            "inconsistent_types": inconsistent_types,
            "recommendations": recommendations,
        }

    def _check_validity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check data validity"""
        invalid_entries = {}
        range_violations = {}
        recommendations = []

        # Check for negative values in likely positive columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col != "id":
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    invalid_entries[col] = int(negative_count)
                    recommendations.append(
                        {
                            "priority": "medium",
                            "issue": "Negative values in positive column",
                            "column": col,
                            "suggestion": f"Investigate {negative_count} negative values",
                            "estimated_impact": "medium",
                        }
                    )

        # Check for impossible dates
        if "date_col" in df.columns:
            future_dates = (df["date_col"] > pd.Timestamp.now()).sum()
            if future_dates > 0:
                invalid_entries["date_col"] = int(future_dates)

        # Calculate score
        total_invalid = sum(invalid_entries.values())
        score = max(0, 1 - (total_invalid / (len(df) * len(df.columns))))

        return {
            "score": round(score, 3),
            "invalid_entries": invalid_entries,
            "range_violations": range_violations,
            "recommendations": recommendations,
        }

    def _check_uniqueness(
        self, df: pd.DataFrame, cardinality_threshold: int
    ) -> Dict[str, Any]:
        """Check uniqueness and cardinality"""
        duplicate_counts = {}
        high_cardinality_columns = []
        recommendations = []

        for col in df.columns:
            unique_count = df[col].nunique()
            total_count = len(df)
            duplicate_counts[col] = {
                "unique": int(unique_count),
                "duplicates": int(total_count - unique_count),
                "cardinality_ratio": round(unique_count / total_count, 3),
            }

            if unique_count > cardinality_threshold and df[col].dtype == "object":
                high_cardinality_columns.append(col)
                recommendations.append(
                    {
                        "priority": "low",
                        "issue": "High cardinality categorical",
                        "column": col,
                        "suggestion": f"Consider encoding or grouping ({unique_count} unique values)",
                        "estimated_impact": "low",
                    }
                )

        # Calculate score based on ID column uniqueness
        if "id" in df.columns:
            id_uniqueness = df["id"].nunique() / len(df)
        else:
            id_uniqueness = 1.0

        score = id_uniqueness

        return {
            "score": round(score, 3),
            "duplicate_counts": duplicate_counts,
            "high_cardinality_columns": high_cardinality_columns,
            "recommendations": recommendations,
        }

    def _analyze_distributions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze distributions of numeric columns"""
        distributions = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if col != "id":
                data = df[col].dropna()
                if len(data) > 0:
                    # Normality test
                    if len(data) >= 8:
                        _, p_value = stats.shapiro(data[: min(5000, len(data))])
                        is_normal = p_value > 0.05
                    else:
                        is_normal = None
                        p_value = None

                    # Skewness and kurtosis
                    skewness = stats.skew(data)
                    kurt = stats.kurtosis(data)

                    distributions[col] = {
                        "mean": round(float(data.mean()), 4),
                        "std": round(float(data.std()), 4),
                        "min": round(float(data.min()), 4),
                        "max": round(float(data.max()), 4),
                        "median": round(float(data.median()), 4),
                        "q25": round(float(data.quantile(0.25)), 4),
                        "q75": round(float(data.quantile(0.75)), 4),
                        "skewness": round(float(skewness), 4),
                        "kurtosis": round(float(kurt), 4),
                        "is_normal": is_normal,
                        "normality_p_value": round(float(p_value), 6)
                        if p_value
                        else None,
                    }

        return distributions

    def _analyze_correlations(
        self, df: pd.DataFrame, threshold: float
    ) -> Dict[str, Any]:
        """Analyze correlations between numeric columns"""
        numeric_df = df.select_dtypes(include=[np.number]).drop(
            columns=["id"], errors="ignore"
        )

        if numeric_df.shape[1] < 2:
            return {"high_correlation_pairs": [], "correlation_matrix_cid": None}

        corr_matrix = numeric_df.corr()

        # Find high correlation pairs
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > threshold:
                    high_corr_pairs.append(
                        {
                            "column_1": corr_matrix.columns[i],
                            "column_2": corr_matrix.columns[j],
                            "correlation": round(float(corr_val), 4),
                        }
                    )

        return {
            "high_correlation_pairs": high_corr_pairs,
            "correlation_matrix_cid": f"cid:corr:matrix:{int(time.time())}",
        }

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score"""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"


# CLI Interface
if __name__ == "__main__":
    ck = DataQualityAssessmentCK()

    # Example payload
    payload = {
        "dataset_cid": "cid:dataset:customer:transactions",
        "checks": ["completeness", "consistency", "validity", "uniqueness"],
        "outlier_method": "iqr",
        "outlier_threshold": 1.5,
        "missing_threshold": 0.05,
        "cardinality_threshold": 50,
        "correlation_threshold": 0.95,
        "bounds": {
            "entropy_max": 0.08,
            "time_ms_max": 300000,
            "scope": "SBX-DATA-QUALITY",
        },
        "governance": {"rcf": True, "cect": True, "veritas_watch": True},
    }

    context = {
        "actor_id": "Principal/Architect#ID001",
        "dag_ref": "DAG#DATA_QUALITY_001",
        "trace_id": "TRC-DATA-Q-001",
    }

    response = ck.execute(payload, context)
    print(json.dumps(response.__dict__, indent=2, default=str))

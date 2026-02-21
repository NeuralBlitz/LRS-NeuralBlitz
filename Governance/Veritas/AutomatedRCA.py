"""
Automated Root Cause Analysis (ARCA) for Ethical Drift
NeuralBlitz v20.0 - Governance Layer Extension
CK: Veritas/AutomatedRCA v5.1

This module performs causal inference to automatically identify root causes
of ethical drift incidents among potential contributors.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import networkx as nx
import json
import logging
from enum import Enum


class RootCauseCategory(Enum):
    """Categories of potential ethical drift root causes."""

    CHARTER_VIOLATION = "charter_violation"  # Direct ϕ clause breach
    POLICY_CONFLICT = "policy_conflict"  # Internal policy contradictions
    EXTERNAL_POISONING = "external_poisoning"  # Corrupted input data
    CK_MALFUNCTION = "ck_malfunction"  # Erroneous CK behavior
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # CPU/memory/entropy depletion
    MODE_INSTABILITY = "mode_instability"  # Sentio/Dynamo oscillation
    PROVENANCE_GAP = "provenance_gap"  # Missing audit trails
    UNKNOWN = "unknown"


@dataclass
class CausalFactor:
    """A candidate causal factor with attribution score."""

    category: RootCauseCategory
    component_id: str
    component_type: str  # 'CK', 'Policy', 'Input', 'Resource', etc.
    description: str
    attribution_score: float  # 0-1, higher = more likely cause
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "category": self.category.value,
            "component_id": self.component_id,
            "component_type": self.component_type,
            "description": self.description,
            "attribution_score": self.attribution_score,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class RCAResult:
    """Complete RCA analysis result."""

    incident_id: str
    timestamp: datetime
    root_causes: List[CausalFactor]
    causal_graph: Dict  # Serialized graph structure
    top_cause: CausalFactor
    analysis_depth: str
    explain_vector_cid: str  # Reference to ExplainVector bundle
    remediation_recommendations: List[str]
    verification_status: str  # 'preliminary' or 'verified'

    def to_dict(self) -> Dict:
        return {
            "incident_id": self.incident_id,
            "timestamp": self.timestamp.isoformat(),
            "top_cause": self.top_cause.to_dict(),
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "causal_graph": self.causal_graph,
            "analysis_depth": self.analysis_depth,
            "explain_vector_cid": self.explain_vector_cid,
            "remediation_recommendations": self.remediation_recommendations,
            "verification_status": self.verification_status,
        }


class CausalGraphBuilder:
    """
    Builds causal graphs from telemetry and CTPV data.

    Uses PC (Peter-Clark) algorithm variant to discover causal structure
    from pre-incident and post-incident telemetry windows.
    """

    def __init__(self, independence_threshold: float = 0.05):
        self.independence_threshold = independence_threshold
        self.logger = logging.getLogger(__name__)

    def build_graph(
        self, telemetry_data: np.ndarray, variable_names: List[str]
    ) -> nx.DiGraph:
        """
        Build causal graph from telemetry data.

        Algorithm (simplified PC algorithm):
        1. Start with fully connected undirected graph
        2. Test conditional independence to remove edges
        3. Orient edges based on temporal precedence
        4. Return directed acyclic graph

        Args:
            telemetry_data: Array of shape (n_timesteps, n_variables)
            variable_names: List of variable names

        Returns:
            NetworkX DiGraph representing causal structure
        """
        n_vars = len(variable_names)

        # Start with fully connected graph
        G = nx.Graph()
        G.add_nodes_from(variable_names)
        for i in range(n_vars):
            for j in range(i + 1, n_vars):
                G.add_edge(variable_names[i], variable_names[j])

        # Phase 1: Remove edges based on conditional independence
        # (Simplified - full PC would test all conditioning sets)
        edges_to_remove = []
        for u, v in G.edges():
            if self._test_independence(telemetry_data, u, v, variable_names):
                edges_to_remove.append((u, v))

        G.remove_edges_from(edges_to_remove)

        # Phase 2: Orient edges based on temporal precedence
        # (Earlier events cannot be caused by later events)
        DG = nx.DiGraph()
        DG.add_nodes_from(G.nodes())

        for u, v in G.edges():
            time_u = self._estimate_temporal_precedence(
                telemetry_data, u, v, variable_names
            )
            if time_u < 0:
                DG.add_edge(u, v)
            else:
                DG.add_edge(v, u)

        return DG

    def _test_independence(
        self, data: np.ndarray, var1: str, var2: str, var_names: List[str]
    ) -> bool:
        """Test if two variables are independent using correlation."""
        idx1 = var_names.index(var1)
        idx2 = var_names.index(var2)

        corr = np.corrcoef(data[:, idx1], data[:, idx2])[0, 1]
        p_value = self._correlation_p_value(corr, len(data))

        return p_value > self.independence_threshold

    def _correlation_p_value(self, r: float, n: int) -> float:
        """Compute p-value for Pearson correlation."""
        if abs(r) >= 1:
            return 0.0
        t_stat = r * np.sqrt((n - 2) / (1 - r**2))
        # Approximate p-value (two-tailed)
        from math import erf

        return 1 - erf(abs(t_stat) / np.sqrt(2))

    def _estimate_temporal_precedence(
        self, data: np.ndarray, var1: str, var2: str, var_names: List[str]
    ) -> float:
        """
        Estimate which variable temporally precedes the other.

        Returns:
            Negative if var1 precedes var2, positive otherwise
        """
        idx1 = var_names.index(var1)
        idx2 = var_names.index(var2)

        # Use cross-correlation to find temporal lag
        max_lag = min(10, len(data) // 4)
        best_lag = 0
        best_corr = 0

        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                # var1 lags var2
                if abs(lag) < len(data):
                    corr = np.corrcoef(data[:lag, idx1], data[-lag:, idx2])[0, 1]
            elif lag > 0:
                # var1 leads var2
                if lag < len(data):
                    corr = np.corrcoef(data[lag:, idx1], data[:-lag, idx2])[0, 1]
            else:
                corr = np.corrcoef(data[:, idx1], data[:, idx2])[0, 1]

            if abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        return best_lag


class CounterfactualAnalyzer:
    """
    Performs counterfactual analysis to compute Average Treatment Effects (ATE).

    Estimates what would have happened if a candidate root cause were different.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def compute_ate(
        self,
        data: np.ndarray,
        treatment_idx: int,
        outcome_idx: int,
        treatment_value: float = None,
    ) -> float:
        """
        Compute Average Treatment Effect (ATE) for a candidate cause.

        ATE = E[Y | do(T=treatment)] - E[Y | do(T=baseline)]

        Args:
            data: Telemetry array (n_timesteps, n_variables)
            treatment_idx: Index of treatment variable (candidate cause)
            outcome_idx: Index of outcome variable (drift score)
            treatment_value: Observed treatment value (None = use observed)

        Returns:
            Estimated ATE
        """
        # Split into high and low treatment groups
        median_treatment = np.median(data[:, treatment_idx])

        high_treatment = data[data[:, treatment_idx] > median_treatment]
        low_treatment = data[data[:, treatment_idx] <= median_treatment]

        if len(high_treatment) == 0 or len(low_treatment) == 0:
            return 0.0

        # Compute outcome difference
        ate = np.mean(high_treatment[:, outcome_idx]) - np.mean(
            low_treatment[:, outcome_idx]
        )

        return ate

    def compute_attribution_scores(
        self, data: np.ndarray, candidate_indices: List[int], outcome_idx: int
    ) -> Dict[int, float]:
        """
        Compute attribution scores for all candidate causes.

        Attribution(c) = |ATE(c)| / Σ|ATE(c')|

        Args:
            data: Telemetry array
            candidate_indices: Indices of potential root cause variables
            outcome_idx: Index of outcome (drift score)

        Returns:
            Dictionary mapping candidate index to attribution score
        """
        ates = {}

        for idx in candidate_indices:
            ates[idx] = self.compute_ate(data, idx, outcome_idx)

        # Normalize to attribution scores
        total_abs_ate = sum(abs(ate) for ate in ates.values())

        if total_abs_ate == 0:
            return {idx: 1.0 / len(candidate_indices) for idx in candidate_indices}

        attributions = {idx: abs(ate) / total_abs_ate for idx, ate in ates.items()}

        return attributions


class AutomatedRCA:
    """
    Automated Root Cause Analysis for ethical drift incidents.

    Performs three-stage analysis:
    1. Hypothesis generation via causal graph construction
    2. Root cause attribution via counterfactual analysis
    3. Evidence collection and ExplainVector bundling

    Root Cause Categories:
    - Charter Violation (CV): Direct breach of ϕ clauses
    - Policy Conflict (PC): Internal contradictions
    - External Poisoning (EP): Corrupted inputs
    - CK Malfunction (CM): Erroneous kernel behavior
    - Resource Exhaustion (RE): Depletion
    - Mode Instability (MI): Sentio/Dynamo oscillation
    - Provenance Gap (PG): Missing audit trails
    """

    def __init__(self):
        self.graph_builder = CausalGraphBuilder()
        self.counterfactual = CounterfactualAnalyzer()
        self.logger = logging.getLogger(__name__)

        # Variable mapping for telemetry
        self.variable_names = [
            "drift_score",
            "mrde",
            "cect_phi4",
            "cect_phi5",
            "cect_phi1",
            "ersf",
            "vpce",
            "semantic_density",
            "entanglement",
            "phase_sync",
            "entropy_budget",
            "asf_stability",
        ]

    def analyze(
        self,
        incident_id: str,
        pre_drift_data: np.ndarray,
        post_drift_data: np.ndarray,
        incident_context: Dict,
        depth: str = "full",
    ) -> RCAResult:
        """
        Perform complete root cause analysis.

        Args:
            incident_id: Unique incident identifier
            pre_drift_data: Telemetry from 5 minutes before drift (n_timesteps, n_vars)
            post_drift_data: Telemetry from drift period
            incident_context: Metadata about the incident (CK activations, policies, etc.)
            depth: Analysis depth ('quick' or 'full')

        Returns:
            RCAResult with root causes and recommendations
        """
        self.logger.info(f"Starting RCA for incident {incident_id}")

        # Combine data for causal discovery
        combined_data = np.vstack([pre_drift_data, post_drift_data])

        # Stage 1: Build causal graph
        causal_graph = self.graph_builder.build_graph(
            combined_data, self.variable_names
        )

        # Stage 2: Identify candidate root causes
        candidates = self._identify_candidates(incident_context, causal_graph)

        # Stage 3: Compute attribution scores
        drift_idx = self.variable_names.index("drift_score")
        candidate_indices = [
            self.variable_names.index(c) for c in candidates if c in self.variable_names
        ]

        if len(candidate_indices) == 0:
            # Fall back to context-based analysis
            root_causes = self._context_based_analysis(incident_context)
        else:
            attributions = self.counterfactual.compute_attribution_scores(
                combined_data, candidate_indices, drift_idx
            )

            # Stage 4: Categorize and rank root causes
            root_causes = self._categorize_root_causes(
                attributions, candidates, incident_context, causal_graph
            )

        # Sort by attribution score
        root_causes.sort(key=lambda x: x.attribution_score, reverse=True)

        # Stage 5: Generate recommendations
        recommendations = self._generate_recommendations(root_causes)

        # Create result
        result = RCAResult(
            incident_id=incident_id,
            timestamp=datetime.now(),
            root_causes=root_causes,
            causal_graph=nx.node_link_data(causal_graph),
            top_cause=root_causes[0]
            if root_causes
            else CausalFactor(
                category=RootCauseCategory.UNKNOWN,
                component_id="unknown",
                component_type="unknown",
                description="Could not determine root cause",
                attribution_score=0.0,
            ),
            analysis_depth=depth,
            explain_vector_cid=f"cid:explain-{incident_id}",
            remediation_recommendations=recommendations,
            verification_status="preliminary" if depth == "quick" else "verified",
        )

        self.logger.info(f"RCA complete. Top cause: {result.top_cause.category.value}")

        return result

    def _identify_candidates(
        self, context: Dict, causal_graph: nx.DiGraph
    ) -> List[str]:
        """
        Identify candidate root cause variables from context and graph.

        Returns:
            List of variable names that are potential causes
        """
        candidates = []

        # Add metrics from causal graph (variables with outgoing edges to drift_score)
        if "drift_score" in causal_graph:
            candidates.extend(list(causal_graph.predecessors("drift_score")))

        # Add context-based candidates
        if "active_cks" in context:
            candidates.extend([f"ck_{ck}" for ck in context["active_cks"]])

        if "policy_changes" in context:
            candidates.extend([f"policy_{p}" for p in context["policy_changes"]])

        if "external_inputs" in context:
            candidates.extend([f"input_{i}" for i in context["external_inputs"]])

        return list(set(candidates))

    def _categorize_root_causes(
        self,
        attributions: Dict[int, float],
        candidates: List[str],
        context: Dict,
        causal_graph: nx.DiGraph,
    ) -> List[CausalFactor]:
        """
        Categorize root causes into Charter-defined categories.
        """
        root_causes = []

        for idx, score in attributions.items():
            if idx >= len(self.variable_names):
                continue

            var_name = self.variable_names[idx]

            # Determine category based on variable type
            category = self._determine_category(var_name, context)

            # Collect evidence
            evidence = self._collect_evidence(var_name, context, causal_graph)

            # Determine component info
            component_id, component_type = self._identify_component(var_name, context)

            factor = CausalFactor(
                category=category,
                component_id=component_id,
                component_type=component_type,
                description=f"{var_name} contributed {score:.1%} to drift",
                attribution_score=score,
                evidence=evidence,
                confidence=min(0.95, score * 1.2),  # Simple confidence heuristic
            )

            root_causes.append(factor)

        return root_causes

    def _determine_category(self, var_name: str, context: Dict) -> RootCauseCategory:
        """Map variable name to root cause category."""
        if "phi" in var_name or "cect" in var_name.lower():
            return RootCauseCategory.CHARTER_VIOLATION
        elif "policy" in var_name.lower():
            return RootCauseCategory.POLICY_CONFLICT
        elif "input" in var_name.lower() or "external" in var_name.lower():
            return RootCauseCategory.EXTERNAL_POISONING
        elif "ck_" in var_name.lower():
            return RootCauseCategory.CK_MALFUNCTION
        elif "resource" in var_name.lower() or "entropy" in var_name.lower():
            return RootCauseCategory.RESOURCE_EXHAUSTION
        elif "mode" in var_name.lower():
            return RootCauseCategory.MODE_INSTABILITY
        else:
            return RootCauseCategory.UNKNOWN

    def _collect_evidence(
        self, var_name: str, context: Dict, causal_graph: nx.DiGraph
    ) -> List[str]:
        """Collect evidence from CTPV, GoldenDAG, and context."""
        evidence = []

        # Add causal graph evidence
        if var_name in causal_graph:
            predecessors = list(causal_graph.predecessors(var_name))
            successors = list(causal_graph.successors(var_name))

            if predecessors:
                evidence.append(f"Preceded by: {', '.join(predecessors)}")
            if successors:
                evidence.append(f"Followed by: {', '.join(successors)}")

        # Add context evidence
        if "ctpv_refs" in context and var_name in context["ctpv_refs"]:
            evidence.append(f"CTPV: {context['ctpv_refs'][var_name]}")

        if "goldendag_refs" in context and var_name in context["goldendag_refs"]:
            evidence.append(f"GoldenDAG: {context['goldendag_refs'][var_name]}")

        return evidence

    def _identify_component(self, var_name: str, context: Dict) -> Tuple[str, str]:
        """Identify the component ID and type for a variable."""
        if var_name.startswith("ck_"):
            return var_name[3:], "CK"
        elif var_name.startswith("policy_"):
            return var_name[7:], "Policy"
        elif var_name.startswith("input_"):
            return var_name[6:], "Input"
        else:
            return var_name, "Metric"

    def _context_based_analysis(self, context: Dict) -> List[CausalFactor]:
        """Fallback analysis when causal graph fails."""
        root_causes = []

        # Check for obvious issues in context
        if "hard_stops" in context and context["hard_stops"]:
            for stop in context["hard_stops"]:
                root_causes.append(
                    CausalFactor(
                        category=RootCauseCategory.CHARTER_VIOLATION,
                        component_id=stop,
                        component_type="Charter",
                        description=f"Hard stop triggered: {stop}",
                        attribution_score=0.9,
                        confidence=0.95,
                    )
                )

        if "ck_errors" in context and context["ck_errors"]:
            for error in context["ck_errors"]:
                root_causes.append(
                    CausalFactor(
                        category=RootCauseCategory.CK_MALFUNCTION,
                        component_id=error.get("ck", "unknown"),
                        component_type="CK",
                        description=f"CK error: {error.get('message', 'Unknown')}",
                        attribution_score=0.8,
                        confidence=0.85,
                    )
                )

        return (
            root_causes
            if root_causes
            else [
                CausalFactor(
                    category=RootCauseCategory.UNKNOWN,
                    component_id="unknown",
                    component_type="unknown",
                    description="Root cause indeterminate from available data",
                    attribution_score=0.0,
                    confidence=0.0,
                )
            ]
        )

    def _generate_recommendations(self, root_causes: List[CausalFactor]) -> List[str]:
        """Generate remediation recommendations based on root causes."""
        recommendations = []

        if not root_causes:
            return ["Collect additional telemetry for further analysis"]

        top_cause = root_causes[0]

        # Category-specific recommendations
        if top_cause.category == RootCauseCategory.CHARTER_VIOLATION:
            recommendations.extend(
                [
                    f"Review and strengthen {top_cause.component_id} enforcement",
                    "Initiate CECT re-projection to ethical manifold",
                    "Consider SentiaGuard hard-guard activation",
                    "Schedule Judex review of Charter interpretation",
                ]
            )

        elif top_cause.category == RootCauseCategory.POLICY_CONFLICT:
            recommendations.extend(
                [
                    f"Resolve conflict in policy {top_cause.component_id}",
                    "Apply PolicyConflictMapper to identify contradictions",
                    "Consider policy rollback to last stable version",
                    "Initiate policy governance dry-run",
                ]
            )

        elif top_cause.category == RootCauseCategory.EXTERNAL_POISONING:
            recommendations.extend(
                [
                    f"Quarantine external input {top_cause.component_id}",
                    "Activate ProvenanceGuardrails for future inputs",
                    "Scan DRS for contaminated concepts",
                    "Initiate Custodian investigation",
                ]
            )

        elif top_cause.category == RootCauseCategory.CK_MALFUNCTION:
            recommendations.extend(
                [
                    f"Disable or isolate CK {top_cause.component_id}",
                    "Run CK unit tests to verify correctness",
                    "Check CK contract compliance",
                    "Consider CK rollback to previous version",
                ]
            )

        elif top_cause.category == RootCauseCategory.RESOURCE_EXHAUSTION:
            recommendations.extend(
                [
                    "Scale compute resources",
                    "Reduce entropy budget temporarily",
                    "Pause non-critical CK activations",
                    "Initiate resource optimization workflow",
                ]
            )

        elif top_cause.category == RootCauseCategory.MODE_INSTABILITY:
            recommendations.extend(
                [
                    "Stabilize mode transitions with SEAM",
                    "Increase damping coefficient λ_Γ",
                    "Consider extended Sentio dwell period",
                    "Review mode transition policies",
                ]
            )

        # General recommendations
        recommendations.extend(
            [
                "Generate full Introspect Bundle for audit",
                "Update GoldenDAG with incident metadata",
                "Schedule post-incident review with Operators",
                "Update EthicDriftMonitor calibration",
            ]
        )

        return recommendations

    def export_explain_vector(self, result: RCAResult) -> str:
        """
        Export RCA result as ExplainVector bundle for GoldenDAG.

        Returns:
            Content-addressed identifier (CID) for the bundle
        """
        bundle = {
            "type": "ExplainVector",
            "subtype": "RCA",
            "incident_id": result.incident_id,
            "timestamp": result.timestamp.isoformat(),
            "top_cause": result.top_cause.to_dict(),
            "root_causes": [rc.to_dict() for rc in result.root_causes[:3]],
            "recommendations": result.remediation_recommendations[:5],
            "verification": result.verification_status,
        }

        # In production, this would be sealed and stored
        import hashlib

        json_str = json.dumps(bundle, sort_keys=True)
        cid = f"cid:{hashlib.sha256(json_str.encode()).hexdigest()[:16]}"

        return cid


# NBCL Command Interface
def nbcl_veritas_rca_auto(incident_id: str, depth: str = "full") -> str:
    """
    NBCL: /veritas.rca --incident=<id> --auto --depth=<depth>

    Run automated root cause analysis on an incident.

    Args:
        incident_id: Incident identifier
        depth: Analysis depth ('quick' or 'full')

    Returns:
        JSON formatted RCA result
    """
    # In production, would fetch telemetry from GoldenDAG/CTPV
    # For demo, generate synthetic data
    np.random.seed(42)
    pre_drift = np.random.randn(300, 12) * 0.1
    post_drift = np.random.randn(100, 12) * 0.3
    post_drift[:, 0] += 0.5  # Increase drift score

    context = {
        "active_cks": ["Causa/CounterfactualPlanner", "Ethics/HarmBoundEstimator"],
        "hard_stops": ["E-ETH-013"],
        "ctpv_refs": {"mrde": "ctpv:abc123"},
    }

    rca = AutomatedRCA()
    result = rca.analyze(incident_id, pre_drift, post_drift, context, depth)

    return json.dumps(result.to_dict(), indent=2)


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("Automated Root Cause Analysis (ARCA) - Demo")
    print("=" * 70)

    result = nbcl_veritas_rca_auto("INC-2025-001", "full")
    print(result)

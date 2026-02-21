#!/usr/bin/env python3
"""
NeuralBlitz Bioinformatics Capability Kernels (CKs) v1.0.0
Working implementation using Biopython
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from Bio import SeqIO, Entrez
from Bio.Seq import Seq
from Bio.SeqUtils import gc_fraction, molecular_weight
from Bio.SeqUtils.ProtParam import ProteinAnalysis

# from Bio.PDB import PDBParser, PDBIO  # Not used in this implementation
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

# ============================================================================
# NEURALBLITZ CK CONTRACT SCHEMAS
# ============================================================================


@dataclass
class CKContract:
    """Base Capability Kernel Contract following NBX schema"""

    kernel: str
    version: str
    intent: str
    inputs: Dict[str, Any]
    outputs_schema: Dict[str, Any]
    bounds: Dict[str, Any]
    governance: Dict[str, Any]
    telemetry: Dict[str, Any]
    risk_factors: List[str]
    veritas_invariants: List[str]
    kpi_metrics: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate input payload against input schema"""
        for key, schema_type in self.inputs.items():
            if key not in payload:
                raise ValueError(f"Missing required input: {key}")
        return True


# ============================================================================
# CK 1: DNA SEQUENCE ANALYZER
# ============================================================================

dna_analyzer_contract = CKContract(
    kernel="Bio/DNASequenceAnalyzer",
    version="1.0.0",
    intent="Analyzes DNA sequences for GC content, molecular weight, ORF detection, and restriction sites using Biopython",
    inputs={
        "sequence": "string (DNA sequence or FASTA file path)",
        "format": "string (fasta, raw, genbank)",
        "analyses": "array[string] (gc_content, molecular_weight, orf_finder, restriction_sites, complement, translate)",
        "restriction_enzymes": "array[string] (optional, e.g., ['EcoRI', 'BamHI'])",
    },
    outputs_schema={
        "gc_content": "float",
        "molecular_weight": "float",
        "orf_positions": "array[object]",
        "restriction_sites": "object",
        "complement": "string",
        "translation": "string",
        "sequence_length": "integer",
        "nucleotide_counts": "object",
        "analysis_timestamp": "string (ISO8601)",
        "provenance_hash": "string (NBHS-512)",
    },
    bounds={"entropy_max": 0.15, "time_ms_max": 5000, "scope": "SBX-BIO-DNA"},
    governance={
        "rcf": True,
        "cect": True,
        "veritas_watch": True,
        "judex_quorum": False,
    },
    telemetry={
        "explain_vector": True,
        "dag_attach": True,
        "trace_id": "DNA-ANALYSIS-TRACE",
    },
    risk_factors=[
        "Sequence contamination",
        "Misinterpretation of ORF positions",
        "Restriction site false positives",
        "Large sequence memory exhaustion",
    ],
    veritas_invariants=[
        "VPROOF#SequenceIntegrity",
        "VPROOF#BiopythonValidation",
        "VPROOF#ExplainabilityCoverage",
    ],
    kpi_metrics=[
        "analysis_latency_ms",
        "sequence_length",
        "gc_content_variance",
        "orf_detection_confidence",
    ],
)


class DNASequenceAnalyzerCK:
    """Capability Kernel for DNA sequence analysis"""

    def __init__(self):
        self.contract = dna_analyzer_contract
        self.restriction_enzymes = {
            "EcoRI": "GAATTC",
            "BamHI": "GGATCC",
            "HindIII": "AAGCTT",
            "PstI": "CTGCAG",
            "SmaI": "CCCGGG",
        }

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DNA analysis with full provenance"""
        # Validate payload
        self.contract.validate_payload(payload)

        start_time = datetime.utcnow()

        # Parse sequence
        sequence_str = payload["sequence"]
        seq_format = payload.get("format", "raw")
        analyses = payload.get("analyses", ["gc_content", "molecular_weight"])

        # Load sequence
        if seq_format == "fasta":
            record = SeqIO.read(io.StringIO(sequence_str), "fasta")
            seq = record.seq
        else:
            seq = Seq(sequence_str.upper())

        results = {
            "sequence_length": len(seq),
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "nucleotide_counts": {
                "A": seq.count("A"),
                "T": seq.count("T"),
                "G": seq.count("G"),
                "C": seq.count("C"),
            },
        }

        # Perform requested analyses
        if "gc_content" in analyses:
            results["gc_content"] = gc_fraction(seq) * 100

        if "molecular_weight" in analyses:
            results["molecular_weight"] = molecular_weight(seq, "DNA")

        if "orf_finder" in analyses:
            results["orf_positions"] = self._find_orfs(seq)

        if "restriction_sites" in analyses:
            enzymes = payload.get("restriction_enzymes", ["EcoRI"])
            results["restriction_sites"] = self._find_restriction_sites(seq, enzymes)

        if "complement" in analyses:
            results["complement"] = str(seq.complement())
            results["reverse_complement"] = str(seq.reverse_complement())

        if "translate" in analyses:
            results["translation"] = str(seq.translate())

        # Generate provenance hash (NBHS-512 simplified)
        results["provenance_hash"] = self._generate_hash(results)

        # Calculate latency
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        results["kpi_metrics"] = {
            "analysis_latency_ms": latency_ms,
            "sequence_length": len(seq),
            "gc_content_variance": self._calculate_gc_variance(seq),
        }

        return results

    def _find_orfs(self, seq: Seq) -> List[Dict]:
        """Find Open Reading Frames"""
        orfs = []
        start_codon = "ATG"
        stop_codons = ["TAA", "TAG", "TGA"]

        for frame in range(3):
            for i in range(frame, len(seq) - 2, 3):
                codon = str(seq[i : i + 3])
                if codon == start_codon:
                    for j in range(i + 3, len(seq) - 2, 3):
                        stop_codon = str(seq[j : j + 3])
                        if stop_codon in stop_codons:
                            orfs.append(
                                {
                                    "start": i,
                                    "end": j + 3,
                                    "frame": frame,
                                    "length": j + 3 - i,
                                }
                            )
                            break
        return orfs

    def _find_restriction_sites(self, seq: Seq, enzymes: List[str]) -> Dict:
        """Find restriction enzyme sites"""
        sites = {}
        seq_str = str(seq)

        for enzyme in enzymes:
            if enzyme in self.restriction_enzymes:
                pattern = self.restriction_enzymes[enzyme]
                positions = []
                start = 0
                while True:
                    pos = seq_str.find(pattern, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1
                sites[enzyme] = {
                    "pattern": pattern,
                    "positions": positions,
                    "count": len(positions),
                }
        return sites

    def _calculate_gc_variance(self, seq: Seq) -> float:
        """Calculate GC content variance in windows"""
        window_size = 100
        gc_values = []

        for i in range(0, len(seq) - window_size, window_size):
            window = seq[i : i + window_size]
            gc_values.append(gc_fraction(window) * 100)

        return float(np.var(gc_values)) if gc_values else 0.0

    def _generate_hash(self, data: Dict) -> str:
        """Generate NBHS-512 style hash (simplified SHA-512)"""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha512(content.encode()).hexdigest()


# ============================================================================
# CK 2: PROTEIN STRUCTURE PREDICTOR
# ============================================================================

protein_predictor_contract = CKContract(
    kernel="Bio/ProteinStructurePredictor",
    version="1.0.0",
    intent="Predicts protein secondary structure, physicochemical properties, and stability using Biopython and empirical methods",
    inputs={
        "sequence": "string (amino acid sequence or FASTA)",
        "format": "string (fasta, raw)",
        "predictions": "array[string] (secondary_structure, stability, physicochemical, domains, disorder)",
        "pdb_template": "string (optional PDB ID for comparative modeling)",
    },
    outputs_schema={
        "secondary_structure": "object (helix%, sheet%, turn%, coil%)",
        "molecular_weight": "float",
        "isoelectric_point": "float",
        "gravy": "float (Grand Average of Hydropathy)",
        "aromaticity": "float",
        "instability_index": "float",
        "stability_prediction": "string (stable/unstable)",
        "flexibility": "array[float]",
        "domain_predictions": "array[object]",
        "analysis_timestamp": "string (ISO8601)",
        "provenance_hash": "string (NBHS-512)",
    },
    bounds={"entropy_max": 0.25, "time_ms_max": 10000, "scope": "SBX-BIO-PROTEIN"},
    governance={
        "rcf": True,
        "cect": True,
        "veritas_watch": True,
        "judex_quorum": False,
    },
    telemetry={
        "explain_vector": True,
        "dag_attach": True,
        "trace_id": "PROTEIN-PREDICT-TRACE",
    },
    risk_factors=[
        "Secondary structure prediction inaccuracy",
        "Unfolded protein state mischaracterization",
        "Large protein computational limits",
        "Template-based modeling errors",
    ],
    veritas_invariants=[
        "VPROOF#SequenceIntegrity",
        "VPROOF#PhysicochemicalValidity",
        "VPROOF#ExplainabilityCoverage",
    ],
    kpi_metrics=[
        "prediction_latency_ms",
        "sequence_length_aa",
        "prediction_confidence",
        "memory_usage_mb",
    ],
)


class ProteinStructurePredictorCK:
    """Capability Kernel for protein structure prediction"""

    def __init__(self):
        self.contract = protein_predictor_contract
        # Chou-Fasman propensities (simplified)
        self.helix_propensity = {"E": 1.53, "A": 1.45, "L": 1.34, "M": 1.20, "Q": 1.17}
        self.sheet_propensity = {"M": 1.67, "V": 1.65, "I": 1.60, "C": 1.30, "Y": 1.29}

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute protein structure prediction"""
        self.contract.validate_payload(payload)

        start_time = datetime.utcnow()

        # Parse sequence
        sequence_str = payload["sequence"]
        seq_format = payload.get("format", "raw")
        predictions = payload.get(
            "predictions", ["secondary_structure", "physicochemical"]
        )

        if seq_format == "fasta":
            record = SeqIO.read(io.StringIO(sequence_str), "fasta")
            seq = str(record.seq)
        else:
            seq = sequence_str.upper()

        # Validate amino acid sequence
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        if not set(seq).issubset(valid_aa):
            raise ValueError("Invalid amino acids in sequence")

        # Initialize analyzer
        analyzer = ProteinAnalysis(seq)

        results = {
            "sequence_length_aa": len(seq),
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "amino_acid_counts": dict(analyzer.count_amino_acids()),
            "amino_acid_percentages": dict(analyzer.get_amino_acids_percent()),
        }

        # Perform predictions
        if "secondary_structure" in predictions:
            results["secondary_structure"] = self._predict_secondary_structure(analyzer)

        if "physicochemical" in predictions:
            results.update(self._calculate_physicochemical_properties(analyzer))

        if "stability" in predictions:
            results["instability_index"] = analyzer.instability_index()
            results["stability_prediction"] = (
                "stable" if analyzer.instability_index() < 40 else "unstable"
            )

        if "flexibility" in predictions:
            results["flexibility"] = self._predict_flexibility(seq)

        # Generate provenance hash
        results["provenance_hash"] = self._generate_hash(results)

        # Calculate metrics
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        results["kpi_metrics"] = {
            "prediction_latency_ms": latency_ms,
            "sequence_length_aa": len(seq),
            "prediction_confidence": self._estimate_confidence(len(seq)),
            "memory_usage_mb": self._estimate_memory(seq),
        }

        return results

    def _predict_secondary_structure(self, analyzer: ProteinAnalysis) -> Dict:
        """Predict secondary structure using Chou-Fasman algorithm"""
        ss_dict = analyzer.secondary_structure_fraction()
        return {
            "helix_fraction": float(ss_dict[0]),
            "sheet_fraction": float(ss_dict[1]),
            "turn_fraction": float(ss_dict[2]),
            "coil_fraction": 1.0
            - float(ss_dict[0])
            - float(ss_dict[1])
            - float(ss_dict[2]),
            "method": "Chou-Fasman/Biopython",
        }

    def _calculate_physicochemical_properties(self, analyzer: ProteinAnalysis) -> Dict:
        """Calculate physicochemical properties"""
        return {
            "molecular_weight": analyzer.molecular_weight(),
            "isoelectric_point": analyzer.isoelectric_point(),
            "gravy": analyzer.gravy(),  # Grand Average of Hydropathy
            "aromaticity": analyzer.aromaticity(),
        }

    def _predict_flexibility(self, seq: str, window: int = 15) -> List[float]:
        """Predict local flexibility using B-values approximation"""
        flexibility = []

        # Flexibility based on amino acid properties
        flex_scores = {
            "G": 1.0,
            "A": 0.8,
            "S": 0.9,
            "P": 1.0,  # Flexible
            "V": 0.4,
            "I": 0.3,
            "L": 0.4,
            "F": 0.3,  # Rigid
            "Y": 0.5,
            "W": 0.3,
            "C": 0.4,
            "M": 0.4,
            "N": 0.7,
            "Q": 0.7,
            "T": 0.8,
            "K": 0.9,
            "R": 0.8,
            "H": 0.6,
            "D": 0.9,
            "E": 0.8,
        }

        for i in range(len(seq)):
            aa = seq[i]
            flexibility.append(flex_scores.get(aa, 0.5))

        return flexibility

    def _estimate_confidence(self, length: int) -> float:
        """Estimate prediction confidence based on sequence length"""
        # Confidence decreases with length due to accumulated errors
        base_confidence = 0.85
        length_penalty = min(0.3, length / 1000 * 0.1)
        return max(0.5, base_confidence - length_penalty)

    def _estimate_memory(self, seq: str) -> float:
        """Estimate memory usage in MB"""
        return len(seq) * 0.001  # Rough estimate

    def _generate_hash(self, data: Dict) -> str:
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha512(content.encode()).hexdigest()


# ============================================================================
# CK 3: GENOMIC DATA VISUALIZER
# ============================================================================

visualizer_contract = CKContract(
    kernel="Bio/GenomicVisualizer",
    version="1.0.0",
    intent="Generates publication-quality visualizations of genomic data including sequence features, GC profiles, and phylogenetic trees",
    inputs={
        "data": "object (sequence data, alignment, or features)",
        "viz_type": "string (gc_plot, feature_map, sequence_logo, phylogenetic_tree, coverage_plot)",
        "format": "string (png, svg, json)",
        "style_config": "object (colors, labels, dimensions)",
        "annotations": "array[object] (optional feature annotations)",
    },
    outputs_schema={
        "visualization": "string (base64 encoded image or JSON specification)",
        "viz_type": "string",
        "dimensions": "object (width, height)",
        "format": "string",
        "data_summary": "object",
        "analysis_timestamp": "string (ISO8601)",
        "provenance_hash": "string (NBHS-512)",
    },
    bounds={"entropy_max": 0.20, "time_ms_max": 8000, "scope": "SBX-BIO-VIZ"},
    governance={
        "rcf": True,
        "cect": True,
        "veritas_watch": True,
        "judex_quorum": False,
    },
    telemetry={
        "explain_vector": True,
        "dag_attach": True,
        "trace_id": "GENOMIC-VIZ-TRACE",
    },
    risk_factors=[
        "Visualization misrepresentation",
        "Large dataset rendering failure",
        "Colorblind accessibility issues",
        "Data scaling artifacts",
    ],
    veritas_invariants=[
        "VPROOF#DataIntegrity",
        "VPROOF#VisualAccuracy",
        "VPROOF#ExplainabilityCoverage",
    ],
    kpi_metrics=[
        "render_latency_ms",
        "data_points_count",
        "image_size_kb",
        "accessibility_score",
    ],
)


class GenomicVisualizerCK:
    """Capability Kernel for genomic data visualization"""

    def __init__(self):
        self.contract = visualizer_contract
        plt.style.use("seaborn-v0_8-darkgrid")

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute genomic visualization"""
        self.contract.validate_payload(payload)

        start_time = datetime.utcnow()

        data = payload["data"]
        viz_type = payload["viz_type"]
        format_type = payload.get("format", "png")
        style_config = payload.get("style_config", {})
        annotations = payload.get("annotations", [])

        # Generate visualization based on type
        if viz_type == "gc_plot":
            viz_data = self._generate_gc_plot(data, style_config)
        elif viz_type == "feature_map":
            viz_data = self._generate_feature_map(data, annotations, style_config)
        elif viz_type == "sequence_logo":
            viz_data = self._generate_sequence_logo(data, style_config)
        elif viz_type == "coverage_plot":
            viz_data = self._generate_coverage_plot(data, style_config)
        else:
            raise ValueError(f"Unknown viz_type: {viz_type}")

        results = {
            "visualization": viz_data,
            "viz_type": viz_type,
            "format": format_type,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "data_summary": self._summarize_data(data),
        }

        # Generate provenance hash
        results["provenance_hash"] = self._generate_hash(results)

        # Calculate metrics
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Estimate image size
        img_bytes = base64.b64decode(
            viz_data.split(",")[1] if "," in viz_data else viz_data
        )

        results["kpi_metrics"] = {
            "render_latency_ms": latency_ms,
            "data_points_count": self._count_data_points(data),
            "image_size_kb": len(img_bytes) / 1024,
            "accessibility_score": self._calculate_accessibility(style_config),
        }

        return results

    def _generate_gc_plot(self, data: Dict, style_config: Dict) -> str:
        """Generate GC content sliding window plot"""
        sequence = data.get("sequence", "")
        window_size = style_config.get("window_size", 100)

        gc_values = []
        positions = []

        for i in range(0, len(sequence) - window_size + 1, window_size // 2):
            window = sequence[i : i + window_size]
            gc_values.append(gc_fraction(window) * 100)
            positions.append(i + window_size // 2)

        fig, ax = plt.subplots(figsize=style_config.get("figsize", (12, 6)))
        ax.plot(
            positions,
            gc_values,
            linewidth=2,
            color=style_config.get("color", "#2E86AB"),
        )
        ax.axhline(y=50, color="red", linestyle="--", alpha=0.5, label="50% GC")
        ax.set_xlabel("Position (bp)", fontsize=12)
        ax.set_ylabel("GC Content (%)", fontsize=12)
        ax.set_title(f"GC Content Profile (Window: {window_size}bp)", fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()

        return self._fig_to_base64(fig)

    def _generate_feature_map(
        self, data: Dict, annotations: List[Dict], style_config: Dict
    ) -> str:
        """Generate genomic feature map"""
        sequence_length = data.get("sequence_length", 1000)

        fig, ax = plt.subplots(figsize=style_config.get("figsize", (14, 6)))

        # Draw sequence backbone
        ax.plot([0, sequence_length], [0, 0], "k-", linewidth=2)

        # Color scheme for features
        feature_colors = {
            "gene": "#E63946",
            "CDS": "#F77F00",
            "exon": "#06A77D",
            "intron": "#118AB2",
            "promoter": "#073B4C",
            "terminator": "#D62828",
        }

        y_offset = 1
        for feature in annotations:
            start = feature.get("start", 0)
            end = feature.get("end", 100)
            feat_type = feature.get("type", "gene")
            strand = feature.get("strand", "+")

            color = feature_colors.get(feat_type, "#8338EC")

            # Draw feature arrow
            arrow_style = ">" if strand == "+" else "<"
            ax.annotate(
                "",
                xy=(end, y_offset),
                xytext=(start, y_offset),
                arrowprops=dict(arrowstyle=arrow_style, color=color, lw=2),
            )

            # Label
            ax.text(
                (start + end) / 2,
                y_offset + 0.5,
                feature.get("name", feat_type),
                ha="center",
                va="bottom",
                fontsize=8,
                rotation=45,
            )

            y_offset += 1.5

        ax.set_xlim(-50, sequence_length + 50)
        ax.set_ylim(-1, y_offset)
        ax.set_xlabel("Position (bp)", fontsize=12)
        ax.set_title("Genomic Feature Map", fontsize=14)
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

        return self._fig_to_base64(fig)

    def _generate_sequence_logo(self, data: Dict, style_config: Dict) -> str:
        """Generate simplified sequence logo"""
        sequences = data.get("sequences", [])
        if not sequences:
            raise ValueError("No sequences provided for logo")

        # Calculate position-specific frequencies
        seq_length = len(sequences[0])
        positions = range(seq_length)

        fig, ax = plt.subplots(figsize=style_config.get("figsize", (12, 4)))

        nucleotides = ["A", "T", "G", "C"]
        colors = {"A": "green", "T": "red", "G": "orange", "C": "blue"}

        for i in positions:
            counts = {nt: 0 for nt in nucleotides}
            for seq in sequences:
                if i < len(seq) and seq[i] in counts:
                    counts[seq[i]] += 1

            total = sum(counts.values())
            if total > 0:
                y_offset = 0
                for nt in nucleotides:
                    freq = counts[nt] / total
                    if freq > 0:
                        ax.bar(
                            i,
                            freq,
                            bottom=y_offset,
                            color=colors[nt],
                            width=0.8,
                            edgecolor="white",
                            linewidth=0.5,
                        )
                        if freq > 0.1:
                            ax.text(
                                i,
                                y_offset + freq / 2,
                                nt,
                                ha="center",
                                va="center",
                                fontsize=10,
                                fontweight="bold",
                                color="white",
                            )
                        y_offset += freq

        ax.set_xlabel("Position", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title("Sequence Logo", fontsize=14)
        ax.set_xticks(positions)
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3, axis="y")

        return self._fig_to_base64(fig)

    def _generate_coverage_plot(self, data: Dict, style_config: Dict) -> str:
        """Generate sequencing coverage plot"""
        positions = data.get("positions", [])
        coverage = data.get("coverage", [])

        fig, ax = plt.subplots(figsize=style_config.get("figsize", (12, 6)))
        ax.fill_between(
            positions, coverage, alpha=0.6, color=style_config.get("color", "#4361EE")
        )
        ax.plot(
            positions,
            coverage,
            linewidth=1.5,
            color=style_config.get("color", "#4361EE"),
        )

        mean_cov = np.mean(coverage) if coverage else 0
        ax.axhline(
            y=mean_cov,
            color="red",
            linestyle="--",
            alpha=0.7,
            label=f"Mean: {mean_cov:.1f}x",
        )

        ax.set_xlabel("Position (bp)", fontsize=12)
        ax.set_ylabel("Coverage Depth", fontsize=12)
        ax.set_title("Sequencing Coverage Profile", fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)

        return self._fig_to_base64(fig)

    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"

    def _summarize_data(self, data: Dict) -> Dict:
        """Generate data summary"""
        summary = {}
        if "sequence" in data:
            summary["sequence_length"] = len(data["sequence"])
        if "sequences" in data:
            summary["num_sequences"] = len(data["sequences"])
            summary["alignment_length"] = (
                len(data["sequences"][0]) if data["sequences"] else 0
            )
        return summary

    def _count_data_points(self, data: Dict) -> int:
        """Count data points"""
        if "sequence" in data:
            return len(data["sequence"])
        if "sequences" in data:
            return sum(len(seq) for seq in data["sequences"])
        if "positions" in data:
            return len(data["positions"])
        return 0

    def _calculate_accessibility(self, style_config: Dict) -> float:
        """Calculate accessibility score (colorblind-friendly)"""
        score = 1.0
        # Check for colorblind-friendly palette
        color = style_config.get("color", "")
        if color and not self._is_colorblind_friendly(color):
            score -= 0.2
        return score

    def _is_colorblind_friendly(self, color: str) -> bool:
        """Check if color is colorblind-friendly (simplified)"""
        # Blues, oranges, and grays are generally safe
        friendly_colors = ["#4361EE", "#F77F00", "#06A77D", "#118AB2", "#E63946"]
        return color in friendly_colors

    def _generate_hash(self, data: Dict) -> str:
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha512(content.encode()).hexdigest()


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================


def run_demonstration():
    """Run demonstration of all 3 CKs"""

    print("=" * 80)
    print("NEURALBLITZ BIOINFORMATICS CAPABILITY KERNELS - DEMONSTRATION")
    print("=" * 80)

    # Test DNA Sequence Analyzer
    print("\n1. DNA SEQUENCE ANALYZER CK")
    print("-" * 40)

    dna_ck = DNASequenceAnalyzerCK()
    print(f"Kernel: {dna_ck.contract.kernel}")
    print(f"Version: {dna_ck.contract.version}")
    print(f"Intent: {dna_ck.contract.intent}")

    sample_dna = "ATGCGATCGATCGATCGATCGTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCGATCGATCGATCGATCGATCGATCGATCG"

    dna_payload = {
        "sequence": sample_dna,
        "format": "raw",
        "analyses": ["gc_content", "molecular_weight", "orf_finder", "complement"],
        "restriction_enzymes": ["EcoRI", "BamHI"],
    }

    try:
        dna_results = dna_ck.execute(dna_payload)
        print(f"\nResults:")
        print(f"  Sequence Length: {dna_results['sequence_length']} bp")
        print(f"  GC Content: {dna_results.get('gc_content', 0):.2f}%")
        print(f"  Molecular Weight: {dna_results.get('molecular_weight', 0):.2f} Da")
        print(f"  ORFs Found: {len(dna_results.get('orf_positions', []))}")
        print(
            f"  Restriction Sites: {list(dna_results.get('restriction_sites', {}).keys())}"
        )
        print(f"  Analysis Time: {dna_results['analysis_timestamp']}")
        print(f"  Provenance Hash: {dna_results['provenance_hash'][:16]}...")
        print(f"  Latency: {dna_results['kpi_metrics']['analysis_latency_ms']:.2f} ms")
    except Exception as e:
        print(f"Error: {e}")

    # Test Protein Structure Predictor
    print("\n2. PROTEIN STRUCTURE PREDICTOR CK")
    print("-" * 40)

    protein_ck = ProteinStructurePredictorCK()
    print(f"Kernel: {protein_ck.contract.kernel}")
    print(f"Version: {protein_ck.contract.version}")
    print(f"Intent: {protein_ck.contract.intent}")

    sample_protein = "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"

    protein_payload = {
        "sequence": sample_protein,
        "format": "raw",
        "predictions": [
            "secondary_structure",
            "physicochemical",
            "stability",
            "flexibility",
        ],
    }

    try:
        protein_results = protein_ck.execute(protein_payload)
        print(f"\nResults:")
        print(f"  Sequence Length: {protein_results['sequence_length_aa']} aa")

        if "secondary_structure" in protein_results:
            ss = protein_results["secondary_structure"]
            print(f"  Secondary Structure:")
            print(f"    - Helix: {ss['helix_fraction'] * 100:.1f}%")
            print(f"    - Sheet: {ss['sheet_fraction'] * 100:.1f}%")
            print(f"    - Turn: {ss['turn_fraction'] * 100:.1f}%")

        if "molecular_weight" in protein_results:
            print(f"  Molecular Weight: {protein_results['molecular_weight']:.2f} Da")
        if "isoelectric_point" in protein_results:
            print(f"  Isoelectric Point: {protein_results['isoelectric_point']:.2f}")
        if "gravy" in protein_results:
            print(f"  GRAVY: {protein_results['gravy']:.3f}")
        if "instability_index" in protein_results:
            print(f"  Instability Index: {protein_results['instability_index']:.2f}")
        if "stability_prediction" in protein_results:
            print(f"  Stability: {protein_results['stability_prediction']}")

        print(f"  Analysis Time: {protein_results['analysis_timestamp']}")
        print(f"  Provenance Hash: {protein_results['provenance_hash'][:16]}...")
        print(
            f"  Latency: {protein_results['kpi_metrics']['prediction_latency_ms']:.2f} ms"
        )
    except Exception as e:
        print(f"Error: {e}")

    # Test Genomic Visualizer
    print("\n3. GENOMIC DATA VISUALIZER CK")
    print("-" * 40)

    viz_ck = GenomicVisualizerCK()
    print(f"Kernel: {viz_ck.contract.kernel}")
    print(f"Version: {viz_ck.contract.version}")
    print(f"Intent: {viz_ck.contract.intent}")

    # GC Plot visualization
    viz_payload = {
        "data": {
            "sequence": sample_dna * 10  # Longer sequence for better plot
        },
        "viz_type": "gc_plot",
        "format": "png",
        "style_config": {"window_size": 50, "figsize": (10, 5), "color": "#2E86AB"},
    }

    try:
        viz_results = viz_ck.execute(viz_payload)
        print(f"\nResults:")
        print(f"  Visualization Type: {viz_results['viz_type']}")
        print(f"  Format: {viz_results['format']}")
        print(f"  Data Points: {viz_results['kpi_metrics']['data_points_count']}")
        print(f"  Image Size: {viz_results['kpi_metrics']['image_size_kb']:.2f} KB")
        print(
            f"  Render Latency: {viz_results['kpi_metrics']['render_latency_ms']:.2f} ms"
        )
        print(
            f"  Accessibility Score: {viz_results['kpi_metrics']['accessibility_score']:.2f}"
        )
        print(f"  Analysis Time: {viz_results['analysis_timestamp']}")
        print(f"  Provenance Hash: {viz_results['provenance_hash'][:16]}...")
        print(
            f"\n  Base64 Image Preview (truncated): {viz_results['visualization'][:60]}..."
        )
    except Exception as e:
        print(f"Error: {e}")

    # Feature Map visualization
    print("\n  Feature Map Example:")
    viz_payload_features = {
        "data": {"sequence_length": 5000},
        "viz_type": "feature_map",
        "format": "png",
        "annotations": [
            {"start": 100, "end": 500, "type": "gene", "name": "GeneA", "strand": "+"},
            {"start": 600, "end": 800, "type": "CDS", "name": "CDS1", "strand": "+"},
            {
                "start": 1200,
                "end": 1500,
                "type": "promoter",
                "name": "Promoter1",
                "strand": "+",
            },
            {
                "start": 2000,
                "end": 3500,
                "type": "gene",
                "name": "GeneB",
                "strand": "-",
            },
            {
                "start": 3600,
                "end": 3800,
                "type": "terminator",
                "name": "Term1",
                "strand": "+",
            },
        ],
        "style_config": {"figsize": (12, 4)},
    }

    try:
        viz_results_features = viz_ck.execute(viz_payload_features)
        print(
            f"    Generated feature map with {len(viz_payload_features['annotations'])} features"
        )
        print(
            f"    Image Size: {viz_results_features['kpi_metrics']['image_size_kb']:.2f} KB"
        )
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)

    return {
        "dna_ck": dna_ck.contract.to_dict(),
        "protein_ck": protein_ck.contract.to_dict(),
        "visualizer_ck": viz_ck.contract.to_dict(),
        "demonstration_results": {
            "dna_analysis": dna_results if "dna_results" in locals() else None,
            "protein_prediction": protein_results
            if "protein_results" in locals()
            else None,
            "visualization": viz_results if "viz_results" in locals() else None,
        },
    }


if __name__ == "__main__":
    results = run_demonstration()

    # Save contracts to JSON for report
    with open("bioinformatics_ck_contracts.json", "w") as f:
        json.dump(
            {
                "Bio/DNASequenceAnalyzer": results["dna_ck"],
                "Bio/ProteinStructurePredictor": results["protein_ck"],
                "Bio/GenomicVisualizer": results["visualizer_ck"],
            },
            f,
            indent=2,
        )

    print("\nContracts exported to: bioinformatics_ck_contracts.json")

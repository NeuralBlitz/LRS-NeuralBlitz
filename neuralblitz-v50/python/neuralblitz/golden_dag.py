"""Backward-compatibility shim for golden_dag.py
Redirects to ComputationalAxioms.python.goldendag_core
Mathematical Coherence must remain 1.0

This file maintains the original import interface while delegating
to the new Three-Pillar architecture location.
"""

import sys
import os

# Add ComputationalAxioms to path if needed
# Path: neuralblitz-v50/python/neuralblitz/golden_dag.py -> neuralblitz-v50/
current_file = os.path.abspath(__file__)
neuralblitz_dir = os.path.dirname(current_file)  # python/neuralblitz
python_dir = os.path.dirname(neuralblitz_dir)  # python
workspace_root = os.path.dirname(python_dir)  # neuralblitz-v50
computational_axioms_path = os.path.join(
    workspace_root, "ComputationalAxioms", "python"
)

if computational_axioms_path not in sys.path:
    sys.path.insert(0, computational_axioms_path)

# Import from new Three-Pillar location
from goldendag_core import (
    GoldenDAG,
    NBHSCryptographicHash,
    TraceID,
    CodexID,
    SEED,
    generate_goldendag,
    generate_trace_id,
    generate_codex_id,
)

__version__ = "50.0.0"
__all__ = [
    "GoldenDAG",
    "NBHSCryptographicHash",
    "TraceID",
    "CodexID",
    "SEED",
    "generate_goldendag",
    "generate_trace_id",
    "generate_codex_id",
]

# Preserve original module name for backwards compatibility
__name__ = "neuralblitz.golden_dag"

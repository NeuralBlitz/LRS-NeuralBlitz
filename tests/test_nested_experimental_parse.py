"""Parse-check selected nested experimental Python modules without executing them.

Import/runtime behavior, scientific hypotheses and numerical claims are NOT
validated by source parseability.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SELECTED = (
    "neuralblitz-v50/examples/07_real_ecosystem_demo.py",
    "neuralblitz-v50/examples/phase1/phase1_integration_demo.py",
    "neuralblitz-v50/neuralblitz/enterprise/autocognition_engine.py",
    "neuralblitz-v50/neuralblitz/enterprise/lrs_knowledge_acquisition.py",
    "neuralblitz-v50/neuralblitz/enterprise/lrs_reasoning_engine.py",
    "neuralblitz-v50/neuralblitz/ml/classifier.py",
    "neuralblitz-v50/neuralblitz/ml/predictor.py",
    "neuralblitz-v50/quantum_foundation.py",
)

class ExperimentalParseTests(unittest.TestCase):
    def test_selected_experimental_python_modules_parse(self):
        for relative in SELECTED:
            with self.subTest(module=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                ast.parse(text, filename=relative)

    def test_demo_does_not_invent_accuracy_from_unlabeled_samples(self):
        text = (ROOT / SELECTED[1]).read_text(encoding="utf-8")
        self.assertNotIn("r.category == r['category']", text)
        self.assertIn("requires labeled holdout", text)

    def test_classifier_vectors_have_seven_intent_dimensions(self):
        tree = ast.parse((ROOT / SELECTED[5]).read_text(encoding="utf-8"))
        candidates = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "test_intents"
                for target in node.targets
            )
        ]
        self.assertEqual(len(candidates), 1)
        outer = candidates[0].value
        self.assertIsInstance(outer, ast.List)
        self.assertEqual(len(outer.elts), 4)
        for example in outer.elts:
            self.assertIsInstance(example, ast.List)
            self.assertEqual(len(example.elts), 7)

if __name__ == "__main__":
    unittest.main()

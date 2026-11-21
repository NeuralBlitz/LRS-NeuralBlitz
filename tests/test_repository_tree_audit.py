"""Synthetic checks for the tracked-repository static inspection tool."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "repo_audit", ROOT / "scripts" / "audit_repository_tree.py"
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

class RepositoryInspectionTests(unittest.TestCase):
    def test_every_binary_is_recorded_without_executing_content(self):
        row = audit.inspect_blob(".coverage", b"SQLite format 3\x00example", {".coverage"})
        self.assertEqual(row["kind"], "binary")
        self.assertIn("tracked-generated-or-cache", row["flags"])
        self.assertEqual(row["bytes"], len(b"SQLite format 3\x00example"))

    def test_python_syntax_is_parsed_without_importing_code(self):
        valid = audit.inspect_blob("example.py", b"import os\nassert True\n", {"example.py"})
        invalid = audit.inspect_blob("broken.py", b"def f(:\n pass\n", {"broken.py"})
        self.assertEqual(valid["validation_error"], "")
        self.assertTrue(invalid["validation_error"].startswith("python-syntax:"))

    def test_json_is_checked_without_executing(self):
        self.assertEqual(
            audit.inspect_blob("manifest.json", b'{"ok": true}', {"manifest.json"})["validation_error"],
            ""
        )
        self.assertEqual(
            audit.inspect_blob("bad.json", b'{bad}', {"bad.json"})["validation_error"],
            "invalid-json"
        )

    def test_missing_markdown_target_is_reported(self):
        row = audit.inspect_blob(
            "docs/readme.md",
            b"[Valid](../README.md) [Missing](oops.md)",
            {"docs/readme.md", "README.md"}
        )
        self.assertEqual(row["kind"], "markdown")
        self.assertEqual(row["broken_local_links"], 1)

    def test_generated_html_is_not_counted_as_verified_source(self):
        row = audit.inspect_blob("htmlcov/index.html", b"<html>coverage</html>", {"htmlcov/index.html"})
        self.assertEqual(row["kind"], "html")
        self.assertIn("tracked-generated-or-cache", row["flags"])

    def test_unsupported_claims_are_flagged_not_validated(self):
        row = audit.inspect_blob(
            "README.md", b"Production-ready, quantum-resistant, 10,000+ devices\n",
            {"README.md"}
        )
        self.assertGreaterEqual(row["claim_markers"], 3)
        self.assertIn("unverified-marketing-term-review", row["flags"])

    def test_unreadable_gitlinks_are_separately_reported(self):
        summary = audit.build_summary([
            {"path": "dependency", "kind": "gitlink-unreadable", "flags": [],
             "validation_error": "", "broken_local_links": 0, "claim_markers": 0}
        ])
        self.assertEqual(summary["gitlinks"], ["dependency"])
        self.assertEqual(summary["unverified_claim_marker_occurrences"], 0)

if __name__ == "__main__":
    unittest.main()

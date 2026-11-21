"""Unit checks for the root review register's inventory policy."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "root_register", ROOT / "scripts" / "check_root_review_register.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class RootReviewRegisterTests(unittest.TestCase):
    def test_current_root_file_inventory_is_covered(self):
        self.assertEqual(tool.check(), [])

    def test_review_rows_are_extracted_without_headings(self):
        text = (
            "# Register\n"
            "| Path | Result |\n"
            "| --- | --- |\n"
            "| `main.py` | inspected |\n"
            "| `README.md` | inspected |\n"
        )
        names, duplicates = tool.review_paths(text)
        self.assertEqual(names, {"main.py", "README.md"})
        self.assertEqual(duplicates, 0)

    def test_duplicate_review_rows_are_rejected(self):
        names, duplicates = tool.review_paths(
            "| `README.md` | one |\n| `README.md` | two |\n"
        )
        self.assertEqual(names, {"README.md"})
        self.assertEqual(duplicates, 1)


if __name__ == "__main__":
    unittest.main()

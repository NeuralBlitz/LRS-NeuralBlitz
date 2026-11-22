"""Gitlink / .gitmodules dependency provenance checks (offline)."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gitlink_integrity", ROOT / "scripts" / "check_submodule_integrity.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class GitlinkIntegrityTests(unittest.TestCase):
    def test_current_gitlinks_and_mappings_are_consistent(self):
        self.assertEqual(module.check(), [])
        self.assertEqual(len(module.gitlinks_from_index()), 4)
        self.assertEqual(len(module.parse_gitmodules(
            (ROOT / ".gitmodules").read_text(encoding="utf-8")
        )), 4)

    def test_unmapped_gitlink_is_detected(self):
        links = module.gitlinks_from_index()
        mapping = dict(module.APPROVED)
        del mapping["neuralblitz-v50/Advanced-Research/Advanced-Research"]
        errors = module.validate(mapping, links)
        self.assertTrue(any("no .gitmodules mapping" in error for error in errors))

    def test_fabricated_mapping_or_gitlink_cannot_be_silently_added(self):
        links = module.gitlinks_from_index()
        path = "neuralblitz-v50/unreviewed"
        tampered = dict(module.APPROVED)
        tampered[path] = "https://github.com/NeuralBlitz/unreviewed.git"
        errors = module.validate(tampered, links)
        self.assertTrue(any("without a tracked gitlink" in error for error in errors))
        links[path] = "f" * 40
        errors = module.validate(tampered, links)
        self.assertTrue(any("Unapproved new Gitlink" in error for error in errors))

    def test_unverified_or_credential_bearing_remotes_are_rejected(self):
        links = module.gitlinks_from_index()
        for url in (
            "https://evil.example.com/Advanced-Research.git",
            "https://user:password@github.com/NeuralBlitz/Advanced-Research.git",
            "git@github.com:NeuralBlitz/Advanced-Research.git",
            "file:///tmp/Advanced-Research",
            "https://github.com/NeuralBlitz/Not-The-Pinned-Repo.git",
        ):
            with self.subTest(url=url):
                mapping = dict(module.APPROVED)
                mapping["neuralblitz-v50/Advanced-Research/Advanced-Research"] = url
                errors = module.validate(mapping, links)
                self.assertTrue(any("explicitly verified HTTPS URL" in e for e in errors))

    def test_empty_and_duplicate_sections_fail_parse(self):
        bad = """[submodule "same"]
path = same
url = https://github.com/NeuralBlitz/example.git
[submodule "same"]
path = same
url = https://github.com/NeuralBlitz/other.git
"""
        with self.assertRaises(Exception):
            module.parse_gitmodules(bad)
        with self.assertRaises(ValueError):
            module.parse_gitmodules('[submodule "same"]\npath = different\nurl = example\n')

    def test_invalid_pinned_shas_are_rejected(self):
        links = module.gitlinks_from_index()
        path = "lrs_agents"
        for sha in ("0" * 40, "xyz", "f" * 39 + "g"):
            with self.subTest(sha=sha):
                mutated = dict(links)
                mutated[path] = sha
                self.assertTrue(any("Gitlink" in x or "SHA" in x for x in module.validate(
                    dict(module.APPROVED), mutated
                )))


if __name__ == "__main__":
    unittest.main()

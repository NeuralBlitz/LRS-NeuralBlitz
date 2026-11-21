"""Standalone checks for VSIX staging and package allowlist policy."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "scripts" / "vscode_candidate.py"
spec = importlib.util.spec_from_file_location("vscode_candidate", script)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidatePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.stage = self.workspace / "stage"
        candidate.stage_extension(self.stage)
        (self.stage / "dist").mkdir()
        (self.stage / "dist" / "extension.js").write_text(
            "/* test-only fixture */\n" + "const testFixture = true;\n" * 8,
            encoding="utf-8",
        )

    def create_fixture_vsix(self, exclude=(), additional=()):
        excluded = set(exclude)
        vsix = self.workspace / "candidate.vsix"
        with zipfile.ZipFile(vsix, "w") as archive:
            archive.writestr("extension.vsixmanifest", "<PackageManifest/>")
            archive.writestr("[Content_Types].xml", "<Types/>")
            for path in self.stage.rglob("*"):
                if not path.is_file():
                    continue
                name = "extension/" + path.relative_to(self.stage).as_posix()
                if name not in excluded:
                    archive.write(path, name)
            for name, data in additional:
                archive.writestr(name, data)
        return vsix

    def test_staging_excludes_the_large_monorepo_and_dev_dependencies(self):
        allowed = candidate.ALLOWED_EXTENSION_TOPLEVEL
        self.assertEqual(
            {p.name for p in self.stage.iterdir()},
            allowed,
        )
        manifest = json.loads((self.stage / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["main"], "./dist/extension.js")
        self.assertNotIn("dependencies", manifest)
        self.assertNotIn("devDependencies", manifest)
        self.assertNotIn("scripts", manifest)
        self.assertNotIn("neuralblitz-v50", allowed)

    def test_valid_minimal_archive_passes(self):
        candidate.verify_candidate(self.create_fixture_vsix())

    def test_archive_rejects_nested_research_project(self):
        vsix = self.create_fixture_vsix(
            additional=[("extension/neuralblitz-v50/research.py", "secret")],
        )
        with self.assertRaisesRegex(ValueError, "Unapproved VSIX content"):
            candidate.verify_candidate(vsix)

    def test_missing_runtime_cannot_be_a_valid_release(self):
        vsix = self.create_fixture_vsix(exclude={"extension/dist/extension.js"})
        with self.assertRaisesRegex(ValueError, "missing essential files"):
            candidate.verify_candidate(vsix)

    def test_missing_contributed_grammar_fails_validation(self):
        manifest = json.loads((self.stage / "package.json").read_text(encoding="utf-8"))
        grammar = manifest["contributes"]["grammars"][0]["path"].removeprefix("./")
        vsix = self.create_fixture_vsix(exclude={"extension/" + grammar})
        with self.assertRaisesRegex(ValueError, "missing packaged asset"):
            candidate.verify_candidate(vsix)

    def test_stage_will_not_overwrite_existing_candidate(self):
        with self.assertRaisesRegex(ValueError, "non-empty stage"):
            candidate.stage_extension(self.stage)

    def test_stage_refuses_to_mutate_checkout(self):
        with self.assertRaisesRegex(ValueError, "outside the repository checkout"):
            candidate.stage_extension(ROOT / "dist" / "candidate")


if __name__ == "__main__":
    unittest.main()

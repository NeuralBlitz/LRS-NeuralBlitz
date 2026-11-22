"""Regressions for current user-facing onboarding documents, not runtime capability proof."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ActiveDocumentationContractTests(unittest.TestCase):
    def test_quickstart_is_not_a_replit_deployment_promise(self):
        quick = (ROOT / "README_SIMPLE.md").read_text(encoding="utf-8")
        self.assertIn("**Status: pre-production.**", quick)
        self.assertIn("node index.js", quick)
        self.assertIn("does **not**", quick)
        self.assertIn("bun install --frozen-lockfile", quick)
        self.assertIn("gateway/requirements-pinned.txt", quick)
        self.assertNotIn('Just Click "Run"', quick)
        self.assertNotIn("264,447x", quick)

    def test_active_api_reference_contains_no_fictional_contract(self):
        api = (ROOT / "docs/API_REFERENCE.md").read_text(encoding="utf-8")
        self.assertIn("**Status: pre-production", api)
        self.assertIn("integration_verified", api)
        self.assertIn("HTTP 501", api)
        self.assertIn("GET /", api)
        self.assertNotIn('"password": "admin123"', api)
        self.assertNotIn("10,000 requests/minute", api)
        self.assertNotIn("Production:  https://api.opencode-lrs.com", api)

    def test_gateway_examples_use_one_shell_for_credentials(self):
        for path in ("README_SIMPLE.md", "docs/API_REFERENCE.md", "gateway/README.md"):
            body = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("uvicorn main:app --host 127.0.0.1 --port 8000 &", body)
            self.assertIn("LRS_GATEWAY_PID=$!", body)
            self.assertIn('kill "$LRS_GATEWAY_PID"', body)
            self.assertIn("--retry-connrefused", body)
            self.assertNotIn("In a second terminal", body)
            self.assertNotIn("In another terminal", body)

    def test_both_previous_documents_are_preserved(self):
        for path in (
            "docs/history/README_SIMPLE-legacy-2026-11-22.md",
            "docs/history/API_REFERENCE-legacy-2026-11-22.md",
        ):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("ARCHIVED", text)
            self.assertGreater(len(text), 100)


if __name__ == "__main__":
    unittest.main()

"""Validate the root gateway's public-facing truth claims without importing FastAPI.

This tests isolated source functions only, not service startup or authentication.
"""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]

def extract(name, context):
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    matches = [x for x in tree.body if isinstance(x, ast.AsyncFunctionDef) and x.name == name]
    if len(matches) != 1:
        raise AssertionError("Expected one route: " + name)
    method = matches[0]
    method.decorator_list = []
    namespace = dict(context)
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=[method], type_ignores=[])
    ), "main.py", "exec"), namespace)
    return namespace[name]


class GatewayTruthTests(unittest.TestCase):
    def test_home_page_does_not_advertise_fake_ai_or_performance(self):
        route = extract("read_root", {})
        html = asyncio.run(route())
        for phrase in ("264,447", "Cognitive AI Active", "JWT authentication",
                       "Enterprise Security", "perfect accuracy", "cognitive_demo.html"):
            self.assertNotIn(phrase, html)
        self.assertIn("Pre-production research prototype", html)
        self.assertIn("does <strong>not execute", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn("<script", html)

    def test_missing_backends_are_reported_unavailable(self):
        route = extract("get_integration_status", {
            "LRS_AVAILABLE": False, "opencode_tool": None, "lrs_agent": None,
            "COGNITIVE_AVAILABLE": False, "MULTI_AGENT_AVAILABLE": False,
        })
        result = asyncio.run(route())
        self.assertEqual(result["integration_active"], False)
        self.assertEqual(result["integration_verified"], False)
        self.assertEqual(result["opencode_available"], False)
        self.assertEqual(result["lrs_agent_precision"], None)
        self.assertEqual(result["lrs_agent_adaptations"], None)

    def test_component_detection_does_not_fake_end_to_end_health(self):
        tool = SimpleNamespace(opencode_path="/local/path")
        agent = SimpleNamespace(belief_state={"precision": .25, "adaptation_count": 3})
        route = extract("get_integration_status", {
            "LRS_AVAILABLE": True, "opencode_tool": tool, "lrs_agent": agent,
            "COGNITIVE_AVAILABLE": True, "MULTI_AGENT_AVAILABLE": True,
        })
        result = asyncio.run(route())
        self.assertTrue(result["opencode_available"])
        self.assertFalse(result["integration_active"])
        self.assertFalse(result["integration_verified"])
        self.assertEqual(result["lrs_agent_precision"], .25)

    def test_legacy_auto_registration_is_opt_in_and_local_bind_default(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("LRS_ENABLE_EXPERIMENTAL_ROUTES") == "1"', source)
        self.assertIn('uvicorn.run(app, host="127.0.0.1"', source)
        self.assertNotIn('uvicorn.run(app, host="0.0.0.0"', source)
        self.assertIn("except ImportError:", source)
        self.assertIn("BACKEND_IMPORT_AVAILABLE = False", source)

    def test_stage_cluster_numbers_are_clearly_labeled_simulations(self):
        a = (ROOT / "deployment_summary.py").read_text(encoding="utf-8")
        b = (ROOT / "stage_clusters_5000_9999_deployment.py").read_text(encoding="utf-8")
        self.assertIn("SIMULATED CAPACITY PLAN", a)
        self.assertIn("no infrastructure was provisioned or verified", a)
        self.assertIn("NO LIVE DEPLOYMENT", b)
        self.assertIn("NO REAL AGENTS PROVISIONED", b)


if __name__ == "__main__":
    unittest.main()

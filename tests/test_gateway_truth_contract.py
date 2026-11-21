"""Offline source-level checks for truthful gateway status and homepage.

These do not import FastAPI or the unavailable LRS gitlink. They do not
establish a working authenticated ASGI integration.
"""

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "main.py"


def isolate_route(name, globals_):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    matches = [
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise AssertionError("Expected exactly one route: " + name)
    node = matches[0]
    node.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = dict(globals_)
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace[name]


class GatewayTruthContractTests(unittest.TestCase):
    def test_home_page_is_explicitly_preproduction_and_not_fake_status(self):
        route = isolate_route("read_root", {})
        html = asyncio.run(route())
        self.assertIn("Pre-production research prototype", html)
        self.assertIn("not execute", html)
        self.assertNotIn("264,447", html)
        self.assertNotIn("JWT authentication", html)
        self.assertNotIn("Enterprise Status: Operational", html)
        self.assertNotIn("Cognitive AI Active", html)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("cdn.tailwindcss.com", html)
        self.assertIn("Content-Security-Policy", html)

    def test_disabled_components_cannot_be_misreported_as_live(self):
        route = isolate_route("get_integration_status", {
            "LRS_AVAILABLE": False,
            "COGNITIVE_AVAILABLE": False,
            "MULTI_AGENT_AVAILABLE": False,
            "opencode_tool": None,
            "lrs_agent": None,
        })
        result = asyncio.run(route())
        self.assertFalse(result["integration_active"])
        self.assertFalse(result["integration_verified"])
        self.assertFalse(result["lrs_available"])
        self.assertFalse(result["opencode_available"])
        self.assertIsNone(result["lrs_agent_precision"])
        self.assertIsNone(result["lrs_agent_adaptations"])
        self.assertIn("not been implemented", result["message"])

    def test_component_detection_does_not_invent_integration_health(self):
        route = isolate_route("get_integration_status", {
            "LRS_AVAILABLE": True,
            "COGNITIVE_AVAILABLE": True,
            "MULTI_AGENT_AVAILABLE": True,
            "opencode_tool": SimpleNamespace(opencode_path="/some/path"),
            "lrs_agent": SimpleNamespace(belief_state={
                "precision": 0.5, "adaptation_count": 2
            }),
        })
        result = asyncio.run(route())
        self.assertTrue(result["opencode_available"])
        self.assertTrue(result["lrs_available"])
        self.assertEqual(result["lrs_agent_precision"], 0.5)
        self.assertEqual(result["lrs_agent_adaptations"], 2)
        self.assertFalse(result["integration_active"])
        self.assertFalse(result["integration_verified"])

    def test_gateway_bind_is_loopback_and_legacy_routes_require_opt_in(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('uvicorn.run(app, host="127.0.0.1", port=8000)', text)
        self.assertIn('os.environ.get("LRS_ENABLE_EXPERIMENTAL_ROUTES") == "1"', text)
        self.assertNotIn('"integration_active": True', text)


if __name__ == "__main__":
    unittest.main()

"""Pre-release structural checks for root demos and declared JSON assets.

These tests parse code and execute only the isolated, dependency-free Flask
handler with stubs. No cloud deployment or VS Code Extension Host is tested.
"""
import ast
import json
from pathlib import Path
import re
import time
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


class ReleaseSourceContractTests(unittest.TestCase):
    def test_root_python_launchers_parse_without_injected_tool_markup(self):
        for name in ("main.py", "server.py", "simple_app.py"):
            with self.subTest(path=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                ast.parse(source, filename=name)
                self.assertNotIn("</content>", source)
                self.assertNotIn('<parameter name="filePath">', source)

    def test_nbcl_and_other_language_configs_are_valid_json_and_pairs(self):
        manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        languages = manifest["contributes"]["languages"]
        self.assertEqual({x["id"] for x in languages}, {"nbcl", "lon", "reflexaellang"})
        for language in languages:
            path = ROOT / language["configuration"]
            with self.subTest(path=str(path)):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(value.get("brackets"), list)
                for pair in value["brackets"]:
                    self.assertIsInstance(pair, list)
                    self.assertEqual(len(pair), 2)
                    self.assertTrue(all(isinstance(ch, str) for ch in pair))
                for pair in value.get("autoClosingPairs", []):
                    self.assertIsInstance(pair, dict)
                    self.assertIsInstance(pair.get("open"), str)
                    self.assertIsInstance(pair.get("close"), str)
                for name in ("increaseIndentPattern", "decreaseIndentPattern"):
                    pattern = value.get("indentationRules", {}).get(name)
                    if pattern is not None:
                        re.compile(pattern)

    def test_azure_template_is_valid_json_without_wildcard_cors(self):
        template = json.loads((
            ROOT / "serverless_deployments/azure_functions/azuredeploy.json"
        ).read_text(encoding="utf-8"))
        self.assertIsInstance(template.get("resources"), list)
        self.assertGreater(len(template["resources"]), 0)
        for resource in template["resources"]:
            if resource.get("type") == "Microsoft.Web/sites":
                settings = resource["properties"]["siteConfig"]
                self.assertEqual(settings["cors"]["allowedOrigins"], [])

    def test_demo_has_no_invented_speedup_or_debugger_exposure(self):
        source = (ROOT / "simple_app.py").read_text(encoding="utf-8")
        self.assertNotIn("264,447", source)
        self.assertNotIn("1.2 milliseconds", source)
        self.assertNotIn("cognitive_score", source)
        self.assertNotIn("time.sleep(", source)
        self.assertIn("app.run(host='127.0.0.1', port=8080, debug=False)", source)
        server = (ROOT / "server.py").read_text(encoding="utf-8")
        self.assertIn('host="127.0.0.1"', server)

    def test_demo_endpoint_counts_only_and_rejects_invalid_requests(self):
        source = (ROOT / "simple_app.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        functions = [
            x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == "analyze"
        ]
        self.assertEqual(len(functions), 1)
        fn = functions[0]
        fn.decorator_list = []
        code = compile(ast.fix_missing_locations(
            ast.Module(body=[fn], type_ignores=[])
        ), str(ROOT / "simple_app.py"), "exec")
        request = SimpleNamespace(get_json=lambda silent=True: {"code": "def fn():\n    if ok:\n        pass"})
        namespace = {
            "request": request, "jsonify": lambda obj: obj, "time": time,
        }
        exec(code, namespace)
        result = namespace["analyze"]()
        self.assertTrue(result["success"])
        self.assertEqual(result["insights"]["functions"], 1)
        self.assertEqual(result["insights"]["conditionals"], 1)
        self.assertEqual(result["patterns_found"], 2)
        self.assertNotIn("cognitive_score", result)
        self.assertGreaterEqual(result["analysis_time_ms"], 0)
        request.get_json = lambda silent=True: {"code": 123}
        rejected, status = namespace["analyze"]()
        self.assertEqual(status, 400)
        self.assertFalse(rejected["success"])
        request.get_json = lambda silent=True: {"code": "x" * 200001}
        oversized, status = namespace["analyze"]()
        self.assertEqual(status, 413)
        self.assertFalse(oversized["success"])


if __name__ == "__main__":
    unittest.main()

"""Validate that gateway startup never executes optional LRS helper constructors.

A synthetic package with explosive import/constructor side effects proves the
default startup path isolates them. This tests the local gateway contract, not
the real Gitlink's functional compatibility.
"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

FAKE_FILES = {
    "lrs_agents/__init__.py": "",
    "lrs_agents/lrs/__init__.py": "",
    "lrs_agents/lrs/opencode/__init__.py": "",
    "lrs_agents/lrs/opencode/simplified_integration.py": """
class OpenCodeTool:
    def __init__(self):
        raise RuntimeError('unsafe OpenCodeTool subprocess probe executed')

class SimplifiedLRSAgent:
    def __init__(self, *args, **kwargs):
        raise RuntimeError('unsafe agent instance constructed')
""",
    "lrs_agents/lrs/benchmarking/__init__.py": "",
    "lrs_agents/lrs/benchmarking/benchmark_integration.py": (
        "raise RuntimeError('benchmark import executed')\n"
    ),
    "lrs_agents/lrs/enterprise/__init__.py": "",
    "lrs_agents/lrs/enterprise/enterprise_security_monitoring.py": (
        "raise RuntimeError('enterprise import executed')\n"
    ),
}


class OptionalLRSImportIsolationTests(unittest.TestCase):
    def make_package(self, directory):
        for filename, body in FAKE_FILES.items():
            location = Path(directory) / filename
            location.parent.mkdir(parents=True, exist_ok=True)
            location.write_text(body, encoding="utf-8")

    def run_isolated(self, package_path, *, enable_experimental=False):
        script = """
import sys
sys.path.insert(0, sys.argv[1])
import main
assert main.BACKEND_IMPORT_AVAILABLE is True
assert main.opencode_tool is None
assert main.lrs_agent is None
assert 'lrs_agents.lrs.benchmarking.benchmark_integration' not in sys.modules
assert 'lrs_agents.lrs.enterprise.enterprise_security_monitoring' not in sys.modules
"""
        if enable_experimental:
            script = """
import sys
sys.path.insert(0, sys.argv[1])
import main
"""
        env = os.environ.copy()
        env.pop("LRS_ENABLE_EXPERIMENTAL_ROUTES", None)
        if enable_experimental:
            env["LRS_ENABLE_EXPERIMENTAL_ROUTES"] = "1"
        return subprocess.run(
            [sys.executable, "-c", script, str(package_path)],
            cwd=ROOT, env=env, text=True, capture_output=True,
            timeout=15, check=False,
        )

    def test_default_import_does_not_run_tools_or_enterprise_plugins(self):
        with tempfile.TemporaryDirectory() as path:
            self.make_package(path)
            result = self.run_isolated(path)
        self.assertEqual(result.returncode, 0, result.stderr[-1200:])

    def test_explicit_opt_in_reaches_isolated_experimental_import(self):
        with tempfile.TemporaryDirectory() as path:
            self.make_package(path)
            result = self.run_isolated(path, enable_experimental=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("benchmark import executed", result.stderr)

    def test_gateway_does_not_use_fabricated_dash_named_submodule_path(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn('sys.path.insert(', source)
        self.assertNotIn('OpenCodeTool() if BACKEND_IMPORT_AVAILABLE', source)
        self.assertIn('opencode_tool = None', source)


if __name__ == "__main__":
    unittest.main()

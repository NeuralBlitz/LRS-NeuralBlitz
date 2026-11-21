"""Isolated behavioral regression checks for the multi-agent workflow endpoint.

Extracting the route function with AST avoids importing the large optional
LRS/FastAPI integration graph. These tests do not replace ASGI integration
tests once a real executor becomes available.
"""

import ast
import asyncio
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "main.py"


class StubHTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def load_workflow_route(multi_agent_available):
    """Compile the actual route function without unrelated app imports."""
    module = ast.parse(ENTRYPOINT.read_text(encoding="utf-8"))
    routes = [
        node for node in module.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "execute_multi_agent_workflow"
    ]
    if len(routes) != 1:
        raise AssertionError("Expected exactly one workflow endpoint")
    route = routes[0]
    route.decorator_list = []
    isolated = ast.fix_missing_locations(
        ast.Module(body=[route], type_ignores=[])
    )
    namespace = {
        "MULTI_AGENT_AVAILABLE": multi_agent_available,
        "HTTPException": StubHTTPException,
    }
    exec(compile(isolated, str(ENTRYPOINT), "exec"), namespace)
    return namespace[route.name]


class WorkflowFailClosedTests(unittest.TestCase):
    def assert_http_failure(self, available, payload, expected_status):
        route = load_workflow_route(available)
        with self.assertRaises(StubHTTPException) as error:
            asyncio.run(route(payload))
        self.assertEqual(error.exception.status_code, expected_status)
        return error.exception.detail

    def test_unavailable_backend_returns_503(self):
        self.assert_http_failure(False, {"tasks": ["inspect"]}, 503)

    def test_no_tasks_returns_400(self):
        self.assert_http_failure(True, {"tasks": []}, 400)

    def test_non_list_tasks_returns_400(self):
        self.assert_http_failure(True, {"tasks": "inspect"}, 400)

    def test_unimplemented_executor_never_reports_completion(self):
        detail = self.assert_http_failure(
            True, {"tasks": ["inspect", "report"]}, 501
        )
        self.assertIn("no tasks were run", detail)


if __name__ == "__main__":
    unittest.main()

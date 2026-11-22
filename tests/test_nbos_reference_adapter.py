"""Authenticated HTTP/ASGI contracts for the real read-only NBOS reference.

The tests use FastAPI/Starlette and the actual adapter handlers, not mocks of
execution results. This is explicitly not a test of a full NBCL engine.
"""

import os
from pathlib import Path
from unittest.mock import patch
import unittest

import httpx
from gateway import nbos_reference as reference

TOKEN = "test-only-reference-strong-ascii-bearer-token-0123456789"


class ReferenceAdapterASGITests(unittest.IsolatedAsyncioTestCase):
    async def send(self, method, path, token=TOKEN, **kwargs):
        headers = kwargs.pop("headers", {})
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        transport = httpx.ASGITransport(app=reference.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1", timeout=5
        ) as client:
            return await client.request(method, path, headers=headers, **kwargs)

    async def test_public_disclaimer_and_authenticated_discovery(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            root = await self.send("GET", "/", token=None)
            denied = await self.send("GET", "/nbos/v1/capabilities", token=None)
            allowed = await self.send("GET", "/nbos/v1/capabilities")
        self.assertEqual(root.status_code, 200)
        self.assertIn("Pre-production research prototype", root.text)
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)
        caps = allowed.json()
        self.assertEqual(caps["protocol"], "nbos/1")
        self.assertIs(caps["compatible"], True)
        self.assertEqual(caps["operations"], list(reference.REFERENCE_OPERATIONS))
        self.assertFalse(caps["execution_engine_available"])
        self.assertFalse(caps["agent_boot_available"])
        self.assertFalse(caps["debugger_available"])
        self.assertNotIn(TOKEN, allowed.text)

    async def test_status_is_real_reference_state_not_fake_agent(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.send("GET", "/status")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["system_status"], "read_only_reference")
        self.assertIs(body["agent_booted"], False)
        self.assertIs(body["execution_engine_available"], False)
        self.assertIs(body["integration_verified"], False)
        self.assertIsNone(body["governance_core"]["veritas_vpce"]["score"])

    async def test_status_and_help_execute_only_after_pure_operations(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            for command in reference.REFERENCE_COMMANDS:
                with self.subTest(command=command):
                    response = await self.send(
                        "POST", "/execute", json={"command": command}
                    )
                    self.assertEqual(response.status_code, 200)
                    payload = response.json()
                    self.assertIs(payload["ok"], True)
                    self.assertIs(payload["completed"], True)
                    self.assertIsInstance(payload["result"], dict)

    async def test_rejects_arbitrary_nbcl_scripts_files_debugger_and_boot(self):
        unsafe = (
            {"command": "/apply --modify-file=secret"},
            {"command": "/status; rm -rf /"},
            {"command": " /status"},
            {"command": "/status\n/execute"},
            {"command": ""},
            {"command": "/boot"},
            {"program": "/etc/passwd"},
            {"program": "demo.nbcl", "breakpoints": []},
            {"command": "/status", "program": "/tmp/file"},
            {"command": "/status", "extra": True},
            {"command": ["/status"]},
        )
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            for body in unsafe:
                with self.subTest(body=body):
                    response = await self.send("POST", "/execute", json=body)
                    self.assertEqual(response.status_code, 422)
                    self.assertIs(response.json()["ok"], False)
                    self.assertIs(response.json()["completed"], False)
            for method, route in (
                ("POST", "/boot"),
                ("GET", "/debug/stack"),
                ("POST", "/debug/evaluate"),
                ("GET", "/debug/variables/local"),
            ):
                missing = await self.send(method, route)
                self.assertEqual(missing.status_code, 404)

    async def test_introspection_only_exposes_real_system_status(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            supported = await self.send(
                "POST", "/introspect", json={"scope": "system"}
            )
            denied = await self.send(
                "POST", "/introspect", json={"scope": "governance"}
            )
            extra = await self.send(
                "POST", "/introspect",
                json={"scope": "system", "extra": "wrong"},
            )
        self.assertEqual(supported.status_code, 200)
        self.assertEqual(supported.json()["status"], reference.reference_status())
        self.assertEqual(supported.json()["scope"], "system")
        self.assertEqual(denied.status_code, 422)
        self.assertEqual(extra.status_code, 422)

    async def test_all_operations_are_auth_guarded_and_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            missing_config = await self.send("GET", "/status")
        self.assertEqual(missing_config.status_code, 503)
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            for method, route, body in (
                ("GET", "/status", None),
                ("POST", "/introspect", {"scope": "system"}),
                ("POST", "/execute", {"command": "/status"}),
            ):
                for supplied in (None, "invalid-token"):
                    with self.subTest(method=method, path=route, token=supplied):
                        kwargs = {"json": body} if body is not None else {}
                        rejected = await self.send(
                            method, route, token=supplied, **kwargs
                        )
                        self.assertEqual(rejected.status_code, 401)
            oversized = await self.send(
                "POST", "/execute",
                headers={"Content-Length": str(1024 * 1024 + 1)},
                content=b"{}",
            )
            self.assertEqual(oversized.status_code, 413)

    async def test_unknown_remote_endpoints_are_never_advertised(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.send("GET", "/nbos/v1/capabilities")
            openapi = await self.send("GET", "/openapi.json")
        self.assertEqual(openapi.status_code, 200)
        paths = openapi.json()["paths"]
        advertised = response.json()["operations"]
        for item in advertised:
            method, route = item.split(" ", 1)
            self.assertIn(route, paths)
            self.assertIn(method.lower(), paths[route])
        self.assertNotIn("/boot", paths)
        self.assertNotIn("/debug/stack", paths)

    def test_reference_module_has_no_shell_or_file_execution(self):
        code = (Path(__file__).resolve().parents[1] /
                "gateway" / "nbos_reference.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "eval(", "exec(", "open(", "Path("):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()

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
        self.assertEqual(caps["execution_modes"], ["command", "source"])
        self.assertIs(caps["subset_interpreter_available"], True)
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
            for command in ("/status", "/help"):
                with self.subTest(command=command):
                    response = await self.send(
                        "POST", "/execute", json={"command": command}
                    )
                    self.assertEqual(response.status_code, 200)
                    payload = response.json()
                    self.assertIs(payload["ok"], True)
                    self.assertIs(payload["completed"], True)
                    self.assertIsInstance(payload["result"], dict)


    async def test_integer_calculation_is_executed_not_faked(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.send(
                "POST", "/execute",
                json={"command": "/calc --a=-12 --op=mul --b=5"},
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIs(body["ok"], True)
        self.assertIs(body["completed"], True)
        self.assertEqual(body["result"], {
            "operation": "mul", "a": -12, "b": 5, "value": -60,
        })

    async def test_bounded_inline_program_executes_ordered_preparsed_steps(self):
        program = "# only pure commands\n/status\n/calc --a=7 --op=add --b=8\n/help\n"
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.send(
                "POST", "/execute", json={"source": program}
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIs(body["ok"], True)
        self.assertIs(body["completed"], True)
        self.assertEqual(body["instruction_count"], 3)
        self.assertEqual([step["line"] for step in body["steps"]], [2, 3, 4])
        self.assertEqual([step["command"] for step in body["steps"]],
                         ["/status", "/calc", "/help"])
        self.assertEqual(body["steps"][1]["result"]["value"], 15)
        self.assertEqual(body["steps"][0]["result"]["agent_booted"], False)

    async def test_authenticated_program_reads_its_own_local_registers(self):
        source = (
            "/local.set --name=budget --value=17\n"
            "/local.add --name=budget --value=-4\n"
            "/local.get --name=budget\n"
        )
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            result = await self.send("POST", "/execute", json={"source": source})
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertIs(body["ok"], True)
        self.assertIs(body["completed"], True)
        self.assertEqual(body["instruction_count"], 3)
        self.assertEqual(body["final_locals"], {"budget": 13})
        self.assertEqual(
            [step["result"]["value"] for step in body["steps"]],
            [17, 13, 13],
        )

    async def test_registers_cannot_be_read_across_http_requests(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            first = await self.send(
                "POST", "/execute",
                json={"source": "/local.set --name=secret --value=777"},
            )
            second = await self.send(
                "POST", "/execute",
                json={"source": "/local.get --name=secret"},
            )
            one_shot = await self.send(
                "POST", "/execute",
                json={"command": "/local.get --name=secret"},
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["final_locals"], {"secret": 777})
        for response in (second, one_shot):
            self.assertEqual(response.status_code, 422)
            self.assertIs(response.json()["completed"], False)
            self.assertNotIn("steps", response.json())
            self.assertNotIn("secret", response.text)

    async def test_program_state_errors_fail_atomically_with_no_results(self):
        malformed = (
            "/status\n/local.get --name=missing",
            "/status\n/local.set --name=x --value=1000000\n"
            "/local.add --name=x --value=1",
            "\n".join(f"/local.set --name={name} --value=1" for name in "abcdefghi"),
        )
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            for source in malformed:
                with self.subTest(length=len(source)):
                    response = await self.send("POST", "/execute", json={"source": source})
                    self.assertEqual(response.status_code, 422)
                    self.assertIs(response.json()["ok"], False)
                    self.assertIs(response.json()["completed"], False)
                    self.assertNotIn("steps", response.json())
                    self.assertNotIn("final_locals", response.json())

    async def test_parallel_http_programs_have_disjoint_ephemeral_state(self):
        import asyncio
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response_a, response_b = await asyncio.gather(
                self.send("POST", "/execute", json={
                    "source": "/local.set --name=x --value=111\n/local.get --name=x"
                }),
                self.send("POST", "/execute", json={
                    "source": "/local.set --name=x --value=-222\n/local.get --name=x"
                }),
            )
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_a.json()["final_locals"], {"x": 111})
        self.assertEqual(response_b.json()["final_locals"], {"x": -222})
        self.assertEqual(response_a.json()["steps"][1]["result"]["value"], 111)
        self.assertEqual(response_b.json()["steps"][1]["result"]["value"], -222)

    async def test_untrusted_inline_programs_are_rejected_without_partial_results(self):
        disallowed = (
            "/status\n/boot\n/help",
            "/status\n/apply --payload=secret",
            "/status\n/calc --a=1 --op=pow --b=9999999",
            "/status\n/calc --a=9999999 --op=mul --b=9999999",
            "/status\n" * 17,
            "/status\n" * 65,
            "# comment only",
            "x" * 4097,
        )
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            for source in disallowed:
                with self.subTest(prefix=repr(source[:35])):
                    response = await self.send(
                        "POST", "/execute", json={"source": source}
                    )
                    self.assertEqual(response.status_code, 422)
                    result = response.json()
                    self.assertIs(result["ok"], False)
                    self.assertIs(result["completed"], False)
                    self.assertNotIn("steps", result)
                    self.assertNotIn("secret", response.text)

    async def test_malformed_command_or_source_envelopes_never_run(self):
        bad = (
            {"source": "/status", "command": "/status"},
            {"source": "/status", "program": "/tmp/secrets"},
            {"source": []},
            {"source": None},
            {"source": ""},
            {"source": "# comment\n"},
            {"command": "/calc --a=1 --op=pow --b=2"},
            {"command": "/status\n/help"},
            {"command": "/help", "trace": True},
        )
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            for payload in bad:
                with self.subTest(payload=repr(payload)):
                    response = await self.send(
                        "POST", "/execute", json=payload
                    )
                    self.assertEqual(response.status_code, 422)
                    self.assertIs(response.json()["completed"], False)

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

"""Real loopback Uvicorn process smoke test for the pre-production gateway.

Unlike ASGITransport tests, these requests cross an actual TCP socket
into a child Python Uvicorn process. The test intentionally does NOT
initialize the missing LRS backend or claim NBOS protocol compatibility.
Only built-in Python modules are used by this test; FastAPI/uvicorn are
installed separately through gateway/requirements-pinned.txt in CI.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def get_free_loopback_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class GatewayLiveProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = secrets.token_urlsafe(48)
        cls.port = get_free_loopback_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.log = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
        env = os.environ.copy()
        env["LRS_GATEWAY_API_TOKEN"] = cls.token
        env.pop("LRS_ENABLE_EXPERIMENTAL_ROUTES", None)
        cls.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "main:app",
                "--host", "127.0.0.1", "--port", str(cls.port),
                "--no-access-log",
            ],
            cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=cls.log, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if cls.process.poll() is not None:
                    raise RuntimeError("Gateway Uvicorn process exited during startup")
                try:
                    code, _, _ = cls.request_raw("GET", "/")
                    if code == 200:
                        return
                except (URLError, TimeoutError, OSError):
                    pass
                time.sleep(0.12)
            raise RuntimeError("Gateway Uvicorn process did not serve GET / before timeout")
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        process = getattr(cls, "process", None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        log = getattr(cls, "log", None)
        if log is not None and not log.closed:
            if process is not None and process.returncode not in (0, -15, None):
                log.seek(0)
                output = log.read(4000)
                print(
                    "Gateway child process exited with return code "
                    f"{process.returncode}. Startup logs: {output}",
                    file=sys.stderr,
                )
            log.close()

    @classmethod
    def request_raw(cls, method, path, *, authenticated=False, payload=None):
        headers = {"Accept": "application/json"}
        data = None
        if authenticated:
            headers["Authorization"] = "Bearer " + cls.token
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            cls.base_url + path, data=data,
            method=method, headers=headers,
        )
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, response.headers, response.read().decode("utf-8")
        except HTTPError as failure:
            with failure:
                return failure.code, failure.headers, failure.read().decode("utf-8")

    def test_live_server_exposes_only_truthful_public_homepage(self):
        status, headers, body = self.request_raw("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Pre-production research prototype", body)
        self.assertNotIn("264,447", body)
        self.assertNotIn("JWT authentication", body)
        self.assertNotIn(self.token, body)

    def test_live_server_rejects_unauthenticated_requests_before_routing(self):
        for method, path in (
            ("GET", "/api/integration/status"),
            ("GET", "/openapi.json"),
            ("GET", "/docs"),
            ("GET", "/status"),
            ("POST", "/boot"),
            ("POST", "/execute"),
        ):
            with self.subTest(path=path):
                status, headers, body = self.request_raw(method, path)
                self.assertEqual(status, 401)
                self.assertEqual(headers.get("WWW-Authenticate"), "Bearer")
                self.assertEqual(headers.get("Cache-Control"), "no-store")
                self.assertNotIn(self.token, body)

    def test_live_server_authenticates_real_gateway_status_but_not_backend(self):
        status, headers, body = self.request_raw(
            "GET", "/api/integration/status", authenticated=True
        )
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIs(payload["integration_active"], False)
        self.assertIs(payload["integration_verified"], False)
        self.assertNotIn(self.token, body)

    def test_live_capability_discovery_is_authenticated_and_negative(self):
        denied_status, _, _ = self.request_raw("GET", "/nbos/v1/capabilities")
        self.assertEqual(denied_status, 401)
        status, _, body = self.request_raw(
            "GET", "/nbos/v1/capabilities", authenticated=True
        )
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["protocol"], "nbos/1")
        self.assertIs(payload["compatible"], False)
        self.assertEqual(payload["operations"], [])
        self.assertNotIn(self.token, body)

    def test_live_server_does_not_fabricate_nbos_routes(self):
        # The VS Code NBOSClient uses /boot, /execute, /status, /introspect
        # and /debug/*; this Python API does not implement those contracts.
        # A protected 404 is honest. A fabricated 200 would be misleading.
        for method, path, payload in (
            ("POST", "/boot", {"mode": "Sentio"}),
            ("POST", "/execute", {"command": "/status"}),
            ("GET", "/status", None),
            ("POST", "/introspect", {"scope": "system"}),
            ("GET", "/debug/stack", None),
        ):
            with self.subTest(path=path):
                status, _, body = self.request_raw(
                    method, path, authenticated=True, payload=payload
                )
                self.assertEqual(status, 404)
                self.assertNotIn(self.token, body)

    def test_live_server_workflow_rejects_unavailable_execution(self):
        status, _, body = self.request_raw(
            "POST", "/api/multi-agent/execute-workflow",
            authenticated=True, payload={"tasks": ["run"]},
        )
        self.assertEqual(status, 503)
        self.assertIn("Multi-agent components not available", body)

    def test_live_server_authenticated_openapi_remains_available(self):
        status, _, body = self.request_raw(
            "GET", "/openapi.json", authenticated=True
        )
        self.assertEqual(status, 200)
        paths = json.loads(body)["paths"]
        self.assertIn("/api/integration/status", paths)
        self.assertIn("/api/multi-agent/execute-workflow", paths)
        self.assertNotIn("/boot", paths)


if __name__ == "__main__":
    unittest.main()

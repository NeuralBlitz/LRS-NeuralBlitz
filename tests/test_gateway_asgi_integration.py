"""HTTP/ASGI integration checks against the real FastAPI gateway application.

Unlike the AST-only contract tests, this module imports FastAPI and sends
requests through httpx's ASGI transport. It intentionally runs with no LRS
gitlink/backend and does not claim real integration service health.
"""

import asyncio
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Do not accidentally load optional unreviewed routes during CI.
os.environ.pop("LRS_ENABLE_EXPERIMENTAL_ROUTES", None)
import main as gateway  # noqa: E402


TOKEN = "a-long-unique-test-only-placeholder-not-used-in-deployment-2026"


class GatewayASGIIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, method, path, token=None, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        transport = httpx.ASGITransport(app=gateway.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1", timeout=5
        ) as client:
            return await client.request(method, path, headers=headers, **kwargs)

    async def test_public_root_is_truthful_without_any_token(self):
        with patch.dict(os.environ, {}, clear=True):
            response = await self.request("GET", "/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Pre-production research prototype", response.text)
        self.assertNotIn("264,447", response.text)
        self.assertNotIn("JWT authentication", response.text)
        self.assertNotIn("<script", response.text)
        self.assertIn("Content-Security-Policy", response.text)

    async def test_unconfigured_gateway_api_fails_closed_for_all_endpoints(self):
        with patch.dict(os.environ, {}, clear=True):
            for method, path in (
                ("GET", "/api/integration/status"),
                ("POST", "/api/multi-agent/execute-workflow"),
                ("GET", "/docs"),
                ("GET", "/openapi.json"),
                ("GET", "/some-unexpected-path"),
            ):
                with self.subTest(path=path):
                    response = await self.request(method, path)
                    self.assertEqual(response.status_code, 503)
                    self.assertNotIn("token", response.headers.get("server", ""))

    async def test_short_or_invalid_token_configuration_fails_closed(self):
        for bad in ("test", "a" * 31, "a" * 33 + " ", "ü" * 40):
            with self.subTest(value_kind=len(bad)):
                with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": bad}):
                    response = await self.request("GET", "/api/integration/status")
                self.assertEqual(response.status_code, 503)

    async def test_wrong_missing_and_duplicate_tokens_are_unauthorized(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            missing = await self.request("GET", "/api/integration/status")
            wrong = await self.request(
                "GET", "/api/integration/status", token="x" * len(TOKEN)
            )
            query = await self.request(
                "GET", "/api/integration/status?token=" + TOKEN
            )
            invalid_scheme = await self.request(
                "GET", "/api/integration/status",
                headers={"Authorization": "Basic " + TOKEN}
            )
            duplicate = await self.request(
                "GET", "/api/integration/status",
                headers={"Authorization": "Bearer " + TOKEN + ",Bearer " + TOKEN}
            )
        for response in (missing, wrong, query, invalid_scheme, duplicate):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers.get("www-authenticate"), "Bearer")
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertNotIn(TOKEN, response.text)

    async def test_good_token_only_proves_gateway_access_not_lrs_backend(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.request(
                "GET", "/api/integration/status", token=TOKEN
            )
            openapi = await self.request("GET", "/openapi.json", token=TOKEN)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIs(result["integration_verified"], False)
        self.assertIs(result["integration_active"], False)
        self.assertEqual(openapi.status_code, 200)
        self.assertIn("/api/multi-agent/execute-workflow", openapi.json()["paths"])

    async def test_no_executor_returns_actual_http_errors_not_success(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            with patch.object(gateway, "MULTI_AGENT_AVAILABLE", False):
                unavailable = await self.request(
                    "POST", "/api/multi-agent/execute-workflow",
                    token=TOKEN, json={"tasks": ["inspect"]}
                )
            with patch.object(gateway, "MULTI_AGENT_AVAILABLE", True):
                invalid = await self.request(
                    "POST", "/api/multi-agent/execute-workflow",
                    token=TOKEN, json={"tasks": []}
                )
                unimplemented = await self.request(
                    "POST", "/api/multi-agent/execute-workflow",
                    token=TOKEN, json={"tasks": ["inspect"]}
                )
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(unimplemented.status_code, 501)
        self.assertIn("no tasks were run", unimplemented.json()["detail"])

    async def test_authenticated_body_limit_rejects_declared_oversize(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.request(
                "POST", "/api/multi-agent/execute-workflow", token=TOKEN,
                headers={"Content-Length": str(gateway.MAX_GATEWAY_BODY_BYTES + 1)},
                content=b"{}",
            )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertNotIn(TOKEN, response.text)

    async def test_streaming_body_limit_cannot_be_bypassed_with_no_length(self):
        async def chunked_body():
            yield b'{"tasks":["'
            yield b"x" * gateway.MAX_GATEWAY_BODY_BYTES
            yield b'"]}'

        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.request(
                "POST", "/api/multi-agent/execute-workflow", token=TOKEN,
                headers={"Content-Type": "application/json"},
                content=chunked_body(),
            )
        self.assertEqual(response.status_code, 413)
        self.assertIn("limit exceeded", response.json()["detail"])

    async def test_oversize_request_requires_authentication_first(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.request(
                "POST", "/api/multi-agent/execute-workflow",
                headers={"Content-Length": str(gateway.MAX_GATEWAY_BODY_BYTES + 1)},
                content=b"{}",
            )
        self.assertEqual(response.status_code, 401)

    async def test_normal_authenticated_request_still_reaches_route(self):
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            response = await self.request(
                "POST", "/api/multi-agent/execute-workflow",
                token=TOKEN, json={"tasks": ["inspect"]},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("Multi-agent components not available", response.text)

    async def test_optional_component_exceptions_never_leak_raw_details(self):
        marker = "private-file-and-token-leak-should-not-appear"
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            with patch.object(gateway, "COGNITIVE_AVAILABLE", True), patch.object(
                gateway, "CognitiveCodeAnalyzer", create=True,
                side_effect=RuntimeError(marker)
            ):
                status = await self.request("GET", "/api/cognitive/status", token=TOKEN)
                analyze = await self.request(
                    "POST", "/api/cognitive/analyze", token=TOKEN,
                    json={"code": "x", "file_path": "example.py"},
                )
            with patch.object(gateway, "MULTI_AGENT_AVAILABLE", True), patch.object(
                gateway, "MultiAgentCoordinator", create=True,
                side_effect=RuntimeError(marker)
            ):
                multi = await self.request("GET", "/api/multi-agent/status", token=TOKEN)

        self.assertEqual(status.status_code, 200)
        self.assertIs(status.json()["cognitive_available"], False)
        self.assertEqual(analyze.status_code, 500)
        self.assertEqual(multi.status_code, 200)
        self.assertIs(multi.json()["multi_agent_available"], False)
        for response in (status, analyze, multi):
            self.assertNotIn(marker, response.text)

    async def test_websocket_handshake_rejects_unconfigured_and_bad_auth(self):
        events = []

        async def receive():
            raise AssertionError("Rejected WebSocket auth must not access receive()")

        async def send(message):
            events.append(message)

        scope = {
            "type": "websocket", "path": "/ws/not-registered",
            "headers": [], "scheme": "ws", "subprotocols": [],
        }
        with patch.dict(os.environ, {}, clear=True):
            await gateway.app(scope, receive, send)
        self.assertEqual(events, [{"type": "websocket.close", "code": 1013}])
        events.clear()
        with patch.dict(os.environ, {"LRS_GATEWAY_API_TOKEN": TOKEN}):
            await gateway.app(scope, receive, send)
        self.assertEqual(events, [{"type": "websocket.close", "code": 4401}])


if __name__ == "__main__":
    unittest.main()

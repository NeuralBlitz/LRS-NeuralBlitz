#!/usr/bin/env python3
"""Comprehensive OpenCode ↔ LRS-Agents Integration Web Interface."""

import asyncio
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import sys
import os
import subprocess
import hmac

# Add current directory to Python path
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lrs-agents")
)

# Optional LRS integration: Gitlink content is not present in a normal
# checkout. Missing modules must not prevent the source-only status API from
# starting, and must never be represented as an operational integration.
try:
    from lrs_agents.lrs.opencode.simplified_integration import (
        OpenCodeTool, SimplifiedLRSAgent,
    )
    from lrs_agents.lrs.benchmarking.benchmark_integration import (
        integrate_benchmarks_into_main,
    )
    from lrs_agents.lrs.enterprise.enterprise_security_monitoring import (
        integrate_enterprise_features,
    )
    BACKEND_IMPORT_AVAILABLE = True
except ImportError:
    OpenCodeTool = None
    SimplifiedLRSAgent = None
    integrate_benchmarks_into_main = None
    integrate_enterprise_features = None
    BACKEND_IMPORT_AVAILABLE = False

# Import cognitive components
try:
    from phase6_neuromorphic_research.phase6_neuromorphic_setup import (
        CognitiveArchitecture,
    )
    from lrs_agents.lrs.opencode.lrs_opencode_integration import CognitiveCodeAnalyzer

    COGNITIVE_AVAILABLE = True
except ImportError:
    COGNITIVE_AVAILABLE = False

# Import multi-agent coordination
try:
    from lrs_agents.lrs.cognitive.multi_agent_coordination import MultiAgentCoordinator

    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False

# Check LRS availability
try:
    import lrs

    LRS_AVAILABLE = True
except ImportError:
    LRS_AVAILABLE = False
    print("Warning: LRS-Agents not available")

app = FastAPI(title="OpenCode ↔ LRS-Agents Integration Hub", version="2.0.0")

# Bound authenticated HTTP request bodies before FastAPI decodes JSON or loads
# optional experimental handlers. This is a local resource limit, not a rate
# limiter, reverse proxy, or production DoS defense.
MAX_GATEWAY_BODY_BYTES = 1024 * 1024


class GatewayAuthMiddleware:
    """Small fail-closed development bearer-token boundary for HTTP and WS.

    Only the static public homepage (GET /) is unauthenticated. This protects
    both declared HTTP routes and any optional, dynamically added endpoints.
    The token must be provisioned outside the repository. This is not OAuth,
    RBAC, session authentication, or evidence of production-ready security.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope_type = scope.get("type")
        if scope_type not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        if (
            scope_type == "http"
            and scope.get("path") == "/"
            and scope.get("method") == "GET"
        ):
            return await self.app(scope, receive, send)

        token = os.environ.get("LRS_GATEWAY_API_TOKEN", "")
        # Long tokens reduce accidental use of short demo credentials. Refuse
        # to serve non-public routes with unset/weak configuration.
        configured = (
            32 <= len(token) <= 512
            and token.isascii()
            and not any(c.isspace() for c in token)
        )
        if not configured:
            if scope_type == "websocket":
                await send({"type": "websocket.close", "code": 1013})
            else:
                response = JSONResponse(
                    {"detail": "Gateway authentication is not configured"},
                    status_code=503,
                    headers={"Cache-Control": "no-store"},
                )
                await response(scope, receive, send)
            return

        supplied = [
            value for name, value in scope.get("headers", [])
            if name.lower() == b"authorization"
        ]
        expected = b"Bearer " + token.encode("ascii")
        authorized = len(supplied) == 1 and hmac.compare_digest(
            supplied[0], expected
        )
        if not authorized:
            if scope_type == "websocket":
                await send({"type": "websocket.close", "code": 4401})
            else:
                response = JSONResponse(
                    {"detail": "Bearer token required"},
                    status_code=401,
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "Cache-Control": "no-store",
                    },
                )
                await response(scope, receive, send)
            return
        if scope_type == "http":
            # Authenticate first so unauthenticated traffic cannot force body
            # buffering. Enforce both declared size and streamed bytes; chunked
            # requests must not bypass the limit.
            lengths = [
                value for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ]
            if len(lengths) > 1:
                response = JSONResponse(
                    {"detail": "Invalid Content-Length headers"},
                    status_code=400, headers={"Cache-Control": "no-store"},
                )
                await response(scope, receive, send)
                return
            if lengths:
                try:
                    declared = int(lengths[0].decode("ascii"))
                    if declared < 0:
                        raise ValueError("negative length")
                except (UnicodeDecodeError, ValueError):
                    response = JSONResponse(
                        {"detail": "Invalid Content-Length"},
                        status_code=400, headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return
                if declared > MAX_GATEWAY_BODY_BYTES:
                    response = JSONResponse(
                        {"detail": "Gateway request body limit exceeded"},
                        status_code=413, headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return

            chunks = []
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > MAX_GATEWAY_BODY_BYTES:
                    response = JSONResponse(
                        {"detail": "Gateway request body limit exceeded"},
                        status_code=413, headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break

            # Replay the bounded body exactly once to the existing ASGI app;
            # later receive calls retain disconnect semantics.
            body = b"".join(chunks)
            replayed = False

            async def replay_receive():
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            return await self.app(scope, replay_receive, send)

        return await self.app(scope, receive, send)


app.add_middleware(GatewayAuthMiddleware)


# The legacy LRS modules may register additional routes with unknown
# authentication and authorization properties. Never expose those routes by
# default; require explicit local opt-in while integration tests are pending.
if os.environ.get("LRS_ENABLE_EXPERIMENTAL_ROUTES") == "1":
    if integrate_benchmarks_into_main is not None:
        integrate_benchmarks_into_main(app)
    if integrate_enterprise_features is not None:
        integrate_enterprise_features(app)


# Data models
class IntegrationRequest(BaseModel):
    system: str  # "opencode" or "lrs"
    action: str
    parameters: Optional[Dict[str, Any]] = None


class IntegrationResponse(BaseModel):
    success: bool
    result: Dict[str, Any]
    integration_notes: str


# Optional backend classes are absent in a checkout without the Gitlink.
# Preserve detection for status reporting, never fabricate a working agent.
opencode_tool = OpenCodeTool() if BACKEND_IMPORT_AVAILABLE else None
lrs_agent = (
    SimplifiedLRSAgent(tools=[opencode_tool])
    if opencode_tool is not None else None
)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Present a truthful status page without simulated availability claims."""
    return """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
    <title>LRS-NeuralBlitz — Experimental Gateway</title>
    <style>
      body { max-width: 56rem; margin: 3rem auto; padding: 0 1rem;
             font: 1rem/1.6 system-ui, sans-serif; color: #1c2430; }
      h1 { line-height: 1.2; } code { background: #edf1f4; padding: .1rem .3rem; }
      a { color: #1758a8; } .notice { border-left: .25rem solid #c68920; padding-left: 1rem; }
    </style>
</head>
<body>
    <h1>LRS-NeuralBlitz — Experimental API Gateway</h1>
    <p class="notice"><strong>Pre-production research prototype.</strong> This page
    does not establish backend availability, secure deployment, performance
    improvement, or completed multi-agent execution.</p>
    <p>Check <code>GET /api/integration/status</code> for source-level
    component detection; detection alone does not verify integration health.</p>
    <p>The multi-agent workflow endpoint currently does <strong>not execute
    tasks</strong> and returns an explicit error for unsupported execution.</p>
    <p>For verified scope, installation limitations and release gates, see
    <a href="https://github.com/NeuralBlitz/LRS-NeuralBlitz/blob/main/README.md">
    the source-backed project README</a>.</p>
</body>
</html>"""


@app.get("/api/integration/status")
async def get_integration_status():
    """Report component detection, not unmeasured end-to-end availability."""
    return {
        "lrs_available": LRS_AVAILABLE,
        "opencode_available": bool(
            opencode_tool is not None
            and getattr(opencode_tool, "opencode_path", None) is not None
        ),
        "lrs_agent_precision": (
            lrs_agent.belief_state.get("precision")
            if lrs_agent is not None and hasattr(lrs_agent, "belief_state")
            else None
        ),
        "lrs_agent_adaptations": (
            lrs_agent.belief_state.get("adaptation_count")
            if lrs_agent is not None and hasattr(lrs_agent, "belief_state")
            else None
        ),
        "cognitive_available": COGNITIVE_AVAILABLE,
        "multi_agent_available": MULTI_AGENT_AVAILABLE,
        "integration_active": False,
        "integration_verified": False,
        "message": "A successful authenticated backend health check has not been implemented",
    }


# Cognitive Monitoring Endpoints
@app.get("/api/cognitive/status")
async def get_cognitive_status():
    """Get cognitive architecture status."""
    if not COGNITIVE_AVAILABLE:
        return {
            "cognitive_available": False,
            "message": "Cognitive components not available",
        }

    try:
        # Create a temporary cognitive analyzer to check status
        analyzer = CognitiveCodeAnalyzer()
        cognitive_stats = analyzer.get_cognitive_insights()

        return {
            "cognitive_available": True,
            "cognitive_enabled": analyzer.cognitive_initialized,
            "cognitive_cycles": cognitive_stats.get("cognitive_cycles", 0),
            "patterns_learned": cognitive_stats.get("patterns_learned", 0),
            "working_memory_items": cognitive_stats.get("working_memory_items", 0),
            "attention_focus": cognitive_stats.get("attention_focus"),
            "temporal_sequences": cognitive_stats.get("temporal_sequences_learned", 0),
        }
    except Exception as e:
        # Do not echo internal filenames, secrets, or dependency details to clients.
        return {"cognitive_available": False, "message": "Cognitive status unavailable"}


@app.post("/api/cognitive/analyze")
async def analyze_code_with_cognition(request: dict):
    """Analyze code using cognitive architecture."""
    if not COGNITIVE_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="Cognitive components not available"
        )

    try:
        code_content = request.get("code", "")
        file_path = request.get("file_path", "unknown.py")

        analyzer = CognitiveCodeAnalyzer()
        analysis_result = analyzer.analyze_code_with_cognition(code_content, file_path)

        return {
            "analysis": analysis_result,
            "cognitive_insights": analyzer.get_cognitive_insights(),
            "success": True,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Cognitive analysis failed"
        )


@app.get("/api/multi-agent/status")
async def get_multi_agent_status():
    """Get multi-agent coordination status."""
    if not MULTI_AGENT_AVAILABLE:
        return {
            "multi_agent_available": False,
            "message": "Multi-agent components not available",
        }

    try:
        # Create coordinator to check status
        coordinator = MultiAgentCoordinator()

        return {
            "multi_agent_available": True,
            "agents_count": len(coordinator.agents),
            "tasks_count": len(coordinator.tasks),
            "completed_tasks": len(coordinator.completed_tasks),
            "cognitive_coordination": coordinator.coordination_cognitive is not None,
            "task_patterns": len(coordinator.task_patterns)
            if hasattr(coordinator, "task_patterns")
            else 0,
        }
    except Exception as e:
        return {"multi_agent_available": False, "message": "Multi-agent status unavailable"}


@app.post("/api/multi-agent/execute-workflow")
async def execute_multi_agent_workflow(request: dict):
    """Fail closed until multi-agent workflow execution is implemented.

    The previous demo returned a completed-workflow response without actually
    executing any tasks. Do not fabricate execution, telemetry, or success.
    """
    if not MULTI_AGENT_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="Multi-agent components not available"
        )

    tasks = request.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise HTTPException(
            status_code=400, detail="Provide a non-empty tasks list"
        )

    raise HTTPException(
        status_code=501,
        detail="Multi-agent workflow execution is not implemented; no tasks were run",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

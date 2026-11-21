#!/usr/bin/env python3
"""Comprehensive OpenCode ↔ LRS-Agents Integration Web Interface."""

import asyncio
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sys
import os
import subprocess

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__))
)  # Add twice to ensure root is in path
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lrs-agents")
)

# Import our integration components
from lrs_agents.lrs.opencode.simplified_integration import (
    OpenCodeTool,
    SimplifiedLRSAgent,
)

# Import benchmark integration
from lrs_agents.lrs.benchmarking.benchmark_integration import (
    integrate_benchmarks_into_main,
    add_benchmark_ui_to_main_html,
)

# Import enterprise security and monitoring
from lrs_agents.lrs.enterprise.enterprise_security_monitoring import (
    integrate_enterprise_features,
)

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

# Integrate benchmark endpoints
integrate_benchmarks_into_main(app)

# Integrate enterprise security and monitoring
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


# Global instances for demo
opencode_tool = OpenCodeTool()
lrs_agent = SimplifiedLRSAgent(tools=[opencode_tool])


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
        return {"cognitive_available": False, "error": str(e)}


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
            status_code=500, detail=f"Cognitive analysis failed: {str(e)}"
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
        return {"multi_agent_available": False, "error": str(e)}


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

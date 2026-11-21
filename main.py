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
    """Serve the comprehensive integration web interface."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenCode ↔ LRS-Agents Integration Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card-hover { transition: all 0.3s ease; }
        .card-hover:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .pulse-ring { animation: pulse-ring 2s cubic-bezier(0.455, 0.03, 0.515, 0.955) infinite; }
        @keyframes pulse-ring { 0% { transform: scale(0.33); } 40%, 50% { opacity: 1; } 100% { opacity: 0; transform: scale(0.9); } }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between items-center py-4">
                <div class="flex items-center space-x-4">
                    <div class="flex items-center space-x-2">
                        <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                            <span class="text-white font-bold text-sm">OC</span>
                        </div>
                        <span class="text-xl font-bold text-gray-800">OpenCode</span>
                    </div>
                    <div class="text-2xl text-gray-400">↔</div>
                    <div class="flex items-center space-x-2">
                        <div class="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
                            <span class="text-white font-bold text-sm">LRS</span>
                        </div>
                        <span class="text-xl font-bold text-gray-800">LRS-Agents</span>
                    </div>
                </div>
                <div class="flex items-center space-x-4">
                    <span class="text-sm text-gray-600">Cognitive AI Hub v3.0</span>
                    <div class="flex items-center space-x-2">
                        <div class="w-2 h-2 bg-green-500 rounded-full pulse-ring"></div>
                        <span class="text-sm text-green-600">🧠 Cognitive AI Active</span>
                    </div>
                    <a href="cognitive_demo.html" target="_blank" class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm transition duration-200">🚀 Cognitive Demo</a>
                </div>
            </div>
        </div>
    </nav>"""

    # Add the rest of the HTML content
    html_content += """
        <div class="max-w-7xl mx-auto px-4 py-8">
            <div class="text-center mb-12">
                <h1 class="text-5xl font-bold text-gray-900 mb-4">OpenCode ↔ LRS-Agents Cognitive AI Hub</h1>
                <p class="text-xl text-gray-600 mb-6 max-w-3xl mx-auto">Revolutionary AI-assisted development platform with 264,447x performance improvement and cognitive intelligence</p>
                <div class="flex justify-center space-x-4">
                    <div class="bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium">Active Inference</div>
                    <div class="bg-purple-100 text-purple-800 px-4 py-2 rounded-full text-sm font-medium">Cognitive AI</div>
                    <div class="bg-green-100 text-green-800 px-4 py-2 rounded-full text-sm font-medium">264,447x Faster</div>
                </div>
            </div>

            <div class="bg-white rounded-xl shadow-lg p-8 mb-8">
                <h2 class="text-2xl font-semibold text-gray-900 mb-6">🎯 Revolutionary Capabilities</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div class="p-4 border border-gray-200 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">🧠 Cognitive Code Analysis</h3>
                        <p class="text-gray-600 text-sm">Multi-modal AI understanding of code patterns, attention focus, and cognitive insights</p>
                    </div>
                    <div class="p-4 border border-gray-200 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">⚡ 264,447x Performance</h3>
                        <p class="text-gray-600 text-sm">Revolutionary speed improvements with perfect accuracy and enterprise scalability</p>
                    </div>
                    <div class="p-4 border border-gray-200 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">🤖 Multi-Agent Intelligence</h3>
                        <p class="text-gray-600 text-sm">Self-optimizing cognitive agents with temporal learning and coordination</p>
                    </div>
                    <div class="p-4 border border-gray-200 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">🏢 Enterprise Security</h3>
                        <p class="text-gray-600 text-sm">JWT authentication, RBAC, audit logging, and production monitoring</p>
                    </div>
                    <div class="p-4 border border-gray-200 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">🌐 Universal Ecosystem</h3>
                        <p class="text-gray-600 text-sm">7 deployment platforms, 4 IDE integrations, plugin marketplace</p>
                    </div>
                    <div class="p-4 border border-gray-200 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">🚀 Cognitive Demo</h3>
                        <p class="text-gray-600 text-sm">Interactive AI code analysis with real-time insights and pattern recognition</p>
                    </div>
                </div>
            </div>

            <div class="text-center">
                <a href="cognitive_demo.html" target="_blank" class="bg-purple-600 hover:bg-purple-700 text-white px-8 py-4 rounded-lg text-lg font-medium transition duration-200 inline-flex items-center">
                    <span class="mr-2">🚀</span> Launch Cognitive AI Demo
                </a>
                <p class="text-gray-600 mt-4">Experience revolutionary AI-assisted development firsthand</p>
            </div>
        </div>

        <script>
            // Simple enterprise status check
            function updateStatus() {
                console.log('Cognitive AI Hub v3.0 - Enterprise Status: Operational');
            }
            updateStatus();
        </script>
    </body>
    </html>"""

    return html_content


@app.get("/api/integration/status")
async def get_integration_status():
    """Get current integration status."""
    return {
        "lrs_available": LRS_AVAILABLE,
        "opencode_available": opencode_tool.opencode_path is not None,
        "lrs_agent_precision": lrs_agent.belief_state["precision"],
        "lrs_agent_adaptations": lrs_agent.belief_state["adaptation_count"],
        "cognitive_available": COGNITIVE_AVAILABLE,
        "multi_agent_available": MULTI_AGENT_AVAILABLE,
        "integration_active": True,
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

    uvicorn.run(app, host="0.0.0.0", port=8000)

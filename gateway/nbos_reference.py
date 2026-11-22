"""Opt-in, read-only NBOS protocol reference server (NOT an LRS/NBCL engine).

This separate local-development process executes precisely two pure read-only
commands. It never boots an agent, runs arbitrary code, reads client file
paths, evaluates expressions or offers debugger operations. Discovery only
advertises methods implemented and tested here.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from gateway.security import GatewayAuthMiddleware

app = FastAPI(
    title="NeuralBlitz Read-only NBOS Reference Adapter",
    version="0.1.0",
)
app.add_middleware(GatewayAuthMiddleware)

REFERENCE_OPERATIONS = (
    "GET /status",
    "POST /introspect",
    "POST /execute",
)
REFERENCE_COMMANDS = ("/status", "/help")


def reference_status():
    """Actual reference-adapter status; never fabricate agent or governance state."""
    return {
        "ok": True,
        "system_status": "read_only_reference",
        "service": "lrs-neuralblitz-readonly-reference",
        "agent_booted": False,
        "execution_engine_available": False,
        "integration_verified": False,
        "governance_core": {
            "charter_status": "unverified",
            "veritas_vpce": {"score": None},
        },
    }


@app.get("/", response_class=HTMLResponse)
async def reference_home():
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>NBOS read-only reference</title></head><body>"
        "<h1>Pre-production research prototype: read-only NBOS reference</h1>"
        "<p>No agent boot, arbitrary NBCL execution, file access or debugger."
        " Only /status and /help read-only commands are implemented.</p>"
        "</body></html>"
    )


@app.get("/nbos/v1/capabilities")
async def reference_capabilities():
    """Protocol compatible *only* for these three read-only operations."""
    return {
        "protocol": "nbos/1",
        "service": "lrs-neuralblitz-readonly-reference",
        "compatible": True,
        "operations": list(REFERENCE_OPERATIONS),
        "supported_commands": list(REFERENCE_COMMANDS),
        "execution_engine_available": False,
        "agent_boot_available": False,
        "debugger_available": False,
    }


@app.get("/status")
async def get_reference_status():
    return reference_status()


@app.post("/introspect")
async def reference_introspect(payload: dict):
    if set(payload) != {"scope"} or payload.get("scope") != "system":
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "error": {"message": "Only read-only 'system' scope is supported"},
            },
        )
    return {
        "ok": True,
        "scope": "system",
        "status": reference_status(),
        "capabilities": await reference_capabilities(),
    }


@app.post("/execute")
async def execute_read_only_command(payload: dict):
    # The VS Code client sends {command: "..."} for individual commands, but
    # {program: "..."} for files. Never resolve a supplied path on the server.
    if set(payload) != {"command"} or not isinstance(payload.get("command"), str):
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "completed": False,
                "error": {
                    "message": "Only single read-only command requests are supported; no file execution"
                },
            },
        )
    command = payload["command"]
    if command not in REFERENCE_COMMANDS:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "completed": False,
                "error": {"message": "Unsupported read-only reference command"},
            },
        )
    if command == "/status":
        value = reference_status()
    else:
        value = {
            "supported_commands": list(REFERENCE_COMMANDS),
            "description": "Read-only local reference operations; no NBCL engine",
        }
    # completed:true is returned only after the permitted operation ran.
    return {"ok": True, "completed": True, "result": value}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)

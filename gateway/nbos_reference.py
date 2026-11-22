"""Opt-in, read-only NBOS protocol reference server (NOT an LRS/NBCL engine).

This separate local-development process runs a finite, side-effect-free NBCL
subset of status/help/integer arithmetic, including bounded inline programs.
It never boots an agent, runs arbitrary code, reads client file paths or
offers debugger operations. Discovery advertises only tested methods.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from gateway.security import GatewayAuthMiddleware
from gateway.nbcl_subset import (
    SUPPORTED_COMMANDS, SubsetSyntaxError, parse_instruction,
    run_instruction, run_program,
)

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
REFERENCE_COMMANDS = SUPPORTED_COMMANDS


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
        " Only /status, /help and bounded /calc source programs are implemented.</p>"
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
        # POST /execute accepts only {command}, never a client file path.
        "execution_modes": ["command", "source"],
        "subset_interpreter_available": True,
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
    """Evaluate exact command OR bounded inline source; no filesystem access."""
    if set(payload) not in ({"command"}, {"source"}):
        return JSONResponse(
            status_code=422,
            content={
                "ok": False, "completed": False,
                "error": {"message": "Expected exactly command or inline source; no file execution"},
            },
        )
    try:
        if "command" in payload:
            parsed = parse_instruction(payload["command"], line=1)
            value = run_instruction(parsed, reference_status)
            return {"ok": True, "completed": True, "result": value}
        return run_program(payload["source"], reference_status)
    except SubsetSyntaxError as exc:
        # Error messages contain a short classification and line number only,
        # never the caller's source/commands/secrets.
        return JSONResponse(
            status_code=422,
            content={
                "ok": False, "completed": False,
                "error": {"message": str(exc)},
            },
        )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)

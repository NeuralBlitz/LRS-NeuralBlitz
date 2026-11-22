# Pinned LRS-Agents runtime integration review — 2026-11-22

**Scope:** Source-only dependency review for `NeuralBlitz/LRS-NeuralBlitz`. The submodule's repository and pinned revision were inspected **read-only**; no files were changed upstream and no LRS-Agents runtime was launched. This does **not** constitute a successful integration test.

## Evidence source

- Gitlink `lrs_agents` at pinned SHA `52ae62ed1f83ba1a798c3235287d5ee46d3bbc76`.
- Upstream repository: [NeuralBlitz/lrs-agents](https://github.com/NeuralBlitz/lrs-agents/tree/52ae62ed1f83ba1a798c3235287d5ee46d3bbc76).
- Exact source files inspected: `lrs/opencode/simplified_integration.py`, `lrs/benchmarking/benchmark_integration.py`, `lrs/enterprise/enterprise_security_monitoring.py`, `lrs/opencode/lrs_opencode_integration.py`, `lrs/cognitive/multi_agent_coordination.py`, `lrs/__init__.py` and `pyproject.toml`.

## Findings for the HTTP gateway

| Interface | Source-level finding | Integration consequence |
| --- | --- | --- |
| OpenCode tool | `OpenCodeTool.__init__` calls `_find_opencode()`, which runs executable-version probes via `subprocess.run`; `get()` can later run constructed commands | **Never instantiate** the helper at HTTP module import/startup merely to populate a status page |
| Lightweight LRS agent | `SimplifiedLRSAgent` is described as a demo agent with `execute_task`; no versioned `/boot`/`/execute` NBOS HTTP server was established | A Python class existing in the pinned source does **not** qualify the gateway as an NBOS executor |
| Benchmark module | The benchmark integration module imports other internal modules at import time and registers an `APIRouter` | Load only behind an explicit, reviewed experimental opt-in |
| Enterprise module | `enterprise_security_monitoring.py` imports `jwt`. Its `integrate_enterprise_features` registers CORS and trusted-host middleware with wildcard values in this revision | Missing dependencies must fail explicit opt-in; never import or register these modules in the default gateway |
| Python package | `pyproject.toml` declares substantial optional/runtime integrations with lower-bound dependency ranges; `jwt` is imported by the enterprise module but is not an explicit direct core dependency there | A dependency-isolated FastAPI install is **not** a sufficient installation of the full submodule |
| Multi-agent coordinator | `MultiAgentCoordinator.execute_workflow` processes queued agent work and marks selected tasks completed; result/error propagation and task semantics require focused review | Do not map the current `/api/multi-agent/execute-workflow` HTTP route to it without independently verified completion and failure cases |

The submodule checkout directory is `lrs_agents` (underscore). A previous gateway `sys.path` insertion targeted the nonexistent `lrs-agents` sibling path and has been removed. Importing `lrs_agents.lrs` depends on a checked-out/available package; the default gateway remains independently runnable without it.

## Implemented local safeguards

- The default gateway imports only the lightweight OpenCode class (if present) and does **not** construct an OpenCode tool or agent at module import time.
- Benchmark and enterprise modules are imported only when `LRS_ENABLE_EXPERIMENTAL_ROUTES=1` is explicitly provided. If required imports fail, startup fails rather than silently registering a partial set of experimental routes.
- The default gateway continues to advertise `compatible: false` on authenticated `GET /nbos/v1/capabilities`. No execution/debugger capabilities are promoted.
- The isolated regression suite `tests/test_gateway_optional_import_isolation.py` injects synthetic modules with deliberately failing imports/constructors to prove the default gateway does not touch them.

## Remaining work before enabling a real adapter

1. Initialize the exact pinned Gitlink in an isolated, controlled CI stage and validate its license, dependency installation and import graph; do not import untrusted modules just to check source existence.
2. Specify and test an explicit NBOS adapter with versioned schemas, allowed methods, authorization, command restrictions, bounded execution and negative/error-path handling.
3. Verify every positive execution result against actual tool outcomes and completion states, rather than a successful HTTP response or coordinator bookkeeping.
4. Keep the original gateway loopback-only until a separate threat model, credentials lifecycle, dependency lock and authenticated staging deployment have passed review.

The findings above describe source evidence and risks, **not** security certifications, agent performance measurements or empirical validation of scientific claims.

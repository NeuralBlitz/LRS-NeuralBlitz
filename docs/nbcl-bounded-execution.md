# Bounded NBCL subset execution — reproducible v0.1 contract

**Status: pre-production, opt-in, local-only reference interpreter.**
This document describes the exact finite grammar and observable behavior in
[`gateway/nbcl_subset.py`](../gateway/nbcl_subset.py) and
[`gateway/nbos_reference.py`](../gateway/nbos_reference.py).
It is **not** a general NBCL interpreter, LRS/NBOS agent boot service,
full semantic DRS engine, filesystem executor, or debugger.

## Supported instructions

The reference supports three independent commands plus three **inline-program-only** local-register commands:

| Command | Executed behavior |
| --- | --- |
| `/status` | Calls the reference service's actual status provider, which reports `agent_booted: false`, `integration_verified: false` |
| `/help` | Returns the actual supported command list and calculation grammar |
| `/calc --a=12 --op=mul --b=-3` | Deterministic bounded **integer** arithmetic; returns `{"operation":"mul","a":12,"b":-3,"value":-36}` |
| `/local.set --name=score --value=12` | Store a bounded signed integer in an **ephemeral register**, visible only to subsequent lines of the same inline source request |
| `/local.add --name=score --value=-5` | Add a bounded integer to an existing register; the resulting value must stay within ±1,000,000 |
| `/local.get --name=score` | Read a previously defined register from the same source request |

The exact arithmetic grammar is
`/calc --a=<integer> --op=<add|sub|mul> --b=<integer>`.
Signed decimal operands may have an optional leading minus and must each
have absolute value at most **1,000,000**. The product result is bounded
by **1,000,000,000,000** in magnitude. Division, exponentiation,
floating point, unbounded integer evaluation, Python syntax, command
pipelines, flags outside this grammar and every other NBCL command are
rejected. There is no dynamic evaluation, file read, shell execution,
network request, model invocation or persisted session state. Local-register names are ASCII lowercase identifiers of 1–16 characters: a leading `a-z`, followed by `a-z`, digits or underscores. At most **8 distinct registers** can be created in one program. `/local.*` instructions are **not permitted** in single-command requests.

## Bounded inline programs

The separate reference adapter accepts exactly one of the following
authenticated request bodies at `POST /execute`:

- `{"command":"/status"}` — exactly one unindented command; maximum **160 characters**.
- `{"source":"# demo\n/status\n/calc --a=12 --op=mul --b=-3\n/help\n"}`
  — an inline text program; **not a file path**.

Inline programs can contain full-line `#` comments, blank lines and
indented supported commands. The parser enforces **at most 4,096
characters**, **64 physical lines**, **16 executable statements**, and
**160 characters per instruction**. The complete program is parsed and
validated **before any instruction executes**. The preflight also simulates the local-register transitions to reject undefined reads/additions, attempts to create a ninth register, and arithmetic overflow **before** any status provider call or result generation. If any instruction or transition is invalid, the server returns HTTP **422**, `ok: false`, `completed: false`, and **no partial steps or register state**.

Successful programs return one verified result per executed statement:

```json
{
  "ok": true,
  "completed": true,
  "instruction_count": 3,
  "steps": [
    {"line": 2, "command": "/status", "result": {"...": "actual status"}},
    {"line": 3, "command": "/calc", "result": {"operation": "mul", "a": 12, "b": -3, "value": -36}},
    {"line": 4, "command": "/help", "result": {"...": "actual help"}}
  ]
}
```

Successful inline programs also return `final_locals`, a sorted dictionary of the program's last register values. It is empty when no local registers were used. Each request allocates a **fresh local dictionary**, even when callers reuse the same bearer token; no state is persisted, shared between HTTP requests, or reconstructed after process restart.

For example, a single inline program can run:

```text
/local.set --name=score --value=12
/local.add --name=score --value=-5
/local.get --name=score
```

The three actual step values are **12, 7, 7**, and `final_locals` is `{"score":7}`. A later request containing only `/local.get --name=score` is refused with HTTP 422 rather than returning a previous caller's value.

The example abbreviates status/help values **only for readability**; the
real API returns concrete full dictionaries. No request text or secrets
are copied into error messages.

## Client negotiation, transport and editor behavior

`GET /nbos/v1/capabilities` advertises
`execution_modes: ["command", "source"]` and
`subset_interpreter_available: true`, `local_state_scope: "single_inline_program"`, and `max_local_registers: 8` for the **reference process only**,
while `execution_engine_available: false`, `agent_boot_available: false`
and `debugger_available: false` remain factual.

The actual VS Code NBOS client requires `nbos/1` capability negotiation
and an explicitly matching mode before transmission. A selected single
command uses `{command}`; a multi-line document or leading-comment
selection uses `{source}`. The client checks that a completed inline
source response has **1–16 step records** with valid line numbers and
commands; an `ok: true` acknowledgment alone cannot masquerade as
completed work. The client **never sends a `{program: filePath}` payload**
to this reference, because `file` is not advertised.

Run and configure the reference using the
[read-only adapter guide](nbos-readonly-reference.md). The root
[`main.py`](../main.py) gateway still has negative NBOS discovery;
do not substitute it for the optional reference process.

## Tests and non-goals

```sh
python -m unittest discover -s tests -p 'test_nbcl_subset.py' -v
python -m unittest discover -s tests -p 'test_nbos_reference_adapter.py' -v
node --test tests/nbosReference.real.integration.cjs
```

The production quality gates run these with pinned Python dependencies
and locked Node/Bun dependencies. The Node suite launches real Uvicorn
over TCP and sends real Axios requests through the actual TypeScript
client; Python tests validate pure arithmetic, complete preparse,
resource limits and rejection of unsafe syntax.

**Not implemented:** arbitrary or canonical complete NBCL/Reflexæl
semantics, persistent variables or sessions, loops, user-defined functions, DRS graph mutation,
AI inference, execution of submitted files, breakpoints, agent sessions,
per-user tenancy, a sandbox for arbitrary programs, or public ingress
security. The result is genuine computation for a deliberately narrow
subset, not full NeuralBlitz functionality or production certification.

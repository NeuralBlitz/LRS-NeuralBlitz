# Multi-agent workflow API — verified implementation status

The POST endpoint \`/api/multi-agent/execute-workflow\` is **not an operational
workflow executor**. Until a real executor is implemented and validated, it
must never report successful task execution.

## Response contract

- **503** when multi-agent components are unavailable.
- **400** when components are available but \`tasks\` is absent, empty, or
  not a list.
- **501** for a nonempty task list when components are available: the
  executor has not been implemented; **no tasks were run**.

The route intentionally does not import or call the demonstration function.
A demo import alone is not proof that submitted tasks were dispatched.

## Verification

Run the dependency-free, isolated endpoint regression suite:

\`\`\`sh
python -m unittest discover -s tests -p 'test_multi_agent_workflow.py' -v
\`\`\`

CI runs these checks when the endpoint, its test, or its workflow changes.
The AST-isolated tests exercise the real endpoint function but do **not**
verify ASGI startup, authentication, request parsing, real task execution,
or integration with the \`lrs_agents\` submodule.

## Criteria for implementing real execution

1. Define validated request/response schemas and per-task IDs.
2. Bind an explicit authenticated executor interface; reject missing backends.
3. Await actual task dispatch and completion, and surface failures.
4. Return success only with execution evidence and machine-readable status.
5. Add ASGI integration tests, cancellation/timeout tests, auth checks,
   and tests proving no false completion for partial or failed workflows.
6. Review side effects and permission boundaries before enabling execution.

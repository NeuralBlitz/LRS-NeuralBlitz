"""Finite, side-effect-free NBCL subset evaluator for the reference service.

This is deliberately *not* a general NBCL runtime. No dynamic evaluation,
imports, files, shell, network, agent state or user-defined operations exist.
All permitted instructions are parsed before any instruction is executed.
"""

from dataclasses import dataclass
import re
from typing import Any, Callable

MAX_SOURCE_CHARS = 4096
MAX_COMMAND_CHARS = 160
MAX_SOURCE_LINES = 64
MAX_STATEMENTS = 16
MAX_ABS_OPERAND = 1_000_000
MAX_LOCAL_REGISTERS = 8

# Local registers exist only while a single inline program runs. They are
# never shared between requests, processes or authenticated callers.
LOCAL_COMMANDS = ("/local.set", "/local.get", "/local.add")
SUPPORTED_COMMANDS = ("/status", "/help", "/calc", *LOCAL_COMMANDS)
_CALC = re.compile(
    r"/calc --a=(-?[0-9]{1,7}) --op=(add|sub|mul) --b=(-?[0-9]{1,7})",
    re.ASCII,
)
_LOCAL_SET = re.compile(
    r"/local\.set --name=([a-z][a-z0-9_]{0,15}) --value=(-?[0-9]{1,7})",
    re.ASCII,
)
_LOCAL_GET = re.compile(
    r"/local\.get --name=([a-z][a-z0-9_]{0,15})",
    re.ASCII,
)
_LOCAL_ADD = re.compile(
    r"/local\.add --name=([a-z][a-z0-9_]{0,15}) --value=(-?[0-9]{1,7})",
    re.ASCII,
)


class SubsetSyntaxError(ValueError):
    """User input outside the documented finite NBCL subset."""


@dataclass(frozen=True)
class Instruction:
    line: int
    name: str
    operation: str = ""
    left: int = 0
    right: int = 0
    symbol: str = ""


def parse_instruction(
    command: str, *, line: int, allow_locals: bool = False
) -> Instruction:
    """Validate one exact command; do not perform evaluation or I/O."""
    if not isinstance(command, str) or len(command) > MAX_COMMAND_CHARS:
        raise SubsetSyntaxError(f"Command length or type rejected at line {line}")
    if command in ("/status", "/help"):
        return Instruction(line=line, name=command)
    match = _CALC.fullmatch(command)
    if match is not None:
        left, action, right = match.groups()
        a = int(left)
        b = int(right)
        if abs(a) > MAX_ABS_OPERAND or abs(b) > MAX_ABS_OPERAND:
            raise SubsetSyntaxError(f"Numeric operand outside bounded range at line {line}")
        return Instruction(
            line=line, name="/calc", operation=action, left=a, right=b,
        )

    # Local commands cannot run through the independent command endpoint:
    # their state exists only for the lifetime of a single inline program.
    for pattern, name in (
        (_LOCAL_SET, "/local.set"),
        (_LOCAL_GET, "/local.get"),
        (_LOCAL_ADD, "/local.add"),
    ):
        match = pattern.fullmatch(command)
        if match is not None:
            if not allow_locals:
                raise SubsetSyntaxError(f"Local commands require inline source at line {line}")
            symbol = match.group(1)
            value = int(match.group(2)) if name != "/local.get" else 0
            if abs(value) > MAX_ABS_OPERAND:
                raise SubsetSyntaxError(f"Local value outside bounded range at line {line}")
            return Instruction(line=line, name=name, symbol=symbol, left=value)
    raise SubsetSyntaxError(f"Unsupported NBCL subset syntax at line {line}")


def _apply_local(instruction: Instruction, local_state: dict[str, int]) -> dict[str, Any]:
    """Pure bounded local transition; used by preflight and execution."""
    name = instruction.symbol
    if instruction.name == "/local.set":
        if name not in local_state and len(local_state) >= MAX_LOCAL_REGISTERS:
            raise SubsetSyntaxError(f"Local register limit exceeded at line {instruction.line}")
        local_state[name] = instruction.left
        return {"name": name, "value": instruction.left, "action": "set"}
    if name not in local_state:
        raise SubsetSyntaxError(f"Undefined local register at line {instruction.line}")
    if instruction.name == "/local.get":
        return {"name": name, "value": local_state[name], "action": "get"}
    if instruction.name == "/local.add":
        value = local_state[name] + instruction.left
        if abs(value) > MAX_ABS_OPERAND:
            raise SubsetSyntaxError(f"Local register overflow at line {instruction.line}")
        local_state[name] = value
        return {"name": name, "value": value, "action": "add"}
    raise RuntimeError("Invalid internal local instruction")


def parse_program(source: str) -> tuple[Instruction, ...]:
    """Prevalidate a bounded program with ephemeral local registers.

    Blank lines and whole-line # comments are ignored. At most 16 actual
    instructions are allowed; any invalid instruction rejects the whole
    program *before* evaluation.
    """
    if not isinstance(source, str) or not source or len(source) > MAX_SOURCE_CHARS:
        raise SubsetSyntaxError("Source must be nonempty text of at most 4096 characters")
    lines = source.splitlines()
    if len(lines) > MAX_SOURCE_LINES:
        raise SubsetSyntaxError("Source contains too many lines")
    statements = []
    for number, original in enumerate(lines, start=1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        statements.append(parse_instruction(line, line=number, allow_locals=True))
        if len(statements) > MAX_STATEMENTS:
            raise SubsetSyntaxError("Source contains too many executable instructions")
    if not statements:
        raise SubsetSyntaxError("Source contains no executable instructions")

    # Simulate every local transition before invoking even the /status
    # provider. An invalid late read, overflow or capacity increase causes
    # rejection without executing or returning *any* program steps.
    scratch: dict[str, int] = {}
    for instruction in statements:
        if instruction.name in LOCAL_COMMANDS:
            _apply_local(instruction, scratch)
    return tuple(statements)


def run_instruction(
    instruction: Instruction, status_provider: Callable[[], dict[str, Any]],
    *, local_state: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Execute only a validated pure instruction against the status provider."""
    if instruction.name == "/status":
        return status_provider()
    if instruction.name == "/help":
        return {
            "supported_commands": list(SUPPORTED_COMMANDS),
            "calc_syntax": "/calc --a=<integer> --op=<add|sub|mul> --b=<integer>",
            "local_scope": "per-inline-program; not persistent across requests",
            "local_syntax": [
                "/local.set --name=<a-z identifier> --value=<integer>",
                "/local.get --name=<a-z identifier>",
                "/local.add --name=<a-z identifier> --value=<integer>",
            ],
            "description": "Local deterministic NBCL subset; no general engine",
        }
    if instruction.name in LOCAL_COMMANDS:
        if local_state is None:
            raise SubsetSyntaxError("Local state requires inline source")
        return _apply_local(instruction, local_state)
    if instruction.name == "/calc":
        actions = {
            "add": lambda a, b: a + b,
            "sub": lambda a, b: a - b,
            "mul": lambda a, b: a * b,
        }
        return {
            "operation": instruction.operation,
            "a": instruction.left,
            "b": instruction.right,
            "value": actions[instruction.operation](instruction.left, instruction.right),
        }
    # A future code change must never accidentally make unknown commands work.
    raise RuntimeError("Invalid internal instruction")


def run_program(
    source: str, status_provider: Callable[[], dict[str, Any]]
) -> dict[str, Any]:
    """Execute an entirely prevalidated finite program, returning real results."""
    instructions = parse_program(source)
    # Fresh local storage for every request: no globals, files, or session
    # registry. Values are discarded even if execution fails.
    local_state: dict[str, int] = {}
    steps = [
        {
            "line": instruction.line,
            "command": instruction.name,
            "result": run_instruction(
                instruction, status_provider, local_state=local_state
            ),
        }
        for instruction in instructions
    ]
    return {
        "ok": True,
        "completed": True,
        "instruction_count": len(steps),
        "steps": steps,
        "final_locals": dict(sorted(local_state.items())),
    }

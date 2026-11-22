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

SUPPORTED_COMMANDS = ("/status", "/help", "/calc")
_CALC = re.compile(
    r"/calc --a=(-?[0-9]{1,7}) --op=(add|sub|mul) --b=(-?[0-9]{1,7})",
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


def parse_instruction(command: str, *, line: int) -> Instruction:
    """Validate one exact command; do not perform evaluation or I/O."""
    if not isinstance(command, str) or len(command) > MAX_COMMAND_CHARS:
        raise SubsetSyntaxError(f"Command length or type rejected at line {line}")
    if command in ("/status", "/help"):
        return Instruction(line=line, name=command)
    match = _CALC.fullmatch(command)
    if match is None:
        raise SubsetSyntaxError(f"Unsupported NBCL subset syntax at line {line}")
    left, action, right = match.groups()
    a = int(left)
    b = int(right)
    if abs(a) > MAX_ABS_OPERAND or abs(b) > MAX_ABS_OPERAND:
        raise SubsetSyntaxError(f"Numeric operand outside bounded range at line {line}")
    return Instruction(
        line=line, name="/calc", operation=action, left=a, right=b,
    )


def parse_program(source: str) -> tuple[Instruction, ...]:
    """Prevalidate a complete, bounded, stateless source program.

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
        statements.append(parse_instruction(line, line=number))
        if len(statements) > MAX_STATEMENTS:
            raise SubsetSyntaxError("Source contains too many executable instructions")
    if not statements:
        raise SubsetSyntaxError("Source contains no executable instructions")
    return tuple(statements)


def run_instruction(
    instruction: Instruction, status_provider: Callable[[], dict[str, Any]]
) -> dict[str, Any]:
    """Execute only a validated pure instruction against the status provider."""
    if instruction.name == "/status":
        return status_provider()
    if instruction.name == "/help":
        return {
            "supported_commands": list(SUPPORTED_COMMANDS),
            "calc_syntax": "/calc --a=<integer> --op=<add|sub|mul> --b=<integer>",
            "description": "Local deterministic NBCL subset; no general engine",
        }
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
    steps = [
        {
            "line": instruction.line,
            "command": instruction.name,
            "result": run_instruction(instruction, status_provider),
        }
        for instruction in instructions
    ]
    return {
        "ok": True,
        "completed": True,
        "instruction_count": len(steps),
        "steps": steps,
    }

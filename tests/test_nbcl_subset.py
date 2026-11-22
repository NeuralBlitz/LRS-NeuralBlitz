"""Deterministic, side-effect-free subset parser and evaluator invariants."""

import unittest

from gateway.nbcl_subset import (
    MAX_ABS_OPERAND,
    MAX_COMMAND_CHARS,
    MAX_SOURCE_CHARS,
    MAX_SOURCE_LINES,
    MAX_STATEMENTS,
    SUPPORTED_COMMANDS,
    SubsetSyntaxError,
    parse_instruction,
    parse_program,
    run_instruction,
    run_program,
)


class NBCLSubsetTests(unittest.TestCase):
    def test_pure_arithmetic_has_correct_exact_results(self):
        cases = (
            ("/calc --a=12 --op=add --b=7", "add", 19),
            ("/calc --a=-5 --op=sub --b=4", "sub", -9),
            ("/calc --a=-11 --op=mul --b=-3", "mul", 33),
            ("/calc --a=1000000 --op=mul --b=-1000000", "mul", -1000000000000),
            ("/calc --a=0 --op=add --b=-0", "add", 0),
        )
        for command, operation, expected in cases:
            with self.subTest(command=command):
                result = run_instruction(
                    parse_instruction(command, line=1),
                    lambda: self.fail("Arithmetic must not touch status"),
                )
                self.assertEqual(result["operation"], operation)
                self.assertEqual(result["value"], expected)
                self.assertIs(type(result["value"]), int)

    def test_exact_grammar_rejects_unrecognized_and_unsafe_syntax(self):
        unsafe = (
            "/boot",
            "/verify",
            "/status --scope=all",
            " /status",
            "/status ",
            "/status; ls",
            "/status\n/boot",
            "/help --verbose",
            "/calc --a=1 --op=div --b=0",
            "/calc --a=1 --op=pow --b=99999",
            "/calc --a=1 --op=add --b=2; touch /tmp/x",
            "/calc --a=2 --op=add --b=3 --extra=1",
            "/calc --a=2 --op=add --b=3\n/boot",
            "/calc --a=9999999 --op=add --b=1",
            "/calc --a=1e9 --op=mul --b=1e9",
            "/calc --a=+1 --op=add --b=2",
            "/calc --a=2 --op=add --b=١",
            "",
            "\x00/status",
            "a" * (MAX_COMMAND_CHARS + 1),
        )
        for command in unsafe:
            with self.subTest(command=repr(command)[:70]):
                with self.assertRaises(SubsetSyntaxError):
                    parse_instruction(command, line=3)
        for nontext in (None, 7, {}, [], b"/status"):
            with self.assertRaises(SubsetSyntaxError):
                parse_instruction(nontext, line=1)

    def test_program_validates_all_steps_before_evaluating_any(self):
        provider_calls = []

        def status_provider():
            provider_calls.append(True)
            return {"ready": True}

        with self.assertRaisesRegex(SubsetSyntaxError, "line 3"):
            run_program("/status\n# note\n/boot", status_provider)
        self.assertEqual(provider_calls, [])

    def test_program_line_numbers_comments_order_and_real_results(self):
        calls = []

        def status_provider():
            calls.append(1)
            return {"kind": "real-status"}

        result = run_program(
            "# example\n\n/status\n   /calc --a=8 --op=sub --b=3\n/help\n",
            status_provider,
        )
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["completed"], True)
        self.assertEqual(result["instruction_count"], 3)
        self.assertEqual([step["line"] for step in result["steps"]], [3, 4, 5])
        self.assertEqual([step["command"] for step in result["steps"]],
                         ["/status", "/calc", "/help"])
        self.assertEqual(result["steps"][1]["result"]["value"], 5)
        self.assertEqual(result["steps"][2]["result"]["supported_commands"],
                         list(SUPPORTED_COMMANDS))
        self.assertEqual(calls, [1])

    def test_program_budgets_reject_unbounded_or_empty_work(self):
        malformed = (
            "",
            "\n# comment only\n",
            "x" * (MAX_SOURCE_CHARS + 1),
            "\n" * (MAX_SOURCE_LINES + 1) + "/status",
            ("/status\n" * (MAX_STATEMENTS + 1)),
            "/status\n/boot\n/status",
            "/calc --a=1000001 --op=add --b=1",
        )
        for source in malformed:
            with self.subTest(length=len(source)):
                with self.assertRaises(SubsetSyntaxError):
                    parse_program(source)
        for wrong in (None, 1, {}, [], False):
            with self.assertRaises(SubsetSyntaxError):
                parse_program(wrong)

    def test_exact_maximum_program_is_accepted(self):
        program = "/status\n" * MAX_STATEMENTS
        parsed = parse_program(program)
        self.assertEqual(len(parsed), MAX_STATEMENTS)
        self.assertEqual(parsed[-1].line, MAX_STATEMENTS)
        self.assertEqual(MAX_ABS_OPERAND, 1_000_000)


if __name__ == "__main__":
    unittest.main()

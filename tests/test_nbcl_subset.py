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

    def test_local_program_transitions_are_computed_and_ordered(self):
        source = (
            "/local.set --name=score --value=12\n"
            "/local.add --name=score --value=-5\n"
            "/local.get --name=score\n"
            "/local.set --name=other_2 --value=-2\n"
            "/local.get --name=other_2\n"
        )
        result = run_program(source, lambda: {"status": "unused"})
        self.assertEqual(result["instruction_count"], 5)
        self.assertEqual([step["result"]["value"] for step in result["steps"]],
                         [12, 7, 7, -2, -2])
        self.assertEqual(result["final_locals"], {"other_2": -2, "score": 7})
        self.assertEqual([step["command"] for step in result["steps"]],
                         ["/local.set", "/local.add", "/local.get",
                          "/local.set", "/local.get"])

    def test_local_state_is_private_to_one_program_even_with_same_name(self):
        first = run_program("/local.set --name=x --value=77\n/local.get --name=x",
                            lambda: {})
        second = run_program("/local.set --name=x --value=-3\n/local.get --name=x",
                             lambda: {})
        self.assertEqual(first["final_locals"], {"x": 77})
        self.assertEqual(second["final_locals"], {"x": -3})
        with self.assertRaisesRegex(SubsetSyntaxError, "Undefined local register at line 1"):
            run_program("/local.get --name=x", lambda: {})

    def test_local_state_syntax_is_never_accepted_as_one_shot_command(self):
        for command in (
            "/local.set --name=x --value=2",
            "/local.get --name=x",
            "/local.add --name=x --value=1",
        ):
            with self.subTest(command=command):
                with self.assertRaisesRegex(SubsetSyntaxError, "require inline source"):
                    parse_instruction(command, line=1)
        with self.assertRaisesRegex(SubsetSyntaxError, "Local state requires inline source"):
            run_instruction(parse_instruction(
                "/local.get --name=x", line=1, allow_locals=True
            ), lambda: {})

    def test_late_undefined_or_overflow_prevents_status_provider_calls(self):
        calls = []
        def provider():
            calls.append(True)
            return {"real": True}
        invalid = (
            "/status\n/local.get --name=missing",
            "/status\n/local.add --name=missing --value=1",
            "/status\n/local.set --name=x --value=1000000\n/local.add --name=x --value=1",
            "/status\n/local.set --name=x --value=-1000000\n/local.add --name=x --value=-1",
        )
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises(SubsetSyntaxError):
                    run_program(source, provider)
                self.assertEqual(calls, [])

    def test_register_count_and_bounds_are_enforced_before_execution(self):
        names = list("abcdefghi")
        maximum = "\n".join(
            f"/local.set --name={name} --value=0" for name in names[:8]
        )
        result = run_program(maximum, lambda: {})
        self.assertEqual(len(result["final_locals"]), 8)
        self.assertEqual(set(result["final_locals"]), set(names[:8]))
        with self.assertRaisesRegex(SubsetSyntaxError, "register limit"):
            run_program(maximum + "\n/local.set --name=i --value=1", lambda: {})
        overwrite = run_program(
            maximum + "\n/local.set --name=a --value=12", lambda: {}
        )
        self.assertEqual(len(overwrite["final_locals"]), 8)
        self.assertEqual(overwrite["final_locals"]["a"], 12)

    def test_local_variable_names_and_values_must_match_finite_grammar(self):
        invalid = (
            "/local.set --name=X --value=1",
            "/local.set --name=1x --value=1",
            "/local.set --name=aaaaaaaaaaaaaaaaa --value=1",
            "/local.set --name=x --value=1000001",
            "/local.set --name=x --value=+1",
            "/local.get --name=x; /status",
            "/local.add --name=x --value=1e2",
            "/local.set --name=x --value=1\n/boot",
        )
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises(SubsetSyntaxError):
                    parse_program(source)

    def test_initial_local_state_is_never_returned_from_previous_request(self):
        calls = []
        def provider():
            calls.append("status")
            return {"ready": True}
        source = (
            "/local.set --name=value --value=5\n"
            "/status\n/local.add --name=value --value=2\n"
            "/local.get --name=value"
        )
        result = run_program(source, provider)
        self.assertEqual(result["final_locals"], {"value": 7})
        self.assertEqual(calls, ["status"])
        self.assertEqual(run_program("/status", provider)["final_locals"], {})

    def test_exact_maximum_program_is_accepted(self):
        program = "/status\n" * MAX_STATEMENTS
        parsed = parse_program(program)
        self.assertEqual(len(parsed), MAX_STATEMENTS)
        self.assertEqual(parsed[-1].line, MAX_STATEMENTS)
        self.assertEqual(MAX_ABS_OPERAND, 1_000_000)


if __name__ == "__main__":
    unittest.main()

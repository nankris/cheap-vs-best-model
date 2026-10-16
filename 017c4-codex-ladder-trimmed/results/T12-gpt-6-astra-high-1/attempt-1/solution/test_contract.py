import copy
from dataclasses import FrozenInstanceError, is_dataclass
from functools import lru_cache
import itertools
import json
import unittest
from unittest.mock import patch

import api
import core
from model import Result
import render
import service


def reference_match(pattern, text):
    """Small recursive oracle that explores wildcard consumption choices."""
    @lru_cache(None)
    def match(p, t):
        if p == len(pattern):
            return t == len(text)
        char = pattern[p]
        if char == "\\":
            end = p + 1
            if end < len(pattern):
                char = pattern[end]
                end += 1
            return t < len(text) and text[t] == char and match(end, t + 1)
        if char == "*":
            globstar = p + 1 < len(pattern) and pattern[p + 1] == "*"
            end = p + (2 if globstar else 1)
            for stop in range(t, len(text) + 1):
                if match(end, stop):
                    return True
                if stop < len(text) and text[stop] == "/" and not globstar:
                    break
            return False
        return (
            t < len(text)
            and (text[t] != "/" if char == "?" else text[t] == char)
            and match(p + 1, t + 1)
        )
    return match(0, 0)


class ContractTests(unittest.TestCase):
    def test_matching_cases(self):
        cases = [
            ("", "", True), ("", "a", False), ("a", "", False),
            ("a", "ba", False), ("a", "ab", False),
            ("?", "😀", True), ("?", "/", False),
            ("?", "e\u0301", False), ("??", "e\u0301", True),
            ("*", "", True), ("*", "ab\nc", True), ("*", "a/b", False),
            ("**", "a/b\nc", True), ("***", "/", True),
            ("a/*/b", "a//b", True), ("a/*/b", "a/x/y/b", False),
            ("a/**/b", "a/x/y/b", True), ("a/**/b", "a/b", False),
            ("**/x", "x", False), ("**/x", "/x", True),
            (r"\*\?", "*?", True), (r"\**", "*abc", True),
            (r"\**", "*/abc", False), (r"\/**", "/abc/def", True),
            ("\\", "\\", True), ("a\\", "a\\", True),
            (r"\\", "\\", True), (r"\a", "a", True),
            ("[a].+", "[a].+", True), ("[a]", "a", False),
        ]
        for pattern, text, expected in cases:
            with self.subTest(pattern=pattern, text=text):
                self.assertIs(core.solve([pattern, text]), expected)

    def test_exhaustive_short_inputs(self):
        patterns = ["".join(p) for n in range(5)
                    for p in itertools.product("a/?*\\", repeat=n)]
        texts = ["".join(t) for n in range(4)
                 for t in itertools.product("a/\\", repeat=n)]
        for pattern in patterns:
            for text in texts:
                self.assertEqual(core.solve([pattern, text]),
                                 reference_match(pattern, text),
                                 (pattern, text))

    def test_public_pipeline(self):
        self.assertTrue(is_dataclass(Result))
        result = service.compute(["**", "a/b"])
        self.assertEqual(result, Result(True))
        with self.assertRaises(FrozenInstanceError):
            result.value = False
        self.assertEqual(render.present(result), "true")
        self.assertEqual(render.present(Result({"é": [1, None]})),
                         json.dumps({"é": [1, None]}))
        with patch.object(core, "solve", return_value=False) as solve:
            rows = ["*", "/"]
            self.assertEqual(service.compute(rows), Result(False))
            solve.assert_called_once_with(rows)

    def test_batch_order_and_pipeline_calls(self):
        rows = [["*", "a"], ["?", "/"], ["**", "a/b"]]
        with patch.object(service, "compute", wraps=service.compute) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(rows))),
                                 [True, False, True])
                self.assertEqual([call.args[0] for call in compute.call_args_list], rows)
                self.assertEqual(present.call_count, len(rows))
        self.assertEqual(json.loads(api.run("[]")), [])

    def test_no_mutation_or_persistent_state(self):
        rows = ["a*", "abc"]
        original = copy.deepcopy(rows)
        self.assertIs(core.solve(rows), True)
        self.assertEqual(service.compute(rows), Result(True))
        self.assertEqual(rows, original)
        self.assertEqual(api.run('[["*", "a"]]'), "[true]")
        self.assertEqual(api.run('[["*", "/"]]'), "[false]")
        self.assertEqual(api.run('[["*", "a"]]'), "[true]")

    def test_long_input_without_recursion(self):
        self.assertIs(core.solve(["**z", "a/" * 5000 + "z"]), True)
        self.assertIs(core.solve(["*a" * 150 + "b", "a" * 300]), False)


if __name__ == "__main__":
    unittest.main()

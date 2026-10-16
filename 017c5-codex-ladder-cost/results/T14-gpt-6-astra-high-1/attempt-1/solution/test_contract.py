import copy
from dataclasses import FrozenInstanceError, is_dataclass
import itertools
import json
import random
import unittest
from unittest.mock import patch

import api
import core
from model import Result
import render
import service


def brute_force_forest(rows):
    """Independent exhaustive oracle for small graphs."""
    nodes, edges = rows
    edges = [edge for edge in edges if edge[0] != edge[1]]

    def components(selected):
        groups = [{node} for node in nodes]
        for u, v, _ in selected:
            left = next(group for group in groups if u in group)
            right = next(group for group in groups if v in group)
            if left is not right:
                left.update(right)
                groups.remove(right)
        return len(groups)

    target = components(edges)
    return min(
        sum(edge[2] for edge in selected)
        for selected in itertools.combinations(edges, len(nodes) - target)
        if components(selected) == target
    )


class ContractTests(unittest.TestCase):
    def test_examples(self):
        cases = [
            ([[], []], 0),
            ([["isolated"], []], 0),
            ([["a"], [["a", "a", -100]]], 0),
            ([["a", "b"], [["a", "b", 9], ["b", "a", -3]]], -3),
            ([["a", "b", "c"], [
                ["a", "b", -5], ["b", "c", -4], ["a", "c", -3]
            ]], -9),
            ([["a", "b", "c", "d", "isolated"], [
                ["a", "b", 7], ["c", "d", -2], ["d", "d", -100]
            ]], 5),
            ([["a", "b", "c"], [
                ["a", "b", 0], ["b", "c", 0], ["a", "c", 0]
            ]], 0),
            ([["a", "b"], [["a", "b", 10 ** 100]]], 10 ** 100),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                result = service.compute(rows)
                self.assertIsInstance(result, Result)
                self.assertEqual(result.value, expected)
                self.assertEqual(render.present(result), json.dumps(expected))
                self.assertEqual(rows, original)
        self.assertEqual(
            json.loads(api.run(json.dumps([rows for rows, _ in cases]))),
            [expected for _, expected in cases],
        )
        self.assertEqual(api.run("[]"), "[]")

    def test_frozen_dataclass(self):
        self.assertTrue(is_dataclass(Result))
        result = Result(42)
        self.assertEqual(result, Result(value=42))
        with self.assertRaises(FrozenInstanceError):
            result.value = 7
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_public_pipeline(self):
        rows = [["a"], []]
        with patch.object(core, "solve", return_value=23) as solve:
            self.assertEqual(service.compute(rows), Result(23))
            solve.assert_called_once_with(rows)
        inputs = [rows, [[], []]]
        results = [Result(23), Result(-7)]
        with patch.object(service, "compute", side_effect=results) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))), [23, -7])
                self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
                self.assertEqual([call.args[0] for call in present.call_args_list], results)

    def test_exhaustive_oracle_and_repeated_calls(self):
        rng = random.Random(9381)
        for _ in range(250):
            nodes = [str(i) for i in range(rng.randrange(1, 6))]
            edges = [
                [rng.choice(nodes), rng.choice(nodes), rng.randrange(-8, 9)]
                for _ in range(rng.randrange(9))
            ]
            rows = [nodes, edges]
            original = copy.deepcopy(rows)
            expected = brute_force_forest(rows)
            self.assertEqual(core.solve(rows), expected)
            self.assertEqual(service.compute(rows), Result(expected))
            self.assertEqual(json.loads(api.run(json.dumps([rows, [[], []], rows]))),
                             [expected, 0, expected])
            self.assertEqual(rows, original)


if __name__ == "__main__":
    unittest.main()

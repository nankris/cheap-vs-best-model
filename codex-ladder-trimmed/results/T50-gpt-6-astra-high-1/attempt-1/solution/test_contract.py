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


def exhaustive(rows):
    best = 0
    for size in range(len(rows) + 1):
        for subset in itertools.combinations(rows, size):
            ordered = sorted(subset)
            if all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])):
                best = max(best, sum(row[2] for row in ordered))
    return best


class ContractTests(unittest.TestCase):
    def test_edge_cases(self):
        cases = [
            ([], 0),
            ([[0, 1, -5], [1, 2, 0]], 0),
            ([[1, 2, 5], [0, 1, 4]], 9),
            ([[0, 2, 5], [0, 2, 5]], 5),
            ([[0, 4, 10], [0, 2, 6], [2, 4, 6]], 12),
            ([[0, 10, 30], [1, 3, 8], [3, 5, 9]], 30),
            ([[-5, -2, 7], [-2, 0, 9], [-4, 1, 10]], 16),
            ([[0, 2, 3], [1, 2, 7], [2, 3, 4]], 11),
            ([[0, 1, 10**100], [1, 2, 10**100]], 2 * 10**100),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(service.compute(rows), Result(expected))
                self.assertEqual(rows, original)

    def test_frozen_dataclass(self):
        result = Result(7)
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, 7)
        with self.assertRaises(FrozenInstanceError):
            result.value = 8
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_public_pipeline(self):
        rows = [[1, 2, 3]]
        with patch.object(core, "solve", return_value=42) as solve:
            self.assertEqual(service.compute(rows), Result(42))
            solve.assert_called_once_with(rows)
        self.assertEqual(render.present(Result(42)), json.dumps(42))
        inputs = [[], rows, [[4, 5, -1]]]
        with patch.object(service, "compute", wraps=service.compute) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))), [0, 3, 0])
                self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
                self.assertEqual(
                    [call.args[0] for call in present.call_args_list],
                    [Result(0), Result(3), Result(0)],
                )

    def test_calls_are_independent(self):
        self.assertEqual(api.run("[]"), "[]")
        for _ in range(3):
            self.assertEqual(json.loads(api.run("[[[0, 1, 9]], []]")), [9, 0])
            self.assertEqual(core.solve([]), 0)
            self.assertEqual(service.compute([[0, 1, -1]]), Result(0))

    def test_randomized_against_exhaustive(self):
        rng = random.Random(137)
        for _ in range(400):
            rows = []
            for _ in range(rng.randrange(10)):
                start = rng.randrange(-5, 8)
                rows.append([start, start + rng.randrange(1, 6), rng.randrange(-8, 20)])
            rng.shuffle(rows)
            original = copy.deepcopy(rows)
            self.assertEqual(core.solve(rows), exhaustive(rows), rows)
            self.assertEqual(rows, original)

    def test_large_input(self):
        rows = [[i, i + 1, 1] for i in reversed(range(20000))]
        self.assertEqual(core.solve(rows), 20000)


if __name__ == "__main__":
    unittest.main()

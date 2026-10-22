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


def exhaustive_reward(rows):
    best = 0
    for size in range(len(rows) + 1):
        for selection in itertools.combinations(rows, size):
            ordered = sorted(selection)
            if all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])):
                best = max(best, sum(job[2] for job in selection))
    return best


class ContractTests(unittest.TestCase):
    def test_algorithm_cases(self):
        cases = [
            ([], 0),
            ([[0, 1, -3], [1, 2, 0]], 0),
            ([[2, 3, 7], [0, 2, 5]], 12),
            ([[0, 2, 5], [0, 2, 5]], 5),
            ([[0, 5, 10], [0, 2, 6], [2, 5, 6]], 12),
            ([[0, 10, 100], [1, 2, 7], [2, 3, 9]], 100),
            ([[-5, -2, 4], [-2, 0, 6], [-4, 0, 9]], 10),
            ([[0, 1, 10**100], [1, 2, 10**100]], 2 * 10**100),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(service.compute(rows), Result(expected))
                self.assertEqual(rows, original)

    def test_random_against_exhaustive_search(self):
        rng = random.Random(42)
        for _ in range(300):
            rows = []
            for _ in range(rng.randrange(9)):
                start = rng.randrange(-5, 6)
                rows.append([start, start + rng.randrange(1, 7), rng.randrange(-9, 16)])
            self.assertEqual(core.solve(rows), exhaustive_reward(rows), rows)

    def test_frozen_model(self):
        result = Result(7)
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, 7)
        with self.assertRaises(FrozenInstanceError):
            result.value = 8

    def test_service_wraps_core(self):
        rows = [[1, 2, 3]]
        with patch.object(core, "solve", return_value=123) as solve:
            self.assertEqual(service.compute(rows), Result(123))
            solve.assert_called_once_with(rows)

    def test_render(self):
        self.assertEqual(render.present(Result(17)), json.dumps(17))

    def test_batch_order_and_call_independence(self):
        inputs = [[], [[0, 1, 8]], [[1, 2, -2]], [[3, 4, 2], [0, 3, 6]]]
        payload = json.dumps(inputs)
        self.assertEqual(json.loads(api.run(payload)), [0, 8, 0, 8])
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(api.run("[[]]"), "[0]")
        self.assertEqual(json.loads(api.run(payload)), [0, 8, 0, 8])

    def test_api_applies_each_pipeline_stage(self):
        inputs = [[], [[0, 1, 5]]]
        with patch.object(service, "compute", wraps=service.compute) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))), [0, 5])
        self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
        self.assertEqual([call.args[0] for call in present.call_args_list], [Result(0), Result(5)])

    def test_large_input(self):
        rows = [[i, i + 1, 1] for i in range(20000, 0, -1)]
        self.assertEqual(core.solve(rows), 20000)


if __name__ == "__main__":
    unittest.main()

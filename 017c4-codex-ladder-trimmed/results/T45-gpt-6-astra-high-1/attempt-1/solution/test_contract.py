import copy
import itertools
import json
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from unittest.mock import patch

import api
import core
import model
import render
import service


class ContractTests(unittest.TestCase):
    def test_interval_cases(self):
        cases = [
            ([], []),
            ([[5, 2]], [[2, 5]]),
            ([[8, 9], [2, 1], [4, 3], [4, 7]], [[1, 9]]),
            ([[1, 2], [4, 5]], [[1, 2], [4, 5]]),
            ([[1, 10], [2, 3], [1, 10]], [[1, 10]]),
            ([[-2, -5], [-1, 0], [2, 2]], [[-5, 0], [2, 2]]),
            ([[10**100, 10**100], [10**100 + 1, 10**100 + 2]],
             [[10**100, 10**100 + 2]]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(rows, original)

    def test_exhaustive_small_inputs(self):
        intervals = list(itertools.product(range(-2, 3), repeat=2))
        for count in range(4):
            for rows in itertools.product(intervals, repeat=count):
                points = sorted({point for a, b in rows
                                 for point in range(min(a, b), max(a, b) + 1)})
                expected = []
                for point in points:
                    if expected and point == expected[-1][1] + 1:
                        expected[-1][1] = point
                    else:
                        expected.append([point, point])
                self.assertEqual(core.solve(rows), expected)

    def test_frozen_result(self):
        result = model.Result([[1, 2]])
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, [[1, 2]])
        with self.assertRaises(FrozenInstanceError):
            result.value = []

    def test_service_wraps_solver_result(self):
        rows = [[2, 1]]
        value = [[1, 2]]
        with patch.object(service, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, model.Result)
        self.assertIs(result.value, value)

    def test_render(self):
        value = {"text": "hello", "values": [None, True, 3]}
        self.assertEqual(render.present(model.Result(value)), json.dumps(value))

    def test_batch_pipeline(self):
        rows = [[], [[3, 1], [4, 7]], [[10, 10]]]
        with patch.object(api, "compute", wraps=service.compute) as compute, \
             patch.object(api, "present", wraps=render.present) as present:
            output = api.run(json.dumps(rows))
        self.assertEqual(json.loads(output), [[], [[1, 7]], [[10, 10]]])
        self.assertEqual([call.args[0] for call in compute.call_args_list], rows)
        self.assertEqual(present.call_count, len(rows))
        self.assertTrue(all(isinstance(call.args[0], model.Result)
                            for call in present.call_args_list))
        self.assertEqual(api.run("[]"), "[]")

    def test_no_aliasing_or_persistent_state(self):
        rows = [[5, 3], [1, 2]]
        original = copy.deepcopy(rows)
        first = service.compute(rows)
        first.value[0][0] = 100
        self.assertEqual(rows, original)
        self.assertEqual(service.compute(rows).value, [[1, 5]])
        self.assertEqual(api.run("[[[1, 1]]]"), "[[[1, 1]]]")
        self.assertEqual(api.run("[[]]"), "[[]]")


if __name__ == "__main__":
    unittest.main()

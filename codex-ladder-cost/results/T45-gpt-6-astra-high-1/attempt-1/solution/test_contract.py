import copy
from dataclasses import FrozenInstanceError, is_dataclass
import itertools
import json
import unittest
from unittest.mock import patch

import api
import core
from model import Result
import render
import service


class ContractTests(unittest.TestCase):
    def test_interval_cases(self):
        cases = [
            ([], []),
            ([[4, 1]], [[1, 4]]),
            ([[8, 10], [2, 1], [3, 5], [5, 7]], [[1, 10]]),
            ([[4, 4], [1, 1]], [[1, 1], [4, 4]]),
            ([[1, 9], [3, 4], [1, 9]], [[1, 9]]),
            ([[-1, -4], [0, 2], [-9, -7]], [[-9, -7], [-4, 2]]),
            ([[10**100, 10**100], [10**100 + 1, 10**100 + 2]],
             [[10**100, 10**100 + 2]]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(service.compute(rows), Result(expected))
                self.assertEqual(rows, original)

    def test_exhaustive_small_integer_unions(self):
        intervals = list(itertools.product(range(-2, 3), repeat=2))
        for rows in itertools.product(intervals, repeat=3):
            covered = set()
            for start, end in rows:
                covered.update(range(min(start, end), max(start, end) + 1))
            expected = []
            for point in sorted(covered):
                if expected and point == expected[-1][1] + 1:
                    expected[-1][1] = point
                else:
                    expected.append([point, point])
            self.assertEqual(core.solve(rows), expected)

    def test_frozen_result(self):
        result = Result([[1, 2]])
        self.assertTrue(is_dataclass(result))
        with self.assertRaises(FrozenInstanceError):
            result.value = []
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_service_wraps_solver_value(self):
        rows = [[1, 2]]
        value = [[7, 8]]
        with patch.object(service, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, Result)
        self.assertIs(result.value, value)

    def test_renderer_uses_json(self):
        value = {"data": [None, True, "text", [1, 3]]}
        self.assertEqual(render.present(Result(value)), json.dumps(value))

    def test_api_batch_and_empty_batch(self):
        rows = [[], [[9, 7], [2, 1]], [[4, 3], [1, 2]]]
        expected = [[], [[1, 2], [7, 9]], [[1, 4]]]
        self.assertEqual(api.run(json.dumps(rows)), json.dumps(expected))
        self.assertEqual(api.run("[]"), "[]")

    def test_api_applies_pipeline_in_order(self):
        rows = [[], [[3, 1]]]
        events = []

        def compute(item):
            events.append(("compute", item))
            return Result(item)

        def present(result):
            events.append(("present", result.value))
            return json.dumps(result.value)

        with patch.object(api, "compute", side_effect=compute), \
                patch.object(api, "present", side_effect=present):
            self.assertEqual(json.loads(api.run(json.dumps(rows))), rows)
        self.assertEqual(events, [
            ("compute", []), ("present", []),
            ("compute", [[3, 1]]), ("present", [[3, 1]]),
        ])

    def test_results_do_not_alias_inputs_or_other_calls(self):
        rows = [[3, 1], [9, 9]]
        original = copy.deepcopy(rows)
        first = service.compute(rows)
        first.value[0][0] = -100
        first.value.append([20, 30])
        self.assertEqual(rows, original)
        self.assertEqual(service.compute(rows).value, [[1, 3], [9, 9]])
        self.assertEqual(service.compute([]).value, [])
        self.assertEqual(api.run("[[[2, 1]]]"), "[[[1, 2]]]")
        self.assertEqual(api.run("[[]]"), "[[]]")


if __name__ == "__main__":
    unittest.main()

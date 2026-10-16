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


class ContractTests(unittest.TestCase):
    def test_frozen_result(self):
        result = Result(7)
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, 7)
        with self.assertRaises(FrozenInstanceError):
            result.value = 8

    def test_service(self):
        rows = [["a"], []]
        with patch.object(core, "solve", return_value=13) as solve:
            self.assertEqual(service.compute(rows), Result(13))
            solve.assert_called_once_with(rows)

    def test_render(self):
        value = {"items": [True, None, "hello", 3]}
        self.assertEqual(render.present(Result(value)), json.dumps(value))

    def test_graph_cases_and_input_preservation(self):
        cases = [
            ([[], []], 0),
            ([["a", "b"], []], 0),
            ([["a"], [["a", "a", -100]]], 0),
            ([["a", "b", "c", "d", "e", "isolated"], [
                ["a", "b", 10], ["a", "b", -3], ["b", "c", 2],
                ["a", "c", 8], ["d", "e", -4], ["c", "c", -99],
            ]], -5),
            ([["a", "b", "c"], [
                ["a", "b", -5], ["b", "c", -4], ["c", "a", -3],
            ]], -9),
            ([["a", "b"], [["a", "b", 10**100]]], 10**100),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(service.compute(rows), Result(expected))
                self.assertEqual(rows, original)
        payload = json.dumps([rows for rows, _ in cases])
        expected = [weight for _, weight in cases]
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(payload)), expected)

    def test_api_applies_pipeline_in_order(self):
        rows = [[["a"], []], [[], []]]
        events = []

        def compute(row):
            events.append(("compute", row))
            return Result(len(row[0]))

        def present(result):
            events.append(("present", result))
            return json.dumps(result.value)

        with patch.object(service, "compute", side_effect=compute), \
                patch.object(render, "present", side_effect=present):
            self.assertEqual(json.loads(api.run(json.dumps(rows))), [1, 0])
        self.assertEqual(events, [
            ("compute", rows[0]), ("present", Result(1)),
            ("compute", rows[1]), ("present", Result(0)),
        ])

    def test_random_graphs_against_exhaustive_forests(self):
        rng = random.Random(42)
        for _ in range(100):
            nodes = list(range(rng.randrange(1, 6)))
            edges = [[rng.choice(nodes), rng.choice(nodes), rng.randrange(-6, 7)]
                     for _ in range(rng.randrange(9))]

            def components(selected):
                groups = [{node} for node in nodes]
                for u, v, _ in selected:
                    left = next(group for group in groups if u in group)
                    right = next(group for group in groups if v in group)
                    if left is not right:
                        left.update(right)
                        groups.remove(right)
                return len(groups)

            count = components(edges)
            needed = len(nodes) - count
            expected = min(
                sum(edge[2] for edge in subset)
                for subset in itertools.combinations(edges, needed)
                if components(subset) == count
            )
            self.assertEqual(core.solve([nodes, edges]), expected)


if __name__ == "__main__":
    unittest.main()

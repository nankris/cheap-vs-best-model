import copy
from dataclasses import FrozenInstanceError, is_dataclass
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

    def test_service_and_render(self):
        rows = [[0, 1, 5], [0, 1]]
        with patch.object(service, "solve", return_value=17) as solve:
            self.assertEqual(service.compute(rows), Result(17))
            solve.assert_called_once_with(rows)
        for value in (None, 0, 5, 10**100):
            self.assertEqual(render.present(Result(value)), json.dumps(value))

    def test_paths(self):
        cases = [
            ([[0, 0]], 0),
            ([[0, 1]], None),
            ([[0, 1, 3], [1, 0]], None),
            ([[0, 1, 9], [0, 1, 2], [0, 1]], 2),
            ([[0, 1, 0], [1, 0, 0], [1, 2, 0], [0, 2]], 0),
            ([[0, 1, 9], [0, 2, 1], [2, 1, 1], [1, 3, 2], [0, 3]], 4),
            ([[0, 1, 1], [0, "a", 1], ["a", "b", 1], [0, "b"]], 2),
            ([[0, 1, 10**100], [1, 2, 10**100], [0, 2]], 2 * 10**100),
            ([[0, 0, 8], [0, 0]], 0),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                before = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(service.compute(rows), Result(expected))
                self.assertEqual(rows, before)
        payload = json.dumps([rows for rows, _ in cases])
        expected = [value for _, value in cases]
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(payload)), expected)

    def test_api_pipeline(self):
        inputs = [[[0, 1]], [[2, 2]]]
        results = [Result(None), Result(0)]
        with patch.object(api, "compute", side_effect=results) as compute:
            with patch.object(api, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))), [None, 0])
        self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
        self.assertEqual([call.args[0] for call in present.call_args_list], results)

    def test_random_graphs_against_bellman_ford(self):
        rng = random.Random(742)
        for _ in range(300):
            size = rng.randrange(1, 12)
            edges = [
                [rng.randrange(size), rng.randrange(size), rng.randrange(20)]
                for _ in range(rng.randrange(50))
            ]
            source, target = rng.randrange(size), rng.randrange(size)
            distances = [None] * size
            distances[source] = 0
            for _ in range(size - 1):
                for u, v, weight in edges:
                    if distances[u] is not None:
                        candidate = distances[u] + weight
                        if distances[v] is None or candidate < distances[v]:
                            distances[v] = candidate
            rows = edges + [[source, target]]
            self.assertEqual(core.solve(rows), distances[target], rows)


if __name__ == "__main__":
    unittest.main()

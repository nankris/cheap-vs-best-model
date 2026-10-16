import copy
from dataclasses import FrozenInstanceError, is_dataclass
import json
import random
import unittest
from unittest.mock import call, patch

import api
import core
from model import Result
import render
import service


class ContractTests(unittest.TestCase):
    def test_result_is_frozen_dataclass(self):
        result = Result(7)
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, 7)
        self.assertEqual(result, Result(7))
        with self.assertRaises(FrozenInstanceError):
            result.value = 8
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_service_wraps_solver_result(self):
        rows = [[1, 2]]
        with patch.object(service, "solve", return_value=13) as solve:
            self.assertEqual(service.compute(rows), Result(13))
            solve.assert_called_once_with(rows)

    def test_renderer(self):
        for value in (None, 0, 42, 10**100):
            self.assertEqual(render.present(Result(value)), json.dumps(value))

    def test_api_uses_pipeline_for_each_input(self):
        inputs = [[[1, 1]], [[1, 2]]]
        results = [Result(0), Result(None)]
        with patch.object(api, "compute", side_effect=results) as compute:
            with patch.object(api, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))), [0, None])
                self.assertEqual(compute.call_args_list, [call(rows) for rows in inputs])
                self.assertEqual(present.call_args_list, [call(r) for r in results])

    def test_graph_cases_and_nonmutation(self):
        cases = [
            ([[1, 1]], 0),
            ([[1, 2]], None),
            ([[1, 2, 3], [2, 1]], None),
            ([[1, 2, 9], [1, 2, 2], [2, 3, 4], [1, 3, 20], [1, 3]], 6),
            ([[1, 2, 0], [2, 1, 0], [2, 3, 0], [1, 3]], 0),
            ([[1, 1, 5], [1, 2, 7], [1, 1]], 0),
            ([[1, 2, 10], [1, 3, 1], [3, 2, 1], [2, 4, 20], [1, 4]], 22),
            ([["s", "a", 1], ["s", 2, 1], [2, "t", 1], ["s", "t"]], 2),
            ([[1, 2, 10**100], [2, 3, 10**100], [1, 3]], 2 * 10**100),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(service.compute(rows), Result(expected))
                self.assertEqual(rows, original)
        payload = json.dumps([rows for rows, _ in cases])
        expected = [value for _, value in cases]
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(payload)), expected)

    def test_random_graphs_against_floyd_warshall(self):
        rng = random.Random(481)
        for _ in range(200):
            size = rng.randrange(1, 9)
            edges = [
                [rng.randrange(size), rng.randrange(size), rng.randrange(15)]
                for _ in range(rng.randrange(50))
            ]
            distance = [[float("inf")] * size for _ in range(size)]
            for vertex in range(size):
                distance[vertex][vertex] = 0
            for u, v, weight in edges:
                distance[u][v] = min(distance[u][v], weight)
            for k in range(size):
                for u in range(size):
                    for v in range(size):
                        distance[u][v] = min(distance[u][v], distance[u][k] + distance[k][v])
            for source in range(size):
                for target in range(size):
                    expected = distance[source][target]
                    if expected == float("inf"):
                        expected = None
                    self.assertEqual(core.solve(edges + [[source, target]]), expected)


if __name__ == "__main__":
    unittest.main()

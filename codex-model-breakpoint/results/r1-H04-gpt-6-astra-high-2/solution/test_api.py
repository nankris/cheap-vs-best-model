import json
import random
import unittest

import api


class ShortestPathTests(unittest.TestCase):
    def check_path(self, rows, expected):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)
        if expected is None:
            self.assertEqual(result, "null")

    def test_examples_and_edge_cases(self):
        cases = [
            ([[1, 1]], 0),
            ([[1, 2]], None),
            ([[1, 2, 7], [1, 2]], 7),
            ([[1, 2, 7], [2, 1]], None),
            ([[1, 2, 7], [3, 3]], 0),
            ([[1, 2, 3], [3, 4, 2], [1, 4]], None),
            ([[1, 3, 20], [1, 2, 4], [2, 3, 5], [1, 3]], 9),
            ([[1, 2, 2], [1, 2, 9], [1, 2]], 2),
            ([[1, 2, 9], [1, 2, 2], [1, 2]], 2),
            ([[1, 1, 0], [1, 2, 0], [2, 1, 0], [2, 3, 0], [1, 3]], 0),
            ([[1, 2, 10**100], [2, 3, 1], [1, 3]], 10**100 + 1),
            ([["s", "a", 2], ["s", 1, 2], [1, "t", 3], ["s", "t"]], 5),
            ([[0, -1, 3], [-1, 2, 4], [0, 2]], 7),
            ([[0, 1, 9], [0, 2, 1], [2, 1, 1], [1, 3, 20], [0, 3]], 22),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.check_path(rows, expected)

    def test_generated_graphs_against_bellman_ford(self):
        rng = random.Random(81723)
        for _ in range(300):
            size = rng.randrange(1, 9)
            edges = [
                [rng.randrange(size), rng.randrange(size), rng.randrange(20)]
                for _ in range(rng.randrange(size * size + 1))
            ]
            source, target = rng.randrange(size), rng.randrange(size)
            distances = [None] * size
            distances[source] = 0
            for _ in range(size - 1):
                for start, end, weight in edges:
                    if distances[start] is not None:
                        candidate = distances[start] + weight
                        if distances[end] is None or candidate < distances[end]:
                            distances[end] = candidate
            rows = edges + [[source, target]]
            with self.subTest(rows=rows):
                self.check_path(rows, distances[target])


if __name__ == "__main__":
    unittest.main()

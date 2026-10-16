import json
import random
import unittest

import api


class PathTests(unittest.TestCase):
    def check_path(self, rows, expected):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_edge_cases(self):
        cases = [
            ([["s", "s"]], 0),
            ([["s", "t"]], None),
            ([[0, 1, 5], [1, 0]], None),
            ([[0, 1, 9], [0, 1, 2], [0, 1]], 2),
            ([[0, 1, 2], [0, 1, 9], [0, 1]], 2),
            ([[0, 1, 10], [0, 2, 1], [2, 1, 1], [1, 3, 2], [0, 3]], 4),
            ([[0, 1, 0], [1, 0, 0], [1, 2, 0], [0, 2]], 0),
            ([[0, 0, 3], [0, 0]], 0),
            ([[0, 1, 10**100], [1, 2, 1], [0, 2]], 10**100 + 1),
            ([["s", 1, 1], ["s", "a", 1], ["a", "t", 1], ["s", "t"]], 2),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.check_path(rows, expected)

    def test_random_graphs_against_bellman_ford(self):
        rng = random.Random(8127)
        for _ in range(500):
            size = rng.randint(1, 8)
            edges = [
                [rng.randrange(size), rng.randrange(size), rng.randrange(15)]
                for _ in range(rng.randrange(40))
            ]
            source, target = rng.randrange(size), rng.randrange(size)
            distances = [None] * size
            distances[source] = 0
            for _ in range(size - 1):
                for start, end, weight in edges:
                    if distances[start] is not None:
                        cost = distances[start] + weight
                        if distances[end] is None or cost < distances[end]:
                            distances[end] = cost
            with self.subTest(edges=edges, source=source, target=target):
                self.check_path(edges + [[source, target]], distances[target])


if __name__ == "__main__":
    unittest.main()

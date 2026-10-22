import json
import random
import unittest

from api import run


class ShortestPathTests(unittest.TestCase):
    def check_path(self, rows, expected):
        result = run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_edge_cases(self):
        cases = [
            ([[7, 7]], 0),
            ([[7, 8]], None),
            ([[1, 2, 3], [2, 1]], None),
            ([[1, 2, 9], [1, 2, 2], [1, 2]], 2),
            ([[1, 2, 2], [1, 2, 9], [1, 2]], 2),
            ([[1, 3, 10], [1, 2, 2], [2, 3, 3], [1, 3]], 5),
            ([[1, 1, 0], [1, 2, 0], [2, 1, 0], [2, 3, 0], [1, 3]], 0),
            ([[1, 2, 4], [9, 9]], 0),
            ([[1, 2, 10**100], [2, 3, 1], [1, 3]], 10**100 + 1),
            ([["s", 1, 0], ["s", "a", 0], ["a", "t", 1], ["s", "t"]], 1),
            ([[0, 1, 10], [0, 2, 1], [2, 1, 1], [1, 3, 20], [0, 3]], 22),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.check_path(rows, expected)
        self.assertEqual(run('[[0, 1]]'), 'null')

    def test_random_graphs_against_bellman_ford(self):
        rng = random.Random(2026)
        for _ in range(500):
            size = rng.randrange(1, 9)
            edges = [
                [rng.randrange(size), rng.randrange(size), rng.randrange(12)]
                for _ in range(rng.randrange(40))
            ]
            source, target = rng.randrange(size), rng.randrange(size)
            distances = {source: 0}
            for _ in range(size - 1):
                for start, end, weight in edges:
                    if start in distances:
                        cost = distances[start] + weight
                        if end not in distances or cost < distances[end]:
                            distances[end] = cost
            self.check_path(edges + [[source, target]], distances.get(target))


if __name__ == '__main__':
    unittest.main()

import itertools
import json
import unittest

from api import run
from core import solve


class IntervalUnionTests(unittest.TestCase):
    def check_union(self, rows, expected):
        result = run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_examples(self):
        cases = [
            ([], []),
            ([[5, 2]], [[2, 5]]),
            ([[8, 10], [1, 3], [3, 6]], [[1, 6], [8, 10]]),
            ([[7, 8], [1, 2], [5, 3], [6, 6]], [[1, 8]]),
            ([[1, 10], [2, 3], [1, 10]], [[1, 10]]),
            ([[-2, -4], [0, -1], [2, 2]], [[-4, 0], [2, 2]]),
            ([[0, 0], [2, 2]], [[0, 0], [2, 2]]),
            ([[10**100, 10**100], [10**100 + 1, 10**100 + 2]],
             [[10**100, 10**100 + 2]]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.check_union(rows, expected)

    def test_exhaustive_small_intervals(self):
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
                self.check_union(rows, expected)

    def test_does_not_mutate_input(self):
        rows = [[5, 3], [1, 2]]
        self.assertEqual(solve(rows), [[1, 5]])
        self.assertEqual(rows, [[5, 3], [1, 2]])


if __name__ == "__main__":
    unittest.main()

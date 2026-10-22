import itertools
import json
import unittest

import api
from core import solve


class IntervalTests(unittest.TestCase):
    def check_union(self, rows, expected):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_examples(self):
        cases = [
            ([], []),
            ([[8, 3]], [[3, 8]]),
            ([[9, 10], [1, 2], [5, 6]], [[1, 2], [5, 6], [9, 10]]),
            ([[1, 3], [3, 7]], [[1, 7]]),
            ([[5, 6], [1, 2], [3, 4]], [[1, 6]]),
            ([[1, 10], [2, 3], [1, 10]], [[1, 10]]),
            ([[-1, -4], [0, 0], [2, 2]], [[-4, 0], [2, 2]]),
            ([[7, 7], [7, 7]], [[7, 7]]),
            ([[10**100, 10**100], [10**100 + 1, 10**100 + 2]],
             [[10**100, 10**100 + 2]]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.check_union(rows, expected)

    def test_exhaustive_small_unions(self):
        intervals = list(itertools.product(range(-2, 3), repeat=2))
        for count in range(4):
            for rows in itertools.product(intervals, repeat=count):
                points = set()
                for start, end in rows:
                    points.update(range(min(start, end), max(start, end) + 1))
                expected = []
                for point in sorted(points):
                    if expected and point == expected[-1][1] + 1:
                        expected[-1][1] = point
                    else:
                        expected.append([point, point])
                self.check_union(rows, expected)

    def test_input_is_not_mutated(self):
        rows = [[6, 4], [1, 3]]
        self.assertEqual(solve(rows), [[1, 6]])
        self.assertEqual(rows, [[6, 4], [1, 3]])


if __name__ == "__main__":
    unittest.main()

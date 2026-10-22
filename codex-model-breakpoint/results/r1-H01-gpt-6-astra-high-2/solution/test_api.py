import itertools
import json
import unittest

from api import run
from core import solve


class IntervalUnionTests(unittest.TestCase):
    def assert_union(self, rows, expected):
        result = run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_edge_cases(self):
        cases = [
            ([], []),
            ([[3, 3]], [[3, 3]]),
            ([[8, 2]], [[2, 8]]),
            ([[8, 9], [1, 2], [5, 6]], [[1, 2], [5, 6], [8, 9]]),
            ([[1, 4], [4, 7]], [[1, 7]]),
            ([[1, 2], [3, 4]], [[1, 4]]),
            ([[1, 2], [4, 5]], [[1, 2], [4, 5]]),
            ([[9, 7], [1, 3], [6, 4]], [[1, 9]]),
            ([[1, 10], [2, 3], [1, 10], [11, 12]], [[1, 12]]),
            ([[-1, -3], [0, 0], [2, 1]], [[-3, 2]]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.assert_union(rows, expected)

    def test_large_integers(self):
        bound = 10 ** 100
        self.assert_union(
            [[bound + 2, bound + 1], [-bound, bound]],
            [[-bound, bound + 2]],
        )

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n [ [3, 1], [4, 5] ] \t')), [[1, 5]])

    def test_input_is_not_modified(self):
        rows = [[5, 3], [1, 2]]
        self.assertEqual(solve(rows), [[1, 5]])
        self.assertEqual(rows, [[5, 3], [1, 2]])

    def test_exhaustive_small_inputs(self):
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
                self.assert_union(rows, expected)


if __name__ == '__main__':
    unittest.main()

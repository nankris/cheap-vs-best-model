import json
import random
import unittest

import api
from core import solve


class IntervalUnionTests(unittest.TestCase):
    def assert_union(self, rows, expected):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_empty(self):
        self.assert_union([], [])

    def test_reversed_endpoints_and_sorted_output(self):
        self.assert_union([[10, 8], [3, 1], [-2, -5]],
                          [[-5, -2], [1, 3], [8, 10]])

    def test_overlaps_containment_and_duplicates(self):
        self.assert_union([[1, 10], [2, 3], [1, 10], [10, 15]], [[1, 15]])

    def test_adjacency_and_transitive_merging(self):
        self.assert_union([[8, 10], [1, 2], [6, 7], [3, 5]], [[1, 10]])

    def test_singletons_and_integer_gaps(self):
        self.assert_union([[4, 4], [0, 0], [1, 1], [-1, -1], [6, 6]],
                          [[-1, 1], [4, 4], [6, 6]])

    def test_arbitrarily_large_integers(self):
        huge = 10 ** 100
        self.assert_union([[huge, 0], [huge + 2, huge + 1], [-huge, -1]],
                          [[-huge, huge + 2]])

    def test_core_does_not_mutate_input(self):
        rows = [[5, 1], [7, 6]]
        self.assertEqual(solve(rows), [[1, 7]])
        self.assertEqual(rows, [[5, 1], [7, 6]])

    def test_randomized_against_integer_set_oracle(self):
        rng = random.Random(2026)
        for _ in range(500):
            rows = [[rng.randint(-20, 20), rng.randint(-20, 20)]
                    for _ in range(rng.randrange(15))]
            points = set()
            for start, end in rows:
                points.update(range(min(start, end), max(start, end) + 1))
            expected = []
            for point in sorted(points):
                if expected and point == expected[-1][1] + 1:
                    expected[-1][1] = point
                else:
                    expected.append([point, point])
            with self.subTest(rows=rows):
                self.assert_union(rows, expected)


if __name__ == "__main__":
    unittest.main()

import itertools
import json
import unittest

from api import run


class OddCoverageTests(unittest.TestCase):
    def assert_coverage(self, rows, expected):
        result = run(json.dumps(rows))
        self.assertIsInstance(result, str)
        value = json.loads(result)
        self.assertIs(type(value), int)
        self.assertEqual(value, expected, rows)

    def test_examples(self):
        cases = [
            ([], 0),
            ([[1, 5]], 4),
            ([[1, 5], [1, 5]], 0),
            ([[1, 5]] * 3, 4),
            ([[0, 4], [2, 6]], 4),
            ([[0, 10], [2, 8], [4, 6]], 6),
            ([[-5, -2], [-2, 3]], 8),
            ([[3, 3], [8, 2], [0, 2]], 2),
            ([[4, 4], [5, -5]], 0),
            ([[10, 12], [-3, 0], [2, 4]], 7),
            ([[-10**30, 10**30], [0, 10**30]], 10**30),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.assert_coverage(rows, expected)

    def test_exhaustive_small_intervals_against_counting_oracle(self):
        intervals = list(itertools.product(range(-2, 3), repeat=2))
        for count in range(4):
            for rows in itertools.combinations_with_replacement(intervals, count):
                expected = sum(
                    sum(start <= point < end for start, end in rows) % 2
                    for point in range(-2, 2)
                )
                self.assert_coverage(rows, expected)
                self.assert_coverage(rows[::-1], expected)


if __name__ == "__main__":
    unittest.main()

import itertools
import json
import random
import unittest

import api
from core import solve


def exhaustive_reward(rows):
    best = 0
    for size in range(1, len(rows) + 1):
        for subset in itertools.combinations(rows, size):
            ordered = sorted(subset)
            if all(left[1] <= right[0]
                   for left, right in zip(ordered, ordered[1:])):
                best = max(best, sum(row[2] for row in subset))
    return best


class SchedulingTests(unittest.TestCase):
    def check_api(self, rows, expected):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        decoded = json.loads(result)
        self.assertIs(type(decoded), int)
        self.assertEqual(decoded, expected)

    def test_edge_cases(self):
        cases = [
            ([], 0),
            ([[1, 2, -5], [2, 3, 0]], 0),
            ([[2, 3, 7], [0, 1, 4], [1, 2, 5]], 16),
            ([[0, 4, 10], [0, 2, 6], [2, 4, 6]], 12),
            ([[0, 4, 15], [0, 2, 6], [2, 4, 6]], 15),
            ([[0, 2, 5], [0, 2, 5], [2, 3, 2]], 7),
            ([[-4, -2, 3], [-2, 0, 8], [-3, 1, 10]], 11),
            ([[0, 3, 5], [1, 3, 8], [3, 4, 4]], 12),
            ([[0, 1, 10**30], [1, 2, 10**30]], 2 * 10**30),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.check_api(rows, expected)

    def test_random_inputs_against_exhaustive_search(self):
        rng = random.Random(2026)
        for _ in range(300):
            rows = []
            for _ in range(rng.randrange(10)):
                start = rng.randrange(-5, 6)
                rows.append([start, start + rng.randrange(1, 6),
                             rng.randrange(-10, 21)])
            rng.shuffle(rows)
            self.check_api(rows, exhaustive_reward(rows))

    def test_solver_preserves_input(self):
        rows = [[3, 4, 5], [0, 3, 6]]
        original = [row[:] for row in rows]
        self.assertEqual(solve(rows), 11)
        self.assertEqual(rows, original)

    def test_long_chain(self):
        self.check_api([[i, i + 1, 1] for i in reversed(range(10000))],
                       10000)


if __name__ == "__main__":
    unittest.main()

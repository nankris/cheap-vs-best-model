import itertools
import json
import random
import unittest

from api import run
from core import solve


def exhaustive_reward(rows):
    best = 0
    for size in range(1, len(rows) + 1):
        for chosen in itertools.combinations(rows, size):
            ordered = sorted(chosen)
            if all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])):
                best = max(best, sum(row[2] for row in chosen))
    return best


class SchedulingTests(unittest.TestCase):
    def check_rows(self, rows, expected):
        result = json.loads(run(json.dumps(rows)))
        self.assertIs(type(result), int)
        self.assertEqual(result, expected)

    def test_examples(self):
        cases = [
            ([], 0),
            ([[0, 1, -2], [1, 2, -1]], 0),
            ([[4, 6, 7], [0, 2, 5], [2, 4, 6]], 18),
            ([[0, 3, 5], [0, 3, 5], [3, 4, 2]], 7),
            ([[0, 5, 10], [0, 2, 6], [2, 5, 6]], 12),
            ([[0, 5, 20], [0, 2, 6], [2, 5, 6]], 20),
            ([[-5, -2, 4], [-2, 0, 3], [-4, 0, 6]], 7),
            ([[0, 2, 0], [2, 3, 10**30]], 10**30),
            ([[0, 4, 5], [1, 4, 9], [4, 5, 2]], 11),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.check_rows(rows, expected)

    def test_random_against_exhaustive_search(self):
        rng = random.Random(143)
        for _ in range(300):
            rows = []
            for _ in range(rng.randrange(10)):
                start = rng.randrange(-5, 8)
                rows.append([start, start + rng.randrange(1, 6), rng.randrange(-8, 16)])
            rng.shuffle(rows)
            with self.subTest(rows=rows):
                self.check_rows(rows, exhaustive_reward(rows))

    def test_does_not_mutate_input(self):
        rows = [[3, 4, 8], [0, 3, 2]]
        original = [row[:] for row in rows]
        self.assertEqual(solve(rows), 10)
        self.assertEqual(rows, original)

    def test_large_chain(self):
        self.check_rows([[i, i + 1, 1] for i in reversed(range(20000))], 20000)


if __name__ == "__main__":
    unittest.main()

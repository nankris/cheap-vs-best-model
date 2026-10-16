import itertools
import json
import random
import unittest

from api import run
from core import solve


def brute_force(rows):
    best = 0
    for mask in range(1 << len(rows)):
        chosen = [row for i, row in enumerate(rows) if mask & (1 << i)]
        if all(a[1] <= b[0] or b[1] <= a[0]
               for a, b in itertools.combinations(chosen, 2)):
            best = max(best, sum(row[2] for row in chosen))
    return best


class SchedulingTests(unittest.TestCase):
    def assert_reward(self, rows, expected):
        result = run(json.dumps(rows))
        self.assertIsInstance(result, str)
        decoded = json.loads(result)
        self.assertIs(type(decoded), int)
        self.assertEqual(decoded, expected)

    def test_examples_and_edge_cases(self):
        cases = [
            ([], 0),
            ([[1, 2, 7]], 7),
            ([[1, 2, -7], [2, 3, -1]], 0),
            ([[1, 2, 0]], 0),
            ([[3, 5, 8], [1, 3, 6], [1, 5, 13]], 14),
            ([[1, 3, 8], [1, 3, 8], [3, 4, 2]], 10),
            ([[0, 10, 10], [1, 2, 6], [2, 3, 6]], 12),
            ([[0, 3, 4], [1, 3, 7], [3, 4, 5]], 12),
            ([[-5, -2, 3], [-2, 0, 4], [-4, 1, 6]], 7),
            ([[0.5, 1.5, 3], [1.5, 2.5, 4]], 7),
            ([[0, 1, 10**30], [1, 2, 10**30]], 2 * 10**30),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.assert_reward(rows, expected)

    def test_input_order_does_not_matter(self):
        rows = [[0, 2, 5], [2, 4, 6], [0, 4, 10], [4, 5, -3]]
        for permutation in itertools.permutations(rows):
            self.assert_reward(permutation, 11)

    def test_random_inputs_against_exhaustive_search(self):
        rng = random.Random(101)
        for _ in range(300):
            rows = []
            for _ in range(rng.randrange(10)):
                start = rng.randrange(-4, 6)
                end = rng.randrange(start + 1, 8)
                rows.append([start, end, rng.randrange(-8, 16)])
            rng.shuffle(rows)
            with self.subTest(rows=rows):
                self.assert_reward(rows, brute_force(rows))

    def test_core_does_not_mutate_input(self):
        rows = [[3, 4, 5], [1, 3, 7]]
        original = [row[:] for row in rows]
        self.assertEqual(solve(rows), 12)
        self.assertEqual(rows, original)

    def test_large_chain(self):
        self.assert_reward([[i, i + 1, 1] for i in reversed(range(20000))], 20000)


if __name__ == "__main__":
    unittest.main()

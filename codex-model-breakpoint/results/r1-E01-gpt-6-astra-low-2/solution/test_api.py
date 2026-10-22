import json
import unittest

from api import run
from codec import decode
from core import solve
from render import present
from service import compute


class SumTests(unittest.TestCase):
    def test_api(self):
        cases = [
            ([], 0),
            ([7], 7),
            ([1, 2, 3, 4], 10),
            ([-8, -3, -1], -12),
            ([-7, 0, 10], 3),
            ([5, -5], 0),
            ([0, 0, 0], 0),
            ([10**100, 10**100, -1], 2 * 10**100 - 1),
            (list(range(1001)), 500500),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                self.assertEqual(json.loads(result), expected)
                self.assertIs(type(json.loads(result)), int)

    def test_json_whitespace(self):
        self.assertEqual(run(' \n [1,\n -2, 3] \t'), '2')

    def test_modules(self):
        values = [4, -2, 9]
        self.assertEqual(decode('[4, -2, 9]'), values)
        self.assertEqual(solve(values), 11)
        self.assertEqual(compute(values), 11)
        self.assertEqual(values, [4, -2, 9])
        self.assertEqual(json.loads(present(11)), 11)


if __name__ == '__main__':
    unittest.main()

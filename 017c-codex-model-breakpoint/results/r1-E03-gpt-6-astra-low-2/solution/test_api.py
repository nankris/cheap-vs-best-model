import json
import unittest

import api
from codec import decode
from core import solve
from render import present
from service import compute


class ApiTests(unittest.TestCase):
    def test_json_round_trip(self):
        cases = [
            ([], 2),
            ([0], 2),
            ([7], 9),
            ([1, 2, 3], 8),
            ([-7, -3], -8),
            ([-9, 4, 5], 2),
            ([10**100, 3, -10**100], 5),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = api.run(json.dumps(values))
                self.assertIsInstance(result, str)
                self.assertEqual(json.loads(result), expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(api.run(' \n[1,\n -2, 4]\t')), 5)

    def test_chained_modules(self):
        values = decode('[4, -1, 6]')
        self.assertEqual(values, [4, -1, 6])
        self.assertEqual(solve(values), 11)
        self.assertEqual(compute(values), 11)
        self.assertEqual(values, [4, -1, 6])
        self.assertEqual(json.loads(present(11)), 11)


if __name__ == '__main__':
    unittest.main()

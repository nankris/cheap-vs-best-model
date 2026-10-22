import json
import unittest

from api import run
from codec import decode
from core import solve
from service import compute


class ApiTests(unittest.TestCase):
    def test_integer_lists(self):
        for values in ([], [0], [7], [1, 2, 3], [-8, -2], [-4, 0, 9],
                       [10**100, 1, -10**100], list(range(-100, 101))):
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                self.assertEqual(json.loads(result), sum(values) + 3)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n[1, -2, 4]\t')), 6)

    def test_chained_modules(self):
        values = decode('[2, -3, 8]')
        self.assertEqual(values, [2, -3, 8])
        self.assertEqual(solve(values), 10)
        self.assertEqual(compute(values), 10)
        self.assertEqual(values, [2, -3, 8])


if __name__ == '__main__':
    unittest.main()

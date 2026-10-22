import json
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_integer_lists(self):
        cases = [
            ([], 3),
            ([0], 3),
            ([7], 10),
            ([1, 2, 3], 9),
            ([-4, -5], -6),
            ([8, -3, 0, -5], 3),
            ([2, 2, 2], 9),
            ([10**100, 1, -(10**100)], 4),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                decoded = json.loads(result)
                self.assertIs(type(decoded), int)
                self.assertEqual(decoded, expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n[ 1,\n -2, 4 ]\t')), 6)

    def test_long_list(self):
        self.assertEqual(json.loads(run(json.dumps(list(range(1000))))), 499503)


if __name__ == '__main__':
    unittest.main()

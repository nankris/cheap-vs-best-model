import json
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_integer_lists(self):
        cases = [
            ([], 1),
            ([0], 1),
            ([7], 8),
            ([1, 2, 3], 7),
            ([-5, -2], -6),
            ([-10, 4, 6], 1),
            ([3, 3, 3], 10),
            ([10**100, 2, -10**100], 3),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                decoded = json.loads(result)
                self.assertIs(type(decoded), int)
                self.assertEqual(decoded, expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n[1,\n -2, 5]\t')), 5)


if __name__ == '__main__':
    unittest.main()

import json
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_integer_lists(self):
        cases = [
            ([], 2),
            ([0], 2),
            ([7], 9),
            ([1, 2, 3], 8),
            ([-8, -3], -9),
            ([-5, 0, 5], 2),
            ([10**100, 3, -(10**100)], 5),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                decoded = json.loads(result)
                self.assertIs(type(decoded), int)
                self.assertEqual(decoded, expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n[1,\n -2, 4]\t')), 5)


if __name__ == '__main__':
    unittest.main()

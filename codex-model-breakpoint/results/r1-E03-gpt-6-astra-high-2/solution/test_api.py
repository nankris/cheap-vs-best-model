import json
import random
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_integer_lists(self):
        cases = [
            ([], 2),
            ([0], 2),
            ([7], 9),
            ([1, 2, 3], 8),
            ([-5, -3], -6),
            ([-4, 0, 4], 2),
            ([3, 3, 3], 11),
            ([10**100, 1, -10**100], 3),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                decoded = json.loads(result)
                self.assertIs(type(decoded), int)
                self.assertEqual(decoded, expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n [1, -2, 3]\t ')), 4)

    def test_generated_lists(self):
        rng = random.Random(0)
        for length in range(100):
            values = [rng.randint(-1000000, 1000000) for _ in range(length)]
            with self.subTest(length=length):
                self.assertEqual(json.loads(run(json.dumps(values))), sum(values) + 2)


if __name__ == '__main__':
    unittest.main()

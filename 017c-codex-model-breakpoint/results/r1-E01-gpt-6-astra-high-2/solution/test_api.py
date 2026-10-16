import json
import random
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_integer_lists(self):
        cases = [
            ([], 0),
            ([7], 7),
            ([1, 2, 3], 6),
            ([-8, -3, -1], -12),
            ([-10, 0, 4, 6], 0),
            ([0, 0, 0], 0),
            ([5, 5, 5], 15),
            ([10**100, 1, -(10**100)], 1),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                decoded = json.loads(result)
                self.assertIs(type(decoded), int)
                self.assertEqual(decoded, expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n[1,\n -2,  3]\t')), 2)

    def test_generated_lists(self):
        generator = random.Random(42)
        for length in range(100):
            values = []
            expected = 0
            for _ in range(length):
                value = generator.randint(-10**20, 10**20)
                values.append(value)
                expected += value
            with self.subTest(length=length):
                self.assertEqual(json.loads(run(json.dumps(values))), expected)


if __name__ == '__main__':
    unittest.main()

import json
import random
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_examples(self):
        for values, expected in [
            ([], 3),
            ([0], 3),
            ([7], 10),
            ([1, 2, 3], 9),
            ([-8, -2], -7),
            ([-5, 0, 5], 3),
            ([10**100, 10**100], 2 * 10**100 + 3),
        ]:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                self.assertEqual(json.loads(result), expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n[1,\n -2, 4]\t')), 6)

    def test_generated_lists(self):
        rng = random.Random(42)
        for length in range(100):
            values = [rng.randint(-10000, 10000) for _ in range(length)]
            expected = 3
            for value in values:
                expected += value
            self.assertEqual(json.loads(run(json.dumps(values))), expected)


if __name__ == '__main__':
    unittest.main()

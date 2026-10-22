import json
import random
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_examples(self):
        cases = [([], 4), ([0], 4), ([7], 11), ([1, 2, 3], 10),
                 ([-5, -2], -3), ([-8, 3, 5], 4),
                 ([10**100, 1, -10**100], 5)]
        for values, expected in cases:
            with self.subTest(values=values):
                result = run(json.dumps(values))
                self.assertIsInstance(result, str)
                self.assertEqual(json.loads(result), expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n [1, -2, 3] \t ')), 6)

    def test_generated_lists(self):
        rng = random.Random(42)
        for _ in range(100):
            values = [rng.randint(-10000, 10000)
                      for _ in range(rng.randrange(100))]
            self.assertEqual(json.loads(run(json.dumps(values))), sum(values) + 4)


if __name__ == '__main__':
    unittest.main()

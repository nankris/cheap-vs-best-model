import json
import random
import unittest

from api import run


class RunTests(unittest.TestCase):
    def test_examples(self):
        for rows, expected in [
            ([], 4),
            ([0], 4),
            ([7], 11),
            ([1, 2, 3], 10),
            ([-9, -2], -7),
            ([-5, 0, 5], 4),
            ([10**100, 7, -(10**100)], 11),
        ]:
            with self.subTest(rows=rows):
                result = run(json.dumps(rows))
                self.assertIsInstance(result, str)
                self.assertEqual(json.loads(result), expected)

    def test_json_whitespace(self):
        self.assertEqual(json.loads(run(' \n[1,\n -2, 3]\t')), 6)

    def test_generated_lists(self):
        rng = random.Random(42)
        for length in range(100):
            rows = [rng.randint(-10000, 10000) for _ in range(length)]
            expected = 4
            for value in rows:
                expected += value
            with self.subTest(length=length):
                self.assertEqual(json.loads(run(json.dumps(rows))), expected)


if __name__ == '__main__':
    unittest.main()

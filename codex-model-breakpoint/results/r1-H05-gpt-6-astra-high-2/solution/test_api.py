import json
import random
import unittest

from api import run


class RunTests(unittest.TestCase):
    def assert_result(self, rows, expected):
        result = run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_empty(self):
        self.assert_result([], [])

    def test_versions_ties_and_sorted_keys(self):
        self.assert_result(
            [
                ["z", 2, "first"],
                ["a", -3, "negative"],
                ["z", 1, "older"],
                ["z", 2, "last tie"],
                ["a", -4, "older negative"],
            ],
            [["a", "negative"], ["z", "last tie"]],
        )

    def test_deletions_and_resurrection(self):
        self.assert_result(
            [
                ["deleted", 5, None],
                ["deleted", 4, "stale"],
                ["tie deleted", 2, "value"],
                ["tie deleted", 2, None],
                ["resurrected", 1, None],
                ["resurrected", 2, "new"],
                ["tie restored", 3, None],
                ["tie restored", 3, "restored"],
            ],
            [["resurrected", "new"], ["tie restored", "restored"]],
        )
        self.assert_result([["only", 0, None]], [])

    def test_json_values_and_escaping(self):
        values = [False, 0, "", True, [], {}, 'comma, quote" newline\n雪']
        rows = [[str(i), 0, value] for i, value in enumerate(values)]
        self.assert_result(rows, [[key, value] for key, _, value in rows])
        self.assert_result([['key,"雪', 1, "value"]], [['key,"雪', "value"]])

    def test_random_rows_against_selection_oracle(self):
        rng = random.Random(42)
        for _ in range(300):
            rows = [
                [rng.choice("abcde"), rng.randint(-5, 5),
                 rng.choice([None, False, 0, "", "value"])]
                for _ in range(rng.randrange(50))
            ]
            expected = []
            for key in sorted({row[0] for row in rows}):
                _, winner = max(
                    ((index, row) for index, row in enumerate(rows) if row[0] == key),
                    key=lambda entry: (entry[1][1], entry[0]),
                )
                if winner[2] is not None:
                    expected.append([key, winner[2]])
            self.assert_result(rows, expected)


if __name__ == "__main__":
    unittest.main()

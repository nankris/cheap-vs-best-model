import json
import unittest
from decimal import localcontext

import api


class ApiTests(unittest.TestCase):
    def run_rows(self, rows):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        return json.loads(result)

    def test_empty(self):
        self.assertEqual(self.run_rows([]), [])

    def test_global_first_id_wins_and_accounts_sort(self):
        rows = [
            ["z", "1.25", "shared"],
            ["a", "99", "shared"],
            ["a", "2.50", "other"],
            ["z", "8", "other"],
            ["z", "0.75", "last"],
        ]
        self.assertEqual(self.run_rows(rows), [["a", "2.50"], ["z", "2.00"]])

    def test_half_even_both_signs_and_negative_zero(self):
        amounts = ["1.005", "1.015", "-1.005", "-1.015", "-0.005", "-0.000", "-0.006"]
        expected = ["1.00", "1.02", "-1.00", "-1.02", "0.00", "0.00", "-0.01"]
        rows = [[str(i), value, i] for i, value in enumerate(amounts)]
        self.assertEqual(self.run_rows(rows), [[str(i), value] for i, value in enumerate(expected)])

    def test_round_only_after_summing(self):
        self.assertEqual(
            self.run_rows([["a", "0.005", 1], ["a", "0.005", 2]]),
            [["a", "0.01"]],
        )

    def test_exact_large_amounts_and_cancellation_under_small_context(self):
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(
                self.run_rows([
                    ["a", "123456789012345678901234567890.005", 1],
                    ["a", "0.01", 2],
                    ["b", "1e40", 3],
                    ["b", "0.015", 4],
                    ["b", "-1e40", 5],
                ]),
                [["a", "123456789012345678901234567890.02"], ["b", "0.02"]],
            )

    def test_json_strings_and_zero_balance(self):
        account = 'a, "quoted"\n雪'
        self.assertEqual(
            self.run_rows([[account, "2.00", "x"], [account, "-2", "y"]]),
            [[account, "0.00"]],
        )


if __name__ == "__main__":
    unittest.main()

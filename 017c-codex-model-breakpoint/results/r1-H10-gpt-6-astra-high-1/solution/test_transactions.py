import copy
import json
import unittest

import api
from service import compute


class TransactionTests(unittest.TestCase):
    def assert_result(self, rows, expected):
        original = copy.deepcopy(rows)
        self.assertEqual(compute(rows), expected)
        self.assertEqual(rows, original)
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_empty_and_unmatched_transactions(self):
        self.assert_result([], [])
        self.assert_result(
            [["commit"], ["rollback"], ["delete", "missing"],
             ["set", "x", 1], ["rollback"], ["commit"]],
            [["x", 1]],
        )

    def test_operations_run_in_order_and_output_is_sorted(self):
        self.assert_result(
            [["set", "z", 1], ["set", "a", 2], ["set", "z", 3],
             ["set", "deleted", 4], ["delete", "deleted"]],
            [["a", 2], ["z", 3]],
        )

    def test_inner_commit_remains_subject_to_outer_rollback(self):
        self.assert_result(
            [["set", "x", {"items": [1, {"ok": True}]}],
             ["begin"], ["delete", "x"], ["set", "new", None],
             ["begin"], ["set", "x", [2, 3]], ["commit"], ["rollback"]],
            [["x", {"items": [1, {"ok": True}]}]],
        )

    def test_inner_rollback_then_outer_commit(self):
        self.assert_result(
            [["set", "x", 0], ["begin"], ["set", "x", 1],
             ["begin"], ["set", "x", 2], ["set", "y", 3],
             ["rollback"], ["commit"], ["rollback"]],
            [["x", 1]],
        )

    def test_rollback_restores_only_latest_snapshot(self):
        self.assert_result(
            [["begin"], ["set", "x", 1], ["begin"],
             ["delete", "x"], ["rollback"], ["rollback"]],
            [],
        )

    def test_open_transaction_retains_current_state(self):
        self.assert_result(
            [["begin"], ["set", "x", False]], [["x", False]]
        )

    def test_nested_json_and_escaped_text(self):
        value = {"a,b": [None, True, False, 1.25, {"text": '雪, "hi"\n'}]}
        self.assert_result([["set", "key,雪", value]], [["key,雪", value]])

    def test_result_does_not_alias_input_values(self):
        rows = [["set", "x", {"items": [1]}]]
        result = compute(rows)
        result[0][1]["items"].append(2)
        self.assertEqual(rows, [["set", "x", {"items": [1]}]])


if __name__ == "__main__":
    unittest.main()

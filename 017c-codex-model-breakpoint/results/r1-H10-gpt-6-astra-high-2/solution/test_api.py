import copy
import json
import unittest

import api
from service import compute


class TransactionTests(unittest.TestCase):
    def check_rows(self, operations, expected):
        payload = json.dumps(operations)
        result = api.run(payload)
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_empty_and_unmatched_transactions(self):
        self.check_rows([], [])
        self.check_rows([
            ["commit"], ["rollback"], ["set", "a", 1],
            ["rollback"], ["commit"],
        ], [["a", 1]])

    def test_order_replacement_deletion_and_sorting(self):
        self.check_rows([
            ["set", "z", 0], ["set", "a", 1], ["set", "z", 2],
            ["set", "b", 3], ["delete", "b"], ["delete", "missing"],
        ], [["a", 1], ["z", 2]])

    def test_rollback_restores_deleted_and_replaced_values(self):
        self.check_rows([
            ["set", "a", {"old": [1, None]}], ["set", "b", False],
            ["begin"], ["set", "a", {"new": [2]}], ["delete", "b"],
            ["set", "c", 3], ["rollback"],
        ], [["a", {"old": [1, None]}], ["b", False]])

    def test_inner_commit_is_undone_by_outer_rollback(self):
        self.check_rows([
            ["set", "a", 0], ["begin"], ["set", "a", 1],
            ["begin"], ["set", "a", 2], ["set", "b", 3],
            ["commit"], ["rollback"],
        ], [["a", 0]])

    def test_inner_rollback_preserves_outer_changes(self):
        self.check_rows([
            ["begin"], ["set", "a", 1], ["begin"], ["delete", "a"],
            ["set", "b", 2], ["rollback"], ["commit"], ["rollback"],
        ], [["a", 1]])

    def test_snapshots_are_consumed_in_stack_order(self):
        self.check_rows([
            ["set", "a", 0], ["begin"], ["set", "a", 1],
            ["begin"], ["set", "a", 2], ["begin"], ["set", "a", 3],
            ["rollback"], ["rollback"], ["commit"], ["rollback"],
        ], [["a", 1]])

    def test_open_transaction_keeps_current_state(self):
        self.check_rows([["begin"], ["set", "a", 1]], [["a", 1]])

    def test_nested_json_round_trip(self):
        value = {"a,b": [True, False, None, 3.5, {"text": "雪,\"\n"}]}
        self.check_rows([["set", "key,雪", value]], [["key,雪", value]])

    def test_input_is_preserved_and_output_is_independent(self):
        operations = [
            ["set", "a", {"items": [1, {"b": 2}]}],
            ["begin"], ["delete", "a"], ["rollback"],
        ]
        original = copy.deepcopy(operations)
        result = compute(operations)
        self.assertEqual(operations, original)
        result[0][1]["items"][1]["b"] = 99
        self.assertEqual(operations, original)

    def test_calls_have_independent_state(self):
        self.check_rows([["begin"], ["set", "a", 1]], [["a", 1]])
        self.check_rows([["rollback"]], [])


if __name__ == "__main__":
    unittest.main()

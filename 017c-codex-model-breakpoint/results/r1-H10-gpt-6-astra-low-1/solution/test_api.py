import copy
import json
import unittest

import api
from core import solve


class TransactionTests(unittest.TestCase):
    def check_rows(self, operations, expected):
        original = copy.deepcopy(operations)
        self.assertEqual(json.loads(api.run(json.dumps(operations))), expected)
        self.assertEqual(solve(operations), expected)
        self.assertEqual(operations, original)

    def test_empty_and_unmatched_transactions(self):
        self.check_rows([], [])
        self.check_rows([
            ["commit"], ["rollback"], ["delete", "missing"],
            ["set", "a", 1], ["rollback"], ["commit"],
        ], [["a", 1]])

    def test_order_overwrite_delete_and_sort(self):
        self.check_rows([
            ["set", "z", 1], ["set", "b", 2], ["set", "a", 3],
            ["set", "z", 4], ["delete", "b"], ["delete", "b"],
        ], [["a", 3], ["z", 4]])

    def test_inner_commit_still_rolled_back_by_outer(self):
        self.check_rows([
            ["set", "a", {"items": [1, None]}], ["begin"],
            ["delete", "a"], ["begin"], ["set", "b", True],
            ["commit"], ["rollback"],
        ], [["a", {"items": [1, None]}]])

    def test_inner_rollback_outer_commit(self):
        self.check_rows([
            ["set", "a", 0], ["begin"], ["set", "a", 1],
            ["begin"], ["set", "a", 2], ["set", "b", 3],
            ["rollback"], ["commit"], ["rollback"],
        ], [["a", 1]])

    def test_open_transaction_keeps_current_state(self):
        self.check_rows([
            ["begin"], ["set", "a", 1], ["begin"], ["delete", "a"],
            ["rollback"],
        ], [["a", 1]])

    def test_nested_json_and_escaped_strings(self):
        value = {"a,b": [None, True, False, 1.5, {"text": '雪\n"\\'}]}
        self.check_rows([["set", "key,雪", value]], [["key,雪", value]])

    def test_result_does_not_alias_input(self):
        rows = [["set", "a", {"items": [1]}], ["begin"], ["rollback"]]
        result = solve(rows)
        result[0][1]["items"].append(2)
        self.assertEqual(rows[0][2], {"items": [1]})


if __name__ == "__main__":
    unittest.main()

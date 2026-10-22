import copy
import json
import random
import unittest

from api import run
from core import solve


class TransactionTests(unittest.TestCase):
    def check_rows(self, rows, expected):
        original = copy.deepcopy(rows)
        self.assertEqual(solve(rows), expected)
        self.assertEqual(rows, original)
        self.assertEqual(json.loads(run(json.dumps(rows))), expected)

    def test_order_sorting_and_deletion(self):
        self.check_rows([], [])
        self.check_rows([
            ["set", "z", 1], ["set", "a", 2], ["set", "z", 3],
            ["delete", "missing"], ["set", "b", 4], ["delete", "b"],
        ], [["a", 2], ["z", 3]])

    def test_inner_commit_can_be_rolled_back_by_outer(self):
        self.check_rows([
            ["set", "a", 1], ["begin"], ["set", "a", 2],
            ["begin"], ["delete", "a"], ["set", "b", 3],
            ["commit"], ["rollback"],
        ], [["a", 1]])

    def test_inner_rollback_and_outer_commit(self):
        self.check_rows([
            ["begin"], ["set", "a", 1], ["begin"], ["set", "a", 2],
            ["rollback"], ["commit"], ["rollback"], ["commit"],
        ], [["a", 1]])

    def test_open_transactions_retain_current_state(self):
        self.check_rows([
            ["commit"], ["rollback"], ["begin"], ["set", "a", None],
            ["begin"], ["set", "b", False],
        ], [["a", None], ["b", False]])

    def test_nested_json_and_input_independence(self):
        value = {"text": 'comma, quote" newline\n雪', "items": [1, None, True, {"x": []}]}
        rows = [["set", "a", value], ["begin"], ["set", "a", []], ["rollback"]]
        self.check_rows(rows, [["a", value]])
        result = solve(rows)
        result[0][1]["items"][3]["x"].append("changed")
        self.assertEqual(value["items"][3]["x"], [])

    def test_random_sequences_against_layer_model(self):
        rng = random.Random(72)
        for _ in range(100):
            layers = [{}]
            rows = []
            for _ in range(100):
                op = rng.choice(["set", "delete", "begin", "commit", "rollback"])
                key = rng.choice(["a", "b", "c"])
                if op == "set":
                    value = {"values": [rng.randrange(10), None]}
                    rows.append([op, key, value])
                    layers[-1][key] = value
                elif op == "delete":
                    rows.append([op, key])
                    layers[-1].pop(key, None)
                else:
                    rows.append([op])
                    if op == "begin":
                        layers.append(copy.deepcopy(layers[-1]))
                    elif len(layers) > 1:
                        current = layers.pop()
                        if op == "commit":
                            layers[-1] = current
            expected = [[key, value] for key, value in sorted(layers[-1].items())]
            self.check_rows(rows, expected)


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, is_dataclass
from unittest.mock import patch

import api
import core
import model
import render
import service


class ContractTests(unittest.TestCase):
    def check_patch(self, document, operations, expected, ok=True):
        rows = [document, operations]
        snapshot = deepcopy(rows)
        self.assertEqual(core.solve(rows), {"ok": ok, "document": expected})
        self.assertEqual(rows, snapshot)

    def test_public_pipeline(self):
        result = model.Result({"answer": [True, None, 3]})
        self.assertTrue(is_dataclass(result))
        with self.assertRaises(FrozenInstanceError):
            result.value = 4
        self.assertEqual(render.present(result), json.dumps(result.value))
        rows = [{}, [["add", "/a", 1]]]
        self.assertEqual(service.compute(rows), model.Result(core.solve(rows)))
        with patch.object(service, "solve", return_value=42) as solve:
            self.assertEqual(service.compute(rows), model.Result(42))
            solve.assert_called_once_with(rows)

    def test_batch_and_no_state(self):
        batch = [
            [{}, [["add", "/a", 1]]],
            [[1], [["remove", "/1"]]],
            [None, [["replace", "", "new"]]],
        ]
        expected = [core.solve(rows) for rows in batch]
        self.assertEqual(json.loads(api.run(json.dumps(batch))), expected)
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(json.dumps(batch))), expected)
        with patch.object(api, "compute", side_effect=model.Result) as compute:
            with patch.object(api, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run("[1, 2]")), [1, 2])
                self.assertEqual(compute.call_count, 2)
                self.assertEqual(present.call_count, 2)

    def test_dict_and_pointer_escaping(self):
        self.check_patch(
            {"a/b": {"~key": [1]}, "": 7, "~1": 8},
            [["add", "/a~1b/~0key/-", 2], ["replace", "/", 9],
             ["test", "/~01", 8], ["remove", "/~01"],
             ["add", "/", 10]],
            {"a/b": {"~key": [1, 2]}, "": 10},
        )
        self.check_patch({}, [["add", "/01", 1], ["add", "/-", 2]],
                         {"01": 1, "-": 2})

    def test_list_operations(self):
        self.check_patch([1, 3], [["add", "/1", 2], ["add", "/3", 4],
                               ["replace", "/0", 0], ["remove", "/2"]],
                         [0, 2, 4])
        self.check_patch([], [["add", "/0", 1], ["add", "/-", 2]], [1, 2])

    def test_roots(self):
        for document in [None, 1, True, "text", [], {}]:
            self.check_patch(document, [["remove", ""]], None)
            self.check_patch(document, [["replace", "", [1]]], [1])
            self.check_patch(document, [["add", "", {}]], {})
            self.check_patch(document, [["test", "", document]], document)
        self.check_patch({}, [["remove", ""], ["add", "", {"a": 1}],
                              ["replace", "/a", 2]], {"a": 2})

    def test_json_equality(self):
        self.check_patch({"a": [1, {"b": None}]},
                         [["test", "", {"a": [1.0, {"b": None}]}]],
                         {"a": [1, {"b": None}]})
        for left, right in [(True, 1), (False, 0), ([True], [1]),
                            ({"a": False}, {"a": 0}), (None, False),
                            ([1, 2], [2, 1]), ({"a": 1}, {"b": 1})]:
            self.check_patch(left, [["test", "", right]], left, ok=False)

    def test_invalid_indices(self):
        for token in ["-1", "00", "01", "+1", "1.0", "", " 0", "٠", "9" * 5000]:
            for op in ["add", "replace", "remove", "test"]:
                operation = [op, "/" + token]
                if op != "remove":
                    operation.append(1)
                with self.subTest(token=token[:20], op=op):
                    self.check_patch([1, 2], [operation], [1, 2], ok=False)
        for op in ["replace", "remove", "test"]:
            for token in ["-", "2"]:
                operation = [op, "/" + token] + ([] if op == "remove" else [1])
                self.check_patch([1, 2], [operation], [1, 2], ok=False)
        self.check_patch([1], [["add", "/2", 3]], [1], ok=False)

    def test_invalid_operations_are_atomic(self):
        invalid = [
            ["copy", "/x", 1], ["replace", "/missing", 1],
            ["remove", "/missing"], ["test", "/x", 99],
            ["add", "/missing/child", 1], ["add", "/x/child", 1],
            ["add", "x", 1], ["add", "/~", 1], ["add", "/~2", 1],
            ["add", None, 1], ["add", "/x"], ["remove", "/x", 1],
            [], {}, [None, "/x", 1],
        ]
        for operation in invalid:
            with self.subTest(operation=operation):
                self.check_patch({"x": 1}, [["add", "/a", 2], operation],
                                 {"x": 1}, ok=False)
        self.check_patch([{}], [["add", "/-/x", 1]], [{}], ok=False)

    def test_values_are_copied(self):
        value = {"items": []}
        self.check_patch({}, [["add", "/a", value], ["add", "/a/items/-", 1],
                              ["add", "/b", value]],
                         {"a": {"items": [1]}, "b": {"items": []}})
        rows = [{"items": []}, []]
        result = core.solve(rows)
        result["document"]["items"].append(1)
        self.assertEqual(rows, [{"items": []}, []])


if __name__ == "__main__":
    unittest.main()

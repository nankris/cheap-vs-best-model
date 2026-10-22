import copy
import json
import unittest
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
        before = copy.deepcopy(rows)
        self.assertEqual(core.solve(rows), {"ok": ok, "document": expected})
        self.assertEqual(rows, before)

    def test_public_model(self):
        result = model.Result({"nested": [True, None]})
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, {"nested": [True, None]})
        with self.assertRaises(FrozenInstanceError):
            result.value = 3

    def test_public_service(self):
        rows = [{}, []]
        value = {"ok": True, "document": {}}
        with patch.object(service, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, model.Result)
        self.assertIs(result.value, value)

    def test_public_renderer(self):
        value = {"text": "雪", "values": [None, False, 2.5]}
        self.assertEqual(render.present(model.Result(value)), json.dumps(value))

    def test_api_pipeline_and_order(self):
        inputs = [
            [{"a": 1}, [["replace", "/a", 2]]],
            [[1], [["remove", "/1"]]],
            [None, [["add", "", "done"]]],
        ]
        with patch.object(api, "compute", wraps=service.compute) as compute:
            with patch.object(api, "present", wraps=render.present) as present:
                output = api.run(json.dumps(inputs))
        self.assertEqual(compute.call_count, 3)
        self.assertEqual(present.call_count, 3)
        self.assertEqual(json.loads(output), [
            {"ok": True, "document": {"a": 2}},
            {"ok": False, "document": [1]},
            {"ok": True, "document": "done"},
        ])
        self.assertEqual(json.loads(api.run("[]")), [])
        self.assertEqual(api.run(json.dumps(inputs)), output)

    def test_nested_operations(self):
        self.check_patch({"a": [{"x": 1}, 2]}, [
            ["add", "/a/1", {"y": 3}],
            ["replace", "/a/0/x", 4],
            ["remove", "/a/2"],
            ["add", "/a/-", 5],
            ["test", "/a", [{"x": 4}, {"y": 3}, 5]],
        ], {"a": [{"x": 4}, {"y": 3}, 5]})

    def test_object_keys_and_escapes(self):
        self.check_patch({"a/b": {"~": 1}, "~1": 2, "": 3}, [
            ["replace", "/a~1b/~0", 4],
            ["test", "/~01", 2],
            ["remove", "/"],
            ["add", "/a~1b/~0", 5],
            ["add", "/01", 6],
            ["add", "/-", 7],
            ["add", "/-1", 8],
        ], {"a/b": {"~": 5}, "~1": 2, "01": 6, "-": 7, "-1": 8})
        self.check_patch({"": {"": 1}, "%20": 2}, [
            ["test", "//", 1], ["test", "/%20", 2],
        ], {"": {"": 1}, "%20": 2})

    def test_root_operations(self):
        for document in [None, True, 42, "text", [], {}]:
            with self.subTest(document=document):
                self.check_patch(document, [["remove", ""]], None)
                self.check_patch(document, [["replace", "", [1]]], [1])
                self.check_patch(document, [["add", "", {}]], {})
                self.check_patch(document, [["test", "", document]], document)
                self.check_patch(document, [], document)
        self.check_patch({}, [
            ["remove", ""], ["test", "", None],
            ["replace", "", []], ["add", "/0", 1],
        ], [1])

    def test_array_boundaries(self):
        self.check_patch([], [["add", "/0", 1], ["add", "/1", 2]], [1, 2])
        self.check_patch([], [["add", "/-", 1]], [1])
        for op in ["add", "replace", "remove", "test"]:
            for token in ["-1", "00", "01", "+0", " 0", "0 ", "1.0", "١", "", "2", "9" * 5000]:
                operation = [op, "/" + token]
                if op != "remove":
                    operation.append(1)
                with self.subTest(op=op, token=token[:20]):
                    self.check_patch([1], [operation], [1], ok=False)
        for op in ["replace", "remove", "test"]:
            for token in ["-", "1"]:
                operation = [op, "/" + token]
                if op != "remove":
                    operation.append(1)
                self.check_patch([1], [operation], [1], ok=False)

    def test_invalid_operations_roll_back(self):
        invalid = [
            ["move", "/x", 1], [], ["add", "/x"],
            ["remove", "/x", 1], ["replace", "/absent", 2],
            ["remove", "/absent"], ["test", "/absent", None],
            ["test", "/x", 99], ["add", "/absent/child", 1],
            ["add", "/x/child", 1], ["remove", "/arr/-/x"],
            ["add", "x", 1], ["add", "/~", 1],
            ["add", "/~2", 1], ["add", "/~01~", 1],
            ["add", None, 1], None, {}, "remove",
        ]
        original = {"x": 1, "arr": []}
        for operation in invalid:
            with self.subTest(operation=operation):
                self.check_patch(original, [
                    ["add", "/changed", True], operation,
                ], original, ok=False)
        self.check_patch(original, [
            ["replace", "", []], ["remove", "/0"],
        ], original, ok=False)

    def test_json_equality(self):
        for left, right, equal in [
            (1, 1.0, True), (False, 0, False), (True, 1, False),
            ({"a": [True]}, {"a": [1]}, False),
            ({"b": 2, "a": 1}, {"a": 1.0, "b": 2}, True),
            ([1, 2], [2, 1], False), (None, False, False),
            ("1", 1, False), ({}, [], False), ([1], [1, 2], False),
        ]:
            with self.subTest(left=left, right=right):
                self.check_patch(left, [["test", "", right]], left, ok=equal)

    def test_inserted_values_and_return_values_are_independent(self):
        value = {"items": []}
        rows = [{}, [
            ["add", "/a", value], ["add", "/b", value],
            ["add", "/a/items/-", 1],
        ]]
        result = core.solve(rows)
        self.assertEqual(result, {"ok": True, "document": {
            "a": {"items": [1]}, "b": {"items": []},
        }})
        self.assertEqual(value, {"items": []})
        result["document"]["b"]["items"].append(2)
        self.assertEqual(value, {"items": []})
        document = {"items": []}
        for operations in [[], [["remove", "/absent"]]]:
            output = core.solve([document, operations])
            output["document"]["items"].append(3)
            self.assertEqual(document, {"items": []})


if __name__ == "__main__":
    unittest.main()

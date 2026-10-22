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
    def test_versions_ties_deletions_and_falsey_values(self):
        rows = [
            ["z", 2, "old"], ["z", 2, "last"], ["z", 1, "stale"],
            ["deleted", 5, None], ["deleted", 4, "stale"],
            ["removed", 1, "old"], ["removed", 1, None],
            ["restored", -2, None], ["restored", -1, "back"],
            ["false", 0, False], ["zero", 0, 0], ["empty", 0, ""],
        ]
        before = copy.deepcopy(rows)
        expected = [
            ["empty", ""], ["false", False], ["restored", "back"],
            ["z", "last"], ["zero", 0],
        ]
        self.assertEqual(core.solve(rows), expected)
        self.assertEqual(rows, before)
        self.assertEqual(core.solve([]), [])
        self.assertEqual(core.solve(rows), expected)

    def test_frozen_result(self):
        result = model.Result([["key", 1]])
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, [["key", 1]])
        with self.assertRaises(FrozenInstanceError):
            result.value = []

    def test_service_wraps_core_result(self):
        rows = [["key", 1, {"nested": [1]}]]
        before = copy.deepcopy(rows)
        self.assertEqual(service.compute(rows), model.Result(core.solve(rows)))
        self.assertEqual(rows, before)
        with patch.object(core, "solve", return_value=["sentinel"]) as solve:
            self.assertEqual(service.compute(rows), model.Result(["sentinel"]))
            solve.assert_called_once_with(rows)

    def test_render_uses_json(self):
        value = [["unicode \u2603", {"value": False, "other": None}]]
        self.assertEqual(render.present(model.Result(value)), json.dumps(value))

    def test_api_batches_and_repeated_calls(self):
        inputs = [[], [["b", 1, 0], ["a", 1, False]], [["b", 2, None]]]
        expected = [[], [["a", False], ["b", 0]], []]
        payload = json.dumps(inputs)
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(payload)), expected)

    def test_api_applies_both_pipeline_stages_per_input(self):
        inputs = [[], [["key", 3, "value"]]]
        with patch.object(service, "compute", wraps=service.compute) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))),
                                 [[], [["key", "value"]]])
        self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
        self.assertEqual([call.args[0] for call in present.call_args_list],
                         [model.Result([]), model.Result([["key", "value"]])])


if __name__ == "__main__":
    unittest.main()

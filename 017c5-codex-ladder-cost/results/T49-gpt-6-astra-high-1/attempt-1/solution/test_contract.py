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
    def test_version_ties_deletions_and_sorting(self):
        rows = [
            ["z", 2, "old"],
            ["a", -3, "first"],
            ["z", 4, None],
            ["z", 3, "stale"],
            ["a", -3, "last"],
            ["b", 0, None],
            ["b", 0, "restored"],
            ["c", 8, "deleted"],
            ["c", 8, None],
        ]
        original = copy.deepcopy(rows)
        self.assertEqual(core.solve(rows), [["a", "last"], ["b", "restored"]])
        self.assertEqual(rows, original)

    def test_falsy_values(self):
        rows = [["c", 1, ""], ["b", 1, 0], ["a", 1, False]]
        self.assertEqual(
            json.dumps(core.solve(rows)),
            '[["a", false], ["b", 0], ["c", ""]]',
        )

    def test_model_is_frozen_dataclass(self):
        result = model.Result([["a", 1]])
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, [["a", 1]])
        with self.assertRaises(FrozenInstanceError):
            result.value = []
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_service_wraps_solver_output(self):
        rows = [["a", 1, "value"]]
        output = [["a", "value"]]
        with patch.object(core, "solve", return_value=output) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, model.Result)
        self.assertIs(result.value, output)

    def test_render_uses_json(self):
        value = [["quote\"", [False, None, "\n", "é", {"x": 0}]]]
        original = copy.deepcopy(value)
        self.assertEqual(render.present(model.Result(value)), json.dumps(value))
        self.assertEqual(value, original)

    def test_api_batch_and_empty_inputs(self):
        inputs = [[], [["b", 2, False], ["a", 1, 0]], [["b", 9, None]]]
        self.assertEqual(
            json.loads(api.run(json.dumps(inputs))),
            [[], [["a", 0], ["b", False]], []],
        )
        self.assertEqual(json.loads(api.run("[]")), [])

    def test_api_applies_both_pipeline_stages_in_order(self):
        events = []

        def compute(rows):
            events.append(("compute", rows))
            return model.Result(rows)

        def present(result):
            self.assertIsInstance(result, model.Result)
            events.append(("present", result.value))
            return json.dumps(result.value)

        inputs = [[], [["a", 1, "x"]]]
        with patch.object(service, "compute", side_effect=compute), patch.object(
            render, "present", side_effect=present
        ):
            self.assertEqual(json.loads(api.run(json.dumps(inputs))), inputs)
        self.assertEqual(events, [
            ("compute", inputs[0]), ("present", inputs[0]),
            ("compute", inputs[1]), ("present", inputs[1]),
        ])

    def test_calls_are_independent(self):
        rows = [["a", 5, "x"]]
        original = copy.deepcopy(rows)
        first = service.compute(rows)
        first.value[0][0] = "changed"
        self.assertEqual(rows, original)
        self.assertEqual(service.compute(rows).value, [["a", "x"]])
        self.assertEqual(core.solve([]), [])
        api.run(json.dumps([rows]))
        self.assertEqual(json.loads(api.run("[[]]")), [[]])


if __name__ == "__main__":
    unittest.main()

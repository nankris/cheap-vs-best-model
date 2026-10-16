import copy
import json
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from unittest.mock import call, patch

import api
import core
import model
import render
import service


class ContractTests(unittest.TestCase):
    def test_components(self):
        rows = [
            ["z", "y"], ["b", "a"], ["c", "b"], ["a", "b"],
            ["singleton", "singleton"], ["y", "z"], ["c", "c"],
        ]
        before = copy.deepcopy(rows)
        expected = [["a", "b", "c"], ["singleton"], ["y", "z"]]
        self.assertEqual(core.solve(rows), expected)
        self.assertEqual(service.compute(rows), model.Result(expected))
        self.assertEqual(rows, before)

    def test_empty_and_repeated_calls(self):
        first = core.solve([["a", "b"]])
        first[0].append("changed")
        self.assertEqual(core.solve([]), [])
        self.assertEqual(core.solve([["a", "b"]]), [["a", "b"]])
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run("[[], []]")), [[], []])

    def test_frozen_result_dataclass(self):
        result = model.Result([["a"]])
        self.assertTrue(is_dataclass(result))
        with self.assertRaises(FrozenInstanceError):
            result.value = []
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_service_wraps_solver_result(self):
        rows = [["a", "b"]]
        value = [["a", "b"]]
        with patch.object(service, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, model.Result)
        self.assertIs(result.value, value)

    def test_renderer_uses_json(self):
        value = [["", 'a"b', "line\nbreak", "\\", "é", "雪"]]
        self.assertEqual(render.present(model.Result(value)), json.dumps(value))

    def test_api_batch_order(self):
        inputs = [
            [["z", "a"], ["x", "x"]], [],
            [["雪", "é"], ["", 'a"b']], [["alone", "alone"]],
        ]
        expected = [
            [["a", "z"], ["x"]], [],
            [["", 'a"b'], ["é", "雪"]], [["alone"]],
        ]
        self.assertEqual(json.loads(api.run(json.dumps(inputs))), expected)

    def test_api_applies_pipeline_to_each_input(self):
        inputs = [[], [["a", "b"]]]
        results = [model.Result([]), model.Result([["a", "b"]])]
        with patch.object(api, "compute", side_effect=results) as compute:
            with patch.object(api, "present", wraps=render.present) as present:
                output = api.run(json.dumps(inputs))
        self.assertEqual(compute.call_args_list, [call(rows) for rows in inputs])
        self.assertEqual(present.call_args_list, [call(result) for result in results])
        self.assertEqual(json.loads(output), [result.value for result in results])

    def test_long_chain(self):
        rows = [[str(index), str(index + 1)] for index in range(3000)]
        self.assertEqual(core.solve(rows), [sorted(str(i) for i in range(3001))])


if __name__ == "__main__":
    unittest.main()

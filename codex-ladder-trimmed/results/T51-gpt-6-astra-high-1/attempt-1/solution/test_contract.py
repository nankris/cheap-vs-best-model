import copy
from dataclasses import FrozenInstanceError, is_dataclass
import json
import unittest
from unittest.mock import patch

import api
import core
from model import Result
import render
import service


class ContractTests(unittest.TestCase):
    def test_components_and_input_preservation(self):
        rows = [
            ["z", "y"], ["b", "a"], ["c", "b"], ["y", "z"],
            ["a", "b"], ["solo", "solo"], ["c", "a"],
        ]
        original = copy.deepcopy(rows)
        expected = [["a", "b", "c"], ["solo"], ["y", "z"]]
        self.assertEqual(core.solve(rows), expected)
        self.assertEqual(service.compute(rows), Result(expected))
        self.assertEqual(rows, original)

    def test_empty_and_string_ordering(self):
        self.assertEqual(core.solve([]), [])
        self.assertEqual(
            core.solve([["é", ""], ["10", "2"], ["A", "A"]]),
            [["", "é"], ["10", "2"], ["A"]],
        )

    def test_frozen_model(self):
        result = Result([["node"]])
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, [["node"]])
        with self.assertRaises(FrozenInstanceError):
            result.value = []

    def test_service_wraps_solver_output(self):
        rows = [["a", "b"]]
        value = [["a", "b"]]
        with patch.object(core, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, Result)
        self.assertIs(result.value, value)

    def test_renderer_uses_json(self):
        value = [["quote\"", "line\n", "é", "\\"]]
        self.assertEqual(render.present(Result(value)), json.dumps(value))

    def test_api_batch_order_and_empty_batches(self):
        inputs = [[["z", "z"]], [], [["b", "a"]]]
        self.assertEqual(
            json.loads(api.run(json.dumps(inputs))),
            [[["z"]], [], [["a", "b"]]],
        )
        self.assertEqual(json.loads(api.run("[]")), [])

    def test_api_uses_each_pipeline_stage(self):
        inputs = [[], [["a", "a"]]]
        results = [Result([]), Result([["a"]])]
        with patch.object(service, "compute", side_effect=results) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                output = api.run(json.dumps(inputs))
        self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
        self.assertEqual([call.args[0] for call in present.call_args_list], results)
        self.assertEqual(json.loads(output), [[], [["a"]]])

    def test_calls_have_independent_state(self):
        result = service.compute([["a", "b"]])
        result.value[0].append("changed")
        self.assertEqual(service.compute([["a", "b"]]).value, [["a", "b"]])
        self.assertEqual(core.solve([["c", "c"]]), [["c"]])
        self.assertEqual(json.loads(api.run("[[]]")), [[]])

    def test_long_chain_does_not_require_recursion(self):
        nodes = [str(index) for index in range(5000)]
        rows = [[left, right] for left, right in zip(nodes, nodes[1:])]
        self.assertEqual(core.solve(rows), [sorted(nodes)])


if __name__ == "__main__":
    unittest.main()

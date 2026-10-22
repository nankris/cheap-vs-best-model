import copy
from dataclasses import FrozenInstanceError, is_dataclass
import itertools
import json
import unittest
from unittest.mock import patch

import api
import core
from model import Result
import render
import service


class ContractTests(unittest.TestCase):
    def test_frozen_result(self):
        result = Result(["a"])
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, ["a"])
        with self.assertRaises(FrozenInstanceError):
            result.value = None
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_service_wraps_solver_result(self):
        rows = [["a", "b"]]
        for value in ([], ["a", "b"], None):
            with patch.object(core, "solve", return_value=value) as solve:
                result = service.compute(rows)
                self.assertIsInstance(result, Result)
                self.assertIs(result.value, value)
                solve.assert_called_once_with(rows)

    def test_render(self):
        for value in (None, [], ["a", 'quote"', "\\", "\n", "é"]):
            self.assertEqual(render.present(Result(value)), json.dumps(value))

    def test_examples_and_input_preservation(self):
        cases = [
            ([], []),
            ([["a", "a"]], None),
            ([["a", "b"], ["b", "a"]], None),
            ([["a", "b"], ["a", "b"]], ["a", "b"]),
            ([["b", "a"], ["z", "y"]], ["b", "a", "z", "y"]),
            ([["a", "b"], ["x", "y"], ["y", "x"]], None),
            ([["", "é"], ["A", "é"]], ["", "A", "é"]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(service.compute(rows), Result(expected))
                self.assertEqual(rows, original)

    def test_api_batch_and_repeated_calls(self):
        payload = json.dumps([[["b", "c"]], [], [["z", "z"]], [["a", "b"]]])
        expected = [["b", "c"], [], None, ["a", "b"]]
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(payload)), expected)
        previous = core.solve([["a", "b"]])
        previous.append("changed")
        self.assertEqual(core.solve([["a", "b"]]), ["a", "b"])

    def test_api_calls_pipeline_for_each_input(self):
        rows = [[], [["a", "a"]]]
        results = [Result([]), Result(None)]
        with patch.object(service, "compute", side_effect=results) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(rows))), [[], None])
        self.assertEqual([call.args for call in compute.call_args_list], [(row,) for row in rows])
        self.assertEqual([call.args for call in present.call_args_list], [(result,) for result in results])

    def test_exhaustive_three_node_graphs(self):
        edges = list(itertools.product("abc", repeat=2))
        for mask in range(1 << len(edges)):
            rows = [list(edge) for index, edge in enumerate(edges) if mask & (1 << index)]
            nodes = sorted({node for edge in rows for node in edge})
            expected = None
            for ordering in itertools.permutations(nodes):
                positions = {node: index for index, node in enumerate(ordering)}
                if all(positions[before] < positions[after] for before, after in rows):
                    expected = list(ordering)
                    break
            with self.subTest(rows=rows):
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(core.solve(rows + rows[::-1]), expected)


if __name__ == "__main__":
    unittest.main()

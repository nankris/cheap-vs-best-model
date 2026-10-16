import copy
import itertools
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
    def test_all_three_node_graphs_against_permutations(self):
        edges = list(itertools.product("abc", repeat=2))
        for mask in range(1 << len(edges)):
            rows = [list(edge) for i, edge in enumerate(edges) if mask & (1 << i)]
            nodes = sorted({node for edge in rows for node in edge})
            expected = None
            for ordering in itertools.permutations(nodes):
                positions = {node: i for i, node in enumerate(ordering)}
                if all(positions[a] < positions[b] for a, b in rows):
                    expected = list(ordering)
                    break
            with self.subTest(rows=rows):
                self.assertEqual(core.solve(rows), expected)

    def test_duplicates_disconnected_nodes_and_newly_ready_nodes(self):
        rows = [["b", "a"], ["z", "x"], ["b", "a"]]
        original = copy.deepcopy(rows)
        self.assertEqual(core.solve(rows), ["b", "a", "z", "x"])
        self.assertEqual(rows, original)
        self.assertEqual(core.solve(rows), ["b", "a", "z", "x"])

    def test_frozen_dataclass_and_service(self):
        result = service.compute([["a", "b"]])
        self.assertIs(type(result), model.Result)
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result, model.Result(["a", "b"]))
        with self.assertRaises(FrozenInstanceError):
            result.value = None
        with patch.object(core, "solve", return_value=["sentinel"]) as solve:
            rows = [["a", "b"]]
            self.assertEqual(service.compute(rows), model.Result(["sentinel"]))
            solve.assert_called_once_with(rows)

    def test_render(self):
        for value in (None, [], ["é", "\"", "\n", ""]):
            self.assertEqual(render.present(model.Result(value)), json.dumps(value))

    def test_api_batch_and_independent_calls(self):
        rows = [[], [["a", "a"]], [["b", "c"], ["a", "c"]],
                [["x", "y"], ["y", "x"]], [["", "é"]]]
        expected = [[], None, ["a", "b", "c"], None, ["", "é"]]
        payload = json.dumps(rows)
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(payload)), expected)

    def test_api_uses_each_pipeline_stage(self):
        inputs = [[], [["a", "b"]]]
        with patch.object(service, "compute", wraps=service.compute) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))), [[], ["a", "b"]])
                self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
                self.assertEqual([call.args[0] for call in present.call_args_list],
                                 [model.Result([]), model.Result(["a", "b"])])

    def test_large_chain_is_iterative(self):
        nodes = [str(i) for i in range(2000)]
        rows = [[a, b] for a, b in zip(nodes, nodes[1:])]
        self.assertEqual(core.solve(rows), nodes)


if __name__ == "__main__":
    unittest.main()

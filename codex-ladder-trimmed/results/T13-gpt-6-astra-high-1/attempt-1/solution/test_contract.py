import copy
from dataclasses import FrozenInstanceError, is_dataclass
import itertools
import json
import unittest
from unittest.mock import patch

import api
import core
import model
import render
import service


class ContractTests(unittest.TestCase):
    def test_components_and_input_preservation(self):
        rows = [["b", "a"], ["a", "b"], ["b", "c"], ["c", "c"],
                ["d", "e"], ["e", "d"], ["b", "a"], ["z", "y"]]
        original = copy.deepcopy(rows)
        expected = [["a", "b"], ["c"], ["d", "e"], ["y"], ["z"]]
        self.assertEqual(core.solve(rows), expected)
        self.assertEqual(service.compute(rows), model.Result(expected))
        self.assertEqual(rows, original)
        self.assertEqual(core.solve(list(reversed(rows))), expected)

    def test_frozen_result(self):
        result = model.Result([["a"]])
        self.assertTrue(is_dataclass(result))
        with self.assertRaises(FrozenInstanceError):
            result.value = []
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_service_wraps_solver(self):
        rows = [["a", "b"]]
        value = [["sentinel"]]
        with patch.object(service, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, model.Result)
        self.assertIs(result.value, value)

    def test_render_and_api(self):
        rows = [["", "quoted\"\n"], ["quoted\"\n", ""], ["雪", "雪"]]
        expected = [["", "quoted\"\n"], ["雪"]]
        self.assertEqual(render.present(model.Result(expected)), json.dumps(expected))
        payload = json.dumps([rows, [], [["x", "y"]], rows])
        self.assertEqual(json.loads(api.run(payload)),
                         [expected, [], [["x"], ["y"]], expected])
        self.assertEqual(api.run("[]"), "[]")

    def test_api_applies_each_pipeline_stage_in_order(self):
        inputs = [[], [["a", "b"]], [["c", "c"]]]
        events = []

        def compute(rows):
            events.append(("compute", rows))
            return model.Result(rows)

        def present(result):
            events.append(("present", result.value))
            return json.dumps(result.value)

        with patch.object(api, "compute", side_effect=compute), \
                patch.object(api, "present", side_effect=present):
            self.assertEqual(json.loads(api.run(json.dumps(inputs))), inputs)
        self.assertEqual(events, [(stage, rows) for rows in inputs
                                  for stage in ("compute", "present")])

    def test_independent_calls(self):
        first = core.solve([["a", "a"]])
        first[0].append("changed")
        self.assertEqual(core.solve([]), [])
        self.assertEqual(core.solve([["a", "a"]]), [["a"]])

    def test_large_graphs(self):
        nodes = [str(i) for i in range(5000)]
        rows = list(zip(nodes, nodes[1:]))
        self.assertEqual(core.solve(rows), sorted([[node] for node in nodes]))
        rows.append((nodes[-1], nodes[0]))
        self.assertEqual(core.solve(rows), [sorted(nodes)])

    def test_all_three_node_graphs_against_reachability(self):
        edges = list(itertools.product("abc", repeat=2))
        for mask in range(1 << len(edges)):
            rows = [edge for i, edge in enumerate(edges) if mask & (1 << i)]
            nodes = {node for edge in rows for node in edge}
            reach = {node: {node} for node in nodes}
            for source, target in rows:
                reach[source].add(target)
            for middle in nodes:
                for source in nodes:
                    if middle in reach[source]:
                        reach[source].update(reach[middle])
            expected = sorted({tuple(sorted(other for other in nodes
                                            if other in reach[node]
                                            and node in reach[other]))
                               for node in nodes})
            self.assertEqual(core.solve(rows), [list(group) for group in expected])


if __name__ == "__main__":
    unittest.main()

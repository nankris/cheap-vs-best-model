import copy
import dataclasses
import itertools
import json
import unittest
from unittest.mock import patch

import api
import core
import model
import render
import service


def reference_components(rows):
    nodes = {node for edge in rows for node in edge}
    reachable = {node: {node} for node in nodes}
    for source, target in rows:
        reachable[source].add(target)
    for middle in nodes:
        for source in nodes:
            if middle in reachable[source]:
                reachable[source].update(reachable[middle])
    remaining = set(nodes)
    components = []
    while remaining:
        node = min(remaining)
        component = sorted(
            other for other in remaining
            if other in reachable[node] and node in reachable[other]
        )
        remaining.difference_update(component)
        components.append(component)
    return sorted(components)


class ContractTests(unittest.TestCase):
    def test_frozen_result(self):
        result = model.Result([["a"]])
        self.assertTrue(dataclasses.is_dataclass(result))
        self.assertEqual(result.value, [["a"]])
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.value = []
        with self.assertRaises(dataclasses.FrozenInstanceError):
            del result.value

    def test_service_wraps_solver_output(self):
        rows = [["a", "b"]]
        value = [["sentinel"]]
        with patch.object(service, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, model.Result)
        self.assertIs(result.value, value)

    def test_render_uses_json(self):
        value = [["\"", "\\", "\n", "é", ""]]
        self.assertEqual(render.present(model.Result(value)), json.dumps(value))

    def test_components_and_duplicates(self):
        rows = [
            ["b", "a"], ["a", "b"], ["b", "c"], ["c", "d"],
            ["d", "c"], ["d", "e"], ["z", "z"], ["a", "b"],
        ]
        self.assertEqual(core.solve(rows), [["a", "b"], ["c", "d"], ["e"], ["z"]])
        self.assertEqual(core.solve([]), [])

    def test_all_three_node_graphs(self):
        edges = list(itertools.product(["a", "b", "c"], repeat=2))
        for mask in range(1 << len(edges)):
            rows = [edge for index, edge in enumerate(edges) if mask & (1 << index)]
            with self.subTest(mask=mask):
                self.assertEqual(core.solve(rows), reference_components(rows))

    def test_long_graphs(self):
        nodes = [str(index) for index in range(5000)]
        rows = list(zip(nodes, nodes[1:]))
        self.assertEqual(core.solve(rows), sorted([node] for node in nodes))
        rows.append((nodes[-1], nodes[0]))
        self.assertEqual(core.solve(rows), [sorted(nodes)])

    def test_api_batch_and_empty_batch(self):
        inputs = [[], [["b", "a"]], [["é", ""], ["", "é"]]]
        self.assertEqual(
            json.loads(api.run(json.dumps(inputs))),
            [[], [["a"], ["b"]], [["", "é"]]],
        )
        self.assertEqual(api.run("[]"), "[]")

    def test_api_applies_both_stages_in_order(self):
        inputs = [[], [["a", "a"]]]
        events = []

        def compute(rows):
            events.append(("compute", rows))
            return model.Result(rows)

        def present(result):
            self.assertIsInstance(result, model.Result)
            events.append(("present", result.value))
            return json.dumps(result.value)

        with patch.object(api, "compute", side_effect=compute), patch.object(
            api, "present", side_effect=present
        ):
            self.assertEqual(json.loads(api.run(json.dumps(inputs))), inputs)
        self.assertEqual(events, [
            ("compute", inputs[0]), ("present", inputs[0]),
            ("compute", inputs[1]), ("present", inputs[1]),
        ])

    def test_no_mutation_or_shared_state(self):
        rows = [["b", "a"], ["a", "b"], ["a", "b"]]
        original = copy.deepcopy(rows)
        result = service.compute(rows)
        render.present(result)
        self.assertEqual(rows, original)
        result.value[0].append("changed")
        self.assertEqual(service.compute(rows).value, [["a", "b"]])
        self.assertEqual(service.compute([]).value, [])
        self.assertEqual(api.run(json.dumps([rows])), '[[["a", "b"]]]')


if __name__ == "__main__":
    unittest.main()

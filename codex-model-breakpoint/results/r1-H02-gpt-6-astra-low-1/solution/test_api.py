import itertools
import json
import unittest

import api


class TopologicalOrderingTests(unittest.TestCase):
    def run_edges(self, edges):
        result = api.run(json.dumps(edges))
        self.assertIsInstance(result, str)
        return json.loads(result)

    def test_examples(self):
        cases = [
            ([], []),
            ([["a", "b"], ["a", "b"]], ["a", "b"]),
            ([["z", "a"], ["b", "c"]], ["b", "c", "z", "a"]),
            ([["a", "b"], ["z", "c"]], ["a", "b", "z", "c"]),
            ([["a", "a"]], None),
            ([["a", "b"], ["b", "a"]], None),
            ([["a", "b"], ["x", "y"], ["y", "x"]], None),
            ([["", "a,b"], ["a,b", '"\\\n'], ['"\\\n', "雪"]],
             ["", "a,b", '"\\\n', "雪"]),
        ]
        for edges, expected in cases:
            with self.subTest(edges=edges):
                self.assertEqual(self.run_edges(edges), expected)

    def test_all_directed_graphs_on_three_nodes(self):
        possible_edges = list(itertools.product(["a", "b", "c"], repeat=2))
        for mask in range(1 << len(possible_edges)):
            edges = [edge for i, edge in enumerate(possible_edges) if mask & (1 << i)]
            nodes = sorted({node for edge in edges for node in edge})
            expected = None
            for ordering in itertools.permutations(nodes):
                positions = {node: i for i, node in enumerate(ordering)}
                if all(positions[before] < positions[after] for before, after in edges):
                    expected = list(ordering)
                    break
            with self.subTest(edges=edges):
                self.assertEqual(self.run_edges(edges), expected)
                self.assertEqual(self.run_edges(list(reversed(edges)) + edges), expected)

    def test_long_chain(self):
        nodes = [str(i) for i in range(2000)]
        edges = list(zip(nodes, nodes[1:]))
        self.assertEqual(self.run_edges(edges), nodes)


if __name__ == "__main__":
    unittest.main()

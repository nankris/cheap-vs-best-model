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
            ([["a", "b"]], ["a", "b"]),
            ([["a", "b"], ["a", "b"], ["b", "c"]], ["a", "b", "c"]),
            ([["b", "a"], ["c", "d"]], ["b", "a", "c", "d"]),
            ([["a", "a"]], None),
            ([["a", "b"], ["b", "a"]], None),
            ([["a", "b"], ["c", "d"], ["d", "c"]], None),
            ([["", "x,y"], ["x,y", '"\\\n'], ['"\\\n', "é"]],
             ["", "x,y", '"\\\n', "é"]),
            ([["2", "z"], ["10", "z"], ["A", "z"]], ["10", "2", "A", "z"]),
        ]
        for edges, expected in cases:
            with self.subTest(edges=edges):
                self.assertEqual(self.run_edges(edges), expected)

    def test_all_three_node_graphs_against_permutation_oracle(self):
        possible_edges = list(itertools.product("abc", repeat=2))
        for mask in range(1 << len(possible_edges)):
            edges = [edge for index, edge in enumerate(possible_edges)
                     if mask & (1 << index)]
            nodes = sorted({node for edge in edges for node in edge})
            expected = None
            for ordering in itertools.permutations(nodes):
                positions = {node: index for index, node in enumerate(ordering)}
                if all(positions[a] < positions[b] for a, b in edges):
                    expected = list(ordering)
                    break
            with self.subTest(edges=edges):
                self.assertEqual(self.run_edges(edges), expected)
                self.assertEqual(self.run_edges(list(reversed(edges)) + edges), expected)

    def test_long_chain(self):
        nodes = [str(index) for index in range(2000)]
        self.assertEqual(self.run_edges(list(zip(nodes, nodes[1:]))), nodes)


if __name__ == "__main__":
    unittest.main()

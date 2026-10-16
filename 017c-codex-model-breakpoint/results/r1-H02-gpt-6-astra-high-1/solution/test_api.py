import itertools
import json
import unittest

import api


class TopologicalOrderingTests(unittest.TestCase):
    def run_rows(self, rows):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        return json.loads(result)

    def test_examples(self):
        cases = [
            ([], []),
            ([["b", "c"], ["a", "b"]], ["a", "b", "c"]),
            ([["a", "b"], ["a", "b"]], ["a", "b"]),
            ([["a", "b"], ["b", "a"]], None),
            ([["a", "a"]], None),
            ([["a", "b"], ["x", "y"], ["y", "x"]], None),
            ([["a", "b"], ["z", "zz"]], ["a", "b", "z", "zz"]),
            ([["b", "c"], ["a", "c"]], ["a", "b", "c"]),
            ([["10", "2"], ["1", "2"]], ["1", "10", "2"]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.assertEqual(self.run_rows(rows), expected)

    def test_json_string_nodes(self):
        nodes = ["", "a,b", 'a"b', "line\nbreak", "\\", "é", "雪"]
        rows = [[node, "终"] for node in nodes]
        self.assertEqual(self.run_rows(rows), sorted(nodes) + ["终"])

    def test_all_three_node_graphs_against_permutations(self):
        edges = list(itertools.product("abc", repeat=2))
        for mask in range(1 << len(edges)):
            rows = [edge for index, edge in enumerate(edges) if mask & (1 << index)]
            nodes = sorted({node for edge in rows for node in edge})
            expected = None
            for ordering in itertools.permutations(nodes):
                positions = {node: index for index, node in enumerate(ordering)}
                if all(positions[before] < positions[after] for before, after in rows):
                    expected = list(ordering)
                    break
            with self.subTest(rows=rows):
                self.assertEqual(self.run_rows(rows), expected)
                self.assertEqual(self.run_rows(list(reversed(rows)) + rows), expected)


if __name__ == "__main__":
    unittest.main()

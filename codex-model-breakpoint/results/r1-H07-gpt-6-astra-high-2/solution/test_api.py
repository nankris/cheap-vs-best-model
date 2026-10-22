import json
import random
import unittest

import api


class ConnectedComponentsTests(unittest.TestCase):
    def check_components(self, rows, expected):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), expected)

    def test_empty(self):
        self.check_components([], [])

    def test_transitive_undirected_edges_and_sorting(self):
        self.check_components(
            [["z", "y"], ["c", "b"], ["a", "b"], ["y", "x"]],
            [["a", "b", "c"], ["x", "y", "z"]],
        )

    def test_loops_and_duplicate_edges(self):
        self.check_components(
            [["z", "z"], ["b", "a"], ["a", "b"], ["b", "a"],
             ["a", "a"], ["z", "z"]],
            [["a", "b"], ["z"]],
        )

    def test_json_strings_and_lexicographic_order(self):
        nodes = ["", "a,b", 'a"b', "a\\b", "a\nb", "é", "10", "2"]
        self.check_components(
            [[node, node] for node in reversed(nodes)],
            [[node] for node in sorted(nodes)],
        )
        self.check_components([[nodes[1], nodes[2]]], [sorted(nodes[1:3])])

    def test_long_chain(self):
        nodes = [str(index) for index in range(3000)]
        self.check_components(list(zip(nodes, nodes[1:])), [sorted(nodes)])

    def test_random_graphs_against_component_merging(self):
        rng = random.Random(719)
        nodes = [str(index) for index in range(12)]
        for _ in range(100):
            rows = [[rng.choice(nodes), rng.choice(nodes)]
                    for _ in range(rng.randrange(30))]
            groups = []
            for left, right in rows:
                merged = {left, right}
                separate = []
                for group in groups:
                    if group & merged:
                        merged.update(group)
                    else:
                        separate.append(group)
                groups = separate + [merged]
            expected = sorted(sorted(group) for group in groups)
            with self.subTest(rows=rows):
                self.check_components(rows, expected)
                rng.shuffle(rows)
                self.check_components([[right, left] for left, right in rows], expected)


if __name__ == "__main__":
    unittest.main()

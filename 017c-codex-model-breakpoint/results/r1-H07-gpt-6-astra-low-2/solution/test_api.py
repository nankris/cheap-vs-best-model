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
            [["z", "y"], ["c", "b"], ["a", "b"], ["x", "y"]],
            [["a", "b", "c"], ["x", "y", "z"]],
        )

    def test_loops_and_duplicates(self):
        self.check_components(
            [["z", "z"], ["b", "a"], ["a", "b"], ["a", "a"]],
            [["a", "b"], ["z"]],
        )

    def test_json_string_nodes(self):
        nodes = ["", "a,b", '"quoted"', "line\nbreak", "雪"]
        self.check_components([[node, node] for node in nodes],
                              [[node] for node in sorted(nodes)])

    def test_long_chain(self):
        nodes = [str(i) for i in range(3000)]
        self.check_components(list(zip(nodes, nodes[1:])), [sorted(nodes)])

    def test_random_graphs_against_component_merging(self):
        rng = random.Random(42)
        for _ in range(100):
            rows = [[rng.choice("abcdefgh"), rng.choice("abcdefgh")]
                    for _ in range(rng.randrange(25))]
            groups = []
            for left, right in rows:
                merged = {left, right}
                remaining = []
                for group in groups:
                    if group & merged:
                        merged |= group
                    else:
                        remaining.append(group)
                groups = remaining + [merged]
            expected = sorted(sorted(group) for group in groups)
            self.check_components(rows, expected)
            rng.shuffle(rows)
            self.check_components([[right, left] for left, right in rows], expected)


if __name__ == "__main__":
    unittest.main()

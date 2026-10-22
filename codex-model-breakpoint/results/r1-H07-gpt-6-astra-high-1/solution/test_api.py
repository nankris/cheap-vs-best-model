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

    def test_transitive_undirected_connections_and_sorting(self):
        self.check_components(
            [["z", "y"], ["c", "b"], ["a", "b"], ["d", "c"]],
            [["a", "b", "c", "d"], ["y", "z"]],
        )

    def test_self_loops_duplicates_and_cycles(self):
        self.check_components(
            [["z", "z"], ["b", "a"], ["a", "b"], ["b", "c"],
             ["c", "a"], ["a", "a"], ["z", "z"]],
            [["a", "b", "c"], ["z"]],
        )

    def test_json_string_nodes(self):
        nodes = ["", "a,b", 'a"b', "a\\b", "a\nb", "\u00e9", "\u2603"]
        self.check_components([[node, node] for node in reversed(nodes)],
                              [[node] for node in sorted(nodes)])

    def test_long_chain(self):
        nodes = [str(i) for i in range(3000)]
        self.check_components(list(zip(nodes, nodes[1:])), [sorted(nodes)])

    def test_random_graphs_against_set_merging_reference(self):
        rng = random.Random(42)
        nodes = [str(i) for i in range(12)]
        for _ in range(100):
            rows = [[rng.choice(nodes), rng.choice(nodes)]
                    for _ in range(rng.randrange(35))]
            groups = []
            for left, right in rows:
                merged = {left, right}
                remaining = []
                for group in groups:
                    if group & merged:
                        merged.update(group)
                    else:
                        remaining.append(group)
                groups = remaining + [merged]
            expected = sorted(sorted(group) for group in groups)
            with self.subTest(rows=rows):
                self.check_components(rows, expected)
                rng.shuffle(rows)
                self.check_components([[b, a] for a, b in rows] + rows, expected)


if __name__ == "__main__":
    unittest.main()

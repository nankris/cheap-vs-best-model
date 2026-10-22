import json
import random
import unittest

import api


class ConnectedComponentsTests(unittest.TestCase):
    def run_rows(self, rows):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        return json.loads(result)

    def test_empty(self):
        self.assertEqual(self.run_rows([]), [])

    def test_undirected_transitive_components_and_order(self):
        rows = [["z", "y"], ["c", "b"], ["a", "b"], ["x", "y"]]
        self.assertEqual(self.run_rows(rows), [["a", "b", "c"], ["x", "y", "z"]])

    def test_self_loops_and_duplicate_edges(self):
        rows = [["z", "z"], ["b", "a"], ["a", "b"], ["b", "a"], ["a", "a"]]
        self.assertEqual(self.run_rows(rows), [["a", "b"], ["z"]])

    def test_json_strings_and_lexicographic_order(self):
        nodes = ["", "a,b", 'a"b', "a\nb", "é", "10", "2", "A"]
        self.assertEqual(self.run_rows([[n, n] for n in nodes]), [[n] for n in sorted(nodes)])

    def test_long_chain(self):
        nodes = [str(i) for i in range(3000)]
        self.assertEqual(self.run_rows(list(zip(nodes, nodes[1:]))), [sorted(nodes)])

    def test_random_graphs_against_component_merging(self):
        rng = random.Random(42)
        for _ in range(200):
            rows = [[rng.choice("abcdefgh"), rng.choice("abcdefgh")]
                    for _ in range(rng.randrange(30))]
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
            self.assertEqual(self.run_rows(rows), expected)
            rng.shuffle(rows)
            self.assertEqual(self.run_rows(rows), expected)


if __name__ == "__main__":
    unittest.main()

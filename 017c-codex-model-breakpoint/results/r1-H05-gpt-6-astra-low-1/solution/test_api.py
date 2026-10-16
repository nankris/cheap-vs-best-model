import json
import random
import unittest

import api


class RunTests(unittest.TestCase):
    def run_rows(self, rows):
        result = api.run(json.dumps(rows))
        self.assertIsInstance(result, str)
        return json.loads(result)

    def test_empty(self):
        self.assertEqual(self.run_rows([]), [])

    def test_versions_ties_and_sorting(self):
        rows = [
            ['z', 2, 'first'], ['a', -2, 'old'], ['z', 1, 'older'],
            ['z', 2, 'last'], ['a', -1, 'new'], ['a', -3, 'oldest'],
        ]
        self.assertEqual(self.run_rows(rows), [['a', 'new'], ['z', 'last']])

    def test_deletions_and_resurrection(self):
        rows = [
            ['a', 5, None], ['a', 4, 'stale'],
            ['b', 1, 'value'], ['b', 1, None],
            ['c', 1, None], ['c', 1, 'restored'],
            ['d', 1, None], ['d', 2, 'new'],
        ]
        self.assertEqual(self.run_rows(rows), [['c', 'restored'], ['d', 'new']])

    def test_falsy_values_and_json(self):
        rows = [
            ['zero', 1, 0], ['false', 1, False], ['empty', 1, ''],
            ['quoted,"key', 1, 'line\n"quoted", café'],
        ]
        result = self.run_rows(rows)
        self.assertEqual(result, sorted([[key, value] for key, _, value in rows]))
        self.assertIs(dict(result)['false'], False)
        self.assertIs(type(dict(result)['zero']), int)

    def test_generated_against_independent_reference(self):
        rng = random.Random(42)
        for _ in range(200):
            rows = [
                [rng.choice('abcd'), rng.randint(-5, 5),
                 rng.choice([None, False, 0, '', 'value'])]
                for _ in range(rng.randrange(50))
            ]
            expected = []
            for key in sorted({row[0] for row in rows}):
                candidates = [(row[1], index, row[2])
                              for index, row in enumerate(rows) if row[0] == key]
                value = max(candidates, key=lambda item: item[:2])[2]
                if value is not None:
                    expected.append([key, value])
            self.assertEqual(self.run_rows(rows), expected)


if __name__ == '__main__':
    unittest.main()

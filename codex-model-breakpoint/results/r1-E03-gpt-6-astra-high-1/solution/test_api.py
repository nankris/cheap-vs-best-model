import json
import unittest

from api import run
from codec import decode
from core import solve
from render import present
from service import compute


class ApiTests(unittest.TestCase):
    def test_json_input_and_output(self):
        cases = [
            ("[]", 2),
            ("[7]", 9),
            ("[1, 2, 3]", 8),
            ("[-8, -3]", -9),
            ("[5, -5, 0]", 2),
            ("[0, 0, 0]", 2),
            (" \n [ 10,\n -4, 3 ] \t", 11),
            (json.dumps([10**100, 3, -(10**100)]), 5),
            (json.dumps([10**100, 1]), 10**100 + 3),
            (json.dumps(list(range(1000))), 499502),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                result = run(payload)
                self.assertIsInstance(result, str)
                value = json.loads(result)
                self.assertIs(type(value), int)
                self.assertEqual(value, expected)

    def test_decode_preserves_integer_list(self):
        self.assertEqual(decode("[12, -4, 0]"), [12, -4, 0])
        self.assertEqual(decode("[]"), [])

    def test_computation_preserves_input(self):
        for operation in (solve, compute):
            with self.subTest(operation=operation.__name__):
                rows = [4, -2, 9]
                self.assertEqual(operation(rows), 13)
                self.assertEqual(rows, [4, -2, 9])
                self.assertEqual(operation([]), 2)

    def test_present_encodes_integer(self):
        self.assertEqual(json.loads(present(-12)), -12)


if __name__ == "__main__":
    unittest.main()

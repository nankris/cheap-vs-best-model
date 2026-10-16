import json
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from unittest.mock import patch

import api
import core
import model
import render
import service


class ContractTests(unittest.TestCase):
    def test_semver_precedence(self):
        expected = [
            "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
            "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11",
            "1.0.0-rc.1", "1.0.0", "1.0.1", "1.0.10",
            "1.1.0", "1.10.0", "2.0.0", "10.0.0",
        ]
        self.assertEqual(core.solve(expected[::-1]), expected)

    def test_identifier_rules(self):
        identifiers = ["0", "2", "10", "-", "A", "Z", "a", "a.0", "a.0.1", "a.1", "a.a", "aa"]
        expected = ["1.0.0-" + item for item in identifiers]
        self.assertEqual(core.solve(expected[::-1]), expected)

    def test_stable_build_ties_and_preservation(self):
        rows = ["1.0.0+z", "1.0.0-a+b", "1.0.0", "1.0.0-a+a", "1.0.0+a", "1.0.0+z"]
        original = rows.copy()
        self.assertEqual(core.solve(rows), [rows[1], rows[3], rows[0], rows[2], rows[4], rows[5]])
        self.assertEqual(rows, original)
        self.assertIsNot(core.solve(rows), rows)

    def test_large_numeric_components(self):
        huge = "1" + "0" * 5000
        for template in ("{}.0.0", "0.{}.0", "0.0.{}", "0.0.0-{}"):
            expected = [template.format("9"), template.format("10"), template.format(huge)]
            self.assertEqual(core.solve(expected[::-1]), expected)

    def test_frozen_result(self):
        result = model.Result(["1.0.0"])
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, ["1.0.0"])
        with self.assertRaises(FrozenInstanceError):
            result.value = []
        with self.assertRaises(FrozenInstanceError):
            del result.value

    def test_service_and_render(self):
        rows = ["2.0.0", "1.0.0"]
        result = service.compute(rows)
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result, model.Result(core.solve(rows)))
        self.assertEqual(rows, ["2.0.0", "1.0.0"])
        for value in (result.value, None, {"text": "é", "flag": True}, []):
            self.assertEqual(render.present(model.Result(value)), json.dumps(value))

    def test_api_batch_and_isolation(self):
        batch = [["2.0.0", "1.0.0"], [], ["0.1.0+build"]]
        payload = json.dumps(batch)
        expected = [["1.0.0", "2.0.0"], [], ["0.1.0+build"]]
        with patch.object(api, "compute", wraps=api.compute) as compute, patch.object(api, "present", wraps=api.present) as present:
            self.assertEqual(json.loads(api.run(payload)), expected)
            self.assertEqual(compute.call_count, len(batch))
            self.assertEqual(present.call_count, len(batch))
        self.assertEqual(api.run("[]"), "[]")
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(json.loads(payload), batch)
        first = service.compute(batch[0])
        first.value.append("99.0.0")
        self.assertEqual(service.compute(batch[0]).value, expected[0])


if __name__ == "__main__":
    unittest.main()

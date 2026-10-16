import json
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from unittest.mock import patch

import api
import core
import model
import render
import service


def journal(commands):
    return json.loads(api.run(json.dumps(commands)))


def put(key, rows, **extra):
    return dict(op="put", key=key, input=rows, **extra)


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_result_and_json_shapes(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute([])
        self.assertIsInstance(result, model.Result)
        with self.assertRaises(FrozenInstanceError):
            result.value = None
        for value in [None, False, 0, 1.5, "雪", [], [1, None], {"x": True}]:
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                computed = service.compute([])
                self.assertEqual(computed.value, value)
                self.assertEqual(json.loads(render.present(computed)), value)
                self.assertEqual(journal([put("", [])])["state"], [["", value]])

    def test_semver_precedence_and_stability(self):
        expected = [
            "0.9.9", "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
            "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1",
            "1.0.0", "1.0.1", "1.1.0", "2.0.0", "10.0.0",
        ]
        rows = list(reversed(expected))
        original = rows[:]
        self.assertEqual(core.solve(rows), expected)
        self.assertEqual(rows, original)
        ties = ["1.0.0+z", "1.0.0+a", "1.0.0", "1.0.0-alpha+b", "1.0.0-alpha+a"]
        self.assertEqual(core.solve(ties), ties[3:] + ties[:3])
        self.assertEqual(core.solve(["1.0.0-a", "1.0.0-Z", "1.0.0-10", "1.0.0-2"]),
                         ["1.0.0-2", "1.0.0-10", "1.0.0-Z", "1.0.0-a"])
        huge = "9" * 5000
        self.assertEqual(core.solve([huge + ".0.0", "10.0.0"]),
                         ["10.0.0", huge + ".0.0"])


class JournalTests(unittest.TestCase):
    def test_commands_sorted_state_and_nested_transactions(self):
        result = journal([
            put("雪", ["2.0.0", "1.0.0"]), put("", []),
            {"op": "begin"}, put("雪", ["3.0.0"]),
            {"op": "begin"}, {"op": "delete", "key": ""},
            {"op": "commit"}, {"op": "list"}, {"op": "rollback"},
            {"op": "get", "key": "雪"},
            {"op": "expect", "key": "", "value": []},
            {"op": "expect", "key": "", "value": None},
            {"op": "expect", "key": "absent", "value": None},
            {"op": "delete", "key": "雪"}, {"op": "get", "key": "雪"},
            {"op": "delete", "key": "雪"},
            {"op": "commit"}, {"op": "rollback"},
        ])
        self.assertEqual(result, {
            "events": [
                {"ok": ["1.0.0", "2.0.0"]}, {"ok": []},
                {"ok": 1}, {"ok": ["3.0.0"]}, {"ok": 2}, {"ok": []},
                {"ok": 1}, {"ok": [["雪", ["3.0.0"]]]}, {"ok": 0},
                {"ok": ["1.0.0", "2.0.0"]}, {"ok": True},
                {"error": "expectation"}, {"error": "expectation"},
                {"ok": ["1.0.0", "2.0.0"]}, {"error": "missing"},
                {"error": "missing"}, {"error": "transaction"}, {"error": "transaction"},
            ], "state": [["", []]], "depth": 0,
        })

    def test_validation_is_atomic_and_failed_ids_are_free(self):
        bad = [None, [], 1, "put", {}, {"op": []}, {"op": {}}, {"op": "unknown"},
               {"op": "put", "key": "k"}, {"op": "put", "input": []},
               {"op": "get"}, {"op": "delete", "key": 1},
               {"op": "expect", "key": "k"}, {"op": "expect", "value": []}]
        bad += [{"op": "rollback", "id": value} for value in [None, True, 0, [], {}]]
        bad += [{"op": op, "key": value, "input": [], "value": []}
                for op in ["put", "get", "delete", "expect"]
                for value in [None, True, 3, [], {}]]
        result = journal([put("k", []), {"op": "begin"}] + bad + [
            {"op": "get", "id": "retry"},
            {"op": "get", "key": "missing", "id": "retry"},
            {"op": "expect", "key": "k", "value": None, "id": "retry"},
            {"op": "list", "id": "retry", "key": None},
        ])
        self.assertEqual(result["events"][2:2 + len(bad)], [{"error": "command"}] * len(bad))
        self.assertEqual(result["events"][-4:], [
            {"error": "command"}, {"error": "missing"},
            {"error": "expectation"}, {"ok": [["k", []]]},
        ])
        self.assertEqual(result["state"], [["k", []]])
        self.assertEqual(result["depth"], 1)

    def test_id_identity_python_equality_and_validation_order(self):
        first = put("k", [], id="", extra={"a": [True], "b": 2})
        equal = put("k", [], id="", extra={"b": 2.0, "a": [1]})
        changed = put("k", [], id="", extra={"a": [False], "b": 2})
        result = journal([first, equal, changed, {"id": ""},
                          {"op": [], "id": ""}, {"op": "list", "id": None}])
        self.assertEqual(result["events"], [
            {"ok": []}, {"ok": []}, {"error": "id-conflict"},
            {"error": "id-conflict"}, {"error": "id-conflict"}, {"error": "command"},
        ])
        with patch.object(core, "solve", return_value={"x": [True, False]}):
            self.assertEqual(journal([put("k", []), {
                "op": "expect", "key": "k", "value": {"x": [1, 0]},
            }])["events"][-1], {"ok": True})

    def test_cached_transaction_events_have_no_side_effects(self):
        begin = {"op": "begin", "id": "b"}
        rollback = {"op": "rollback", "id": "r"}
        commit = {"op": "commit", "id": "c"}
        result = journal([
            commit, begin, begin, put("k", [], id="p"), rollback,
            put("k", [], id="p"), rollback, {"op": "begin"}, commit,
            {"op": "begin"}, commit, begin,
        ])
        self.assertEqual(result["events"], [
            {"error": "transaction"}, {"ok": 1}, {"ok": 1}, {"ok": []},
            {"ok": 0}, {"ok": []}, {"ok": 0}, {"ok": 1}, {"ok": 0},
            {"ok": 1}, {"ok": 0}, {"ok": 1},
        ])
        self.assertEqual(result["state"], [])
        self.assertEqual(result["depth"], 1)

    def test_read_and_delete_replay_and_run_isolation(self):
        get = {"op": "get", "key": "k", "id": "g"}
        listing = {"op": "list", "id": "l"}
        delete = {"op": "delete", "key": "k", "id": "d"}
        expect = {"op": "expect", "key": "k", "value": [], "id": "e"}
        result = journal([put("k", []), get, listing, expect, delete,
                          put("k", ["1.0.0"]), get, listing, expect, delete])
        self.assertEqual(result["events"][-4:], [
            {"ok": []}, {"ok": [["k", []]]}, {"ok": True}, {"ok": []},
        ])
        self.assertEqual(result["state"], [["k", ["1.0.0"]]])
        self.assertEqual(journal([get]), {
            "events": [{"error": "missing"}], "state": [], "depth": 0,
        })
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})

    def test_ownership_boundaries(self):
        commands = [put("k", ["2.0.0", "1.0.0"], id="p"), {"op": "begin"}]
        before = deepcopy(commands)
        real_loads = json.loads
        with patch.object(api.json, "loads", side_effect=lambda value: commands if value == "payload" else real_loads(value)):
            api.run("payload")
        self.assertEqual(commands, before)

        state, stack = {}, []
        value = {"nested": [[]]}
        with patch.object(core, "solve", return_value=value):
            event = api._execute(put("k", []), state, stack)
        value["nested"][0].append("outside")
        event["ok"]["nested"][0].append("event")
        self.assertEqual(state, {"k": {"nested": [[]]}})
        api._execute({"op": "begin"}, state, stack)
        state["k"]["nested"][0].append("live")
        self.assertEqual(stack, [{"k": {"nested": [[]]}}])
        for command in [{"op": "get", "key": "k"}, {"op": "list"}]:
            returned = api._execute(command, state, stack)
            if command["op"] == "get":
                returned["ok"]["nested"][0].append("read")
            else:
                returned["ok"][0][1]["nested"][0].append("list")
        self.assertEqual(state["k"]["nested"], [["live"]])
        api._execute({"op": "rollback"}, state, stack)
        self.assertEqual(state, {"k": {"nested": [[]]}})


if __name__ == "__main__":
    unittest.main()

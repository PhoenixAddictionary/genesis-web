"""genesis.event.v1 envelope: schema file and stdlib validator agree; cross-field rules hold."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_genesis_events import (  # noqa: E402
    FINANCIAL, OBJECT_TYPES, PROJECTION, PUBLIC_STATES, SCHEMA, load_events, validate_event, validate_events,
)

EXAMPLE = ROOT / "maker-handshake/schemas/examples/recorded-failure-replay.jsonl"
MASTERPLAN_STATES = {
    "SIGNAL_FROM_A_POSSIBLE_FUTURE", "CONCEPT_PREVIEW", "RECORDED_REPLAY", "CURRENT_PROGRAM_STATE", "BLOCKED",
    "REJECTED_BY_REALITY", "ACCEPTED_RESEARCH_STATE", "SUPERSEDED", "WITHDRAWN",
}


def good() -> dict:
    return copy.deepcopy(load_events(EXAMPLE)[0])


class EnvelopeTests(unittest.TestCase):
    def test_schema_matches_masterplan_grammar(self):
        self.assertEqual(PUBLIC_STATES, MASTERPLAN_STATES)
        self.assertEqual(len(OBJECT_TYPES), 33)
        self.assertTrue(FINANCIAL <= OBJECT_TYPES and PROJECTION <= OBJECT_TYPES)
        self.assertEqual(SCHEMA["properties"]["schema"]["const"], "genesis.event.v1")
        self.assertEqual(set(SCHEMA["required"]), set(SCHEMA["properties"]))

    def test_example_spine_is_valid(self):
        report = validate_events(load_events(EXAMPLE))
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["count"], 2)

    def test_missing_unknown_and_wrong_enums(self):
        event = good()
        del event["receipts"]
        event["extra"] = 1
        event["toState"] = "LIVE"
        event["objectType"] = "Comment"
        event["actor"] = {"type": "bot", "id": ""}
        event["occurredAt"] = "yesterday"
        errors, _ = validate_event(event)
        joined = "\n".join(errors)
        for needle in ("missing keys ['receipts']", "unknown keys ['extra']", "toState 'LIVE'",
                       "objectType 'Comment'", "actor must be", "occurredAt"):
            self.assertIn(needle, joined)

    def test_cross_field_rules(self):
        cases = {
            "ADMIT requires": dict(evidenceEffect="ADMIT", toState="CONCEPT_PREVIEW"),
            "REJECT requires": dict(evidenceEffect="REJECT", toState="CONCEPT_PREVIEW"),
            "SUPERSEDED requires": dict(toState="SUPERSEDED", fromState=None),
            "is financial": dict(objectType="Bounty", evidenceEffect="CANDIDATE"),
            "is a projection": dict(objectType="ParliamentMotion", evidenceEffect="ADMIT",
                                    toState="ACCEPTED_RESEARCH_STATE", receipts=[{"id": "r"}]),
            "needs at least one receipt": dict(toState="ACCEPTED_RESEARCH_STATE", evidenceEffect="ADMIT", receipts=[]),
            "PROTECTED events": dict(disclosure="PROTECTED", publicText="x"),
            "QUESTION_ANSWERED requires": dict(objectType="Question", eventType="QUESTION_ANSWERED", receipts=[]),
            "QUESTION_ABSTAINED requires": dict(objectType="Question", eventType="QUESTION_ABSTAINED", publicText=None),
        }
        for needle, patch in cases.items():
            event = good()
            event.update(patch)
            errors, _ = validate_event(event)
            self.assertTrue(any(needle in e for e in errors), (needle, errors))

    def test_question_cross_field_rules_v1(self):
        """AMD-0003 V1: QUESTION_ANSWERED needs a receipt, QUESTION_ABSTAINED needs typed publicText."""
        answered = good()
        answered.update(objectType="Question", eventType="QUESTION_ANSWERED", receipts=[{"id": "passage:1"}])
        self.assertEqual(validate_event(answered)[0], [])

        abstained = good()
        abstained.update(objectType="Question", eventType="QUESTION_ABSTAINED", receipts=[],
                          publicText="NO_SOURCES: nothing in the frozen corpus answers this.")
        self.assertEqual(validate_event(abstained)[0], [])

        blank_abstain = good()
        blank_abstain.update(objectType="Question", eventType="QUESTION_ABSTAINED", publicText="   ")
        errors, _ = validate_event(blank_abstain)
        self.assertTrue(any("QUESTION_ABSTAINED requires" in e for e in errors), errors)

        # eventType alone (wrong objectType) never triggers the Question-only rule.
        wrong_object = good()
        wrong_object.update(objectType="Attempt", eventType="QUESTION_ANSWERED", receipts=[])
        self.assertEqual(validate_event(wrong_object)[0], [])

    def test_live_wording_is_dissent_not_error(self):
        event = good()
        event["publicText"] = "Live feed of the Dock"
        errors, dissents = validate_event(event)
        self.assertEqual(errors, [])
        self.assertEqual(len(dissents), 1)
        event["toState"] = "CURRENT_PROGRAM_STATE"
        self.assertEqual(validate_event(event)[1], [])

    def test_duplicate_ids_fail_and_cli_exit_codes(self):
        events = load_events(EXAMPLE)
        events.append(copy.deepcopy(events[0]))
        self.assertIn("duplicate eventId", "\n".join(validate_events(events)["errors"]))
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps(events), encoding="utf-8")
            for path, code in ((EXAMPLE, 0), (bad, 1)):
                proc = subprocess.run([sys.executable, str(ROOT / "tools/validate_genesis_events.py"), str(path)],
                                      capture_output=True, text=True, timeout=30)
                self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Validate GENESIS event envelopes (genesis.event.v1) with the standard library only.

Reads a JSON array, a single object, or JSON Lines. Enforces the schema in
maker-handshake/schemas/genesis.event.v1.schema.json plus its cross-field
rules. Exit 0 = valid (DISSENT notes may still be present), 1 = errors.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "maker-handshake" / "schemas" / "genesis.event.v1.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
PROPS = SCHEMA["properties"]
REQUIRED = set(SCHEMA["required"])
PUBLIC_STATES = set(SCHEMA["$defs"]["publicState"]["enum"])
OBJECT_TYPES = set(SCHEMA["$defs"]["objectType"]["enum"])
DISCLOSURE = set(PROPS["disclosure"]["enum"])
EFFECTS = set(PROPS["evidenceEffect"]["enum"])
ACTOR_TYPES = set(PROPS["actor"]["properties"]["type"]["enum"])
FINANCIAL = {"SupportMission", "Bounty", "AssetCard", "BenefitLedger"}
PROJECTION = {"PublicProjection", "WorldManifest", "ParliamentMotion", "ResourceNeed"}
# AMD-0003 V1: reserved eventType names for objectType Question. A soft reservation —
# enforced only by the cross-field rules below, not by an eventType enum (that closed
# vocabulary is codification gap G4, dispatched but not landed on main).
QUESTION_ANSWERED = "QUESTION_ANSWERED"
QUESTION_ABSTAINED = "QUESTION_ABSTAINED"
EVENT_ID = re.compile(PROPS["eventId"]["pattern"])
RUN_ID = re.compile(PROPS["runId"]["pattern"])
WORK_ORDER = re.compile(PROPS["workOrderId"]["pattern"])
EVENT_TYPE = re.compile(PROPS["eventType"]["pattern"])
SHA256 = re.compile(SCHEMA["$defs"]["ref"]["properties"]["sha256"]["pattern"])


def _is_datetime(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return value.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", value) is not None


def _check_refs(name: str, value, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{name}: must be an array")
        return
    for index, ref in enumerate(value):
        where = f"{name}[{index}]"
        if not isinstance(ref, dict) or not isinstance(ref.get("id"), str) or not ref["id"]:
            errors.append(f"{where}: needs a non-empty id")
            continue
        if set(ref) - {"id", "sha256", "path"}:
            errors.append(f"{where}: unknown keys {sorted(set(ref) - {'id', 'sha256', 'path'})}")
        digest = ref.get("sha256")
        if digest is not None and (not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            errors.append(f"{where}: sha256 must be 64 lowercase hex characters or null")


def validate_event(event) -> tuple[list[str], list[str]]:
    """Return (errors, dissents) for one envelope."""
    errors: list[str] = []
    dissents: list[str] = []
    if not isinstance(event, dict):
        return ["event must be an object"], []
    missing = REQUIRED - set(event)
    if missing:
        errors.append(f"missing keys {sorted(missing)}")
    extra = set(event) - set(PROPS)
    if extra:
        errors.append(f"unknown keys {sorted(extra)}")
    get = event.get
    if get("schema") != "genesis.event.v1":
        errors.append("schema must be genesis.event.v1")
    if not isinstance(get("eventId"), str) or not EVENT_ID.fullmatch(get("eventId")):
        errors.append("eventId must match EVT-...")
    if get("programId") != "GENESIS":
        errors.append("programId must be GENESIS")
    if get("runId") is not None and (not isinstance(get("runId"), str) or not RUN_ID.match(get("runId"))):
        errors.append("runId must be null or start with RUN-")
    if get("workOrderId") is not None and (
        not isinstance(get("workOrderId"), str) or not WORK_ORDER.fullmatch(get("workOrderId"))
    ):
        errors.append("workOrderId must be null or GX-nnn")
    if get("objectType") not in OBJECT_TYPES:
        errors.append(f"objectType {get('objectType')!r} is not a canonical object")
    if not isinstance(get("objectId"), str) or not get("objectId"):
        errors.append("objectId must be a non-empty string")
    if not isinstance(get("eventType"), str) or not EVENT_TYPE.fullmatch(get("eventType")):
        errors.append("eventType must be UPPER_SNAKE_CASE")
    if get("fromState") is not None and get("fromState") not in PUBLIC_STATES:
        errors.append(f"fromState {get('fromState')!r} is not a public state")
    if get("toState") not in PUBLIC_STATES:
        errors.append(f"toState {get('toState')!r} is not a public state")
    if not _is_datetime(get("occurredAt")):
        errors.append("occurredAt must be an ISO 8601 date-time with offset")
    actor = get("actor")
    if (not isinstance(actor, dict) or set(actor) != {"type", "id"} or actor.get("type") not in ACTOR_TYPES
            or not isinstance(actor.get("id"), str) or not actor["id"]):
        errors.append("actor must be {type: agent|human|system, id}")
    for name in ("inputs", "outputs", "receipts"):
        _check_refs(name, get(name, []), errors)
    if get("disclosure") not in DISCLOSURE:
        errors.append("disclosure must be PUBLIC_SAFE, PROJECT_PRIVATE or PROTECTED")
    if get("evidenceEffect") not in EFFECTS:
        errors.append("evidenceEffect must be NONE, CANDIDATE, REOPEN, ADMIT or REJECT")
    text = get("publicText")
    if text is not None and not isinstance(text, str):
        errors.append("publicText must be a string or null")

    effect, to_state, obj = get("evidenceEffect"), get("toState"), get("objectType")
    if effect == "ADMIT" and to_state != "ACCEPTED_RESEARCH_STATE":
        errors.append("ADMIT requires toState ACCEPTED_RESEARCH_STATE")
    if effect == "REJECT" and to_state != "REJECTED_BY_REALITY":
        errors.append("REJECT requires toState REJECTED_BY_REALITY")
    if to_state == "SUPERSEDED" and get("fromState") is None:
        errors.append("SUPERSEDED requires the preserved prior fromState")
    if obj in FINANCIAL and effect != "NONE":
        errors.append(f"{obj} is financial; evidenceEffect must be NONE")
    if obj in PROJECTION and effect in {"ADMIT", "REJECT"}:
        errors.append(f"{obj} is a projection; it may not ADMIT or REJECT research state")
    if to_state == "ACCEPTED_RESEARCH_STATE" and not get("receipts"):
        errors.append("ACCEPTED_RESEARCH_STATE needs at least one receipt")
    if get("disclosure") == "PROTECTED" and text is not None:
        errors.append("PROTECTED events carry publicText null")
    event_type = get("eventType")
    if obj == "Question" and event_type == QUESTION_ANSWERED and not get("receipts"):
        errors.append("QUESTION_ANSWERED requires at least one receipt (AMD-0003 V1)")
    if obj == "Question" and event_type == QUESTION_ABSTAINED and not (isinstance(text, str) and text.strip()):
        errors.append("QUESTION_ABSTAINED requires non-empty publicText naming the refusal (AMD-0003 V1)")
    if isinstance(text, str) and re.search(r"(?i)\blive\b", text) and to_state != "CURRENT_PROGRAM_STATE":
        dissents.append("publicText says 'live' outside CURRENT_PROGRAM_STATE (§5)")
    return errors, dissents


def load_events(path: Path) -> list:
    raw = path.read_text(encoding="utf-8")
    stripped = raw.strip()
    if not stripped:
        return []
    if stripped[0] in "[{":
        try:
            data = json.loads(stripped)
        except ValueError:
            data = None
        if data is not None:
            return data if isinstance(data, list) else [data]
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def validate_events(events: list) -> dict:
    report = {"schema": "genesis.event.v1", "count": len(events), "errors": [], "dissents": []}
    seen: dict[str, int] = {}
    for index, event in enumerate(events):
        errors, dissents = validate_event(event)
        label = event.get("eventId", f"#{index}") if isinstance(event, dict) else f"#{index}"
        if isinstance(event, dict) and isinstance(event.get("eventId"), str):
            if event["eventId"] in seen:
                errors.append(f"duplicate eventId (first at #{seen[event['eventId']]})")
            else:
                seen[event["eventId"]] = index
        report["errors"].extend(f"{label}: {e}" for e in errors)
        report["dissents"].extend(f"{label}: {d}" for d in dissents)
    report["status"] = "FAIL" if report["errors"] else ("DISSENT" if report["dissents"] else "PASS")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    worst = 0
    for path in args.paths:
        try:
            report = validate_events(load_events(path))
        except (OSError, ValueError) as error:
            report = {"status": "FAIL", "count": 0, "errors": [f"unreadable: {error}"], "dissents": []}
        report["path"] = str(path)
        print(json.dumps(report, indent=2))
        worst = max(worst, 1 if report["status"] == "FAIL" else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main())

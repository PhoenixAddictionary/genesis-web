#!/usr/bin/env python3
"""Validate GENESIS plug-in packets (genesis.packet.v1) and receipts (genesis.receipt.v1).

Standard library only, mirroring tools/validate_genesis_events.py's shape and its
"exit 0 = valid" contract. Two things this file does NOT do: it does not grade a
guest's claims (that stays a maintainer's read), and it does not resolve a merge
conflict between two receipts for the same packet (that is an integrator act).

Usage:
    python tools/validate_packet.py packets/PKT-001.json [more paths...]
    python tools/validate_packet.py receipts/PKT-001.json
    python tools/validate_packet.py --check-index packets/INDEX.json

Exit 0 = every named file (or, in --check-index mode, the whole index) is valid.
Exit 1 = at least one error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA_PATH = ROOT / "packets" / "schemas" / "genesis.packet.v1.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "receipts" / "schemas" / "genesis.receipt.v1.schema.json"
INDEX_SCHEMA_PATH = ROOT / "packets" / "schemas" / "genesis.packet-index.v1.schema.json"
PACKET_SCHEMA = json.loads(PACKET_SCHEMA_PATH.read_text(encoding="utf-8"))
RECEIPT_SCHEMA = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
INDEX_SCHEMA = json.loads(INDEX_SCHEMA_PATH.read_text(encoding="utf-8"))

PACKET_ID = re.compile(PACKET_SCHEMA["properties"]["id"]["pattern"])
PACKET_STATUSES = set(PACKET_SCHEMA["$defs"]["status"]["enum"])
COMMIT = re.compile(PACKET_SCHEMA["properties"]["baseCommit"]["pattern"])
CLAIMED_BY = re.compile(PACKET_SCHEMA["properties"]["claimedBy"]["pattern"])

RECEIPT_ACTOR_ID = re.compile(RECEIPT_SCHEMA["properties"]["actor"]["properties"]["id"]["pattern"])
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _is_datetime(value) -> bool:
    if not isinstance(value, str):
        return False
    from datetime import datetime

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return value.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", value) is not None


def _check_string_array(name: str, value, errors: list[str], min_items: int = 0) -> None:
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        errors.append(f"{name}: must be an array of strings")
        return
    if len(value) < min_items:
        errors.append(f"{name}: needs at least {min_items} item(s)")


def validate_packet(packet) -> list[str]:
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["packet must be an object"]
    props = PACKET_SCHEMA["properties"]
    required = set(PACKET_SCHEMA["required"])
    missing = required - set(packet)
    if missing:
        errors.append(f"missing keys {sorted(missing)}")
    extra = set(packet) - set(props)
    if extra:
        errors.append(f"unknown keys {sorted(extra)}")
    get = packet.get
    if get("schema") != "genesis.packet.v1":
        errors.append("schema must be genesis.packet.v1")
    if not isinstance(get("id"), str) or not PACKET_ID.fullmatch(get("id")):
        errors.append("id must match PKT-NNN[optional suffix]")
    if get("status") not in PACKET_STATUSES:
        errors.append(f"status {get('status')!r} is not one of {sorted(PACKET_STATUSES)}")
    if not isinstance(get("baseCommit"), str) or not COMMIT.fullmatch(get("baseCommit")):
        errors.append("baseCommit must be a 40-char lowercase hex commit hash")
    if not isinstance(get("task"), str) or not get("task"):
        errors.append("task must be a non-empty string")
    _check_string_array("verifyCommand", get("verifyCommand", []), errors, min_items=1)
    _check_string_array("doneCriteria", get("doneCriteria", []), errors, min_items=1)
    _check_string_array("stopConditions", get("stopConditions", []), errors)
    _check_string_array("boundaries", get("boundaries", []), errors, min_items=1)
    if not _is_datetime(get("publishedAt")):
        errors.append("publishedAt must be an ISO 8601 date-time with offset")
    claimed_by = get("claimedBy")
    if "claimedBy" in packet and claimed_by is not None:
        if not isinstance(claimed_by, str) or not CLAIMED_BY.fullmatch(claimed_by):
            errors.append("claimedBy must be null or vendor/handle")
    receipt_id = get("receiptId")
    if "receiptId" in packet and receipt_id is not None and not isinstance(receipt_id, str):
        errors.append("receiptId must be null or a string")

    status = get("status")
    if status in {"MERGED", "SUBMITTED"} and not receipt_id:
        errors.append(f"status {status} requires a non-null receiptId")
    if status == "OPEN" and (claimed_by is not None or receipt_id is not None):
        errors.append("status OPEN requires claimedBy and receiptId to both be null")
    return errors


def validate_receipt(receipt, packet: dict | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]
    props = RECEIPT_SCHEMA["properties"]
    required = set(RECEIPT_SCHEMA["required"])
    missing = required - set(receipt)
    if missing:
        errors.append(f"missing keys {sorted(missing)}")
    extra = set(receipt) - set(props)
    if extra:
        errors.append(f"unknown keys {sorted(extra)}")
    get = receipt.get
    if get("schema") != "genesis.receipt.v1":
        errors.append("schema must be genesis.receipt.v1")
    if not isinstance(get("packetId"), str) or not PACKET_ID.fullmatch(get("packetId")):
        errors.append("packetId must match PKT-NNN[optional suffix]")
    if not isinstance(get("branch"), str) or not get("branch"):
        errors.append("branch must be a non-empty string")
    if not isinstance(get("headCommit"), str) or not COMMIT.fullmatch(get("headCommit")):
        errors.append("headCommit must be a 40-char lowercase hex commit hash")
    _check_string_array("verifyCommand", get("verifyCommand", []), errors, min_items=1)
    if not isinstance(get("verifierOutput"), str):
        errors.append("verifierOutput must be a string (verbatim command output)")
    if not isinstance(get("verifierExitCode"), int) or isinstance(get("verifierExitCode"), bool):
        errors.append("verifierExitCode must be an integer")
    actor = get("actor")
    if (not isinstance(actor, dict) or set(actor) != {"type", "id"} or actor.get("type") != "guest"
            or not isinstance(actor.get("id"), str) or not RECEIPT_ACTOR_ID.fullmatch(actor.get("id", ""))):
        errors.append("actor must be {type: guest, id: vendor/handle}")
    claims = get("claims", [])
    if "claims" in receipt:
        _check_string_array("claims", claims, errors)
    evidence = get("evidence", [])
    if "evidence" in receipt:
        if not isinstance(evidence, list):
            errors.append("evidence must be an array")
        else:
            for index, ref in enumerate(evidence):
                where = f"evidence[{index}]"
                if not isinstance(ref, dict) or not isinstance(ref.get("id"), str) or not ref["id"]:
                    errors.append(f"{where}: needs a non-empty id")
                    continue
                if set(ref) - {"id", "sha256", "path"}:
                    errors.append(f"{where}: unknown keys {sorted(set(ref) - {'id', 'sha256', 'path'})}")
                digest = ref.get("sha256")
                if digest is not None and (not isinstance(digest, str) or not SHA256.fullmatch(digest)):
                    errors.append(f"{where}: sha256 must be 64 lowercase hex characters or null")
    if not _is_datetime(get("submittedAt")):
        errors.append("submittedAt must be an ISO 8601 date-time with offset")

    if packet is not None and isinstance(get("verifyCommand"), list):
        if get("verifyCommand") != packet.get("verifyCommand"):
            errors.append("verifyCommand must equal the referenced packet's verifyCommand exactly")
        if get("packetId") != packet.get("id"):
            errors.append(f"packetId {get('packetId')!r} does not match packet id {packet.get('id')!r}")
    return errors


def validate_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return {"path": str(path), "status": "FAIL", "errors": [f"unreadable: {error}"]}
    schema = data.get("schema") if isinstance(data, dict) else None
    if schema == "genesis.packet.v1":
        errors = validate_packet(data)
    elif schema == "genesis.receipt.v1":
        errors = validate_receipt(data)
    else:
        errors = [f"unrecognized or missing \"schema\" field: {schema!r}"]
    return {"path": str(path), "status": "FAIL" if errors else "PASS", "errors": errors}


def _json_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _resolve_ref(schema: dict, root: dict) -> dict:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    if not ref.startswith("#/"):
        return schema
    node: object = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return schema
        node = node[part]
    return node if isinstance(node, dict) else schema


def validate_schema_shape(instance, schema: dict, root: dict | None = None, where: str = "index") -> list[str]:
    """Enforce the draft-2020-12 subset this repository's index schema uses.

    Stdlib only. Covers type, const, enum, required, additionalProperties: false,
    properties, items, $ref, pattern, format date-time, minLength, and minItems.
    Every message starts with 'schema shape:' so a bad index is a schema error,
    not a later KeyError.
    """
    if root is None:
        root = schema
    schema = _resolve_ref(schema, root)
    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        actual = _json_type(instance)
        if actual not in allowed:
            errors.append(f"schema shape: {where} must be {' or '.join(allowed)}, got {actual}")
            return errors
    if "const" in schema and instance != schema["const"]:
        errors.append(f"schema shape: {where} must be {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"schema shape: {where} {instance!r} is not one of {list(schema['enum'])}")
    if schema.get("format") == "date-time" and isinstance(instance, str) and not _is_datetime(instance):
        errors.append(f"schema shape: {where} must be an ISO 8601 date-time with offset")
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and isinstance(instance, str) and re.fullmatch(pattern, instance) is None:
        errors.append(f"schema shape: {where} must match {pattern}")
    min_length = schema.get("minLength")
    if isinstance(min_length, int) and isinstance(instance, str) and len(instance) < min_length:
        errors.append(f"schema shape: {where} must have length >= {min_length}")
    min_items = schema.get("minItems")
    if isinstance(min_items, int) and isinstance(instance, list) and len(instance) < min_items:
        errors.append(f"schema shape: {where} needs at least {min_items} item(s)")
    if isinstance(instance, dict) and ("properties" in schema or "required" in schema or schema.get("additionalProperties") is False):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"schema shape: missing required key {key!r}")
        if schema.get("additionalProperties") is False:
            for key in sorted(set(instance) - set(props)):
                errors.append(f"schema shape: unknown key {key!r}")
        for key, sub in props.items():
            if key in instance and isinstance(sub, dict):
                errors.extend(validate_schema_shape(instance[key], sub, root, f"{where}.{key}"))
    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(instance):
            errors.extend(validate_schema_shape(item, schema["items"], root, f"{where}[{index}]"))
    return errors


def check_index(index_path: Path) -> dict:
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return {"path": str(index_path), "status": "FAIL", "errors": [f"unreadable: {error}"]}
    errors: list[str] = validate_schema_shape(index, INDEX_SCHEMA)
    if not isinstance(index, dict) or not isinstance(index.get("packets"), list):
        return {"path": str(index_path), "status": "FAIL", "errors": errors}

    packets_dir = index_path.parent
    seen_ids: set[str] = set()
    for entry_index, entry in enumerate(index["packets"]):
        where = f"packets[{entry_index}]"
        if not isinstance(entry, dict) or not {"id", "status", "path", "sha256"} <= set(entry):
            errors.append(f"{where}: needs id, status, path, sha256")
            continue
        seen_ids.add(entry["id"])
        packet_path = (ROOT / entry["path"]) if not Path(entry["path"]).is_absolute() else Path(entry["path"])
        if not packet_path.is_file():
            errors.append(f"{where}: {entry['path']} does not exist on disk")
            continue
        raw = packet_path.read_bytes()
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != entry["sha256"]:
            errors.append(f"{where}: sha256 mismatch for {entry['path']} "
                          f"(index says {entry['sha256']}, on-disk file hashes to {actual_hash})")
        try:
            on_disk = json.loads(raw.decode("utf-8"))
        except ValueError as error:
            errors.append(f"{where}: {entry['path']} is not valid JSON: {error}")
            continue
        if on_disk.get("id") != entry["id"]:
            errors.append(f"{where}: on-disk id {on_disk.get('id')!r} does not match index id {entry['id']!r}")
        if on_disk.get("status") != entry["status"]:
            errors.append(f"{where}: on-disk status {on_disk.get('status')!r} "
                          f"does not match index status {entry['status']!r}")
        packet_errors = validate_packet(on_disk)
        errors.extend(f"{entry['id']}: {e}" for e in packet_errors)

    on_disk_packet_files = sorted(
        p for p in packets_dir.glob("*.json") if p.name != "INDEX.json"
    )
    for packet_file in on_disk_packet_files:
        try:
            on_disk = json.loads(packet_file.read_text(encoding="utf-8"))
        except ValueError:
            continue
        packet_id = on_disk.get("id") if isinstance(on_disk, dict) else None
        if packet_id not in seen_ids:
            errors.append(f"{packet_file.name}: on disk but not listed in {index_path.name} (orphan packet)")

    return {"path": str(index_path), "status": "FAIL" if errors else "PASS", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help="packet or receipt JSON files to validate")
    parser.add_argument("--check-index", type=Path, default=None,
                        help="validate a packets/INDEX.json against the packet files it lists (and vice versa)")
    args = parser.parse_args()
    if not args.paths and args.check_index is None:
        parser.error("give at least one path, or --check-index INDEX.json")

    worst = 0
    if args.check_index is not None:
        report = check_index(args.check_index)
        print(json.dumps(report, indent=2))
        worst = max(worst, 1 if report["status"] == "FAIL" else 0)
    for path in args.paths:
        report = validate_file(path)
        print(json.dumps(report, indent=2))
        worst = max(worst, 1 if report["status"] == "FAIL" else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate one genesis.live-tick.v1 line for HEAD and append it to spine/live.jsonl.

Run by .github/workflows/live-tick.yml on every push to main (Build-Zeit cadence,
Owner-Akt 2, 2026-09-17 - never the visitor's browser clock). Standard library +
git subprocess calls only, mirroring tools/validate_genesis_events.py's shape.

v1 classifies only two ways - see spine/schemas/genesis.live-tick.v1.schema.json
for why a finer betreiber/bahn split is not attempted here.

Usage:
    python tools/generate_live_tick.py            # append a tick for HEAD, if new
    python tools/generate_live_tick.py --dry-run   # print the tick, don't write
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spine" / "schemas" / "genesis.live-tick.v1.schema.json"
LIVE_PATH = ROOT / "spine" / "live.jsonl"
GUEST_RECEIPT = re.compile(r"^receipts/PKT-[0-9]{3}[A-Za-z0-9-]*\.json$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _run(args: list[str]) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def head_commit() -> str:
    return _run(["git", "rev-parse", "HEAD"])


def author_date(commit: str) -> str:
    # %aI = author date, strict ISO 8601, always carries an offset.
    return _run(["git", "show", "-s", "--format=%aI", commit])


def changed_paths(commit: str) -> list[tuple[str, str]]:
    """[(status, path), ...] for commit vs. its first parent. Root commit -> []."""
    try:
        parent = _run(["git", "rev-parse", commit + "^"])
    except subprocess.CalledProcessError:
        return []  # no parent: nothing to diff, nothing was "added" relative to before
    raw = _run(["git", "diff", "--name-status", parent, commit])
    pairs = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        pairs.append((status[:1], path))
    return pairs


def classify(changed: list[tuple[str, str]]) -> str:
    """The one real signal: did this push ADD a receipts/PKT-*.json file."""
    for status, path in changed:
        if status == "A" and GUEST_RECEIPT.match(path):
            return "gast"
    return "projekt"


def build_tick(commit: str, occurred_at: str, klass: str, generated_at: str) -> dict:
    return {
        "schema": "genesis.live-tick.v1",
        "commit": commit,
        "occurredAt": occurred_at,
        "class": klass,
        "generatedAt": generated_at,
    }


def validate_tick(tick: dict) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    required = set(schema["required"])
    errors = []
    missing = required - set(tick)
    if missing:
        errors.append(f"missing keys {sorted(missing)}")
    extra = set(tick) - set(schema["properties"])
    if extra:
        errors.append(f"unknown keys {sorted(extra)}")
    if tick.get("schema") != "genesis.live-tick.v1":
        errors.append("schema must be genesis.live-tick.v1")
    if not isinstance(tick.get("commit"), str) or not COMMIT.fullmatch(tick["commit"]):
        errors.append("commit must be a 40-char lowercase hex commit hash")
    if tick.get("class") not in {"gast", "projekt"}:
        errors.append("class must be gast or projekt")
    for field in ("occurredAt", "generatedAt"):
        value = tick.get(field)
        if not isinstance(value, str):
            errors.append(f"{field} must be a string")
            continue
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{field} must be an ISO 8601 date-time")
    return errors


def last_tick_commit() -> str | None:
    if not LIVE_PATH.exists():
        return None
    last_line = None
    for line in LIVE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last_line = line
    if last_line is None:
        return None
    try:
        return json.loads(last_line).get("commit")
    except ValueError:
        return None


def check_file(path: Path) -> dict:
    """Validate every line of an existing live-tick file against the schema (CI use)."""
    errors: list[str] = []
    count = 0
    if path.exists():
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            count += 1
            try:
                tick = json.loads(line)
            except ValueError as error:
                errors.append(f"line {index + 1}: not valid JSON: {error}")
                continue
            errors.extend(f"line {index + 1}: {e}" for e in validate_tick(tick))
    return {"path": str(path), "count": count, "status": "FAIL" if errors else "PASS", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print the tick, do not touch spine/live.jsonl")
    parser.add_argument("--check-file", type=Path, default=None,
                        help="validate every existing line in this file against genesis.live-tick.v1 and exit "
                             "(does not generate a new tick)")
    args = parser.parse_args()

    if args.check_file is not None:
        report = check_file(args.check_file)
        print(json.dumps(report, indent=2))
        return 1 if report["status"] == "FAIL" else 0

    commit = head_commit()
    if last_tick_commit() == commit:
        print(json.dumps({"status": "SKIP", "reason": "already ticked", "commit": commit}, indent=2))
        return 0

    tick = build_tick(
        commit=commit,
        occurred_at=author_date(commit),
        klass=classify(changed_paths(commit)),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    errors = validate_tick(tick)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors, "tick": tick}, indent=2))
        return 1

    print(json.dumps({"status": "PASS", "tick": tick}, indent=2))
    if args.dry_run:
        return 0

    with LIVE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(tick, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate THE WORLD ring's event set from THIS repository's own real history.

Replaces the 2026-09-16 one-time snapshot baked into index.html, which — per its
own receipt line — was built from a DIFFERENT repository's (PhoenixAddictionary/
memoria-mcp) git + PR + CI history, not genesis-web's own. That was disclosed
(the receipt line says so), but still reads, to a visitor, as "this project's
real history" (the section header's own words) when it was a borrowed proxy.
genesis-web now has 50+ real commits and real PRs of its own; there is no more
reason to borrow.

Usage:
    python tools/generate_world_ring.py                # compute + print a JSON summary, write nothing
    python tools/generate_world_ring.py --write         # regenerate the ring block in index.html
    python tools/generate_world_ring.py --check         # exit 1 if index.html is stale vs. real history

Data sources (real, verifiable, nothing invented):
  - commits:            `git log` on HEAD's ancestry (this checkout)
  - PR opens/merges/closes: `gh pr list --repo <owner>/<repo> --state all` (GitHub CLI,
                          locally authenticated — same tool a maintainer already uses)
  - CI:                  `gh run list` for the "CI" workflow, matched to each merged
                          PR's exact merge-commit SHA (`gh pr view --json mergeCommit`)

AGGREGATION RULE, disclosed (not hidden): CI fires on every push, so a raw per-run
feed would roughly double ring density against the commit glyphs already at ~1:1
with pushes, with little new information. Instead: one CI glyph per MERGED PR, using
the real conclusion of the CI run whose headSha equals that PR's merge commit — the
same "meaningful milestone, not raw feed" choice this repo already made for
spine/live.jsonl's Build-Zeit cadence (see spine/schemas/genesis.live-tick.v1.schema.json).
A PR that never merged gets no CI glyph from this rule (its close event still shows).

Standard library + subprocess (git, gh) only, mirroring tools/generate_live_tick.py's shape.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"
REPO = "PhoenixAddictionary/genesis-web"

RING_START = "<!-- WORLD-RING:START -->"
RING_END = "<!-- WORLD-RING:END -->"
SURFACE_START = "<!-- WORLD-SURFACE:START -->"
SURFACE_END = "<!-- WORLD-SURFACE:END -->"
GAUGES_START = "<!-- WORLD-GAUGES:START -->"
GAUGES_END = "<!-- WORLD-GAUGES:END -->"
SOURCE_START = "<!-- WORLD-SOURCE:START -->"
SOURCE_END = "<!-- WORLD-SOURCE:END -->"

# Same angular span as the 2026-09-16 snapshot (-55 .. 229.2), so the visual "gate
# gap" at the bottom of the ring is unchanged; only the density within it changes
# as real event count grows.
ANGLE_START = -55.0
ANGLE_END = 229.2

RADIUS = {"commit": 0.46, "ci": 0.6, "open": 0.74, "close": 0.9, "merge": 1.0}
GLYPH = {"commit": "•", "ci": "⚙", "open": "⊕", "close": "✕", "merge": "✓"}


def _run(args: list[str]) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout


@dataclass
class Event:
    kind: str          # commit | open | merge | close | ci
    ts: datetime        # real timestamp used for ordering + display
    title: str           # full hover/detail title, e.g. "PR #12 opened"
    label: str            # short surface-list label
    detail: str = ""       # long-form label for the surface list / one-event zoom
    key: str = ""            # short identifier shown in the ring (sha7 or PR number)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def collect_commits() -> list[Event]:
    raw = _run(["git", "log", "--format=%H|%h|%aI|%s"])
    events = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        full, short, iso, subject = line.split("|", 3)
        events.append(Event(
            kind="commit",
            ts=_parse_iso(iso),
            title=f"commit {short} — {subject}",
            label=f"commit {short}",
            detail=f"commit {short} — {subject}",
            key=short,
        ))
    return events


def collect_prs() -> tuple[list[Event], dict[int, str]]:
    """Returns (events, {pr_number: mergeCommitSha}) for CI matching."""
    raw = _run(["gh", "pr", "list", "--repo", REPO, "--state", "all",
                "--json", "number,title,createdAt,mergedAt,closedAt,state,mergeCommit",
                "--limit", "500"])
    prs = json.loads(raw)
    events: list[Event] = []
    merge_shas: dict[int, str] = {}
    for pr in prs:
        n = pr["number"]
        title = pr["title"]
        events.append(Event(
            kind="open",
            ts=_parse_iso(pr["createdAt"]),
            title=f"PR #{n} opened",
            label=f"PR #{n} opened",
            detail=f"PR #{n} opened — {title}",
            key=str(n),
        ))
        if pr["state"] == "MERGED" and pr.get("mergedAt"):
            events.append(Event(
                kind="merge",
                ts=_parse_iso(pr["mergedAt"]),
                title=f"PR #{n} merged",
                label=f"PR #{n} merged",
                detail=f"PR #{n} merged — {title}",
                key=str(n),
            ))
            merge_sha = (pr.get("mergeCommit") or {}).get("oid")
            if merge_sha:
                merge_shas[n] = merge_sha
        elif pr["state"] == "CLOSED" and pr.get("closedAt"):
            events.append(Event(
                kind="close",
                ts=_parse_iso(pr["closedAt"]),
                title=f"PR #{n} closed",
                label=f"PR #{n} closed",
                detail=f"PR #{n} closed — {title} — kept on the record",
                key=str(n),
            ))
    return events, merge_shas


def collect_ci(merge_shas: dict[int, str]) -> list[Event]:
    raw = _run(["gh", "run", "list", "--repo", REPO, "--workflow", "CI",
                "--json", "headSha,conclusion,createdAt,status", "--limit", "500"])
    runs = json.loads(raw)
    by_sha: dict[str, dict] = {}
    for run in runs:
        if run.get("status") != "completed":
            continue
        # keep the earliest completed run per sha (the real, first-seen conclusion)
        sha = run["headSha"]
        if sha not in by_sha or run["createdAt"] < by_sha[sha]["createdAt"]:
            by_sha[sha] = run
    events: list[Event] = []
    for pr_number, sha in merge_shas.items():
        run = by_sha.get(sha)
        if run is None:
            continue  # no completed CI run against this exact merge commit -- omit, don't guess
        conclusion = run["conclusion"]
        events.append(Event(
            kind="ci",
            ts=_parse_iso(run["createdAt"]),
            title=f"CI {conclusion} — PR #{pr_number} merge",
            label=f"CI {conclusion}",
            detail=f"CI — {conclusion} (PR #{pr_number} merge commit)",
            key=conclusion,
        ))
    return events


def build_events() -> list[Event]:
    events = collect_commits()
    pr_events, merge_shas = collect_prs()
    events += pr_events
    events += collect_ci(merge_shas)
    events.sort(key=lambda e: e.ts)
    return events


def _fmt_short(ts: datetime) -> str:
    return ts.strftime("%m-%d")


def _fmt_time(ts: datetime) -> str:
    return ts.strftime("%m-%d %H:%M")


def render_ring(events: list[Event]) -> str:
    n = len(events)
    step = (ANGLE_END - ANGLE_START) / (n - 1) if n > 1 else 0.0
    lines = []
    for i, ev in enumerate(events):
        angle = ANGLE_START + i * step
        radius = RADIUS[ev.kind]
        glyph = GLYPH[ev.kind]
        title = f"{ev.title} — {_fmt_time(ev.ts)}"
        lines.append(
            f'          <span class="pl-ev k-{ev.kind}" style="--a:{angle:g}; --r:{radius}" '
            f'title="{_esc(title)}">{glyph}<i class="pl-lab mono">{_fmt_short(ev.ts)} · {_esc(ev.label)}</i></span>'
        )
    return "\n".join(lines)


def render_surface(events: list[Event]) -> str:
    lines = []
    for ev in events:
        lines.append(
            f'          <li class="sv-ev k-{ev.kind}"><span class="g">{GLYPH[ev.kind]}</span>'
            f'<span class="t">{_fmt_time(ev.ts)}</span><span class="l">{_esc(ev.detail)}</span></li>'
        )
    return "\n".join(lines)


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace('"', "&quot;")
                .replace("<", "&lt;").replace(">", "&gt;"))


GUEST_RECEIPT = re.compile(r"^receipts/PKT-[0-9]{3}[A-Za-z0-9-]*\.json$")


def count_crossings() -> int:
    """A crossing = a real, committed receipts/PKT-*.json file -- the same signal
    tools/generate_live_tick.py already uses to classify a push as `gast`. Counting
    the files themselves (not re-deriving from PR history) avoids a second,
    possibly-drifting definition of the same fact."""
    return len(list((ROOT / "receipts").glob("PKT-*.json")))


def count_releases() -> int:
    raw = _run(["gh", "release", "list", "--repo", REPO])
    return len([line for line in raw.splitlines() if line.strip()])


def count_schemas() -> int:
    return len(list(ROOT.glob("*/schemas/*.schema.json")))


def count_tests() -> int:
    return len([p for p in (ROOT / "tests").glob("test_*.py")])


def count_automations() -> int:
    return len(list((ROOT / ".github" / "workflows").glob("*.yml")))


WORK_ORDERS_UNRESOLVED = (
    "packets/INDEX.json lists 1 (PKT-001), the page's own \"zoom in -- the work "
    "orders: the GX lane\" section lists 5 GX-* items, and the currently displayed "
    "gauge says 2 -- three different real artifacts, three different counts. Not "
    "computed here on purpose: guessing a fourth number would add a definition, "
    "not remove the ambiguity. Left at its current displayed value (2) until a "
    "human picks which artifact this gauge means."
)


def gauges_line(events: list[Event], *, work_orders_current: str) -> str:
    n = len(events)
    parts = [
        f"{n} EVENTS", f"{count_crossings()} CROSSINGS", f"{count_releases()} RELEASES",
        f"{work_orders_current} WORK ORDERS",
        f"{count_schemas()} SCHEMAS", f"{count_tests()} TESTS", f"{count_automations()} AUTOMATIONS",
    ]
    return " · ".join(parts)


def apply(text: str, start_marker: str, end_marker: str, new_body: str, inline: bool = False) -> str:
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"markers {start_marker!r}/{end_marker!r} not found in index.html")
    replacement = (start_marker + new_body + end_marker if inline
                   else start_marker + "\n" + new_body + "\n          " + end_marker)
    return pattern.sub(lambda _m: replacement, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="regenerate index.html's ring block in place")
    parser.add_argument("--check", action="store_true", help="exit 1 if index.html is stale vs. real history")
    args = parser.parse_args()

    events = build_events()
    summary = {
        "total_events": len(events),
        "commits": sum(1 for e in events if e.kind == "commit"),
        "pr_opens": sum(1 for e in events if e.kind == "open"),
        "pr_merges": sum(1 for e in events if e.kind == "merge"),
        "pr_closes": sum(1 for e in events if e.kind == "close"),
        "ci": sum(1 for e in events if e.kind == "ci"),
        "gauges_line": gauges_line(events, work_orders_current="2"),
        "work_orders_unresolved": WORK_ORDERS_UNRESOLVED,
    }

    if not args.write and not args.check:
        print(json.dumps(summary, indent=2))
        return 0

    ring_html = render_ring(events)
    surface_html = render_surface(events)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_html = (f"source: git log + pull-request and CI history of THIS repository "
                   f"(PhoenixAddictionary/genesis-web), read {today}")
    current = INDEX_PATH.read_text(encoding="utf-8")
    updated = apply(current, RING_START, RING_END, "          " + ring_html)
    updated = apply(updated, SURFACE_START, SURFACE_END, "          " + surface_html)
    updated = apply(updated, GAUGES_START, GAUGES_END, summary["gauges_line"], inline=True)
    updated = apply(updated, SOURCE_START, SOURCE_END, source_html, inline=True)

    if args.check:
        stale = updated != current
        print(json.dumps({**summary, "stale": stale}, indent=2))
        return 1 if stale else 0

    INDEX_PATH.write_text(updated, encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

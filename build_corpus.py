#!/usr/bin/env python3
"""Freeze corpus-src/*.txt into a content-addressed corpus.json (korpus 0.2).

Per docs/engine-api-contract.md §4: one manifest hash names the whole frozen
snapshot; every passage carries a deterministic id, a human locator, and its
own sha256. A corpus is never mutated in place — new content = new version.
"""

import hashlib
import json
import re
from pathlib import Path

SRC = Path(__file__).parent / "corpus-src"
OUT = Path(__file__).parent / "corpus.json"
VERSION = "0.3"
FROZEN = "2026-09-16"
MAX_PASSAGE_CHARS = 1100


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\s*\n\s*", " ", text)).strip()


def split_long(locator, text):
    if len(text) <= MAX_PASSAGE_CHARS:
        return [(locator, text)]
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    parts, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > MAX_PASSAGE_CHARS:
            parts.append(cur)
            cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur:
        parts.append(cur)
    if len(parts) == 1:
        return [(locator, parts[0])]
    return [(f"{locator} ({k})", part) for k, part in enumerate(parts, 1)]


def parse(path: Path):
    raw = path.read_text(encoding="utf-8")
    head, _, body = raw.partition("\n##")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip().upper()] = v.strip()
    sections = re.split(r"^## +", "##" + body if body else "", flags=re.M)
    passages = []
    for sec in sections:
        sec = sec.strip().lstrip("#").strip()
        if not sec:
            continue
        locator, _, text = sec.partition("\n")
        locator = locator.strip()
        if not text.strip():
            continue
        for loc, part in split_long(locator, text.strip()):
            norm = normalize(part)
            if len(norm) < 40:
                continue
            passages.append({
                "id": f"{meta['SOURCE']}:{slug(loc)}",
                "s": meta["SOURCE"],
                "loc": loc,
                "sha256": sha256(norm),
                "text": norm,
            })
    return meta, passages


def main():
    sources, all_passages = [], []
    for path in sorted(SRC.glob("*.txt")):
        meta, passages = parse(path)
        src_hash = sha256("".join(p["sha256"] for p in passages))
        sources.append({
            "sourceId": meta["SOURCE"],
            "title": meta.get("TITLE", ""),
            "translator": meta.get("TRANSLATOR", ""),
            "provenance": meta.get("PROVENANCE", ""),
            "license": meta.get("LICENSE", "public domain"),
            "version": VERSION,
            "passageCount": len(passages),
            "sourceSha256": src_hash,
        })
        all_passages.extend(passages)
        print(f"{meta['SOURCE']:10s} {len(passages):4d} passages  sha256 {src_hash[:12]}  ({path.name})")

    ids = [p["id"] for p in all_passages]
    assert len(ids) == len(set(ids)), "duplicate passage ids"
    manifest_sha = sha256(json.dumps(
        {"version": VERSION, "frozen": FROZEN, "sources": sources},
        sort_keys=True, separators=(",", ":")))
    corpus = {
        "version": VERSION,
        "frozen": FROZEN,
        "manifestSha256": manifest_sha,
        "passageCount": len(all_passages),
        "sources": sources,
        "passages": all_passages,
    }
    OUT.write_text(json.dumps(corpus, ensure_ascii=False, separators=(",", ":")))
    print(f"\nkorpus {VERSION} · {len(all_passages)} passages · {len(sources)} sources")
    print(f"manifest sha256 {manifest_sha}")
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()

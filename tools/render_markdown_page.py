#!/usr/bin/env python3
"""Render one markdown doc (PLUG-IN.md and its .de/.hu siblings) into a static,
styled HTML page - so a visitor following a link from a tweet/HN post sees the
real site instead of raw markdown source with literal asterisks and brackets.

Deliberately not a general markdown engine: it covers exactly the constructs
these three files use (h1/h2, bold, inline code, links, ordered/unordered
lists, blockquote, paragraphs) and nothing else - a hand-rolled subset is
easier to verify than pulling in a dependency for three known documents.
No build step at *serve* time: this runs once here, at commit time, and
commits its plain HTML output, same pattern as build_corpus.py freezing
corpus-src/ into corpus.json.

Usage:
    python tools/render_markdown_page.py   # regenerates all three pages
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = [
    {
        "src": ROOT / "PLUG-IN.md",
        "out": ROOT / "plugin" / "index.html",
        "lang": "en",
        "title": "Plugging in — GENESIS",
        "description": "Fork, take an open packet, build it, send it back as a pull request with a machine-checked receipt.",
        "canonical": "https://openpassage.org/plugin/",
        "switch": [("EN", "/plugin/", "en", True), ("DE", "/de/plugin/", "de", False), ("HU", "/hu/plugin/", "hu", False)],
    },
    {
        "src": ROOT / "PLUG-IN.de.md",
        "out": ROOT / "de" / "plugin" / "index.html",
        "lang": "de",
        "title": "Einklinken — GENESIS",
        "description": "Forken, ein offenes Paket nehmen, bauen, als Pull Request mit maschinell geprüftem Receipt zurückgeben.",
        "canonical": "https://openpassage.org/de/plugin/",
        "switch": [("EN", "/plugin/", "en", False), ("DE", "/de/plugin/", "de", True), ("HU", "/hu/plugin/", "hu", False)],
    },
    {
        "src": ROOT / "PLUG-IN.hu.md",
        "out": ROOT / "hu" / "plugin" / "index.html",
        "lang": "hu",
        "title": "Bekapcsolódás — GENESIS",
        "description": "Fork, végy egy nyitott csomagot, építsd meg, add vissza pull requestként géppel ellenőrzött receipttel.",
        "canonical": "https://openpassage.org/hu/plugin/",
        "switch": [("EN", "/plugin/", "en", False), ("DE", "/de/plugin/", "de", False), ("HU", "/hu/plugin/", "hu", True)],
    },
]

BACK_LABEL = {"en": "← back to the well", "de": "← zurück zum Brunnen", "hu": "← vissza a kúthoz"}

LIST_ITEM_RE = re.compile(r"^\d+\.\s")


def parse_blocks(text: str) -> list[tuple[str, object]]:
    lines = text.split("\n")
    n = len(lines)
    blocks: list[tuple[str, object]] = []
    i = 0
    # the first non-blank line of every source file is its own 🌐-language
    # nav line - dropped here, replaced by a freshly generated one pointing
    # at the rendered pages (see render_page()).
    while i < n and lines[i].strip() == "":
        i += 1
    if i < n and lines[i].lstrip().startswith("\U0001F310"):
        i += 1

    while i < n:
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
            i += 1
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            i += 1
        elif line.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip())
                i += 1
            blocks.append(("blockquote", " ".join(buf)))
        elif LIST_ITEM_RE.match(line):
            items = []
            while i < n and LIST_ITEM_RE.match(lines[i]):
                item = [LIST_ITEM_RE.sub("", lines[i])]
                i += 1
                while i < n and lines[i].strip() != "" and lines[i].startswith(" ") and not LIST_ITEM_RE.match(lines[i].lstrip()):
                    item.append(lines[i].strip())
                    i += 1
                items.append(" ".join(item))
            blocks.append(("ol", items))
        elif line.startswith("- "):
            items = []
            while i < n and lines[i].startswith("- "):
                item = [lines[i][2:]]
                i += 1
                while i < n and lines[i].strip() != "" and lines[i].startswith("  ") and not lines[i].lstrip().startswith("- "):
                    item.append(lines[i].strip())
                    i += 1
                items.append(" ".join(item))
            blocks.append(("ul", items))
        else:
            buf = [line]
            i += 1
            while (i < n and lines[i].strip() != "" and not lines[i].startswith("#")
                   and not lines[i].startswith(">") and not LIST_ITEM_RE.match(lines[i])
                   and not lines[i].startswith("- ")):
                buf.append(lines[i])
                i += 1
            blocks.append(("p", " ".join(buf)))
    return blocks


def _rootify(match: re.Match) -> str:
    """These pages are served from a subdirectory (/plugin/, /de/plugin/,
    /hu/plugin/), but every link in the source markdown is written relative
    to the repository root (where the .md file itself lives) - e.g.
    "packets/INDEX.json". Left as-is, that resolves to
    /plugin/packets/INDEX.json (doesn't exist). Root-relative it instead,
    same fix as well.js's fetch() calls in the earlier i18n commit."""
    label, href = match.group(1), match.group(2)
    if not re.match(r"^(https?:|mailto:|#|/)", href):
        href = "/" + href
    return f'<a href="{href}">{label}</a>'


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _rootify, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # single-asterisk italic, e.g. "*evidence to check*" - applied after
    # bold consumes every "**", so a genuinely lone "*" (as in the code
    # span `receipts/PKT-*.json`) has no partner left to pair with and is
    # correctly left alone; verified by hand against all three source
    # files before adding this (only one italic span each, no stray pairs).
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def blocks_to_html(blocks: list[tuple[str, object]]) -> str:
    out = []
    for kind, content in blocks:
        if kind == "h1":
            out.append(f"<h1>{inline(content)}</h1>")
        elif kind == "h2":
            out.append(f"<h2>{inline(content)}</h2>")
        elif kind == "blockquote":
            out.append(f"<blockquote><p>{inline(content)}</p></blockquote>")
        elif kind == "p":
            out.append(f"<p>{inline(content)}</p>")
        elif kind == "ol":
            items = "".join(f"<li>{inline(it)}</li>" for it in content)
            out.append(f"<ol>{items}</ol>")
        elif kind == "ul":
            items = "".join(f"<li>{inline(it)}</li>" for it in content)
            out.append(f"<ul>{items}</ul>")
    return "\n".join(out)


def render_page(page: dict) -> str:
    body = blocks_to_html(parse_blocks(page["src"].read_text(encoding="utf-8")))
    switch_html = " · ".join(
        f'<span aria-current="page">{code}</span>' if current
        else f'<a class="quiet" href="{href}" hreflang="{hreflang}" lang="{hreflang}">{code}</a>'
        for code, href, hreflang, current in page["switch"]
    )
    hreflang_links = "\n".join(
        f'<link rel="alternate" hreflang="{hreflang}" href="https://openpassage.org{href}">'
        for _code, href, hreflang, _cur in page["switch"]
    ) + '\n<link rel="alternate" hreflang="x-default" href="https://openpassage.org/plugin/">'
    back = BACK_LABEL[page["lang"]]
    return f"""<!DOCTYPE html>
<html lang="{page['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(page['title'], quote=False)}</title>
<meta name="description" content="{html.escape(page['description'], quote=False)}">
<link rel="canonical" href="{page['canonical']}">
{hreflang_links}
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/plugin/plugin.css">
</head>
<body class="plugin-body">
<nav class="lang-switch mono plugin-langnav" aria-label="Language">{switch_html}</nav>
<main class="plugin-doc">
{body}
<p class="plugin-back"><a class="quiet" href="/">{back}</a></p>
</main>
</body>
</html>
"""


def main() -> None:
    for page in PAGES:
        page["out"].parent.mkdir(parents=True, exist_ok=True)
        page["out"].write_text(render_page(page), encoding="utf-8", newline="\n")
        print(f"wrote {page['out'].relative_to(ROOT)}")


if __name__ == "__main__":
    main()

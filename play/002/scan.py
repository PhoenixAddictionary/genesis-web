# Licensed under the Apache License, Version 2.0. See LICENSE.
"""Hebrew Psalter search. The King James text is a control, not the corpus.

search() reads one argument: the Hebrew Psalter. It does not take a book list.
A hit is a detector match that names a psalm and a verse in that text.
english_control() says what the English text says, and those lines are not hits.
A remembered pattern that cannot be shown at a Hebrew verse is a drop.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

# Remembered English strings. They are not search keys. citation_or_drop
# checks them after search() and never turns them into hits.
REMEMBERED_ENGLISH = ("Amen, and Amen", "are ended")

# Post-hoc hypothesis, applied only in drops_for(), never inside search().
REMEMBERED_SEAM_PSALMS = (41, 72, 89, 106, 150)

_PSALM_RE = re.compile(r"^## Psalm (\d+)\s*$")
_VERSE_RE = re.compile(r"^(\d+) (.*)$")
_EN_AMEN = re.compile(r"(?i)\bamen\b")
_EN_DOUBLE = re.compile(r"(?i)\bamen,\s+and\s+amen\b")
_EN_ENDED = re.compile(r"(?i)\bare ended\b")

NOT_SCANNED = (
    "acrostics; qere/ketiv; cantillation as a seam test; "
    "manuscript layout (blank lines between books)"
)


def parse_psalter(text: str) -> list[dict]:
    """Psalm and verse numbers as the text numbers them."""
    psalms: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        heading = _PSALM_RE.match(line.strip())
        if heading:
            current = {"psalm": int(heading.group(1)), "verses": []}
            psalms.append(current)
            continue
        if current is None:
            continue
        verse = _VERSE_RE.match(line)
        if verse:
            current["verses"].append(
                {"verse": int(verse.group(1)), "text": verse.group(2).strip()}
            )
    return psalms


def skeleton(word: str) -> str:
    """Consonant letters only. Cantillation and vowel points are not consonants."""
    return "".join(ch for ch in word if "\u05D0" <= ch <= "\u05EA")


def hebrew_words(verse: str) -> list[str]:
    """Words split on whitespace and maqqef. Paseq and sof pasuq are not words."""
    verse = verse.replace("\u05BE", " ")
    words = []
    for raw in verse.split():
        token = raw.strip("\u05C0\u05C3\u05BE.,;:!?()[]\"'")
        if skeleton(token):
            words.append(token)
    return words


def _place(verse: int, ordered: list[int]) -> str:
    if not ordered:
        return "outside the last two verses"
    if verse == ordered[-1]:
        return "last verse"
    if len(ordered) >= 2 and verse == ordered[-2]:
        return "second to last"
    return "outside the last two verses"


def _amen_hits(psalm: int, verse: int, place: str, words: list[str]) -> list[dict]:
    hits = []
    i = 0
    while i < len(words):
        skel = skeleton(words[i])
        nxt = skeleton(words[i + 1]) if i + 1 < len(words) else ""
        if skel == "אמן" and nxt == "ואמן":
            hits.append(
                {
                    "psalm": psalm,
                    "verse": verse,
                    "place": place,
                    "detector": "double-amen",
                    "pointed": f"{words[i]} + {words[i + 1]}",
                    "seam": place != "outside the last two verses",
                }
            )
            i += 2
            continue
        if skel in ("אמן", "ואמן"):
            hits.append(
                {
                    "psalm": psalm,
                    "verse": verse,
                    "place": place,
                    "detector": "single-amen",
                    "pointed": words[i],
                    "seam": place != "outside the last two verses",
                }
            )
        i += 1
    return hits


def _ended_hit(psalm: int, verse: int, place: str, words: list[str], verse_text: str) -> dict | None:
    if place == "outside the last two verses":
        return None
    pointed = []
    seen_kalu = False
    seen_tefillot = False
    for word in words:
        skel = skeleton(word)
        if skel == "כלו":
            seen_kalu = True
            pointed.append(word)
        elif skel == "תפלות":
            seen_tefillot = True
            pointed.append(word)
    if not (seen_kalu and seen_tefillot):
        return None
    return {
        "psalm": psalm,
        "verse": verse,
        "place": place,
        "detector": "are-ended",
        "pointed": " + ".join(pointed),
        "verse_text": verse_text,
        "seam": True,
    }


def _blessing(psalm: int, verse: int, place: str, words: list[str]) -> dict | None:
    if place != "outside the last two verses":
        return None
    for i in range(len(words) - 1):
        if skeleton(words[i]) == "ברוך" and skeleton(words[i + 1]) == "יהוה":
            return {
                "psalm": psalm,
                "verse": verse,
                "place": place,
                "pointed": f"{words[i]} + {words[i + 1]}",
            }
    return None


def require_verse(hit: dict) -> None:
    """A hit with no verse is a failed test."""
    if "psalm" not in hit or "verse" not in hit:
        raise ValueError("hit has no verse")
    if not isinstance(hit["psalm"], int) or not isinstance(hit["verse"], int):
        raise ValueError("hit has no verse")


def search(text: str) -> dict:
    """Find formulas in the Hebrew Psalter. One argument. No book list."""
    hits: list[dict] = []
    blessings: list[dict] = []
    psalm_numbers: list[int] = []
    for psalm in parse_psalter(text):
        psalm_numbers.append(psalm["psalm"])
        ordered = [item["verse"] for item in psalm["verses"]]
        for item in psalm["verses"]:
            place = _place(item["verse"], ordered)
            words = hebrew_words(item["text"])
            hits.extend(_amen_hits(psalm["psalm"], item["verse"], place, words))
            ended = _ended_hit(
                psalm["psalm"], item["verse"], place, words, item["text"]
            )
            if ended:
                hits.append(ended)
            # The first verse is not the middle of the psalm.
            if ordered and item["verse"] != ordered[0]:
                blessing = _blessing(psalm["psalm"], item["verse"], place, words)
                if blessing:
                    blessings.append(blessing)
    for hit in hits:
        require_verse(hit)
    return {
        "opened": "Westminster Leningrad Codex, public domain",
        "hits": hits,
        "blessings": blessings,
        "psalm_numbers": psalm_numbers,
        "not_scanned": NOT_SCANNED,
    }


def english_control(text: str) -> dict:
    """What the English text says. Labeled control. Never a hit."""
    controls = []
    psalm_numbers = []
    neither = []
    for psalm in parse_psalter(text):
        psalm_numbers.append(psalm["psalm"])
        amen_or_ended = False
        for item in psalm["verses"]:
            if _EN_DOUBLE.search(item["text"]):
                amen_or_ended = True
                controls.append(
                    {
                        "psalm": psalm["psalm"],
                        "verse": item["verse"],
                        "label": '"Amen, and Amen"',
                        "role": "control",
                    }
                )
            elif _EN_AMEN.search(item["text"]):
                amen_or_ended = True
                controls.append(
                    {
                        "psalm": psalm["psalm"],
                        "verse": item["verse"],
                        "label": "single Amen",
                        "role": "control",
                    }
                )
            if _EN_ENDED.search(item["text"]):
                amen_or_ended = True
                controls.append(
                    {
                        "psalm": psalm["psalm"],
                        "verse": item["verse"],
                        "label": '"are ended"',
                        "role": "control",
                    }
                )
        if psalm["psalm"] == 150 and not amen_or_ended:
            neither.append(150)
    for row in controls:
        if row["role"] != "control":
            raise ValueError("english control labeled as something else")
    return {"controls": controls, "psalm_numbers": psalm_numbers, "neither": neither}


def citation_or_drop(hits: list[dict], psalm: int, verse: int) -> str:
    """A remembered address is a hit only when that Hebrew verse is already cited."""
    for hit in hits:
        require_verse(hit)
        if hit["psalm"] == psalm and hit["verse"] == verse:
            return "hit"
    return "drop"


_ENGLISH_DETECTOR = {
    "Amen, and Amen": "double-amen",
    "are ended": "are-ended",
    '"Amen, and Amen"': "double-amen",
    '"are ended"': "are-ended",
    "single Amen": "single-amen",
}


def _citation_refs(hits: list[dict], detector: str, psalm: int | None = None) -> list[str]:
    refs = []
    for hit in hits:
        require_verse(hit)
        if hit["detector"] != detector:
            continue
        if psalm is not None and hit["psalm"] != psalm:
            continue
        ref = f"{hit['psalm']}:{hit['verse']}"
        if ref not in refs:
            refs.append(ref)
    return refs


def drops_for(hebrew_text: str, found: dict, control: dict) -> list[str]:
    """Post-hoc. Does not create hits and does not tell search() where to look.

    A remembered English string is a drop only when no Hebrew hit shows that
    formula. When the hits already cite it, the English words are not the
    citation, and the line names those Hebrew verses. It does not say that
    no Hebrew verse exists.
    """
    lines = []
    for pattern in REMEMBERED_ENGLISH:
        if any(pattern in hit.get("pointed", "") for hit in found["hits"]):
            raise ValueError("English string promoted to a hit")
        refs = _citation_refs(found["hits"], _ENGLISH_DETECTOR[pattern])
        if refs:
            cited = ", ".join(refs)
            lines.append(
                f'"{pattern}": English words are not the citation. '
                f"Hebrew citation is {cited}."
            )
        else:
            lines.append(f'drop: "{pattern}" — no Hebrew verse — not a hit')
    if not isinstance(hebrew_text, str):
        raise ValueError("hebrew text missing")
    hit_addresses = {(hit["psalm"], hit["verse"]) for hit in found["hits"]}
    for row in control["controls"]:
        address = (row["psalm"], row["verse"])
        if address in hit_addresses:
            continue
        refs = _citation_refs(
            found["hits"], _ENGLISH_DETECTOR[row["label"]], psalm=row["psalm"]
        )
        if refs:
            cited = ", ".join(refs)
            lines.append(
                f"drop: KJV control {row['psalm']}:{row['verse']} — "
                f"Hebrew citation is {cited}"
            )
        else:
            lines.append(
                f"drop: KJV control {row['psalm']}:{row['verse']} — not a Hebrew hit"
            )
    seam_psalms = {hit["psalm"] for hit in found["hits"] if hit["seam"]}
    for psalm in REMEMBERED_SEAM_PSALMS:
        if psalm not in seam_psalms:
            lines.append(
                f"drop: remembered seam after {psalm} — no Hebrew verse — not a hit"
            )
    return lines


def _verdict(found: dict) -> str:
    interior = [
        hit for hit in found["hits"]
        if hit["detector"] == "double-amen" and not hit["seam"]
    ]
    if interior:
        refs = ", ".join(f"{hit['psalm']}:{hit['verse']}" for hit in interior)
        return (
            f"A double Amen is cited at {refs}, outside the last two verses. "
            "That refutes treating the terminal double Amens as one repeated seam."
        )
    doubles = [h for h in found["hits"] if h["detector"] == "double-amen"]
    singles = [h for h in found["hits"] if h["detector"] == "single-amen"]
    ended = [h for h in found["hits"] if h["detector"] == "are-ended"]

    def fmt(rows: list[dict]) -> str:
        if not rows:
            return "none"
        return ", ".join(f"{row['psalm']}:{row['verse']} {row['place']}" for row in rows)

    return (
        f"Terminal double Amen: {fmt(doubles)}. "
        f"Terminal single Amen: {fmt(singles)}. "
        f"Terminal כלו and תפלות: {fmt(ended)}. "
        "No double Amen sits outside the last two verses of its psalm."
    )


def _hit_line(hit: dict) -> str:
    require_verse(hit)
    seam = "seam" if hit["seam"] else "not a seam"
    line = (
        f"- {hit['psalm']}:{hit['verse']} {hit['place']} {hit['detector']} "
        f"{hit['pointed']} {seam}"
    )
    if hit["detector"] == "are-ended":
        line += f" verse: {hit['verse_text']}"
    return line


def format_receipt(hebrew_text: str, kjv_text: str) -> str:
    found = search(hebrew_text)
    control = english_control(kjv_text)
    lines = [
        "search",
        "text: Westminster Leningrad Codex, public domain",
        "morphology: not opened",
        "bhs: not opened",
        "bhq: not opened",
        "hits:",
    ]
    if found["hits"]:
        lines.extend(_hit_line(hit) for hit in found["hits"])
    else:
        lines.append("- none")
    lines.append("blessing:")
    if found["blessings"]:
        for row in found["blessings"]:
            lines.append(
                f"- {row['psalm']}:{row['verse']} blessing, outside the last two verses, not a seam"
            )
    else:
        lines.append("- none")
    lines.append(
        "not scanned: "
        + found["not_scanned"]
        + ". This run has no detector for them, so it does not report a miss."
    )
    lines.append("verdict: " + _verdict(found))
    lines.append("")
    lines.append("control")
    lines.append("label: control")
    lines.append("text: King James Version. What the English text says. Not hits.")
    if control["controls"]:
        for row in control["controls"]:
            lines.append(f"- {row['psalm']}:{row['verse']} control {row['label']}")
    else:
        lines.append("- none")
    for psalm in control["neither"]:
        lines.append(f"- {psalm} control neither formula")
    lines.append("")
    lines.append("drops")
    lines.extend("- " + drop for drop in drops_for(hebrew_text, found, control))
    return "\n".join(lines) + "\n"


def render_page(receipt: str) -> str:
    if not receipt.endswith("\n"):
        receipt += "\n"
    body = html.escape(receipt, quote=False)
    # No text nodes outside the receipt. A newline between tags would show up
    # as page text, and the page is only the receipt.
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"></head>"
        f"<!-- CC0 1.0. Generated receipt. --><body><pre>{body}</pre></body></html>\n"
    )


def write_page(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parent
    hebrew = (root / "wlc-psalms.txt").read_text(encoding="utf-8")
    kjv = (root / "kjv-psalms.txt").read_text(encoding="utf-8")
    receipt = format_receipt(hebrew, kjv)
    page = render_page(receipt)
    (root / "index.html").write_text(page, encoding="utf-8")
    return receipt


def main() -> None:
    write_page()


if __name__ == "__main__":
    main()

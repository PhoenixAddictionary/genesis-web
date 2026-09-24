# Licensed under the Apache License, Version 2.0. See LICENSE.
"""Play 002: Hebrew search, King James as control, citation or drop."""
from __future__ import annotations

import importlib.util
import inspect
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "play" / "002"


def load_scan():
    spec = importlib.util.spec_from_file_location("play002_scan", PLAY / "scan.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan = load_scan()
WLC = (PLAY / "wlc-psalms.txt").read_text(encoding="utf-8")
KJV = (PLAY / "kjv-psalms.txt").read_text(encoding="utf-8")


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pre = []
        self.other = []
        self.in_pre = 0

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.in_pre += 1

    def handle_endtag(self, tag):
        if tag == "pre" and self.in_pre:
            self.in_pre -= 1

    def handle_data(self, data):
        if self.in_pre:
            self.pre.append(data)
        else:
            self.other.append(data)


def visible_parts(page: str) -> tuple[str, str]:
    parser = VisibleText()
    parser.feed(page)
    return "".join(parser.pre), "".join(parser.other)


def visible(page: str) -> str:
    pre, other = visible_parts(page)
    assert other.strip() == ""
    return pre


def section(receipt: str, name: str) -> str:
    lines = receipt.splitlines()
    start = lines.index(name)
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index] in ("search", "control", "drops"):
            end = index
            break
    return "\n".join(lines[start:end])


def verse_map(text: str) -> dict[tuple[int, int], str]:
    found = {}
    psalm = None
    for line in text.splitlines():
        heading = scan._PSALM_RE.match(line.strip())
        if heading:
            psalm = int(heading.group(1))
            continue
        if psalm is None:
            continue
        verse = scan._VERSE_RE.match(line)
        if verse:
            found[(psalm, int(verse.group(1)))] = verse.group(2)
    return found


def independent_amen(text: str) -> list[tuple[int, int, str]]:
    rows = []
    for (psalm, verse), body in verse_map(text).items():
        words = scan.hebrew_words(body)
        i = 0
        while i < len(words):
            skel = scan.skeleton(words[i])
            nxt = scan.skeleton(words[i + 1]) if i + 1 < len(words) else ""
            if skel == "אמן" and nxt == "ואמן":
                rows.append((psalm, verse, "double-amen"))
                i += 2
                continue
            if skel in ("אמן", "ואמן"):
                rows.append((psalm, verse, "single-amen"))
            i += 1
    return rows


def test_search_function_takes_only_the_hebrew_text():
    assert list(inspect.signature(scan.search).parameters) == ["text"]


def test_kjv_string_alone_is_not_a_hit():
    english_only = "## Psalm 1\n1 Amen, and Amen.\n2 The prayers are ended.\n"
    assert scan.search(english_only)["hits"] == []
    assert scan.search(KJV)["hits"] == []
    found = scan.search(WLC)
    for hit in found["hits"]:
        assert "Amen, and Amen" not in hit["pointed"]
        assert "are ended" not in hit["pointed"]


def test_remembered_pattern_with_no_hebrew_verse_is_a_drop():
    hebrew = "## Psalm 17\n1 מילה\n2 מילה\n3 מילה\n4 סוף\n"
    kjv = "## Psalm 17\n1 A line.\n2 A line.\n3 Amen, and Amen.\n4 The prayers are ended.\n"
    found = scan.search(hebrew)
    assert scan.citation_or_drop(found["hits"], 17, 3) == "drop"
    assert found["hits"] == []
    receipt = scan.format_receipt(hebrew, kjv)
    assert "17:3" not in section(receipt, "search")
    drops = section(receipt, "drops")
    assert 'drop: "Amen, and Amen" — no Hebrew verse — not a hit' in drops
    assert 'drop: "are ended" — no Hebrew verse — not a hit' in drops
    assert "drop: KJV control 17:3 — not a Hebrew hit" in drops
    assert "drop: KJV control 17:4 — not a Hebrew hit" in drops


def test_hebrew_longer_word_containing_amen_letters_is_not_a_hit():
    hebrew = "## Psalm 2\n1 אֲמָנוֹן sits in the middle.\n2 מילה\n3 אָמֵן\n"
    found = scan.search(hebrew)
    longer = scan.skeleton("אֲמָנוֹן")
    amen = "\u05d0\u05de\u05e0"
    assert longer != amen
    assert longer != "\u05d5" + amen
    assert amen in longer
    assert [(h["psalm"], h["verse"], h["detector"]) for h in found["hits"]] == [
        (2, 3, "single-amen")
    ]
    assert all("אֲמָנוֹן" not in h["pointed"] for h in found["hits"])


def test_kjv_control_firmament_and_lamentation_are_not_amen():
    assert "firmament" in KJV.lower()
    assert "lamentation" in KJV.lower()
    control = scan.english_control(KJV)
    verses = verse_map(KJV)
    firmament = {addr for addr, body in verses.items() if "firmament" in body.lower()}
    lament = {addr for addr, body in verses.items() if "lamentation" in body.lower()}
    assert firmament and lament
    labeled = {(row["psalm"], row["verse"]) for row in control["controls"]}
    assert firmament.isdisjoint(labeled)
    assert lament.isdisjoint(labeled)
    assert scan.search(KJV)["hits"] == []


def test_hebrew_tokenizer_niqqud_cantillation_maqqef_and_leading_vav():
    hebrew = (
        "## Psalm 2\n"
        "1 prefix\n"
        "2 אָ֘מֵ֥ן ׀ וְאָמֵֽן\n"
        "3 אָמֵן־וְאָמֵן\n"
        "## Psalm 4\n"
        "1 אֲמָנוֹן\n"
        "2 וְאָמֵן\n"
    )
    found = scan.search(hebrew)
    kinds = [(h["psalm"], h["verse"], h["detector"], h["pointed"]) for h in found["hits"]]
    assert (2, 2, "double-amen", "אָ֘מֵ֥ן + וְאָמֵֽן") in kinds
    assert (2, 3, "double-amen", "אָמֵן + וְאָמֵן") in kinds
    assert (4, 2, "single-amen", "וְאָמֵן") in kinds
    assert all(h["psalm"] != 4 or h["verse"] != 1 for h in found["hits"])
    assert scan.skeleton("וְאָמֵן") == "ואמן"
    assert scan.skeleton("אָ֘מֵ֥ן") == "אמן"


def test_hebrew_pointing_is_reported_not_interpreted():
    hebrew = "## Psalm 6\n1 אָ֘מֵ֥ן ׀ וְאָמֵֽן\n"
    found = scan.search(hebrew)
    assert len(found["hits"]) == 1
    pointed = found["hits"][0]["pointed"]
    assert "אָ֘מֵ֥ן" in pointed
    assert "וְאָמֵֽן" in pointed
    assert "\u05B8" in pointed  # qamats, kept
    assert "\u0598" in pointed  # zarqa, kept
    assert scan.skeleton("אָ֘מֵ֥ן") == "אמן"
    assert "\u0598" not in scan.skeleton("אָ֘מֵ֥ן")
    assert "\u05B8" not in scan.skeleton("אָ֘מֵ֥ן")


def test_english_control_address_is_dropped_when_the_hebrew_verse_differs():
    found = scan.search(WLC)
    control = scan.english_control(KJV)
    hit_at = {(hit["psalm"], hit["verse"]) for hit in found["hits"]}
    mismatches = [
        row for row in control["controls"] if (row["psalm"], row["verse"]) not in hit_at
    ]
    assert mismatches, "this pair of texts has at least one English address the Hebrew does not cite"
    receipt = scan.format_receipt(WLC, KJV)
    search_section = section(receipt, "search")
    drops = section(receipt, "drops")
    for row in mismatches:
        address = f"{row['psalm']}:{row['verse']}"
        assert f"- {address} " not in search_section
        assert f"drop: KJV control {address} — not a Hebrew hit" in drops
        assert row["role"] == "control"
    # The Hebrew citation keeps its own verse: same psalm, different verse, both visible.
    hebrew_amens = {(p, v) for p, v, _ in independent_amen(WLC)}
    english_amens = {
        (row["psalm"], row["verse"])
        for row in control["controls"]
        if "Amen" in row["label"]
    }
    shared_psalms = {p for p, _ in hebrew_amens} & {p for p, _ in english_amens}
    differed = False
    for psalm in shared_psalms:
        hv = sorted(v for p, v in hebrew_amens if p == psalm)
        ev = sorted(v for p, v in english_amens if p == psalm)
        if hv != ev:
            differed = True
            for verse in ev:
                assert f"- {psalm}:{verse} " not in search_section
            for verse in hv:
                assert f"- {psalm}:{verse} " in search_section
    assert differed


def test_hebrew_mid_psalm_blessing_is_not_a_seam():
    verses = verse_map(WLC)
    by_psalm: dict[int, list[int]] = {}
    for psalm, verse in verses:
        by_psalm.setdefault(psalm, []).append(verse)
    expected = []
    for (psalm, verse), body in verses.items():
        ordered = by_psalm[psalm]
        if verse in set(ordered[-2:]):
            continue
        words = scan.hebrew_words(body)
        for i in range(len(words) - 1):
            if scan.skeleton(words[i]) == "ברוך" and scan.skeleton(words[i + 1]) == "יהוה":
                if ordered.index(verse) not in (0, len(ordered) - 1):
                    expected.append((psalm, verse))
                break
    assert expected, "the vendored Hebrew has a mid-psalm ברוך יהוה"
    found = scan.search(WLC)
    blessing_at = {(row["psalm"], row["verse"]) for row in found["blessings"]}
    hit_at = {(hit["psalm"], hit["verse"]) for hit in found["hits"]}
    for address in expected:
        assert address in blessing_at
        assert address not in hit_at
    receipt = scan.format_receipt(WLC, KJV)
    search_section = section(receipt, "search")
    sample = expected[0]
    assert f"- {sample[0]}:{sample[1]} blessing, outside the last two verses, not a seam" in search_section
    assert f"- {sample[0]}:{sample[1]} " not in "\n".join(
        line for line in search_section.splitlines() if line.startswith("- ") and "blessing" not in line
    )


def test_blessing_alone_is_not_a_seam():
    hebrew = (
        "## Psalm 9\n"
        "1 Blessed be the LORD\n"
        "2 בָּרוּךְ יְהוָה\n"
        "3 מילה\n"
        "4 בָּרוּךְ\n"
        "5 בָּרוּךְ יְהוָה\n"
    )
    found = scan.search(hebrew)
    assert found["hits"] == []
    assert [(row["psalm"], row["verse"]) for row in found["blessings"]] == [(9, 2)]


def test_hebrew_formulas_are_different_detectors():
    hebrew = (
        "## Psalm 4\n"
        "1 כָּלוּ תְפִלּוֹת\n"
        "2 מילה\n"
        "3 אָמֵן\n"
        "4 כָּלוּ תְפִלּוֹת\n"
        "## Psalm 7\n"
        "1 א\n"
        "2 ב\n"
        "3 אָמֵן וְאָמֵן\n"
    )
    found = scan.search(hebrew)
    rows = [(h["psalm"], h["verse"], h["detector"], h["seam"]) for h in found["hits"]]
    assert (4, 1, "are-ended", True) not in rows
    assert (4, 3, "single-amen", True) in rows
    assert (4, 4, "are-ended", True) in rows
    assert (7, 3, "double-amen", True) in rows
    assert not any(h["detector"] == "double-amen" and h["psalm"] == 4 for h in found["hits"])
    assert not any(h["detector"] == "single-amen" and h["psalm"] == 7 for h in found["hits"])


def test_hebrew_synthetic_endings_off_the_five_book_list():
    hebrew = (
        "## Psalm 3\n"
        "1 א\n"
        "2 ב\n"
        "3 אָמֵן וְאָמֵן\n"
        "## Psalm 8\n"
        "1 א\n"
        "2 אָמֵן וְאָמֵן\n"
        "3 כָּלוּ תְפִלּוֹת\n"
    )
    kjv = "## Psalm 1\n1 Nothing here.\n"
    found = scan.search(hebrew)
    assert [(h["psalm"], h["verse"], h["detector"]) for h in found["hits"]] == [
        (3, 3, "double-amen"),
        (8, 2, "double-amen"),
        (8, 3, "are-ended"),
    ]
    assert {41, 72, 89, 106, 150}.isdisjoint(h["psalm"] for h in found["hits"])
    receipt = scan.format_receipt(hebrew, kjv)
    search_section = section(receipt, "search")
    assert "- 3:3 " in search_section
    assert "- 8:2 " in search_section
    assert "- 8:3 " in search_section
    assert "Not one script of five identical endings" not in receipt
    drops = section(receipt, "drops")
    for psalm in (41, 72, 89, 106, 150):
        assert f"drop: remembered seam after {psalm} — no Hebrew verse — not a hit" in drops


def test_hypothesis_psalm_without_a_hebrew_formula_is_a_drop():
    verses = verse_map(WLC)
    last_two = sorted(verse for psalm, verse in verses if psalm == 150)[-2:]
    for verse in last_two:
        words = scan.hebrew_words(verses[(150, verse)])
        skels = [scan.skeleton(word) for word in words]
        assert "אמן" not in skels and "ואמן" not in skels
        assert not ("כלו" in skels and "תפלות" in skels)
    found = scan.search(WLC)
    assert all(hit["psalm"] != 150 for hit in found["hits"])
    receipt = scan.format_receipt(WLC, KJV)
    assert "drop: remembered seam after 150 — no Hebrew verse — not a hit" in section(receipt, "drops")
    assert "- 150:" not in section(receipt, "search")


def test_hebrew_not_scanned_is_not_reported_as_absent():
    receipt = scan.format_receipt(WLC, KJV)
    search_section = section(receipt, "search")
    for name in ("acrostics", "qere/ketiv", "cantillation as a seam test", "manuscript layout"):
        assert name in search_section
    assert "not scanned:" in search_section
    assert "does not report a miss" in search_section
    assert "acrostics are absent" not in receipt
    assert "no qere" not in receipt
    assert "cantillation is absent" not in receipt


def test_search_opens_wlc_text_and_not_morphology():
    assert "https://ebible.org/find/details.php?id=hboWLC" in WLC
    assert "https://grovescenter.org/file-downloads/" in WLC
    assert "public domain" in WLC.lower()
    assert "strong=" not in WLC
    assert "x-morph" not in WLC
    assert "BHS" not in WLC.split("PROVENANCE:", 1)[1].split("LICENSE:", 1)[0] or "Not BHS" in WLC
    receipt = scan.format_receipt(WLC, KJV)
    search_section = section(receipt, "search")
    assert "Westminster Leningrad Codex, public domain" in search_section
    assert "morphology: not opened" in search_section
    assert "bhs: not opened" in search_section
    assert "bhq: not opened" in search_section
    assert "label: control" in section(receipt, "control")
    assert "Not hits." in section(receipt, "control")


def test_every_hit_points_at_a_vendored_hebrew_verse():
    verses = verse_map(WLC)
    found = scan.search(WLC)
    assert found["hits"], "the Hebrew text has at least one citation"
    seen = [(h["psalm"], h["verse"], h["detector"]) for h in found["hits"] if h["detector"] != "are-ended"]
    assert seen == [(p, v, d) for p, v, d in independent_amen(WLC)]
    for hit in found["hits"]:
        scan.require_verse(hit)
        body = verses[(hit["psalm"], hit["verse"])]
        for part in hit["pointed"].split(" + "):
            assert part in body
        if hit["detector"] == "are-ended":
            assert hit["verse_text"] == body
    try:
        scan.require_verse({"psalm": 41, "detector": "double-amen"})
    except ValueError as exc:
        assert "no verse" in str(exc)
    else:
        raise AssertionError("hit with no verse must fail")


def test_interior_double_amen_refutes():
    hebrew = "## Psalm 5\n1 אָמֵן וְאָמֵן\n2 מילה\n3 מילה\n4 סוף\n"
    found = scan.search(hebrew)
    assert found["hits"][0]["seam"] is False
    assert found["hits"][0]["verse"] == 1
    receipt = scan.format_receipt(hebrew, "## Psalm 1\n1 No formula.\n")
    verdict = section(receipt, "search").split("verdict: ", 1)[1]
    assert "refutes" in verdict
    assert "5:1" in verdict
    assert "This text does not have that" not in receipt
    assert "Not one script of five identical endings" not in receipt


def test_receipt_does_not_claim_the_setup():
    receipt = scan.format_receipt(WLC, KJV)
    page = scan.render_page(receipt)
    blob = receipt + "\n" + visible(page)
    for banned in (
        "greater intelligence",
        "redaction",
        "composition",
        "found the setup",
        "Suppose a greater intelligence",
    ):
        assert banned not in blob
    assert "A note on this scan" not in visible(page)


def test_page_visible_text_is_only_the_receipt():
    receipt = scan.format_receipt(WLC, KJV)
    page = scan.render_page(receipt)
    assert visible(page) == receipt
    assert "<title" not in page
    assert "<h1" not in page
    assert "fetch(" not in page
    assert "http://" not in page
    assert "https://" not in page
    search_section = section(receipt, "search")
    assert "Amen, and Amen" not in search_section
    assert "are ended" not in search_section
    control = section(receipt, "control")
    assert "Amen, and Amen" in control
    assert "are ended" in control
    assert "label: control" in control


def test_committed_page_matches_the_function():
    page = (PLAY / "index.html").read_text(encoding="utf-8")
    receipt = scan.format_receipt(WLC, KJV)
    assert page == scan.render_page(receipt)
    assert visible(page) == receipt


if __name__ == "__main__":
    import traceback

    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception:
                failed += 1
                print("FAIL", name)
                traceback.print_exc()
            else:
                print("ok", name)
    raise SystemExit(failed)

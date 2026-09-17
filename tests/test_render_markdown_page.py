"""render_markdown_page.py: the hand-rolled subset parser stays correct on
the three real source files, and its output is committed and up to date."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import render_markdown_page as rmp  # noqa: E402


class InlineTests(unittest.TestCase):
    def test_bold_link_code(self):
        out = rmp.inline("**bold** and [text](packets/INDEX.json) and `code`")
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn('<a href="/packets/INDEX.json">text</a>', out)
        self.assertIn("<code>code</code>", out)

    def test_italic_does_not_eat_a_lone_asterisk_in_code(self):
        out = rmp.inline("*evidence to check*, then `receipts/PKT-*.json` stays put")
        self.assertIn("<em>evidence to check</em>", out)
        self.assertIn("<code>receipts/PKT-*.json</code>", out)

    def test_absolute_and_anchor_links_are_not_rootified(self):
        out = rmp.inline("[ext](https://example.com/x) [anchor](#world) [root](/already)")
        self.assertIn('href="https://example.com/x"', out)
        self.assertIn('href="#world"', out)
        self.assertIn('href="/already"', out)

    def test_html_is_escaped_before_tags_are_introduced(self):
        out = rmp.inline("a < b && `<id>` stays literal")
        self.assertIn("&lt; b", out)
        self.assertIn("<code>&lt;id&gt;</code>", out)


class BlockParseTests(unittest.TestCase):
    def test_leading_language_line_is_dropped(self):
        text = "\U0001F310 **English** · [Deutsch](PLUG-IN.de.md)\n\n# Title\n\nBody.\n"
        blocks = rmp.parse_blocks(text)
        self.assertEqual(blocks[0], ("h1", "Title"))

    def test_ordered_list_groups_wrapped_continuation_lines(self):
        text = "1. **First.** Some text\n   that wraps onto\n   a second line.\n2. **Second.** One line.\n"
        blocks = rmp.parse_blocks(text)
        self.assertEqual(blocks[0][0], "ol")
        self.assertEqual(len(blocks[0][1]), 2)
        self.assertIn("that wraps onto a second line", blocks[0][1][0])

    def test_blockquote_and_unordered_list(self):
        text = "> line one\n> line two\n\n- item one\n- item two\n"
        blocks = rmp.parse_blocks(text)
        self.assertEqual(blocks[0], ("blockquote", "line one line two"))
        self.assertEqual(blocks[1], ("ul", ["item one", "item two"]))


class RealFileTests(unittest.TestCase):
    """Exercise the parser against the real, current source files - not a
    synthetic fixture. Confirms the subset the parser covers matches what
    these three files actually use today."""

    def test_all_three_sources_parse_to_a_single_h1_and_are_non_empty(self):
        for page in rmp.PAGES:
            blocks = rmp.parse_blocks(page["src"].read_text(encoding="utf-8"))
            h1s = [b for b in blocks if b[0] == "h1"]
            self.assertEqual(len(h1s), 1, page["src"])
            self.assertGreater(len(blocks), 5, page["src"])

    def test_rendered_output_matches_what_is_committed(self):
        """If someone edits PLUG-IN*.md without re-running the generator,
        this fails - the committed HTML would silently drift from its
        source, exactly the class of bug this tool exists to prevent."""
        for page in rmp.PAGES:
            expected = rmp.render_page(page)
            actual = page["out"].read_text(encoding="utf-8")
            self.assertEqual(actual, expected,
                             f"{page['out']} is stale - run python tools/render_markdown_page.py")

    def test_no_leftover_markdown_syntax_in_rendered_output(self):
        """The whole point: no visitor should ever see a literal ** [ ] ` in
        the rendered page body."""
        import re
        for page in rmp.PAGES:
            body = rmp.blocks_to_html(rmp.parse_blocks(page["src"].read_text(encoding="utf-8")))
            self.assertNotRegex(body, r"\*\*[^<]", page["src"])
            self.assertNotRegex(body, r"(?<!href=)\[[^\]]+\]\(", page["src"])


if __name__ == "__main__":
    unittest.main()

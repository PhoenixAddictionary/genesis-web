"""genesis.live-tick.v1: classification signal, schema validity, idempotency."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import generate_live_tick as gen_live  # noqa: E402


class ClassifyTests(unittest.TestCase):
    def test_added_guest_receipt_is_gast(self):
        changed = [("A", "receipts/PKT-001.json"), ("M", "packets/PKT-001.json")]
        self.assertEqual(gen_live.classify(changed), "gast")

    def test_modified_receipt_is_not_gast(self):
        # only an ADD counts - a later edit to an already-counted receipt isn't a new arrival.
        changed = [("M", "receipts/PKT-001.json")]
        self.assertEqual(gen_live.classify(changed), "projekt")

    def test_unrelated_changes_are_projekt(self):
        changed = [("M", "index.html"), ("A", "packets/PKT-002.json")]
        self.assertEqual(gen_live.classify(changed), "projekt")

    def test_added_schema_file_is_not_a_receipt(self):
        changed = [("A", "receipts/schemas/genesis.receipt.v1.schema.json")]
        self.assertEqual(gen_live.classify(changed), "projekt")

    def test_no_changes_is_projekt(self):
        self.assertEqual(gen_live.classify([]), "projekt")


class TickShapeTests(unittest.TestCase):
    def test_valid_tick_has_no_errors(self):
        tick = gen_live.build_tick(
            commit="a" * 40, occurred_at="2026-09-17T10:00:00+02:00",
            klass="gast", generated_at="2026-09-17T12:00:00Z",
        )
        self.assertEqual(gen_live.validate_tick(tick), [])

    def test_bad_commit_and_class_and_dates_are_caught(self):
        tick = gen_live.build_tick(
            commit="not-a-hash", occurred_at="yesterday", klass="bahn", generated_at="also-not-a-date",
        )
        errors = gen_live.validate_tick(tick)
        joined = "\n".join(errors)
        self.assertIn("commit must be", joined)
        self.assertIn("class must be", joined)
        self.assertIn("occurredAt must be", joined)
        self.assertIn("generatedAt must be", joined)


class RepoIntegrationTests(unittest.TestCase):
    """Exercises the real git plumbing against a throwaway repo - no mocks."""

    def _git(self, repo: Path, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

    def _init_repo(self, repo: Path) -> None:
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "test@example.invalid")
        self._git(repo, "config", "user.name", "Test")

    def test_first_commit_has_no_parent_and_classifies_projekt(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            (repo / "README.md").write_text("hi", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-q", "-m", "root")
            head = self._git(repo, "rev-parse", "HEAD")
            gen_live.ROOT = repo  # point the module's subprocess cwd at the throwaway repo
            try:
                self.assertEqual(gen_live.changed_paths(head), [])
                self.assertEqual(gen_live.classify(gen_live.changed_paths(head)), "projekt")
            finally:
                gen_live.ROOT = ROOT

    def test_added_receipt_file_detected_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            (repo / "README.md").write_text("hi", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-q", "-m", "root")

            (repo / "receipts").mkdir()
            (repo / "receipts" / "PKT-001.json").write_text("{}", encoding="utf-8")
            self._git(repo, "add", "receipts/PKT-001.json")
            self._git(repo, "commit", "-q", "-m", "guest receipt")
            head = self._git(repo, "rev-parse", "HEAD")

            gen_live.ROOT = repo
            try:
                changed = gen_live.changed_paths(head)
                self.assertIn(("A", "receipts/PKT-001.json"), changed)
                self.assertEqual(gen_live.classify(changed), "gast")
            finally:
                gen_live.ROOT = ROOT

    def test_idempotent_skip_on_repeat_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            (repo / "README.md").write_text("hi", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-q", "-m", "root")
            head = self._git(repo, "rev-parse", "HEAD")

            live_path = repo / "spine" / "live.jsonl"
            live_path.parent.mkdir(parents=True)
            tick = gen_live.build_tick(head, "2026-09-17T10:00:00Z", "projekt", "2026-09-17T10:00:01Z")
            live_path.write_text(json.dumps(tick) + "\n", encoding="utf-8")

            gen_live.ROOT = repo
            gen_live.LIVE_PATH = live_path
            try:
                self.assertEqual(gen_live.last_tick_commit(), head)
            finally:
                gen_live.ROOT = ROOT
                gen_live.LIVE_PATH = ROOT / "spine" / "live.jsonl"


class CliTests(unittest.TestCase):
    def test_dry_run_on_real_repo_does_not_modify_live_jsonl(self):
        before = (ROOT / "spine" / "live.jsonl").read_bytes() if (ROOT / "spine" / "live.jsonl").exists() else None
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools/generate_live_tick.py"), "--dry-run"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        after = (ROOT / "spine" / "live.jsonl").read_bytes() if (ROOT / "spine" / "live.jsonl").exists() else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

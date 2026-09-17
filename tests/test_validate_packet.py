"""genesis.packet.v1 / genesis.receipt.v1: schema files and stdlib validator agree."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_packet import (  # noqa: E402
    PACKET_SCHEMA, RECEIPT_SCHEMA, check_index, validate_packet, validate_receipt,
)

REAL_PACKET = ROOT / "packets" / "PKT-001.json"
REAL_INDEX = ROOT / "packets" / "INDEX.json"


def good_packet() -> dict:
    return copy.deepcopy(json.loads(REAL_PACKET.read_text(encoding="utf-8")))


def good_receipt(packet: dict | None = None) -> dict:
    packet = packet or good_packet()
    return {
        "schema": "genesis.receipt.v1",
        "packetId": packet["id"],
        "branch": "maker/pkt-001",
        "headCommit": "a" * 40,
        "verifyCommand": packet["verifyCommand"],
        "verifierOutput": "5 passed in 0.12s",
        "verifierExitCode": 0,
        "actor": {"type": "guest", "id": "github/octocat"},
        "submittedAt": "2026-09-17T12:00:00Z",
    }


class PacketSchemaTests(unittest.TestCase):
    def test_schema_shape(self):
        self.assertEqual(PACKET_SCHEMA["properties"]["schema"]["const"], "genesis.packet.v1")
        self.assertEqual(set(PACKET_SCHEMA["required"]) <= set(PACKET_SCHEMA["properties"]), True)

    def test_real_packet_is_valid(self):
        self.assertEqual(validate_packet(good_packet()), [])

    def test_missing_and_unknown_keys(self):
        packet = good_packet()
        del packet["task"]
        packet["extra"] = 1
        errors = validate_packet(packet)
        joined = "\n".join(errors)
        self.assertIn("missing keys ['task']", joined)
        self.assertIn("unknown keys ['extra']", joined)

    def test_bad_id_status_commit(self):
        packet = good_packet()
        packet.update(id="PKT-1", status="DONE", baseCommit="not-a-hash")
        errors = validate_packet(packet)
        joined = "\n".join(errors)
        self.assertIn("id must match", joined)
        self.assertIn("status 'DONE'", joined)
        self.assertIn("baseCommit must be", joined)

    def test_empty_required_arrays_rejected(self):
        packet = good_packet()
        packet.update(verifyCommand=[], doneCriteria=[], boundaries=[])
        errors = validate_packet(packet)
        self.assertTrue(any("verifyCommand" in e for e in errors))
        self.assertTrue(any("doneCriteria" in e for e in errors))
        self.assertTrue(any("boundaries" in e for e in errors))

    def test_status_cross_field_rules(self):
        merged_no_receipt = good_packet()
        merged_no_receipt.update(status="MERGED", receiptId=None)
        errors = validate_packet(merged_no_receipt)
        self.assertTrue(any("requires a non-null receiptId" in e for e in errors))

        open_but_claimed = good_packet()
        open_but_claimed.update(status="OPEN", claimedBy="github/someone")
        errors = validate_packet(open_but_claimed)
        self.assertTrue(any("claimedBy and receiptId to both be null" in e for e in errors))

        merged_ok = good_packet()
        merged_ok.update(status="MERGED", receiptId="PKT-001")
        self.assertEqual(validate_packet(merged_ok), [])


class ReceiptSchemaTests(unittest.TestCase):
    def test_schema_shape(self):
        self.assertEqual(RECEIPT_SCHEMA["properties"]["schema"]["const"], "genesis.receipt.v1")

    def test_good_receipt_is_valid(self):
        self.assertEqual(validate_receipt(good_receipt()), [])

    def test_actor_must_be_guest_vendor_slash_handle(self):
        receipt = good_receipt()
        receipt["actor"] = {"type": "agent", "id": "not-vendor-slash-handle"}
        errors = validate_receipt(receipt)
        self.assertTrue(any("actor must be" in e for e in errors))

        receipt2 = good_receipt()
        receipt2["actor"] = {"type": "guest", "id": "no-slash-here"}
        errors2 = validate_receipt(receipt2)
        self.assertTrue(any("actor must be" in e for e in errors2))

    def test_verifier_output_and_exit_code_types(self):
        receipt = good_receipt()
        receipt["verifierOutput"] = 123
        receipt["verifierExitCode"] = "0"
        errors = validate_receipt(receipt)
        self.assertTrue(any("verifierOutput must be" in e for e in errors))
        self.assertTrue(any("verifierExitCode must be" in e for e in errors))

    def test_cross_check_against_packet(self):
        packet = good_packet()
        receipt = good_receipt(packet)
        receipt["verifyCommand"] = ["echo", "different"]
        errors = validate_receipt(receipt, packet=packet)
        self.assertTrue(any("must equal the referenced packet's verifyCommand" in e for e in errors))

        receipt2 = good_receipt(packet)
        receipt2["packetId"] = "PKT-999"
        errors2 = validate_receipt(receipt2, packet=packet)
        self.assertTrue(any("does not match packet id" in e for e in errors2))

    def test_evidence_refs(self):
        receipt = good_receipt()
        receipt["evidence"] = [{"id": "capture:1", "sha256": "not-hex", "path": None}]
        errors = validate_receipt(receipt)
        self.assertTrue(any("sha256 must be 64 lowercase" in e for e in errors))


class IndexTests(unittest.TestCase):
    def test_real_index_is_valid(self):
        report = check_index(REAL_INDEX)
        self.assertEqual(report["status"], "PASS", report)

    def test_missing_on_disk_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            packets_dir = Path(tmp)
            index_path = packets_dir / "INDEX.json"
            index_path.write_text(json.dumps({
                "schema": "genesis.packet-index.v1",
                "packets": [{"id": "PKT-999", "status": "OPEN", "path": "packets/PKT-999.json", "sha256": "0" * 64}],
            }), encoding="utf-8")
            report = check_index(index_path)
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("does not exist on disk" in e for e in report["errors"]))

    def test_hash_mismatch_and_status_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            packets_dir = Path(tmp)
            packet = good_packet()
            packet_path = packets_dir / "PKT-001.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            real_hash = hashlib.sha256(packet_path.read_bytes()).hexdigest()

            index_path = packets_dir / "INDEX.json"
            index_path.write_text(json.dumps({
                "schema": "genesis.packet-index.v1",
                "packets": [{"id": "PKT-001", "status": "SUBMITTED", "path": str(packet_path), "sha256": "f" * 64}],
            }), encoding="utf-8")
            report = check_index(index_path)
            self.assertEqual(report["status"], "FAIL")
            joined = "\n".join(report["errors"])
            self.assertIn("sha256 mismatch", joined)
            self.assertIn("does not match index status", joined)
            self.assertNotEqual(real_hash, "f" * 64)

    def test_orphan_packet_file_not_in_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            packets_dir = Path(tmp)
            packet = good_packet()
            (packets_dir / "PKT-001.json").write_text(json.dumps(packet), encoding="utf-8")
            orphan = good_packet()
            orphan["id"] = "PKT-002"
            (packets_dir / "PKT-002.json").write_text(json.dumps(orphan), encoding="utf-8")

            real_hash = hashlib.sha256((packets_dir / "PKT-001.json").read_bytes()).hexdigest()
            index_path = packets_dir / "INDEX.json"
            index_path.write_text(json.dumps({
                "schema": "genesis.packet-index.v1",
                "packets": [{"id": "PKT-001", "status": "OPEN", "path": str(packets_dir / "PKT-001.json"),
                            "sha256": real_hash}],
            }), encoding="utf-8")
            report = check_index(index_path)
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("orphan packet" in e for e in report["errors"]))


class CliTests(unittest.TestCase):
    def test_cli_exit_codes(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools/validate_packet.py"), str(REAL_PACKET)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        proc_index = subprocess.run(
            [sys.executable, str(ROOT / "tools/validate_packet.py"), "--check-index", str(REAL_INDEX)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc_index.returncode, 0, proc_index.stdout + proc_index.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad-packet.json"
            broken = good_packet()
            broken["status"] = "NOT_A_STATUS"
            bad.write_text(json.dumps(broken), encoding="utf-8")
            proc_bad = subprocess.run(
                [sys.executable, str(ROOT / "tools/validate_packet.py"), str(bad)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(proc_bad.returncode, 1, proc_bad.stdout + proc_bad.stderr)


if __name__ == "__main__":
    unittest.main()

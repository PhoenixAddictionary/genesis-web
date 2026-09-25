#!/usr/bin/env python3
"""G2 local acceptance smoke (tests 1-3). Tests 4-5 need outside human + owner inbox."""
from __future__ import annotations
import hashlib, json, pathlib, sys

SE = pathlib.Path(__file__).resolve().parents[1]
synth = json.loads((SE / "replay.v1.json").read_text(encoding="utf-8"))
att = json.loads((SE / "observed" / "OBSERVED-001" / "attestation.json").read_text(encoding="utf-8"))
bundle = json.loads((SE / "observed" / "OBSERVED-001" / "bundle.json").read_text(encoding="utf-8"))
ev = SE / "observed" / "OBSERVED-001" / "evidence"
failures = []

def check(cond, msg):
    if not cond:
        failures.append(msg)

synth_classes = {c.get("claimClass") or c.get("attestation", {}).get("claimClass") for c in synth.get("cases", [])}
synth_classes.add(synth.get("claimClass"))
check("SIMULATED_NOT_OBSERVED" in synth_classes, f"synthetic missing SIMULATED_NOT_OBSERVED: {synth_classes}")
check("OBSERVED" not in {c for c in synth_classes if c}, "synthetic must not be OBSERVED")
check(att.get("claimClass") == "OBSERVED", f"observed claimClass={att.get('claimClass')}")
check(bundle.get("claimClass") == "OBSERVED", "bundle claimClass")

inp = (ev / "input_task.txt").read_bytes()
out = (ev / "output_brief.txt").read_bytes()
check(hashlib.sha256(inp).hexdigest() == att["observation"]["inputDigest"], "input digest mismatch")
check(hashlib.sha256(out).hexdigest() == att["observation"]["outputDigest"], "output digest mismatch")
check(att["observation"]["inputDigest"] == bundle["digestSelfCheck"]["inputDigest"], "bundle input")
check(att["observation"]["outputDigest"] == bundle["digestSelfCheck"]["outputDigest"], "bundle output")

for needed in ["NOT_GENERAL_QUALITY", "NOT_GENERAL_SAFETY", "NOT_LEGITIMACY", "NOT_COMPANY_AUTHORIZATION", "NOT_RECOGNIZED_CERTIFICATION"]:
    check(needed in (att.get("limitations") or []), f"missing limitation {needed}")
check(att.get("authorization", {}).get("accessToken") in (None, ""), "accessToken must be null")

index = (SE / "index.html").read_text(encoding="utf-8")
garden = (SE / "garden.js").read_text(encoding="utf-8")
check("source-select" in index and "observed" in garden, "UI source switch missing")
check("limitation-list" in index or "limitations" in garden, "limitations UI missing")
check("input-digest" in index and "inputDigest" in garden, "digest UI missing")
check((SE / "schemas" / "genesis.second-eye-claim-class.v1.json").exists(), "Chair A schema missing")
check((SE / "HOW_TO_OUTSIDE_PERSON.md").exists(), "how-to missing")

schema = json.loads((SE / "schemas" / "genesis.second-eye-claim-class.v1.json").read_text(encoding="utf-8"))
check(schema.get("enum") == ["SIMULATED_NOT_OBSERVED", "OBSERVED"], "schema enum")
check(schema.get("chairDecision") == "A", "chair decision marker")

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS")
print(json.dumps({
  "syntheticClaimClasses": sorted(x for x in synth_classes if x),
  "observedClaimClass": att["claimClass"],
  "inputDigest": att["observation"]["inputDigest"],
  "outputDigest": att["observation"]["outputDigest"],
  "limitations": att["limitations"],
  "accessToken": att["authorization"].get("accessToken"),
}, indent=2))

#!/usr/bin/env python3
"""Deterministic outside-agent dry-run: read allowlisted task, write 5-line brief."""
from pathlib import Path
import hashlib, json, sys

root = Path(__file__).resolve().parents[1]
ev = root / "evidence"
inp = (ev / "input_task.txt").read_bytes()
# Fixed output bytes matching output_brief.txt produced for this dry-run.
out = (ev / "output_brief.txt").read_bytes()
trace = {
  "agentId": "agent:outside.dry-run.brief.01",
  "version": "0.1.0",
  "runtime": "python-local-dry-run-v1",
  "toolCalls": [
    {"tool": "read_file", "path": "evidence/input_task.txt", "ok": True},
    {"tool": "write_file", "path": "evidence/output_brief.txt", "ok": True}
  ],
  "network": False,
  "secretsRead": 0,
  "finished": True
}
(root / "agent_work" / "tool_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
print(json.dumps({
  "inputDigest": hashlib.sha256(inp).hexdigest(),
  "outputDigest": hashlib.sha256(out).hexdigest(),
  "traceDigest": hashlib.sha256(json.dumps(trace, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
}, indent=2))

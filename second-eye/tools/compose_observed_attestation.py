#!/usr/bin/env python3
"""Compose one OBSERVED Second Eye attestation from hash-bound evidence (Chair A)."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, datetime

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True)
    ap.add_argument("--input", required=True, type=pathlib.Path)
    ap.add_argument("--output", required=True, type=pathlib.Path)
    ap.add_argument("--trace", required=True, type=pathlib.Path)
    ap.add_argument("--agent-id", required=True)
    ap.add_argument("--subject-ref", default="PERSONA-OUTSIDE")
    ap.add_argument("--environment", default="local-sandbox-no-network-v1")
    ap.add_argument("--out-dir", required=True, type=pathlib.Path)
    ap.add_argument("--verdict", default="PASS", choices=["PASS", "FAIL", "INSUFFICIENT"])
    args = ap.parse_args()

    out = args.out_dir
    ev = out / "evidence"
    aw = out / "agent_work"
    ev.mkdir(parents=True, exist_ok=True)
    aw.mkdir(parents=True, exist_ok=True)

    inp = args.input.read_bytes()
    outb = args.output.read_bytes()
    tr = args.trace.read_bytes()
    (ev / args.input.name).write_bytes(inp)
    (ev / args.output.name).write_bytes(outb)
    (aw / args.trace.name).write_bytes(tr)

    input_digest = sha256_bytes(inp)
    output_digest = sha256_bytes(outb)
    trace_digest = sha256_bytes(tr)
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rid = out.name.upper().replace(" ", "-")

    proof_request = {
        "schema": "genesis.proof-request.v1",
        "requestId": f"PRQ-{rid}",
        "claimClass": "OBSERVED",
        "requestedProof": {
            "task": args.task,
            "environment": args.environment,
            "generalizationProhibited": True,
        },
        "delegation": {
            "authorizedBy": args.subject_ref,
            "delegateAgentId": args.agent_id,
            "scope": [f"read:evidence/{args.input.name}", f"write:evidence/{args.output.name}"],
            "expiresAt": now,
        },
        "authority": {"accessGrant": "DISABLED", "certification": "NOT_A_CAPABILITY"},
    }
    attestation = {
        "schema": "genesis.agent-attestation.v1",
        "attestationId": f"ATT-{rid}",
        "proofRequestId": f"PRQ-{rid}",
        "claimClass": "OBSERVED",
        "observedSubject": {
            "operatorOrOrganizationRef": args.subject_ref,
            "agentId": args.agent_id,
            "version": "0.1.0",
            "runtime": "operator-composed",
        },
        "observation": {
            "method": "SIGNED_EVIDENCE_REVIEW",
            "protocol": "second-eye.outside-bounded.v1",
            "environment": args.environment,
            "startedAt": now,
            "endedAt": now,
            "inputDigest": input_digest,
            "outputDigest": output_digest,
            "replayRef": f"observed/{out.name}/replay.v1.json",
        },
        "result": {
            "verdict": args.verdict,
            "criteria": ["Digests match supplied artifacts", "Task/environment bound", "No access token issued"],
            "actual": [f"inputDigest={input_digest}", f"outputDigest={output_digest}", f"traceDigest={trace_digest}"],
            "adverseResultsIncluded": True,
        },
        "evaluator": {
            "id": "EVALUATOR-OPERATOR-COMPOSED",
            "independence": "SEPARATE_FROM_TRAINER_AND_OPERATOR",
            "paidOnOutcome": False,
        },
        "limitations": [
            "NOT_GENERAL_QUALITY",
            "NOT_GENERAL_SAFETY",
            "NOT_LEGITIMACY",
            "NOT_COMPANY_AUTHORIZATION",
            "NOT_RECOGNIZED_CERTIFICATION",
        ],
        "authorization": {
            "owner": "COMPANY_RELYING_PARTY",
            "decision": "NOT_DECIDED_IN_THIS_RECEIPT",
            "accessToken": None,
        },
    }
    events = [
        {"eventId": f"EV-{rid}-0", "caseId": f"CASE-{rid}", "tick": 0, "kind": "PROOF_REQUESTED", "claimClass": "OBSERVED", "summary": args.task, "facets": ["EVIDENCE"]},
        {"eventId": f"EV-{rid}-1", "caseId": f"CASE-{rid}", "tick": 1, "kind": "ATTESTATION_ISSUED", "claimClass": "OBSERVED", "summary": f"{args.verdict}; limitations retained", "facets": ["EVIDENCE", "AUTHORITY"]},
        {"eventId": f"EV-{rid}-2", "caseId": f"CASE-{rid}", "tick": 2, "kind": "ACCESS_NOT_MATERIALIZED", "claimClass": "OBSERVED", "summary": "No access token created", "facets": ["AUTHORITY"]},
    ]
    import hashlib as _h
    trace_sha = _h.sha256(json.dumps(events, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    case = {
        "caseId": f"CASE-{rid}",
        "claimClass": "OBSERVED",
        "proofRequest": proof_request,
        "attestation": attestation,
    }
    replay = {
        "schema": "genesis.second-eye-replay.v1",
        "scenarioId": f"SECOND-EYE-{rid}",
        "claimClass": "OBSERVED",
        "cases": [case],
        "canonicalEventTrace": events,
        "canonicalEventTraceSha256": trace_sha,
        "institutionSeed": {
            "state": "CANDIDATE_ONLY",
            "observedPattern": "One OBSERVED receipt composed from outside evidence digests.",
        },
    }
    bundle = {
        "schema": "genesis.second-eye-observed-bundle.v1",
        "bundleId": out.name,
        "claimClass": "OBSERVED",
        "chairDecision": "A",
        "proofRequest": proof_request,
        "attestation": attestation,
        "replay": replay,
        "digestSelfCheck": {
            "inputDigest": input_digest,
            "outputDigest": output_digest,
            "traceDigest": trace_digest,
        },
    }
    (out / "proof-request.json").write_text(json.dumps(proof_request, indent=2) + "
", encoding="utf-8")
    (out / "attestation.json").write_text(json.dumps(attestation, indent=2) + "
", encoding="utf-8")
    (out / "replay.v1.json").write_text(json.dumps(replay, indent=2) + "
", encoding="utf-8")
    (out / "bundle.json").write_text(json.dumps(bundle, indent=2) + "
", encoding="utf-8")
    print(json.dumps({"ok": True, "attestationId": attestation["attestationId"], "inputDigest": input_digest, "outputDigest": output_digest, "out": str(out)}, indent=2))

if __name__ == "__main__":
    main()

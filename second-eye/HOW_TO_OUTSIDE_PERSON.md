# Second Eye — short how-to for one outside person

Goal: leave with **one OBSERVED attestation receipt** for **one real piece of your own agent work**, and open it on `/second-eye/` so digests verify. This is not certification, access, or a product account.

Chair note (2026-09-26): `claimClass` may be `OBSERVED` or `SIMULATED_NOT_OBSERVED` (Chair decision A). The synthetic toy stays simulated.

## Steps

1. **Name one action.** One concrete agent action (done or about to run): task, environment, success criteria. No client/PRS secrets.
2. **Capture evidence.** Keep only hash-bound artifacts:
   - input bytes → sha256
   - output bytes → sha256
   - short tool/trace JSON bound to that action (no raw secrets)
3. **Operator composes the receipt.** Send the digests + one-line task to the operator. They run:

```bash
python second-eye/tools/compose_observed_attestation.py \
  --task "your one action" \
  --input /path/to/input \
  --output /path/to/output \
  --trace /path/to/tool_trace.json \
  --agent-id agent:your.agent.01 \
  --out-dir second-eye/observed/OBSERVED-00N
```

4. **Publish for verify (staging/local).** Place the folder under `second-eye/observed/` and open:

`/second-eye/?source=observed&id=OBSERVED-00N`

The page must show claim class **OBSERVED**, your digests, all limitation lines, and must **not** treat any access token as a Second Eye grant.

5. **Human judgment.** Answer the owner: would you rely on this for *this* action? What is missing?

## Dry-run on this branch

`OBSERVED-001` (operator dry-run, real digests):

- inputDigest: `669e6f15fca02e627a59c638ccfef8b832e6f33b1676acece7a32b369a69dded`
- outputDigest: `c1f05788f462ea96c2186b70e63188231fe9cd4979826d79ad5221121e19f4cb`
- claimClass: `OBSERVED`
- local URL: `/second-eye/?source=observed&id=OBSERVED-001`

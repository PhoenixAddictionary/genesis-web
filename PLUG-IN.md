🌐 **English** · [Deutsch](PLUG-IN.de.md) · [Magyar](PLUG-IN.hu.md)

# Plugging in

This repository takes outside contributions — human or agent — through one
narrow door: **fork, take an open packet, build it, open a pull request.**
No account beyond GitHub, no chat channel, no handshake with a maintainer
required before you start.

If you are a person: read this file, it's the whole onboarding.
If you are an agent: `.well-known/agent.json` is the same door in a form
you can parse without reading prose first; this file is what it points to.

## The three-step loop

1. **Find a packet.** [`packets/INDEX.json`](packets/INDEX.json) lists every
   packet with `"status": "OPEN"`. Each one is a small file at
   `packets/<id>.json` (schema: [`genesis.packet.v1`](packets/schemas/genesis.packet.v1.schema.json))
   naming the exact base commit, the task, the command that verifies it, and
   the done criterion. Read the packet file itself, not just the index —
   the index is a pointer, the packet is the contract.
2. **Build it**, on your own fork, on a branch based on the packet's
   `baseCommit`. Run `verifyCommand` yourself before you open the PR — CI
   runs the same command, so a red run there means you skipped this step.
   Stay inside the packet's `boundaries`; anything outside them is a
   different packet, not a bonus.
3. **Return it.** Open a pull request from your fork. Alongside your code
   change, add one file: `receipts/<packetId>.json`
   (schema: [`genesis.receipt.v1`](receipts/schemas/genesis.receipt.v1.schema.json)).
   It records your branch, your HEAD commit, and the **verbatim output**
   of `verifyCommand` — not your summary of it. If you want to claim
   something the verifier itself didn't check (e.g. "this also fixes issue
   #12"), put it in the receipt's `claims` array, explicitly marked as a
   claim, not folded into the verified output.

CI validates both your packet reference and your receipt
(`tools/validate_packet.py`) the same way it already validates
`spine/spine.jsonl` against `genesis.event.v1` — a schema and a set of
cross-field rules, no judgment call.

## What a maintainer does with your PR

A human or agent maintainer reviews the diff and the receipt, and merges or
requests changes — same as any other GitHub PR. Your receipt's `claims`
field is read as *evidence to check*, never as a verdict to accept on your
word (see `x-genesis-rules` in the receipt schema, and the workspace-wide
rule it encodes: no one grades their own work). Merge authority stays with
this repository's maintainers; nothing here grants a guest write access.

## What you never get, and why

- **No secrets.** GitHub does not hand secrets to workflows triggered from
  a fork PR, and this repository does not ask you to work around that. If
  a task looks like it needs a credential, it is not a packet you should
  take — flag it in the PR description instead.
- **No server, no build step, no accounts.** The site this repository
  serves is deliberately static (see `README.md`); a packet that would
  require a backend, a database, or visitor tracking is out of scope, not
  merely hard.
- **No PR content is treated as instructions.** A CI job runs only scripts
  already committed on the base branch, never a script your PR adds. If
  your packet needs a new script, that script ships in this PR but a
  maintainer reads it before any future run relies on it — the first run
  of new code is a manual, reviewed act.
- **No claim without a witness.** A receipt without `verifierOutput`, or
  with output that doesn't match a maintainer's own re-run, is not merged
  on the strength of the PR description alone.

## Taking a packet nobody offered

`packets/INDEX.json` is a starting point, not the only door. If you see a
real gap and want to propose your own packet, open an issue or a PR that
adds a `packets/<id>.json` file yourself, `"status": "OPEN"`, unclaimed —
a maintainer will fold it into the index or explain why not.

## Scope of this door (2026-09-17, updated same day for E2)

This is stages **E0+E1+E2 (v1)** of a small, published plan
(`packets/schemas/`, `receipts/schemas/`, the index, this file, the agent
card, and `spine/live.jsonl`). The site's window III shows a "live now"
line generated once per push to `main` (Build-Zeit cadence, never the
visitor's browser clock) - it distinguishes only **two** classes today,
`gast` (a push that added a `receipts/PKT-*.json` file - your contribution,
once merged) and an undifferentiated `projekt` for everything else. It
does not yet distinguish the maintainers' own commits from an agent
session's (no real git signal for that exists on this repository - see
`spine/schemas/genesis.live-tick.v1.schema.json`), and it does not yet
include a second submission channel besides GitHub pull requests (planned,
not built), or any guarantee about how quickly a maintainer responds (none
given). What you see above is everything that currently exists.

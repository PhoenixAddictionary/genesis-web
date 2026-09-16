# spine.jsonl — a frozen, curated-only event set

This file is **not a live feed**. It is a hand-built, one-time snapshot of exactly
four `genesis.event.v1` records, written once and never appended to. `well.js`
only ever `fetch()`es it (same static-file pattern as `corpus.json`); the browser
never writes to it, never grows it, and never sends anything to it. A file that
"appended" a real visitor's question at runtime would be a fake spine — the
opposite of what this project's constitution requires (see `index.html` §M3a,
"no claim without a receipt"). Real visitor questions are **never** recorded,
hashed, or stored anywhere — see project rule P7 (non-ingestion): only these
four pre-selected, pre-verified curated probe questions have a real event
behind them.

## What each event is

Each of the four lines corresponds to exactly one curated probe question from
`probes/korpus-0.3.json`, replayed at freeze time against the real, unmodified
`well.js` engine (see `probes/receipt-korpus-0.3.json` for the actual-vs-expected
receipt this event set is built from: 10/10 probes matched, korpus 0.3, manifest
`409032026696…`). Nothing here is invented — every `receipts[].id` /
`receipts[].sha256` pair is copied from a real passage in `corpus.json`.

| Question (exact, case-insensitive match) | `eventId` | `eventType` |
|---|---|---|
| `what does the tao say about water?` | `EVT-WELL-PROBE-HIT-TAO-WATER-001` | `QUESTION_ANSWERED` |
| `what happens to the soul after death?` | `EVT-WELL-PROBE-HIT-UPANISHAD-SOUL-DEATH-001` | `QUESTION_ANSWERED` |
| `is the self eternal or does it return to dust?` | `EVT-WELL-PROBE-CONTESTED-SELF-DUST-001` | `QUESTION_ANSWERED` (contested — Owner ruling R2: both sourced positions shown, neither resolved) |
| `how do i configure a kubernetes cluster?` | `EVT-WELL-PROBE-NO-MATCH-KUBERNETES-001` | `QUESTION_ABSTAINED` (`NO_SOURCES`) |

## Validation

Validated against the real `genesis.event.v1.schema.json` (schema + cross-field
rules) from the `PhoenixAddictionary/memoria-mcp` repository's
`tools/validate_genesis_events.py`, at freeze time: **exit 0, zero errors**
against all four lines. This file is copied verbatim from that validated run —
`well.js` (and no other maker) must not regenerate, reorder, or edit a single
field of it. If the korpus or the engine ever changes such that a live result
no longer backs one of these four frozen events, `well.js`'s own
`resolveSpineMatch()` re-checks the live outcome on every submit and falls back
to the ordinary `CONCEPT` state rather than trusting this table blindly — see
that function's comments in `well.js`.

## Extending this set (for a future maker)

Do not hand-write a new line by guessing the schema. To add a fifth curated
event:

1. Pick one more curated, pre-verified probe question — one whose retrieval
   outcome against the current korpus is stable and already documented in
   `probes/korpus-0.3.json` / `probes/receipt-korpus-0.3.json` (or a fresh,
   equivalently-verified probe).
2. Build the event object using the SAME schema shape as the four lines above
   (`genesis.event.v1`), with real `receipts[]` entries copied from the actual
   `corpus.json` passages that answer it (id + full sha256 — never truncated,
   never invented).
3. Run it through `PhoenixAddictionary/memoria-mcp`'s
   `tools/validate_genesis_events.py` against `maker-handshake/schemas/genesis.event.v1.schema.json`
   and require exit 0 / zero errors before adding the line — the same bar this
   file was held to.
4. Append the validated line to `spine.jsonl` (never edit an existing line —
   this is a append-only, once-frozen file, same discipline as the crossing
   ledger described in `index.html` §B).
5. Add the question-to-eventId mapping to `well.js`'s `SPINE_QUESTION_MAP`, and
   add the matching live-outcome re-verification branch to `resolveSpineMatch()`
   (do not skip this step — a mapping entry without a live re-check is exactly
   the "trust the table blindly" failure mode this file's validation exists to
   prevent). If the new event adds a glyph to Window III's peek ring, also give
   it a fixed, non-colliding `{a, r}` position in `SPINE_GLYPH_POSITION`.
6. Extend `capture.py`'s spine-wiring checks for the new question — never
   remove or weaken an existing check when adding a new one.

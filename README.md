🌐 **English** · [Deutsch](README.de.md) · [Magyar](README.hu.md)

# GENESIS — the well

A question-first prototype: real primary-source retrieval over a small, frozen,
content-addressed corpus of public-domain philosophical/religious texts. No
generated prose — sources or an honest, typed refusal. No accounts, no
tracking, no visitor data stored or transmitted; questions are never sent
anywhere and never leave the browser.

Status: **prototype / engine v0**. This is not a finished product; framing,
positioning, and further build-out are ongoing.

## Run it

```bash
python3 -m http.server 8017
# open http://localhost:8017/
```

Any static file server works — plain HTML/CSS/JS, no build step, no
dependencies beyond Python 3 and a browser. `well.js` fetches `corpus.json`
from the same directory, so serve over HTTP (a `file://` URL blocks the
fetch; the page still renders and the engine emits its honest
`ENGINE_UNREACHABLE` abstention).

## What's here

| Path | Role |
|---|---|
| `index.html`, `styles.css`, `well.js` | The site: an empty terminal → three windows on a result (**I** sources, **II** engine, **III** a living peek of real project history) |
| `corpus.json` | korpus 0.4 — frozen, content-addressed: 358 passages, 5 public-domain sources (korpus 0.3, 293 passages / 4 sources, is preserved verbatim as `corpus-0.3.json`) |
| `corpus-src/*.txt` | The normalized source texts (Tao Te Ching/Legge; Isha+Katha+Mundaka+Kena+Prasna Upanishads/Müller; Bhagavad Gita/Arnold; KJV selections; the complete Book of Job/KJV), with provenance in each header |
| `build_corpus.py` | Re-freezes `corpus-src/` into `corpus.json` (bump the version for new content — a corpus is never mutated in place) |
| `probes/` | A frozen, curated probe set + a freeze-time script that runs retrieval against the real engine and writes a receipt (hit/miss per probe, bound to the corpus manifest hash) |
| `spine/` | A small set of curated questions wired to real, schema-validated events (`genesis.event.v1`) that appear in window III's peek — never real visitor questions, never anyone's actual input |
| `capture.py` | The verification harness: automated checks across normal / no-JS / reduced-motion, drives a real browser over CDP |
| `variant-a/b/c.html` | Three earlier visual-direction comparisons (kept for the record) |
| `tools/validate_genesis_events.py`, `maker-handshake/schemas/` | Vendored verbatim from `PhoenixAddictionary/memoria-mcp@81a79ce` (2026-09-16) — validates `spine/spine.jsonl` against the `genesis.event.v1` schema. Not modified; re-vendor from source on schema changes. |
| `PLUG-IN.md`, `.well-known/agent.json`, `AGENTS.md` | The contribution door for outside human or agent contributors: what's open, how to take it, how to return it. Start with `PLUG-IN.md`. |
| `packets/`, `receipts/`, `tools/validate_packet.py` | The packet/receipt contract behind that door (`genesis.packet.v1`, `genesis.receipt.v1`) — a bounded, hash-indexed unit of open work and the machine-checked proof-of-work returned for it. |
| `spine/live.jsonl`, `tools/generate_live_tick.py`, `.github/workflows/live-tick.yml` | Window III's "live now" line: one `genesis.live-tick.v1` record per push to `main` (Build-Zeit cadence — never the visitor's browser clock), classifying only `gast` (a push that added a guest receipt) vs. undifferentiated `projekt` — see `spine/schemas/genesis.live-tick.v1.schema.json` for why. |
| `LICENSE`, `LICENSING.md` | Three licenses for three kinds of content (code, corpus, generated output) — see `LICENSING.md` for which applies where. |
| `de/`, `hu/`, `robots.txt`, `sitemap.xml` | Localized copies of `index.html` (German, Hungarian) plus the hreflang scaffolding (`<link rel="alternate" hreflang="…">` on every version, self-referencing `<link rel="canonical">`, a sitemap carrying the same annotations). The retrieval engine itself stays English-only — it searches the English `corpus.json` regardless of page language, disclosed right at the input on the localized pages. `PLUG-IN.de.md`/`PLUG-IN.hu.md`, `README.de.md`/`README.hu.md`, `AGENTS.de.md`/`AGENTS.hu.md` cover the docs; each names the English original as authoritative on conflict. |

## Contributing

Outside contributions, human or agent, go through one door: see
[`PLUG-IN.md`](PLUG-IN.md). Machine-readable form: `.well-known/agent.json`.

## Principles

- **Sources or silence.** An answer is either grounded in a retrievable
  passage (shown with its excerpt, locator, and hash) or the engine says so
  honestly — never a composed, uncited reply.
- **No visitor data collected, stored, or transmitted.** Questions are
  processed entirely in the browser against the local corpus file.
- **Nothing on screen without a real mechanism behind it.** No fabricated
  activity, no invented numbers, no decorated emptiness.

## Verify

```bash
python3 capture.py   # expects the server on :8017; needs a local Chrome
```

CI (`.github/workflows/ci.yml`) runs on every push/PR: the vendored
`genesis.event.v1` validator (+ its own test suite) against `spine/spine.jsonl`,
the `genesis.live-tick.v1` validator (+ its own test suite) against
`spine/live.jsonl`, the `genesis.packet.v1`/`genesis.receipt.v1` validator
(+ its own test suite) against `packets/`, `receipts/`, and
`packets/INDEX.json`, and the real `capture.py` browser suite via headless
Chrome. `.github/workflows/live-tick.yml` runs separately, only on a push
to `main`, and appends the actual live-tick line (see the table above).

**Not wired, on purpose:** `verify_genesis_surface.py` and the zeuge witness/
claim-detect probe (`witness_receipt.py`), both from `memoria-mcp`. Checked
directly (2026-09-17) rather than assumed: both tools are built around a
Verbum checkout and `maker-handshake/packets/<order>/` work-order structure
that this static-site repo doesn't have, and `witness_receipt.py` additionally
needs the external `zeuge` binary, which isn't vendored or installable here.
Wiring them in anyway would produce a check that always reports absence or
doesn't apply — a fake green (or a fake red), not a real one. They become
relevant once this repo integrates with a live Verbum-backed engine (H3) or
gets its own work-order/packet flow.

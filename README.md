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
| `corpus.json` | korpus 0.3 — frozen, content-addressed: 293 passages, 4 public-domain sources |
| `corpus-src/*.txt` | The normalized source texts (Tao Te Ching/Legge; Isha+Katha+Mundaka Upanishads/Müller; Bhagavad Gita/Arnold; KJV selections), with provenance in each header |
| `build_corpus.py` | Re-freezes `corpus-src/` into `corpus.json` (bump the version for new content — a corpus is never mutated in place) |
| `probes/` | A frozen, curated probe set + a freeze-time script that runs retrieval against the real engine and writes a receipt (hit/miss per probe, bound to the corpus manifest hash) |
| `spine/` | A small set of curated questions wired to real, schema-validated events (`genesis.event.v1`) that appear in window III's peek — never real visitor questions, never anyone's actual input |
| `capture.py` | The verification harness: automated checks across normal / no-JS / reduced-motion, drives a real browser over CDP |
| `variant-a/b/c.html` | Three earlier visual-direction comparisons (kept for the record) |

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

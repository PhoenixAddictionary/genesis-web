---
cursor:
  subagentId: "bc-eff61e5f-eeb4-5e92-af88-dbe23510e145"
---

# GENESIS well prototype — how to run

Complete archived source of the standalone prototype (session of 2026-09-16). No build step, no dependencies beyond Python 3 and a browser.

## Serve

```bash
cd well-prototype-src
python3 -m http.server 8017
# open http://localhost:8017/
```

Any static file server works — the page is plain HTML/CSS/JS. The question engine (`well.js`) fetches `/corpus.json` from the site root, so serve the repository root over HTTP (opening `index.html` as a `file://` URL blocks the fetch; everything else still renders and the engine emits its honest ENGINE_UNREACHABLE abstention).

## What's here

| File | Role |
|---|---|
| `index.html`, `styles.css`, `well.js` | The site: empty terminal → **three-window first wiring** (I sources / II engine / III living picture) → shaft → zoomable world ring → boundary → message beats → constitution → hidden thing → zeros → instrument → void → water → casting → about → colophon. No-JS (form jumps to `#world`) and reduced-motion safe throughout. |
| `corpus.json` | korpus 0.4 — frozen, content-addressed: 358 passages, 5 public-domain sources. korpus 0.3 (293 passages, 4 sources, manifest sha256 `409032026696…`) is preserved verbatim as `corpus-0.3.json`. Live manifest sha256 `42f9311b3de0…` |
| `corpus-src/*.txt` | The normalized source texts (Tao Te Ching/Legge; Isha, Katha, Mundaka, Kena and Prasna Upanishads/Müller; Bhagavad Gita/Arnold; KJV selections; the complete Book of Job/KJV) with provenance URLs in each header |
| `build_corpus.py` | Re-freezes `corpus-src/` into `corpus.json` (bump `VERSION` for new content — a corpus is never mutated in place) |
| `capture.py` | Verification + media harness: 70 automated checks across normal / no-JS / reduced-motion, drives installed Chrome over raw CDP (needs `google-chrome` + `requests` + ffmpeg), records the journey/zoom/question clips |
| `variant-a/b/c.html` | The three world-redesign comparison pages (B was chosen and folded into the main build) |
| `shot_question.py` | Leftover one-off screenshot helper from v1 (safe to ignore) |

## Verify

```bash
google-chrome --headless=new --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-cdp --disable-gpu --hide-scrollbars \
  --window-size=1440,900 about:blank &
python3 capture.py   # expects the server on :8017
```

## Governing docs (in this store)

`docs/site-depth-map.md` (four-layer stack + spectacle queue) · `plans/verdrahtung-build-plan.md` (wire the three windows) · `docs/session-index.md` (full catalog for the next Claude) · `docs/dramaturgy-strategy.md` (ten beats) · `docs/engine-api-contract.md` (the engine contract this v0 implements in retrieve-mode) · `internal/well-prototype-build-report.md` (full build history and deferred items).

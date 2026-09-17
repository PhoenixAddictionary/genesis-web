# Licensing

This repository carries three licenses for three different kinds of content
(owner decision, 2026-09-17). A pull request touching more than one kind
should say so in its description.

| Content | License | Where |
|---|---|---|
| Code — `*.py`, `*.js`, `*.html`, `*.css`, `tools/`, `packets/schemas/`, `receipts/schemas/`, CI workflows | **Apache License 2.0** | [`LICENSE`](LICENSE) |
| Corpus source texts — `corpus-src/*.txt` and the frozen `corpus*.json` built from them | **Public domain** (each source text predates copyright or is an out-of-copyright translation; provenance is recorded in each file's own header) | headers in `corpus-src/*.txt`, `build_corpus.py` |
| Generated output — anything the engine or a probe run produces at query time (answers, receipts, capture screenshots), and this repository's own machine-readable artifacts (`spine/*.jsonl`, `packets/*.json`, `receipts/*.json`) | **CC0 1.0** (no rights reserved) | this file |

Nothing here changes the boundary already stated in [`README.md`](README.md):
no accounts, no tracking, no visitor data stored or transmitted. A license
governs reuse of what is *in* this repository; it says nothing about, and
grants no right to collect, data about people who visit the running site.

A contribution submitted through a packet (see [`PLUG-IN.md`](PLUG-IN.md))
is licensed under the same terms as the file it touches, by the act of
submitting a pull request — mirroring GitHub's own terms of service
(a fork accepts the upstream license by using it) rather than adding a
separate CLA.

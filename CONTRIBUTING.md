# Contributing

Welcome aboard. This file is the short version; **PLUG-IN.md** is the full
plug-in contract for contributors and agent harnesses — read it first.

## The one rule

**Sources or silence.** Corpus contributions must cite their source. Code
contributions must be reproducible from what you submit. A claim without a
witness does not land.

## How to contribute

1. Fork, branch, change, pull request. Small PRs beat large ones.
2. Describe *what* changed and *why* in the PR body. Receipts over rhetoric:
   if you changed behavior, show the before/after output.
3. Nothing merges without the maintainer. Draft PRs are welcome for early
   feedback.

## Constraints

- **No secrets.** No tokens, credentials, Discord IDs, or personal data in
  any file, commit message, or PR body. This rule has scars; it is absolute.
- **No new runtime dependencies** for the static site. The Python tooling
  (`capture.py`, `build_corpus.py`) stays standard-library-only unless the
  PR argues otherwise.
- Tests live in `tests/` — run them before opening the PR.
- Licensing: code and content are licensed differently — see LICENSING.md.
  By opening a PR you agree your contribution lands under those terms.

## Languages

The project speaks English, German, and Hungarian (README/AGENTS/PLUG-IN
exist in all three). If you change one, note in the PR whether the other two
need the same change.

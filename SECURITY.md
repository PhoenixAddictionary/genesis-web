# Security Policy

## Scope

This repository is a static site plus the corpus pipeline behind it
(`capture.py`, `build_corpus.py`, `corpus-src/` → `corpus.json`). There is no
server-side application and no user database. The realistic risks are:

- secrets, tokens, or personal data committed into the repo or the corpus,
- a malicious corpus contribution (a "source" that is not a source),
- dependency or build-pipeline issues in the Python tooling.

## Reporting

- Prefer GitHub's private vulnerability reporting (Security tab → Report a
  vulnerability) for anything sensitive.
- Otherwise open an issue **without** the sensitive detail (no secret values,
  no personal data) and say where the problem lives.
- If you find a committed secret, say so immediately and say which file — do
  not quote the secret itself.

There is no SLA. This is a community project; reports are read and answered
in the open unless they must stay private.

## Rules that already protect you

- Sources or silence: the corpus answers from its sources or not at all. A
  contribution that cannot cite its source does not land.
- No tokens, no credentials, no Discord IDs, no personal data in any file —
  the house has scars from this; the rule is absolute.

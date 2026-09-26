# G2 Claude Transferzettel v2 — local pass receipt

**When:** 2026-09-26 ~08:34–08:45 Europe/Zurich (CEST / UTC+2)
**Actor:** Chairman-Rep@Inofficial (Grok Bot executor) on IntelligenceSystem
**Worktree only:** `C:\Users\sirne\Desktop\Projekte\.claude\worktrees\g2-second-eye-smallest`
**Branch:** `claude/g2-second-eye-smallest`
**Parent tip (basis):** `fe14e5eed1e806ffc66bd1c1252af403994fe474` (`fe14e5e` — New Bot gap-fill)
**New SHA:** e5810a5ff4f7bf4befc0fb33f7c521425c19a1d5 (e5810a5) — tip after amend; commit blob may cite prior self-SHA
**Product thesis:** Artifact-in-view = still-readable filled OBSERVED receipt (not cubes/flicker hero; not brochure Value×3/FAQ).

Hard constraints honored: no prod deploy, no merge, no outreach, no mail, no outside share. Digests/tokens/claims only from OBSERVED-001. Claim classes remain OBSERVED | SIMULATED_NOT_OBSERVED. EN pitch + DE mirror kept. D3 public unfurl validate not run.

---

## A4 fold measure (Playwright headless Chromium, local http://127.0.0.1:8765/)

| Viewport | cardTop (px) | screensToCardTop | title in fold | PASS in fold | claimClass in fold | Loading/UNKNOWN above fold |
|----------|-------------:|-----------------:|:-------------:|:------------:|:------------------:|:--------------------------:|
| 1440×900 (desktop) | 543.2 | 0.604 | yes | yes | yes | none |
| 390×844 (mobile) | 678.9 | 0.804 | yes | yes | yes | none |

Source select is inside collapsed lab-panel details (not between pitch and receipt). Construction: hero/receipt padding compacted so card head (title + PASS + claimClass) lands in first desktop viewport by CSS, then remeasured.

---

## Build-order checklist

| ID | Item | Status |
|----|------|--------|
| A4 | Fold measure / card head in first desktop viewport | **PASS** (numbers above) |
| A5 | Source-select out from between pitch and receipt into lab details | **PASS** |
| Artifact-in-view | Remove/demote digest-cubes / flicker-build / building-observation chrome | **PASS** |
| E1 | Static HTML bake OBSERVED-001 fields; zero Loading/UNKNOWN above fold | **PASS** |
| A3 | garden.js error path uses LOAD_ERROR / Could not load receipt / — ; documented on receipt | **PASS** |
| A6 | CTA = Check this receipt; synthetic compare kept; no signup/waitlist/demo | **PASS** |
| Brochure rollback | Value×3 + FAQ removed; disqualifier, proof-strip, OG, try-one, OBSERVED default kept | **PASS** |
| OG | Tags kept; public unfurl not validated (D3 locked) | **PASS / locked** |
| Verify | python second-eye/tools/verify_g2_local.py | **PASS** |
| Commit | Branch only; no push (no upstream) | **PASS** |

### Observed bake (OBSERVED-001 only — not invented)

- attestationId: ATT-OBSERVED-001
- claimClass: OBSERVED
- result: PASS
- inputDigest: 669e6f15fca02e627a59c638ccfef8b832e6f33b1676acece7a32b369a69dded
- outputDigest: c1f05788f462ea96c2186b70e63188231fe9cd4979826d79ad5221121e19f4cb
- Authorized to: read:evidence/input_task.txt · write:evidence/output_brief.txt until 2026-09-26T01:00:00Z
- Was asked: Summarize Second Eye non-claims in exactly 5 bullet lines for a relying party.
- Verified by: EVALUATOR-OUTSIDE-INDEPENDENT-DRY-RUN · SEPARATE_FROM_TRAINER_AND_OPERATOR · outcome fee: no
- accessToken: null

---

## A / B / C / D / E (pass vs open)

| Lane | Status | Notes |
|------|--------|-------|
| A | **PASS** | fold / source demotion / load-error / CTA / claim visibility |
| B | **PASS** | brochure rollback; keep disqualifier/proof/OG/try-one/OBSERVED |
| C | **PASS** | claimClass OBSERVED or SIMULATED_NOT_OBSERVED only; load = LOAD_ERROR |
| D | **PASS / locked** | OG kept; D3 public unfurl not done |
| E | **PASS** | E1 static bake; foldHits empty |

---

## Explicit NOT DONE

- No prod deploy, no merge, no outreach/mail/outside share, no PR, no push
- No public OG unfurl (D3 locked)
- Outside-human acceptance 4–5 still Owner
- Visual-Maker OG polish optional
- M5 tip-land still Owner/integrator

## Blockers / next Owner eyes

- Owner eyes on local first viewport before any prod GO
- Branch has no upstream — push only on Owner request

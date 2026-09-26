# G2 Transferzettel v2 — First-Screen-Polish (lokal)

**Wann:** 2026-09-26 Europe/Zurich
**Owner GO:** Item 4 — Second Eye G2 first-screen polish
**Worktree:** `C:\Users\sirne\Desktop\Projekte\.claude\worktrees\g2-second-eye-smallest`
**Branch:** `claude/g2-second-eye-smallest`
**Tip before:** `fe14e5e` (Gap-fill nach `9690939`)
**Kein Prod-Deploy · kein Merge auf main**

## Kurz (Owner)

Lokaler Kandidat zeigt die **gefüllte OBSERVED-Quittung** als Hero (Artifact-in-View), nicht Lab-Cubes. Vier `Loading…` sind weg. Lab-Chrome (Source/Trace/Case/Ledger) steckt unter der Karte in einer zugeklappten Disclosure. Fehlerpfad malt **LOAD_ERROR / —**, nie claimClass `UNKNOWN`. CTA: **Check digests on this receipt**. OG-Tags + `og-second-eye.png` (1200×630) vorbereitet. `python second-eye/tools/verify_g2_local.py` → **PASS**.

Live `openpassage.org/second-eye/` bleibt Lab-Stub. Unfurl-Validierung gesperrt bis separates Owner-GO für Deploy.

## Entscheidungen

| Punkt | Entscheidung | Warum |
|---|---|---|
| A3 Fehlerpfad | `LOAD_ERROR` / `—` statt `UNKNOWN` | `UNKNOWN` ist keine Chair-A-Claim-Klasse |
| A6 CTA | `Check digests on this receipt` → `#digest-title` | Artefakt-Handlung auf Digest-Mechanik; kein Signup |
| A5 Lab | Source/Modes/Case/Ledger unter Karte in `<details>` | Opacity allein ist keine Demotion |
| Hero | Cubes/Flicker entfernt | Binding: Artifact-in-View |
| Brochure | Value×3 + FAQ entfernt | v2 Anti-Liste |
| D3 Unfurl | nicht gemacht | braucht öffentliche URL / Prod |

## A4 Fold-Messung

```json
{
  "desktop": {
    "viewport": "1440x900",
    "cardTop": 477.2,
    "screensToCardTop": 0.53,
    "headerInFold": true,
    "passInFold": true,
    "claimInFold": true,
    "cta": "Check digests on this receipt",
    "watermark": "OBSERVED",
    "foldHits": []
  },
  "mobile": {
    "viewport": "390x844",
    "cardTop": 435.6,
    "screensToCardTop": 0.516,
    "headerInFold": true,
    "passInFold": true,
    "claimInFold": true,
    "mobileWithin1_5": true,
    "cta": "Check digests on this receipt",
    "watermark": "OBSERVED",
    "foldHits": []
  }
}
```

PASS: Desktop Titel+PASS+claimClass im ersten Viewport; Mobil cardTop ≤ 1,5 Screens und Kartenkopf im Fold.

## Verify

- Falsch: `tools/verify_g2_local.py` am Repo-Root — fehlt
- Korrekt: `python second-eye/tools/verify_g2_local.py` → **PASS**

## Dateien geändert

- `second-eye/index.html`
- `second-eye/garden.js`
- `second-eye/garden.css`
- (OG-Bild bereits in `fe14e5e`)

## Blockiert

1. Prod-Deploy / Unfurl — separates GO
2. Merge auf main — separates GO
3. Owner-Frage A8 optional: führt EN oder DE? (Mobil blendet DE-Pitch aus Platzgründen)

## Explicit NOT CLAIMED

Kein Launch · kein Telemetry · kein Mail · keine Zertifikats-/Zugangssprache · Live-Seite nicht aktualisiert.

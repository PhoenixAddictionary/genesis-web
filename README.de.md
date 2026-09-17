🌐 [English](README.md) · **Deutsch** · [Magyar](README.hu.md)

> Diese Übersetzung ist informativ. Bei Widersprüchen gilt die englische Fassung
> ([`README.md`](README.md)) als massgeblich.

# GENESIS — der Brunnen

Ein frage-zuerst-Prototyp: echtes Primärquellen-Retrieval über einen kleinen,
eingefrorenen, inhaltsadressierten Korpus gemeinfreier philosophischer/religiöser
Texte. Keine generierte Prosa — Quellen oder eine ehrliche, typisierte Ablehnung.
Keine Konten, kein Tracking, keine gespeicherten oder übertragenen Besucherdaten;
Fragen werden nie irgendwohin gesendet und verlassen nie den Browser.

Status: **Prototyp / Engine v0**. Dies ist kein fertiges Produkt; Rahmung,
Positionierung und weiterer Ausbau sind im Gange.

## Ausführen

```bash
python3 -m http.server 8017
# öffne http://localhost:8017/
```

Jeder statische Dateiserver funktioniert — reines HTML/CSS/JS, kein Build-Schritt,
keine Abhängigkeiten ausser Python 3 und einem Browser. `well.js` lädt `corpus.json`
aus demselben Verzeichnis, also über HTTP servieren (eine `file://`-URL blockiert
den Fetch; die Seite rendert trotzdem, und die Engine gibt ihre ehrliche
`ENGINE_UNREACHABLE`-Ablehnung aus).

## Was hier ist

| Pfad | Rolle |
|---|---|
| `index.html`, `styles.css`, `well.js` | Die Seite: ein leeres Terminal → drei Fenster zu einem Ergebnis (**I** Quellen, **II** Engine, **III** ein lebender Blick auf echte Projektgeschichte) |
| `corpus.json` | korpus 0.4 — eingefroren, inhaltsadressiert: 358 Passagen, 5 gemeinfreie Quellen (korpus 0.3, 293 Passagen / 4 Quellen, bleibt wortwörtlich erhalten als `corpus-0.3.json`) |
| `corpus-src/*.txt` | Die normalisierten Quelltexte (Tao Te Ching/Legge; Isha+Katha+Mundaka+Kena+Prasna Upanishaden/Müller; Bhagavad Gita/Arnold; KJV-Auszüge; das vollständige Buch Hiob/KJV), mit Herkunftsangabe in jedem Header |
| `build_corpus.py` | Friert `corpus-src/` erneut zu `corpus.json` ein (Version bei neuem Inhalt erhöhen — ein Korpus wird nie an Ort und Stelle verändert) |
| `probes/` | Ein eingefrorenes, kuratiertes Proben-Set + ein Freeze-Zeit-Skript, das Retrieval gegen die echte Engine ausführt und ein Receipt schreibt (Treffer/Fehltreffer je Probe, an den Korpus-Manifest-Hash gebunden) |
| `spine/` | Eine kleine Menge kuratierter Fragen, verdrahtet mit echten, schema-validierten Ereignissen (`genesis.event.v1`), die im Blick von Fenster III erscheinen — nie echte Besucherfragen, nie irgendjemandes tatsächliche Eingabe |
| `capture.py` | Der Verifikations-Harness: automatisierte Prüfungen über normal / kein-JS / reduzierte Bewegung, steuert einen echten Browser über CDP |
| `variant-a/b/c.html` | Drei frühere visuelle Richtungsvergleiche (für die Aufzeichnung aufbewahrt) |
| `tools/validate_genesis_events.py`, `maker-handshake/schemas/` | Wortwörtlich übernommen aus `PhoenixAddictionary/memoria-mcp@81a79ce` (2026-09-16) — validiert `spine/spine.jsonl` gegen das `genesis.event.v1`-Schema. Nicht verändert; bei Schema-Änderungen erneut aus der Quelle übernehmen. |
| `PLUG-IN.md`, `.well-known/agent.json`, `AGENTS.md` | Die Beitrags-Tür für externe menschliche oder Agenten-Beitragende: was offen ist, wie man es nimmt, wie man es zurückgibt. Start bei `PLUG-IN.md`. |
| `packets/`, `receipts/`, `tools/validate_packet.py` | Der Paket-/Receipt-Vertrag hinter dieser Tür (`genesis.packet.v1`, `genesis.receipt.v1`) — eine begrenzte, hash-indexierte Einheit offener Arbeit und der maschinell geprüfte Arbeitsnachweis dafür. |
| `spine/live.jsonl`, `tools/generate_live_tick.py`, `.github/workflows/live-tick.yml` | Die „live now"-Zeile in Fenster III: ein `genesis.live-tick.v1`-Datensatz je Push auf `main` (Build-Zeit-Kadenz — nie die Uhr des Besucher-Browsers), der nur `gast` (ein Push, der einen Gast-Receipt hinzufügte) von undifferenziertem `projekt` unterscheidet — siehe `spine/schemas/genesis.live-tick.v1.schema.json` für den Grund. |
| `LICENSE`, `LICENSING.md` | Drei Lizenzen für drei Arten von Inhalt (Code, Korpus, generierte Ausgabe) — siehe `LICENSING.md`, welche wo gilt. |
| `de/`, `hu/`, `robots.txt`, `sitemap.xml` | Lokalisierte Kopien von `index.html` (Deutsch, Ungarisch) plus das Hreflang-Gerüst (`<link rel="alternate" hreflang="…">` auf jeder Version, selbstreferenzierendes `<link rel="canonical">`, eine Sitemap mit denselben Annotationen). Die Retrieval-Engine selbst bleibt nur-englisch — sie durchsucht das englische `corpus.json` unabhängig von der Seitensprache, direkt bei der Eingabe auf den lokalisierten Seiten offengelegt. `PLUG-IN.de.md`/`PLUG-IN.hu.md`, `README.de.md`/`README.hu.md`, `AGENTS.de.md`/`AGENTS.hu.md` decken die Docs ab; jede nennt das englische Original als massgeblich bei Widerspruch. |

## Mitwirken

Externe Beiträge, menschlich oder von Agenten, gehen durch eine Tür: siehe
[`PLUG-IN.md`](PLUG-IN.md). Maschinenlesbare Form: `.well-known/agent.json`.

## Prinzipien

- **Quellen oder Schweigen.** Eine Antwort ist entweder in einer abrufbaren
  Passage verankert (gezeigt mit Auszug, Fundstelle und Hash) oder die Engine
  sagt es ehrlich — nie eine komponierte, unbelegte Antwort.
- **Keine Besucherdaten gesammelt, gespeichert oder übertragen.** Fragen werden
  vollständig im Browser gegen die lokale Korpus-Datei verarbeitet.
- **Nichts auf dem Bildschirm ohne echten Mechanismus dahinter.** Keine
  vorgetäuschte Aktivität, keine erfundenen Zahlen, keine dekorierte Leere.

## Verifizieren

```bash
python3 capture.py   # erwartet den Server auf :8017; braucht ein lokales Chrome
```

CI (`.github/workflows/ci.yml`) läuft bei jedem Push/PR: der übernommene
`genesis.event.v1`-Validator (+ seine eigene Test-Suite) gegen `spine/spine.jsonl`,
der `genesis.live-tick.v1`-Validator (+ seine eigene Test-Suite) gegen
`spine/live.jsonl`, der `genesis.packet.v1`/`genesis.receipt.v1`-Validator
(+ seine eigene Test-Suite) gegen `packets/`, `receipts/` und
`packets/INDEX.json`, und die echte `capture.py`-Browser-Suite über headless
Chrome. `.github/workflows/live-tick.yml` läuft separat, nur bei einem Push
auf `main`, und hängt die eigentliche Live-Tick-Zeile an (siehe Tabelle oben).

**Absichtlich nicht verdrahtet:** `verify_genesis_surface.py` und die Zeuge-
Witness-/Claim-Detect-Probe (`witness_receipt.py`), beide aus `memoria-mcp`.
Direkt geprüft (2026-09-17), nicht angenommen: beide Werkzeuge sind um einen
Verbum-Checkout und die `maker-handshake/packets/<order>/`-Work-Order-Struktur
gebaut, die dieses statische Seiten-Repo nicht hat, und `witness_receipt.py`
braucht zusätzlich das externe `zeuge`-Binary, das hier nicht mitgeliefert oder
installierbar ist. Sie trotzdem zu verdrahten würde eine Prüfung erzeugen, die
immer Abwesenheit meldet oder nicht zutrifft — ein falsches Grün (oder Rot),
kein echtes. Sie werden relevant, sobald dieses Repo mit einer echten
Verbum-gestützten Engine integriert (H3) oder einen eigenen
Work-Order-/Paket-Fluss bekommt.

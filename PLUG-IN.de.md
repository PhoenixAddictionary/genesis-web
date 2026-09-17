🌐 [English](PLUG-IN.md) · **Deutsch** · [Magyar](PLUG-IN.hu.md)

> Diese Übersetzung ist informativ. Bei Widersprüchen gilt die englische Fassung
> ([`PLUG-IN.md`](PLUG-IN.md)) als massgeblich — insbesondere für Schema-Feldnamen,
> Dateipfade und Lizenztext, die hier unverändert (englisch) stehen bleiben.

# Einklinken

Dieses Repository nimmt Beiträge von aussen — Mensch oder Agent — durch eine
einzige, schmale Tür an: **forken, ein offenes Paket nehmen, bauen, einen Pull
Request öffnen.** Kein Konto ausser GitHub, kein Chat-Kanal, kein Handschlag mit
einem Maintainer vor dem Start nötig.

Wenn du ein Mensch bist: Diese Datei lesen, das ist das ganze Onboarding.
Wenn du ein Agent bist: [`.well-known/agent.json`](.well-known/agent.json) ist
dieselbe Tür in einer Form, die du ohne vorherigen Prosa-Text parsen kannst;
diese Datei ist das Ziel, auf das sie verweist.

## Die drei Schritte

1. **Ein Paket finden.** [`packets/INDEX.json`](packets/INDEX.json) listet jedes
   Paket mit `"status": "OPEN"`. Jedes ist eine kleine Datei unter
   `packets/<id>.json` (Schema: [`genesis.packet.v1`](packets/schemas/genesis.packet.v1.schema.json)),
   die den genauen Basis-Commit, die Aufgabe, den Befehl, der sie verifiziert,
   und das Fertig-Kriterium nennt. Lies die Paket-Datei selbst, nicht nur den
   Index — der Index ist ein Zeiger, das Paket ist der Vertrag.
2. **Bauen**, im eigenen Fork, auf einem Branch basierend auf dem
   `baseCommit` des Pakets. Führe `verifyCommand` selbst aus, bevor du den PR
   öffnest — CI führt denselben Befehl aus, ein roter Lauf dort bedeutet also,
   dass dieser Schritt übersprungen wurde. Bleib innerhalb der `boundaries`
   des Pakets; alles ausserhalb ist ein anderes Paket, kein Bonus.
3. **Zurückgeben.** Öffne einen Pull Request von deinem Fork. Füge neben
   deiner Code-Änderung eine Datei hinzu: `receipts/<packetId>.json`
   (Schema: [`genesis.receipt.v1`](receipts/schemas/genesis.receipt.v1.schema.json)).
   Sie hält deinen Branch, deinen HEAD-Commit und die **wortwörtliche
   Ausgabe** von `verifyCommand` fest — nicht deine Zusammenfassung davon.
   Willst du etwas behaupten, das der Verifier selbst nicht geprüft hat
   (z. B. „das behebt auch Issue #12"), gehört das ins `claims`-Feld des
   Receipts, ausdrücklich als Behauptung markiert, nicht in die verifizierte
   Ausgabe eingefaltet.

CI validiert sowohl deine Paket-Referenz als auch dein Receipt
(`tools/validate_packet.py`), genauso wie sie bereits `spine/spine.jsonl`
gegen `genesis.event.v1` validiert — ein Schema und feste Querfeld-Regeln,
keine Ermessensentscheidung.

## Was ein Maintainer mit deinem PR macht

Ein menschlicher oder Agent-Maintainer prüft den Diff und das Receipt und
merged oder fordert Änderungen an — wie bei jedem anderen GitHub-PR. Das
`claims`-Feld deines Receipts wird als *zu prüfende Evidenz* gelesen, nie als
auf dein Wort hin zu akzeptiertes Urteil (siehe `x-genesis-rules` im
Receipt-Schema und die Workspace-weite Regel, die es kodiert: niemand
bewertet die eigene Arbeit). Die Merge-Autorität bleibt bei den Maintainern
dieses Repositories; nichts hier gewährt einem Gast Schreibzugriff.

## Was du nie bekommst, und warum

- **Keine Geheimnisse.** GitHub gibt Workflows, die von einem Fork-PR
  ausgelöst werden, keine Secrets weiter, und dieses Repository verlangt
  keinen Workaround dafür. Sieht eine Aufgabe so aus, als bräuchte sie eine
  Anmeldeinformation, ist das kein Paket, das du nehmen solltest — markiere
  es stattdessen in der PR-Beschreibung.
- **Kein Server, kein Build-Schritt, keine Konten.** Die Seite, die dieses
  Repository ausliefert, ist absichtlich statisch (siehe `README.md`); ein
  Paket, das ein Backend, eine Datenbank oder Besucher-Tracking bräuchte,
  ist ausserhalb des Umfangs, nicht nur schwierig.
- **Kein PR-Inhalt wird als Anweisung behandelt.** Ein CI-Job führt nur
  bereits auf dem Basis-Branch committete Skripte aus, nie ein Skript, das
  dein PR hinzufügt. Braucht dein Paket ein neues Skript, wird es in diesem
  PR mitgeliefert, aber ein Maintainer liest es, bevor sich ein künftiger
  Lauf darauf verlässt — der erste Lauf von neuem Code ist ein manueller,
  geprüfter Akt.
- **Keine Behauptung ohne Zeugen.** Ein Receipt ohne `verifierOutput`, oder
  mit einer Ausgabe, die nicht mit dem eigenen Nachlauf eines Maintainers
  übereinstimmt, wird nicht allein auf Basis der PR-Beschreibung gemergt.

## Ein Paket nehmen, das niemand angeboten hat

`packets/INDEX.json` ist ein Ausgangspunkt, nicht die einzige Tür. Siehst du
eine echte Lücke und willst dein eigenes Paket vorschlagen, öffne ein Issue
oder einen PR, der selbst eine `packets/<id>.json`-Datei hinzufügt,
`"status": "OPEN"`, unbeansprucht — ein Maintainer nimmt es in den Index auf
oder erklärt, warum nicht.

## Umfang dieser Tür (Stand 2026-09-17, gleichentags für E2 aktualisiert)

Das sind die Stufen **E0+E1+E2 (v1)** eines kleinen, veröffentlichten Plans
(`packets/schemas/`, `receipts/schemas/`, der Index, diese Datei, die
Agentenkarte, und `spine/live.jsonl`). Fenster III der Seite zeigt eine
„live now"-Zeile, einmal je Push auf `main` generiert (Build-Zeit-Kadenz,
nie die Uhr des Besucher-Browsers) — sie unterscheidet heute nur **zwei**
Klassen: `gast` (ein Push, der eine `receipts/PKT-*.json`-Datei hinzufügte —
dein Beitrag, sobald gemergt) und ein undifferenziertes `projekt` für alles
andere. Sie unterscheidet noch nicht die Commits der Maintainer von denen
einer Agenten-Session (es gibt dafür kein echtes Git-Signal auf diesem
Repository — siehe `spine/schemas/genesis.live-tick.v1.schema.json`), und
es gibt noch keinen zweiten Einreichungskanal ausser GitHub Pull Requests
(geplant, nicht gebaut), und keine Zusage, wie schnell ein Maintainer
antwortet (keine gegeben). Was oben steht, ist alles, was derzeit existiert.
